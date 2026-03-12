"""
Eminence HealthOS — Patient Digital Twin Agent (#63)
Layer 5 (Measurement): Maintains a living computational model of each patient's
health trajectory, integrating vitals, labs, conditions, and medications into a
unified digital twin representation.
"""

from __future__ import annotations

import hashlib
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

# Population baseline reference values for comparison
POPULATION_BASELINES: dict[str, dict[str, Any]] = {
    "heart_rate_baseline": {"mean": 72.0, "std": 8.0, "unit": "bpm"},
    "bp_systolic": {"mean": 120.0, "std": 12.0, "unit": "mmHg"},
    "bp_diastolic": {"mean": 80.0, "std": 8.0, "unit": "mmHg"},
    "bmi": {"mean": 25.0, "std": 4.0, "unit": "kg/m2"},
    "hba1c": {"mean": 5.4, "std": 0.5, "unit": "%"},
    "egfr": {"mean": 90.0, "std": 15.0, "unit": "mL/min/1.73m2"},
    "cholesterol_ldl": {"mean": 100.0, "std": 25.0, "unit": "mg/dL"},
}


class PatientDigitalTwinAgent(BaseAgent):
    name = "patient_digital_twin"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = (
        "Maintains a living computational model of each patient's health "
        "trajectory by integrating vitals, labs, conditions, and medications"
    )
    min_confidence = 0.6

    async def process(self, input_data: AgentInput) -> AgentOutput:
        action = input_data.context.get("action", "build_twin")

        if action == "build_twin":
            return self._build_twin(input_data)
        elif action == "update_twin":
            return self._update_twin(input_data)
        elif action == "get_state":
            return self._get_state(input_data)
        elif action == "health_timeline":
            return self._health_timeline(input_data)
        elif action == "compare_baseline":
            return self._compare_baseline(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unsupported action '{action}' requested",
                status=AgentStatus.FAILED,
            )

    # ── build_twin ───────────────────────────────────────────────────────────

    def _build_twin(self, input_data: AgentInput) -> AgentOutput:
        """Create a digital twin from patient data with physiological parameters."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or uuid.uuid4())

        vitals = ctx.get("vitals", {})
        conditions = ctx.get("conditions", [])
        medications = ctx.get("medications", [])
        risk_factors = ctx.get("risk_factors", [])
        demographics = ctx.get("demographics", {})

        physiological_params = {
            "heart_rate_baseline": vitals.get("heart_rate", 72.0),
            "bp_systolic": vitals.get("bp_systolic", 120.0),
            "bp_diastolic": vitals.get("bp_diastolic", 80.0),
            "bmi": vitals.get("bmi", 25.0),
            "hba1c": vitals.get("hba1c", 5.4),
            "egfr": vitals.get("egfr", 90.0),
            "cholesterol_ldl": vitals.get("cholesterol_ldl", 100.0),
        }

        overall_health_score = self._compute_health_score(
            physiological_params, conditions, risk_factors,
        )

        twin_id = hashlib.sha256(
            f"{patient_id}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]

        twin_state: dict[str, Any] = {
            "twin_id": twin_id,
            "patient_id": patient_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "physiological_parameters": physiological_params,
            "risk_factors": risk_factors,
            "active_conditions": conditions,
            "medications": medications,
            "demographics": demographics,
            "overall_health_score": round(overall_health_score, 4),
            "status": "active",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=twin_state,
            confidence=0.90,
            rationale=(
                f"Digital twin created for patient {patient_id} with "
                f"health score {overall_health_score:.2f}"
            ),
        )

    # ── update_twin ──────────────────────────────────────────────────────────

    def _update_twin(self, input_data: AgentInput) -> AgentOutput:
        """Integrate new observations into existing twin state."""
        ctx = input_data.context
        existing_state = ctx.get("twin_state", {})
        new_observations = ctx.get("observations", {})

        if not existing_state:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No existing twin state provided"},
                confidence=0.0,
                rationale="Cannot update twin without existing state",
                status=AgentStatus.FAILED,
            )

        params = dict(existing_state.get("physiological_parameters", {}))
        for key, value in new_observations.items():
            if key in params:
                params[key] = value

        conditions = ctx.get("conditions", existing_state.get("active_conditions", []))
        risk_factors = ctx.get("risk_factors", existing_state.get("risk_factors", []))
        medications = ctx.get("medications", existing_state.get("medications", []))

        overall_health_score = self._compute_health_score(params, conditions, risk_factors)

        updated_state: dict[str, Any] = {
            **existing_state,
            "physiological_parameters": params,
            "active_conditions": conditions,
            "risk_factors": risk_factors,
            "medications": medications,
            "overall_health_score": round(overall_health_score, 4),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "version": existing_state.get("version", 1) + 1,
            "last_observation_count": len(new_observations),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=updated_state,
            confidence=0.88,
            rationale=(
                f"Twin updated with {len(new_observations)} observations; "
                f"health score recalculated to {overall_health_score:.2f}"
            ),
        )

    # ── get_state ────────────────────────────────────────────────────────────

    def _get_state(self, input_data: AgentInput) -> AgentOutput:
        """Return current twin state snapshot."""
        ctx = input_data.context
        twin_state = ctx.get("twin_state", {})

        if not twin_state:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No twin state available", "exists": False},
                confidence=0.5,
                rationale="No digital twin found for this patient",
            )

        snapshot = {
            **twin_state,
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
            "exists": True,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=snapshot,
            confidence=0.95,
            rationale="Current twin state snapshot retrieved",
        )

    # ── health_timeline ──────────────────────────────────────────────────────

    def _health_timeline(self, input_data: AgentInput) -> AgentOutput:
        """Generate projected health timeline with monthly snapshots for 12 months."""
        ctx = input_data.context
        twin_state = ctx.get("twin_state", {})
        params = twin_state.get("physiological_parameters", {})
        months = ctx.get("months", 12)

        if not params:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No twin state with physiological parameters provided"},
                confidence=0.0,
                rationale="Cannot project timeline without baseline parameters",
                status=AgentStatus.FAILED,
            )

        # Compute monthly drift rates per parameter (annualized trends)
        drift_rates = self._estimate_drift_rates(ctx.get("trends", {}))

        snapshots: list[dict[str, Any]] = []
        for month in range(1, months + 1):
            projected: dict[str, float] = {}
            for param, baseline in params.items():
                if not isinstance(baseline, (int, float)):
                    continue
                drift = drift_rates.get(param, 0.0)
                projected[param] = round(baseline + (drift * month), 2)

            projected_score = self._compute_health_score(
                projected,
                twin_state.get("active_conditions", []),
                twin_state.get("risk_factors", []),
            )

            snapshots.append({
                "month": month,
                "projected_vitals": projected,
                "projected_health_score": round(projected_score, 4),
            })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_id": twin_state.get("patient_id"),
                "baseline_health_score": twin_state.get("overall_health_score"),
                "projection_months": months,
                "monthly_snapshots": snapshots,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.75,
            rationale=f"Health timeline projected for {months} months with gradual drift",
        )

    # ── compare_baseline ─────────────────────────────────────────────────────

    def _compare_baseline(self, input_data: AgentInput) -> AgentOutput:
        """Compare current twin state against population baselines."""
        ctx = input_data.context
        twin_state = ctx.get("twin_state", {})
        params = twin_state.get("physiological_parameters", {})

        if not params:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No twin state provided for comparison"},
                confidence=0.0,
                rationale="Cannot compare without physiological parameters",
                status=AgentStatus.FAILED,
            )

        deviations: list[dict[str, Any]] = []
        comparisons: dict[str, dict[str, Any]] = {}

        for param, value in params.items():
            if param not in POPULATION_BASELINES or not isinstance(value, (int, float)):
                continue
            baseline = POPULATION_BASELINES[param]
            mean = baseline["mean"]
            std = baseline["std"]
            z_score = (value - mean) / std if std > 0 else 0.0

            comparison: dict[str, Any] = {
                "patient_value": value,
                "population_mean": mean,
                "population_std": std,
                "z_score": round(z_score, 2),
                "unit": baseline["unit"],
                "status": "normal",
            }

            if abs(z_score) > 2.0:
                comparison["status"] = "significant_deviation"
                deviations.append({
                    "parameter": param,
                    "z_score": round(z_score, 2),
                    "patient_value": value,
                    "population_mean": mean,
                    "direction": "above" if z_score > 0 else "below",
                })
            elif abs(z_score) > 1.0:
                comparison["status"] = "mild_deviation"

            comparisons[param] = comparison

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_id": twin_state.get("patient_id"),
                "comparisons": comparisons,
                "significant_deviations": deviations,
                "deviation_count": len(deviations),
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.85,
            rationale=(
                f"Baseline comparison complete — "
                f"{len(deviations)} significant deviation(s) found"
            ),
        )

    # ── Internal Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_health_score(
        params: dict[str, Any],
        conditions: list[Any],
        risk_factors: list[Any],
    ) -> float:
        """
        Compute an overall health score (0-1) from physiological parameters,
        active conditions, and risk factors. Higher is healthier.
        """
        score = 1.0

        # Penalize deviations from optimal ranges
        penalties: dict[str, tuple[float, float, float]] = {
            # param: (optimal, max_deviation, weight)
            "heart_rate_baseline": (72.0, 40.0, 0.10),
            "bp_systolic": (120.0, 60.0, 0.15),
            "bp_diastolic": (80.0, 40.0, 0.10),
            "bmi": (22.0, 20.0, 0.10),
            "hba1c": (5.4, 4.0, 0.15),
            "egfr": (90.0, 60.0, 0.15),
            "cholesterol_ldl": (100.0, 100.0, 0.10),
        }

        for param, (optimal, max_dev, weight) in penalties.items():
            value = params.get(param)
            if value is None or not isinstance(value, (int, float)):
                continue
            deviation = abs(value - optimal) / max_dev
            score -= weight * min(1.0, deviation)

        # Penalize for active conditions
        condition_penalty = min(0.15, len(conditions) * 0.03)
        score -= condition_penalty

        # Penalize for risk factors
        risk_penalty = min(0.10, len(risk_factors) * 0.02)
        score -= risk_penalty

        return max(0.0, min(1.0, score))

    @staticmethod
    def _estimate_drift_rates(trends: dict[str, Any]) -> dict[str, float]:
        """
        Estimate monthly drift rates per parameter from historical trends.
        Falls back to small natural drift when no trend data is available.
        """
        default_drifts: dict[str, float] = {
            "heart_rate_baseline": 0.1,
            "bp_systolic": 0.2,
            "bp_diastolic": 0.1,
            "bmi": 0.05,
            "hba1c": 0.02,
            "egfr": -0.15,
            "cholesterol_ldl": 0.3,
        }

        drift_rates: dict[str, float] = {}
        for param, default in default_drifts.items():
            drift_rates[param] = trends.get(param, default)

        return drift_rates
