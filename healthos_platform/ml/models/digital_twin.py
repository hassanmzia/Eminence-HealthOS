"""
Patient Digital Twin -- physiological simulation using differential equations.

Implements compartmental ODE models for:
  - Glucose-Insulin dynamics (Bergman Minimal Model)
  - Blood pressure dynamics (Windkessel Model)
  - Medication pharmacokinetics (1-compartment PK model)
  - Renal function trajectory (CKD progression model)

Used for:
  - "What-if" therapy simulations (e.g., adding metformin 500mg twice daily)
  - Hypoglycemia risk prediction for insulin dose adjustments
  - BP response to antihypertensive dose changes
  - CKD progression trajectory under different interventions

Adapted for HealthOS (FastAPI + SQLAlchemy). Django ORM references have been
replaced with plain-dict / data-class patient interfaces so the simulation
engine is framework-agnostic.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.digital_twin")


# ------------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------------

@dataclass
class PatientPhysiologyParams:
    """
    Physiological parameters calibrated to an individual patient.
    These are estimated from longitudinal lab and vital observations.
    """
    # Bergman Minimal Model parameters (glucose-insulin dynamics)
    glucose_effectiveness: float = 0.028     # Sg -- insulin-independent glucose uptake [1/min]
    insulin_sensitivity: float = 0.00007     # Si -- insulin-mediated glucose uptake [L/(mU*min^2)]
    insulin_clearance: float = 0.025         # n -- insulin clearance rate [1/min]
    remote_insulin_factor: float = 0.020     # p2 -- rate of insulin action on remote compartment
    liver_glucose_production: float = 0.012  # Gb -- basal endogenous glucose production [mmol/min]
    basal_glucose: float = 5.5              # Gb -- basal plasma glucose [mmol/L]
    basal_insulin: float = 10.0             # Ib -- basal plasma insulin [mU/L]
    glucose_distribution_volume: float = 13.0  # Vg -- volume of glucose distribution [L]
    insulin_distribution_volume: float = 12.0  # Vi -- volume of insulin distribution [L]

    # Windkessel BP model parameters
    arterial_compliance: float = 1.2        # C -- arterial compliance [mL/mmHg]
    peripheral_resistance: float = 1.0     # R -- peripheral vascular resistance [mmHg*s/mL]
    cardiac_output: float = 5000.0         # Q -- cardiac output [mL/min]
    heart_rate: float = 70.0              # HR [bpm]

    # CKD progression parameters
    baseline_egfr: float = 75.0            # eGFR [mL/min/1.73m^2]
    egfr_decline_rate: float = -1.5        # Annual eGFR decline [mL/min/year]
    proteinuria_factor: float = 1.0        # Multiplier for proteinuria effect on CKD progression

    # PK parameters (representative, overridden per medication)
    default_half_life: float = 8.0         # Hours
    default_bioavailability: float = 0.85


@dataclass
class SimulationScenario:
    """
    A clinical scenario to simulate (e.g., medication change, lifestyle intervention).
    """
    name: str
    duration_hours: float = 24.0
    dt_minutes: float = 5.0               # Simulation time step

    # Meal events: list of (time_minutes, carb_grams)
    meals: List[Tuple[float, float]] = field(default_factory=list)

    # Insulin doses: list of (time_minutes, dose_units)
    insulin_boluses: List[Tuple[float, float]] = field(default_factory=list)

    # Continuous insulin rate [units/hour]
    basal_insulin_rate: float = 0.0

    # Oral medications: list of (time_minutes, drug_name, dose_mg)
    oral_medications: List[Tuple[float, str, float]] = field(default_factory=list)

    # Lifestyle factors
    exercise_start_min: Optional[float] = None
    exercise_duration_min: float = 30.0
    exercise_intensity: float = 0.5       # 0-1 (0=rest, 1=maximal)

    # BP interventions
    antihypertensive_dose_factor: float = 1.0  # Multiplier (1.0 = current dose)


@dataclass
class SimulationResult:
    """Results from running a digital twin simulation."""
    scenario_name: str
    time_points: List[float]              # Minutes from start
    glucose_trajectory: List[float]       # mmol/L
    insulin_trajectory: List[float]       # mU/L
    systolic_bp_trajectory: List[float]   # mmHg
    diastolic_bp_trajectory: List[float]  # mmHg
    drug_concentration: Dict[str, List[float]]  # Drug name -> plasma concentration

    # Summary statistics
    mean_glucose: float = 0.0
    glucose_cv: float = 0.0              # Coefficient of variation
    time_in_range_pct: float = 0.0      # % time 70-180 mg/dL
    hypoglycemia_events: int = 0         # Number of events <70 mg/dL
    hyperglycemia_events: int = 0        # Number of events >180 mg/dL
    mean_systolic_bp: float = 0.0
    mean_diastolic_bp: float = 0.0
    egfr_1year: float = 0.0
    egfr_5year: float = 0.0

    warnings: List[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Medication PK Database
# ------------------------------------------------------------------

MEDICATION_PK = {
    "metformin": {
        "half_life_hours": 6.5,
        "bioavailability": 0.55,
        "Vd_L_per_kg": 3.4,
        "glucose_lowering_effect": 0.85,
        "insulin_sensitizing": True,
    },
    "glipizide": {
        "half_life_hours": 3.0,
        "bioavailability": 0.95,
        "Vd_L_per_kg": 0.3,
        "insulin_secretagogue": True,
        "insulin_release_units_per_mg": 0.15,
    },
    "insulin_glargine": {
        "half_life_hours": 12.0,
        "bioavailability": 1.0,
        "Vd_L_per_kg": 0.15,
        "peak_hours": None,  # Peakless
        "duration_hours": 24.0,
    },
    "insulin_lispro": {
        "half_life_hours": 1.0,
        "bioavailability": 1.0,
        "Vd_L_per_kg": 0.15,
        "onset_min": 15,
        "peak_hours": 1.0,
        "duration_hours": 4.0,
    },
    "lisinopril": {
        "half_life_hours": 12.0,
        "bioavailability": 0.25,
        "Vd_L_per_kg": 1.0,
        "bp_reduction_systolic": -10.0,
        "bp_reduction_diastolic": -6.0,
        "renal_protective": True,
        "egfr_effect_per_year": +1.5,
    },
    "amlodipine": {
        "half_life_hours": 35.0,
        "bioavailability": 0.64,
        "Vd_L_per_kg": 21.0,
        "bp_reduction_systolic": -8.0,
        "bp_reduction_diastolic": -5.0,
    },
    "metoprolol": {
        "half_life_hours": 3.5,
        "bioavailability": 0.50,
        "Vd_L_per_kg": 5.6,
        "bp_reduction_systolic": -9.0,
        "bp_reduction_diastolic": -5.0,
        "hr_reduction_bpm": -12.0,
    },
    "atorvastatin": {
        "half_life_hours": 14.0,
        "bioavailability": 0.14,
        "Vd_L_per_kg": 381.0,
        "ldl_reduction_pct": -45.0,
    },
    "empagliflozin": {
        "half_life_hours": 12.4,
        "bioavailability": 0.78,
        "Vd_L_per_kg": 1.4,
        "glucose_lowering_effect": 0.70,
        "bp_reduction_systolic": -3.5,
        "bp_reduction_diastolic": -2.0,
        "egfr_effect_per_year": +2.0,
        "weight_loss_kg": -2.5,
    },
    "semaglutide": {
        "half_life_hours": 168.0,  # 7 days
        "bioavailability": 0.89,
        "Vd_L_per_kg": 0.12,
        "glucose_lowering_effect": 0.90,
        "weight_loss_kg": -5.0,
        "bp_reduction_systolic": -4.0,
        "insulin_release_boost": 0.30,
    },
}


# ------------------------------------------------------------------
# ODE Models
# ------------------------------------------------------------------

def bergman_minimal_model(
    state: np.ndarray,
    t: float,
    params: PatientPhysiologyParams,
    meal_rate: float,
    insulin_input: float,
    exercise_effect: float = 0.0,
) -> np.ndarray:
    """
    Bergman Minimal Model ODEs for glucose-insulin dynamics.

    State vector: [G, X, I]
        G -- plasma glucose [mmol/L]
        X -- remote insulin (interstitial compartment) [1/min]
        I -- plasma insulin [mU/L]

    Reference: Bergman RN et al. J Clin Invest. 1981;68(6):1456-1467.
    """
    G, X, I = state
    p = params

    dG = (
        -p.glucose_effectiveness * G
        - X * G
        + p.liver_glucose_production
        + meal_rate / p.glucose_distribution_volume
        - exercise_effect * G * 0.5
    )

    dX = (
        -p.remote_insulin_factor * X
        + p.insulin_sensitivity * (I - p.basal_insulin)
    )

    dI = (
        -p.insulin_clearance * (I - p.basal_insulin)
        + insulin_input / p.insulin_distribution_volume
    )

    return np.array([dG, dX, dI])


def windkessel_bp_model(
    state: np.ndarray,
    t: float,
    params: PatientPhysiologyParams,
    drug_bp_effect: float = 0.0,
) -> np.ndarray:
    """
    2-element Windkessel model for arterial blood pressure dynamics.

    State vector: [P_a] -- mean arterial pressure [mmHg]
    """
    P = state[0]
    p = params
    R_eff = p.peripheral_resistance * (1.0 + drug_bp_effect)
    dP = (p.cardiac_output / 60.0 - P / R_eff) / p.arterial_compliance
    return np.array([dP])


def ckd_progression_model(
    egfr: float,
    years: float,
    params: PatientPhysiologyParams,
    treatment_egfr_slope_modifier: float = 0.0,
) -> float:
    """
    Simple linear CKD progression model (Levey et al.).
    Returns projected eGFR [mL/min/1.73m^2].
    """
    annual_rate = params.egfr_decline_rate * params.proteinuria_factor + treatment_egfr_slope_modifier
    projected_egfr = egfr + annual_rate * years
    return max(projected_egfr, 0.0)


def one_compartment_pk(
    concentration: float,
    dose_rate: float,
    elimination_rate: float,
    volume: float,
) -> float:
    """
    1-compartment pharmacokinetic model ODE.
    dC/dt = (dose_rate / V) - k_el * C
    """
    return (dose_rate / volume) - elimination_rate * concentration


# ------------------------------------------------------------------
# RK4 ODE Solver
# ------------------------------------------------------------------

def rk4_step(
    f,
    state: np.ndarray,
    t: float,
    dt: float,
    **kwargs,
) -> np.ndarray:
    """4th-order Runge-Kutta integration step."""
    k1 = f(state, t, **kwargs)
    k2 = f(state + 0.5 * dt * k1, t + 0.5 * dt, **kwargs)
    k3 = f(state + 0.5 * dt * k2, t + 0.5 * dt, **kwargs)
    k4 = f(state + dt * k3, t + dt, **kwargs)
    return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


# ------------------------------------------------------------------
# Helper: observation accessor (replaces Django ORM queries)
# ------------------------------------------------------------------

def _get_observations(
    patient_data: Dict[str, Any],
    code: str,
    *,
    since: Optional[datetime] = None,
    order_desc: bool = True,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve observations from a patient data dict.

    Expected ``patient_data`` layout::

        {
            "fhir_id": "...",
            "age": 55,
            "gender": "male",
            "observations": [
                {"code": "2339-0", "value": 120.0, "effective_datetime": datetime(...)},
                ...
            ],
            "conditions": [...],
            "medication_requests": [...],
            ...
        }
    """
    obs_list = patient_data.get("observations", [])
    filtered = [o for o in obs_list if o.get("code") == code]
    if since is not None:
        filtered = [o for o in filtered if o.get("effective_datetime") and o["effective_datetime"] >= since]
    filtered.sort(key=lambda o: o.get("effective_datetime", datetime.min), reverse=order_desc)
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def _latest_obs_value(
    patient_data: Dict[str, Any],
    code: str,
    *,
    since: Optional[datetime] = None,
) -> Optional[float]:
    """Return the most recent observation value for a LOINC code, or None."""
    results = _get_observations(patient_data, code, since=since, limit=1)
    if results and results[0].get("value") is not None:
        return float(results[0]["value"])
    return None


# ------------------------------------------------------------------
# Patient Digital Twin
# ------------------------------------------------------------------

class PatientDigitalTwin:
    """
    Patient Digital Twin for physiological simulation.

    Workflow:
        1. Calibrate parameters from patient's longitudinal EHR data
        2. Run ODE simulation for a given clinical scenario
        3. Return time-series trajectories and clinical summaries
        4. Compare scenarios to guide therapy decisions

    ``patient_data`` should be a plain dict (or Pydantic model converted
    via ``.dict()``) containing observations, conditions, and medication
    requests -- no Django ORM dependency.

    Example usage::

        twin = PatientDigitalTwin(patient_data)
        twin.calibrate()

        baseline = twin.run_scenario(SimulationScenario(name="baseline"))

        new_scenario = SimulationScenario(name="add_empa")
        new_scenario.oral_medications = [(480, "empagliflozin", 10)]
        empa_result = twin.run_scenario(new_scenario)

        comparison = twin.compare_scenarios(baseline, empa_result)
    """

    def __init__(self, patient_data: Optional[Dict[str, Any]] = None):
        self.patient_data = patient_data
        self.params = PatientPhysiologyParams()
        self.version = "digital_twin_v1"
        self._calibrated = False

    def calibrate(self) -> bool:
        """
        Calibrate physiological parameters from patient EHR data.
        Returns True if calibration succeeded, False if insufficient data.
        """
        if self.patient_data is None:
            logger.warning("No patient data provided for calibration.")
            return False

        try:
            self._calibrate_glucose_params()
            self._calibrate_bp_params()
            self._calibrate_ckd_params()
            self._calibrated = True
            fhir_id = self.patient_data.get("fhir_id", "unknown")
            logger.info(f"Digital twin calibrated for patient {fhir_id}")
            return True
        except Exception as e:
            logger.error(f"Digital twin calibration failed: {e}")
            return False

    # -- Calibration helpers (use plain-dict accessors) ----------------

    def _calibrate_glucose_params(self):
        """Calibrate glucose-insulin model parameters from CGM and HbA1c data."""
        now = datetime.now(tz=timezone.utc)
        cutoff_90d = now - timedelta(days=90)

        glucose_obs = _get_observations(self.patient_data, "2339-0", since=cutoff_90d, order_desc=False)
        glucose_vals = [float(o["value"]) for o in glucose_obs if o.get("value") is not None]

        if glucose_vals:
            glucose_arr = np.array(glucose_vals)
            mean_glucose = np.mean(glucose_arr)
            self.params.basal_glucose = mean_glucose / 18.0
            glucose_cv = np.std(glucose_arr) / mean_glucose if mean_glucose > 0 else 0.15
            self.params.insulin_sensitivity = max(0.00002, 0.0001 - glucose_cv * 0.0001)

        hba1c_obs = _get_observations(self.patient_data, "4548-4", since=cutoff_90d, limit=1)
        if hba1c_obs and hba1c_obs[0].get("value") is not None:
            hba1c = float(hba1c_obs[0]["value"])
            eag_mgdl = 28.7 * hba1c - 46.7
            self.params.basal_glucose = eag_mgdl / 18.0
            self.params.insulin_sensitivity *= max(0.3, 1.0 - (hba1c - 5.7) * 0.08)
            self.params.liver_glucose_production *= min(2.0, 1.0 + (hba1c - 5.7) * 0.05)

    def _calibrate_bp_params(self):
        """Calibrate Windkessel BP parameters from recent BP readings."""
        now = datetime.now(tz=timezone.utc)
        cutoff_30d = now - timedelta(days=30)

        systolic_obs = _get_observations(self.patient_data, "8480-6", since=cutoff_30d, order_desc=False)
        systolic_vals = [float(o["value"]) for o in systolic_obs if o.get("value") is not None]

        if systolic_vals:
            sys_arr = np.array(systolic_vals)
            mean_systolic = np.mean(sys_arr)

            diastolic_obs = _get_observations(self.patient_data, "8462-4", since=cutoff_30d, order_desc=False)
            diastolic_vals = [float(o["value"]) for o in diastolic_obs if o.get("value") is not None]

            if diastolic_vals:
                dia_arr = np.array(diastolic_vals)
                mean_diastolic = np.mean(dia_arr)
                map_mmhg = mean_diastolic + (mean_systolic - mean_diastolic) / 3.0
                co_ml_per_sec = self.params.cardiac_output / 60.0
                self.params.peripheral_resistance = map_mmhg / co_ml_per_sec

        hr_obs = _get_observations(self.patient_data, "8867-4", since=cutoff_30d, order_desc=False)
        hr_vals = [float(o["value"]) for o in hr_obs if o.get("value") is not None]
        if hr_vals:
            self.params.heart_rate = float(np.mean(hr_vals))

    def _calibrate_ckd_params(self):
        """Calibrate CKD progression model from longitudinal eGFR data."""
        now = datetime.now(tz=timezone.utc)
        cutoff_2y = now - timedelta(days=730)

        egfr_obs = _get_observations(self.patient_data, "33914-3", since=cutoff_2y, order_desc=False)
        egfr_obs = [o for o in egfr_obs if o.get("value") is not None]

        if len(egfr_obs) >= 2:
            values = [float(o["value"]) for o in egfr_obs]
            times = [o["effective_datetime"] for o in egfr_obs]

            if len(values) >= 2:
                self.params.baseline_egfr = float(values[-1])
                days_elapsed = [(t - times[0]).days for t in times]
                if days_elapsed[-1] > 0:
                    slope_per_day = np.polyfit(days_elapsed, values, 1)[0]
                    self.params.egfr_decline_rate = slope_per_day * 365.0
        elif egfr_obs:
            self.params.baseline_egfr = float(egfr_obs[-1].get("value", 75.0))

        # Proteinuria (UACR)
        cutoff_90d = now - timedelta(days=90)
        uacr_obs = _get_observations(self.patient_data, "14959-1", since=cutoff_90d, limit=1)
        if uacr_obs and uacr_obs[0].get("value") is not None:
            uacr = float(uacr_obs[0]["value"])
            if uacr > 300:
                self.params.proteinuria_factor = 2.5
            elif uacr > 30:
                self.params.proteinuria_factor = 1.5

    # -- Simulation ----------------------------------------------------

    def run_scenario(self, scenario: SimulationScenario) -> SimulationResult:
        """
        Run a physiological simulation for a given clinical scenario.
        Uses RK4 numerical integration at the specified time step.
        Returns SimulationResult with full time-series trajectories.
        """
        if not self._calibrated:
            self.calibrate()

        dt = scenario.dt_minutes
        total_steps = int(scenario.duration_hours * 60 / dt)
        time_points = [i * dt for i in range(total_steps)]

        G0 = self.params.basal_glucose
        X0 = 0.0
        I0 = self.params.basal_insulin
        P0 = self.params.peripheral_resistance * (self.params.cardiac_output / 60.0)

        glucose_traj: List[float] = []
        insulin_traj: List[float] = []
        systolic_traj: List[float] = []
        diastolic_traj: List[float] = []
        drug_concentrations: Dict[str, List[float]] = {name: [] for name in MEDICATION_PK.keys()}

        glucose_state = np.array([G0, X0, I0])
        bp_state = np.array([P0])

        drug_states: Dict[str, float] = {}

        drug_elim_rates: Dict[str, float] = {}
        drug_volumes: Dict[str, float] = {}
        for drug_name, pk in MEDICATION_PK.items():
            t_half_min = pk["half_life_hours"] * 60.0
            drug_elim_rates[drug_name] = np.log(2) / t_half_min
            drug_volumes[drug_name] = pk.get("Vd_L_per_kg", 1.0) * 70.0

        for t_min, drug_name, dose_mg in scenario.oral_medications:
            if drug_name not in drug_states:
                drug_states[drug_name] = 0.0

        for t_min, drug_name, dose_mg in scenario.oral_medications:
            if drug_name in MEDICATION_PK:
                if drug_name not in drug_states:
                    drug_states[drug_name] = 0.0

        warnings: List[str] = []

        for step, t in enumerate(time_points):

            # -- Meal inputs --
            meal_rate_mmol_min = 0.0
            for meal_t, carb_g in scenario.meals:
                if abs(t - meal_t) < dt:
                    glucose_mmol = carb_g * 0.0556
                    meal_rate_mmol_min = glucose_mmol / 60.0

            # -- Insulin inputs --
            insulin_input_mU_min = scenario.basal_insulin_rate / 60.0
            for bolus_t, bolus_units in scenario.insulin_boluses:
                if abs(t - bolus_t) < dt:
                    insulin_input_mU_min += (bolus_units * 1000) / 5.0

            # -- Oral medication dosing and PK --
            for dose_t, drug_name, dose_mg in scenario.oral_medications:
                if abs(t - dose_t) < dt and drug_name in MEDICATION_PK:
                    pk = MEDICATION_PK[drug_name]
                    bioavailability = pk.get("bioavailability", 0.80)
                    absorbed_dose = dose_mg * bioavailability
                    volume = drug_volumes.get(drug_name, 70.0)
                    if drug_name not in drug_states:
                        drug_states[drug_name] = 0.0
                    drug_states[drug_name] += absorbed_dose / volume

            # -- Update drug concentrations (PK elimination) --
            for drug_name in list(drug_states.keys()):
                k_el = drug_elim_rates.get(drug_name, 0.001)
                dC = one_compartment_pk(
                    concentration=drug_states[drug_name],
                    dose_rate=0.0,
                    elimination_rate=k_el,
                    volume=drug_volumes.get(drug_name, 70.0),
                )
                drug_states[drug_name] = max(0.0, drug_states[drug_name] + dC * dt)
                if drug_name in drug_concentrations:
                    drug_concentrations[drug_name].append(drug_states[drug_name])

            # -- Compute drug effects --
            total_glucose_reduction = 1.0
            for drug_name, concentration in drug_states.items():
                pk = MEDICATION_PK.get(drug_name, {})
                if pk.get("insulin_secretagogue") and concentration > 0.01:
                    extra_insulin = pk.get("insulin_release_units_per_mg", 0.1) * concentration
                    insulin_input_mU_min += extra_insulin
                if pk.get("glucose_lowering_effect") and concentration > 0.01:
                    factor = pk["glucose_lowering_effect"] * min(concentration / 0.5, 1.0)
                    total_glucose_reduction *= (1.0 - factor * 0.3)

            # BP drug effects
            total_bp_resistance_change = 0.0
            for drug_name, concentration in drug_states.items():
                pk = MEDICATION_PK.get(drug_name, {})
                if pk.get("bp_reduction_systolic") and concentration > 0.01:
                    effect_fraction = min(concentration / 0.5, 1.0)
                    sbp_reduction = pk["bp_reduction_systolic"] * effect_fraction
                    co_per_sec = self.params.cardiac_output / 60.0
                    if co_per_sec > 0:
                        total_bp_resistance_change += sbp_reduction / co_per_sec / 3.0

            # -- Exercise effect --
            exercise_effect = 0.0
            if scenario.exercise_start_min is not None:
                exercise_end = scenario.exercise_start_min + scenario.exercise_duration_min
                if scenario.exercise_start_min <= t < exercise_end:
                    exercise_effect = scenario.exercise_intensity

            # -- Integrate glucose-insulin ODE (RK4) --
            glucose_state_new = rk4_step(
                bergman_minimal_model,
                glucose_state,
                t,
                dt,
                params=self.params,
                meal_rate=meal_rate_mmol_min,
                insulin_input=insulin_input_mU_min,
                exercise_effect=exercise_effect,
            )
            glucose_state_new[0] = np.clip(glucose_state_new[0], 1.0, 30.0)
            glucose_state_new[1] = np.clip(glucose_state_new[1], 0.0, 1.0)
            glucose_state_new[2] = np.clip(glucose_state_new[2], 0.0, 500.0)
            glucose_state = glucose_state_new

            # -- Integrate BP ODE (RK4) --
            bp_state = rk4_step(
                windkessel_bp_model,
                bp_state,
                t,
                dt,
                params=self.params,
                drug_bp_effect=total_bp_resistance_change,
            )
            bp_state[0] = np.clip(bp_state[0], 40.0, 250.0)

            # -- Record trajectories --
            glucose_mgdl = glucose_state[0] * 18.0
            glucose_traj.append(glucose_mgdl)
            insulin_traj.append(glucose_state[2])

            pulse_pressure = 40.0
            map_val = float(bp_state[0])
            systolic_traj.append(map_val + 2 * pulse_pressure / 3)
            diastolic_traj.append(map_val - pulse_pressure / 3)

        # Pad missing drug trajectories
        for drug_name in list(drug_concentrations.keys()):
            if len(drug_concentrations[drug_name]) < total_steps:
                drug_concentrations[drug_name] = [0.0] * total_steps

        # -- Compute summary statistics --
        glucose_arr = np.array(glucose_traj)
        mean_glucose = float(np.mean(glucose_arr))
        glucose_cv = float(np.std(glucose_arr) / mean_glucose) if mean_glucose > 0 else 0.0
        tir = float(np.sum((glucose_arr >= 70) & (glucose_arr <= 180)) / len(glucose_arr))
        hypo_events = int(np.sum(glucose_arr < 70))
        hyper_events = int(np.sum(glucose_arr > 250))

        systolic_arr = np.array(systolic_traj)
        mean_sbp = float(np.mean(systolic_arr))
        diastolic_arr = np.array(diastolic_traj)
        mean_dbp = float(np.mean(diastolic_arr))

        treatment_egfr_modifier = 0.0
        for drug_name in drug_states:
            pk = MEDICATION_PK.get(drug_name, {})
            treatment_egfr_modifier += pk.get("egfr_effect_per_year", 0.0)

        egfr_1year = ckd_progression_model(
            self.params.baseline_egfr, 1.0, self.params, treatment_egfr_modifier
        )
        egfr_5year = ckd_progression_model(
            self.params.baseline_egfr, 5.0, self.params, treatment_egfr_modifier
        )

        if hypo_events > 0:
            warnings.append(f"HYPOGLYCEMIA RISK: {hypo_events} time points below 70 mg/dL")
        if mean_glucose > 250:
            warnings.append(f"POOR GLYCEMIC CONTROL: Mean glucose {mean_glucose:.0f} mg/dL")
        if mean_sbp > 150:
            warnings.append(f"UNCONTROLLED HYPERTENSION: Mean SBP {mean_sbp:.0f} mmHg")
        if egfr_5year < 15:
            warnings.append(f"CKD PROGRESSION: Projected eGFR {egfr_5year:.0f} at 5 years (Stage 5)")
        elif egfr_5year < 30:
            warnings.append(f"CKD PROGRESSION: Projected eGFR {egfr_5year:.0f} at 5 years (Stage 4)")

        return SimulationResult(
            scenario_name=scenario.name,
            time_points=time_points,
            glucose_trajectory=glucose_traj,
            insulin_trajectory=insulin_traj,
            systolic_bp_trajectory=systolic_traj,
            diastolic_bp_trajectory=diastolic_traj,
            drug_concentration=drug_concentrations,
            mean_glucose=mean_glucose,
            glucose_cv=glucose_cv,
            time_in_range_pct=tir * 100.0,
            hypoglycemia_events=hypo_events,
            hyperglycemia_events=hyper_events,
            mean_systolic_bp=mean_sbp,
            mean_diastolic_bp=mean_dbp,
            egfr_1year=egfr_1year,
            egfr_5year=egfr_5year,
            warnings=warnings,
        )

    def compare_scenarios(
        self,
        baseline: SimulationResult,
        intervention: SimulationResult,
    ) -> Dict[str, Any]:
        """Compare two simulation scenarios and return delta metrics."""
        comparison = {
            "baseline_scenario": baseline.scenario_name,
            "intervention_scenario": intervention.scenario_name,
            "glucose_metrics": {
                "mean_glucose_change_mgdl": intervention.mean_glucose - baseline.mean_glucose,
                "tir_change_pct": intervention.time_in_range_pct - baseline.time_in_range_pct,
                "glucose_cv_change": intervention.glucose_cv - baseline.glucose_cv,
                "hypoglycemia_events_change": intervention.hypoglycemia_events - baseline.hypoglycemia_events,
            },
            "bp_metrics": {
                "systolic_change_mmhg": intervention.mean_systolic_bp - baseline.mean_systolic_bp,
                "diastolic_change_mmhg": intervention.mean_diastolic_bp - baseline.mean_diastolic_bp,
            },
            "renal_metrics": {
                "egfr_1year_change": intervention.egfr_1year - baseline.egfr_1year,
                "egfr_5year_change": intervention.egfr_5year - baseline.egfr_5year,
                "baseline_egfr_1year": baseline.egfr_1year,
                "baseline_egfr_5year": baseline.egfr_5year,
                "intervention_egfr_1year": intervention.egfr_1year,
                "intervention_egfr_5year": intervention.egfr_5year,
            },
            "intervention_warnings": intervention.warnings,
            "net_benefit": self._compute_net_benefit(baseline, intervention),
        }
        return comparison

    def _compute_net_benefit(
        self,
        baseline: SimulationResult,
        intervention: SimulationResult,
    ) -> Dict[str, Any]:
        """Compute a net clinical benefit score for an intervention."""
        glucose_benefit = (
            (baseline.mean_glucose - intervention.mean_glucose) / baseline.mean_glucose
            if baseline.mean_glucose > 0 else 0
        ) * 0.4

        tir_benefit = (
            (intervention.time_in_range_pct - baseline.time_in_range_pct) / 100.0
        ) * 0.3

        hypo_penalty = (
            max(0, intervention.hypoglycemia_events - baseline.hypoglycemia_events) / 288.0
        ) * -0.5

        bp_benefit = (
            max(0, baseline.mean_systolic_bp - intervention.mean_systolic_bp) / 20.0
        ) * 0.15

        renal_benefit = (
            max(0, intervention.egfr_5year - baseline.egfr_5year) / 15.0
        ) * 0.15

        net_score = float(np.clip(
            glucose_benefit + tir_benefit + hypo_penalty + bp_benefit + renal_benefit,
            -1.0, 1.0,
        ))

        return {
            "net_benefit_score": net_score,
            "recommendation": (
                "Intervention likely beneficial" if net_score > 0.1
                else "Intervention may increase risk" if net_score < -0.1
                else "Marginal benefit -- clinical judgment required"
            ),
            "components": {
                "glucose_benefit": round(glucose_benefit, 3),
                "tir_benefit": round(tir_benefit, 3),
                "hypo_penalty": round(hypo_penalty, 3),
                "bp_benefit": round(bp_benefit, 3),
                "renal_benefit": round(renal_benefit, 3),
            },
        }

    def simulate_medication_addition(
        self,
        drug_name: str,
        dose_mg: float,
        dosing_times_hours: Optional[List[float]] = None,
        duration_hours: float = 24.0,
    ) -> Dict:
        """
        Convenience method: simulate adding a new medication.

        Args:
            drug_name: Drug name (must be in MEDICATION_PK)
            dose_mg: Dose in mg
            dosing_times_hours: List of dosing times (default: [8.0] = 8am)
            duration_hours: Simulation duration in hours

        Returns:
            {baseline, intervention, comparison} dict.
        """
        if drug_name not in MEDICATION_PK:
            return {"error": f"Drug '{drug_name}' not in pharmacokinetics database"}

        if dosing_times_hours is None:
            dosing_times_hours = [8.0]

        baseline_scenario = SimulationScenario(
            name="current_therapy",
            duration_hours=duration_hours,
            meals=[
                (7 * 60, 60),
                (12 * 60, 75),
                (18 * 60, 70),
            ],
            basal_insulin_rate=self._get_current_basal_rate(),
        )

        dosing_events = [
            (int(h * 60), drug_name, dose_mg)
            for h in dosing_times_hours
        ]
        intervention_scenario = SimulationScenario(
            name=f"add_{drug_name}_{dose_mg}mg",
            duration_hours=duration_hours,
            meals=baseline_scenario.meals,
            basal_insulin_rate=baseline_scenario.basal_insulin_rate,
            oral_medications=dosing_events,
        )

        baseline_result = self.run_scenario(baseline_scenario)
        intervention_result = self.run_scenario(intervention_scenario)

        return {
            "baseline": {
                "mean_glucose_mgdl": round(baseline_result.mean_glucose, 1),
                "time_in_range_pct": round(baseline_result.time_in_range_pct, 1),
                "mean_systolic_bp": round(baseline_result.mean_systolic_bp, 1),
                "egfr_5year": round(baseline_result.egfr_5year, 1),
            },
            "intervention": {
                "mean_glucose_mgdl": round(intervention_result.mean_glucose, 1),
                "time_in_range_pct": round(intervention_result.time_in_range_pct, 1),
                "mean_systolic_bp": round(intervention_result.mean_systolic_bp, 1),
                "egfr_5year": round(intervention_result.egfr_5year, 1),
                "hypoglycemia_events": intervention_result.hypoglycemia_events,
                "warnings": intervention_result.warnings,
            },
            "comparison": self.compare_scenarios(baseline_result, intervention_result),
        }

    def _get_current_basal_rate(self) -> float:
        """Get current basal insulin rate from active medication requests."""
        if self.patient_data is None:
            return 0.0
        try:
            med_requests = self.patient_data.get("medication_requests", [])
            for rx in med_requests:
                if rx.get("status") != "active":
                    continue
                display = (rx.get("medication_display") or "").lower()
                if "glargine" not in display:
                    continue
                dosage = rx.get("dosage_instruction")
                if isinstance(dosage, list) and dosage:
                    dose = dosage[0].get("doseQuantity", {}).get("value", 0)
                    return float(dose) / 24.0
        except Exception:
            pass
        return 0.0

    def get_ckd_trajectory(self, years: int = 10) -> Dict:
        """
        Get CKD progression trajectory under current and optimized treatment.
        Returns projected eGFR by year under different scenarios.
        """
        if not self._calibrated:
            self.calibrate()

        current_trajectory = []
        for year in range(years + 1):
            egfr = ckd_progression_model(self.params.baseline_egfr, year, self.params, 0.0)
            current_trajectory.append({"year": year, "egfr": round(egfr, 1)})

        renal_protection_effect = (
            MEDICATION_PK["lisinopril"]["egfr_effect_per_year"] +
            MEDICATION_PK["empagliflozin"]["egfr_effect_per_year"]
        )
        optimized_trajectory = []
        for year in range(years + 1):
            egfr = ckd_progression_model(
                self.params.baseline_egfr, year, self.params, renal_protection_effect
            )
            optimized_trajectory.append({"year": year, "egfr": round(egfr, 1)})

        def ckd_stage(egfr):
            if egfr >= 90:
                return "G1"
            elif egfr >= 60:
                return "G2"
            elif egfr >= 45:
                return "G3a"
            elif egfr >= 30:
                return "G3b"
            elif egfr >= 15:
                return "G4"
            else:
                return "G5 (Kidney Failure)"

        current_5yr = current_trajectory[min(5, years)]["egfr"]
        current_10yr = current_trajectory[min(10, years)]["egfr"]
        optimized_5yr = optimized_trajectory[min(5, years)]["egfr"]
        optimized_10yr = optimized_trajectory[min(10, years)]["egfr"]

        return {
            "baseline_egfr": self.params.baseline_egfr,
            "annual_decline_rate": round(self.params.egfr_decline_rate, 2),
            "current_treatment_trajectory": current_trajectory,
            "optimized_treatment_trajectory": optimized_trajectory,
            "current_5yr_stage": ckd_stage(current_5yr),
            "current_10yr_stage": ckd_stage(current_10yr),
            "optimized_5yr_stage": ckd_stage(optimized_5yr),
            "optimized_10yr_stage": ckd_stage(optimized_10yr),
            "benefit_of_optimization": {
                "egfr_preserved_at_5yr": round(optimized_5yr - current_5yr, 1),
                "egfr_preserved_at_10yr": round(optimized_10yr - current_10yr, 1),
            },
        }
