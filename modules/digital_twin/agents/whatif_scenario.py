"""
Eminence HealthOS — What-If Scenario Agent (#64)
Layer 3 (Decisioning): Simulates hypothetical clinical scenarios such as medication
changes, lifestyle modifications, or treatment cessation, projecting outcomes over
30/60/90-day horizons with stochastic variation.
"""

from __future__ import annotations

import hashlib
import math
import random
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

# Effect profiles for common medication classes on key vitals
MEDICATION_EFFECTS: dict[str, dict[str, float]] = {
    "ace_inhibitor": {"bp_systolic": -12.0, "bp_diastolic": -6.0, "egfr": 2.0},
    "arb": {"bp_systolic": -10.0, "bp_diastolic": -5.5, "egfr": 1.5},
    "beta_blocker": {"bp_systolic": -8.0, "bp_diastolic": -4.0, "heart_rate": -10.0},
    "statin": {"cholesterol_ldl": -40.0, "hba1c": -0.1},
    "metformin": {"hba1c": -1.2, "bmi": -0.5},
    "sglt2_inhibitor": {"hba1c": -0.8, "bmi": -1.0, "bp_systolic": -4.0, "egfr": 1.0},
    "glp1_agonist": {"hba1c": -1.0, "bmi": -2.5, "bp_systolic": -3.0},
    "insulin": {"hba1c": -1.5, "bmi": 1.0},
    "diuretic": {"bp_systolic": -10.0, "bp_diastolic": -5.0},
    "calcium_channel_blocker": {"bp_systolic": -9.0, "bp_diastolic": -5.0, "heart_rate": -3.0},
}

# Lifestyle intervention effect profiles (per-month improvement rates)
LIFESTYLE_EFFECTS: dict[str, dict[str, float]] = {
    "regular_exercise": {
        "bp_systolic": -0.8, "bp_diastolic": -0.5, "bmi": -0.3,
        "hba1c": -0.05, "cholesterol_ldl": -1.5, "heart_rate": -0.5,
    },
    "diet_improvement": {
        "bp_systolic": -0.5, "bmi": -0.4, "hba1c": -0.08,
        "cholesterol_ldl": -2.0,
    },
    "smoking_cessation": {
        "bp_systolic": -1.0, "bp_diastolic": -0.5, "heart_rate": -1.0,
        "egfr": 0.3,
    },
    "weight_loss_program": {
        "bp_systolic": -1.2, "bp_diastolic": -0.7, "bmi": -0.6,
        "hba1c": -0.1, "cholesterol_ldl": -2.5,
    },
    "stress_reduction": {
        "bp_systolic": -0.4, "bp_diastolic": -0.3, "heart_rate": -0.8,
    },
    "sleep_optimization": {
        "bp_systolic": -0.3, "heart_rate": -0.4, "hba1c": -0.03,
    },
}

# Monthly deterioration rates when treatment is stopped
TREATMENT_STOP_DETERIORATION: dict[str, dict[str, float]] = {
    "antihypertensive": {"bp_systolic": 3.0, "bp_diastolic": 1.5},
    "statin": {"cholesterol_ldl": 8.0},
    "diabetes_medication": {"hba1c": 0.3, "bmi": 0.2},
    "heart_rate_control": {"heart_rate": 3.0, "bp_systolic": 1.5},
    "renal_protective": {"egfr": -1.5, "bp_systolic": 2.0},
}

PROJECTION_HORIZONS = [30, 60, 90]


class WhatIfScenarioAgent(BaseAgent):
    name = "whatif_scenario"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Simulates hypothetical clinical scenarios — medication changes, lifestyle "
        "modifications, or treatment cessation — and projects outcomes over 30/60/90 days"
    )
    min_confidence = 0.55

    async def process(self, input_data: AgentInput) -> AgentOutput:
        action = input_data.context.get("action", "simulate_medication_change")

        if action == "simulate_medication_change":
            return self._simulate_medication_change(input_data)
        elif action == "simulate_lifestyle_change":
            return self._simulate_lifestyle_change(input_data)
        elif action == "simulate_treatment_stop":
            return self._simulate_treatment_stop(input_data)
        elif action == "compare_scenarios":
            return self._compare_scenarios(input_data)
        elif action == "risk_impact":
            return self._risk_impact(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unsupported action '{action}' requested",
                status=AgentStatus.FAILED,
            )

    # ── simulate_medication_change ────────────────────────────────────────────

    def _simulate_medication_change(self, input_data: AgentInput) -> AgentOutput:
        """Model the effect of adding/removing/changing a medication on key vitals."""
        ctx = input_data.context
        scenario = ctx.get("scenario", {})
        baseline = ctx.get("baseline_vitals", {})

        medication_class = scenario.get("medication_class", "")
        change_type = scenario.get("change_type", "add")  # add, remove, switch
        dosage_factor = scenario.get("dosage_factor", 1.0)

        if not baseline:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No baseline vitals provided"},
                confidence=0.0,
                rationale="Cannot simulate without baseline vitals",
                status=AgentStatus.FAILED,
            )

        effects = MEDICATION_EFFECTS.get(medication_class, {})
        if not effects:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": f"Unknown medication class: {medication_class}",
                    "supported_classes": list(MEDICATION_EFFECTS.keys()),
                },
                confidence=0.0,
                rationale=f"No effect profile for medication class '{medication_class}'",
                status=AgentStatus.FAILED,
            )

        # Reverse effects when removing medication
        direction = -1.0 if change_type == "remove" else 1.0

        projections: list[dict[str, Any]] = []
        for days in PROJECTION_HORIZONS:
            months = days / 30.0
            # Effects ramp up over time following an exponential approach curve
            ramp = 1.0 - math.exp(-0.5 * months)
            projected: dict[str, Any] = {}
            for vital, base_val in baseline.items():
                if not isinstance(base_val, (int, float)):
                    projected[vital] = base_val
                    continue
                effect = effects.get(vital, 0.0) * direction * dosage_factor * ramp
                noise = random.gauss(0, abs(effect) * 0.1) if effect != 0 else 0
                projected[vital] = round(base_val + effect + noise, 2)

            projections.append({
                "day": days,
                "projected_vitals": projected,
                "effect_ramp": round(ramp, 3),
            })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "scenario_type": "medication_change",
                "medication_class": medication_class,
                "change_type": change_type,
                "dosage_factor": dosage_factor,
                "baseline_vitals": baseline,
                "projections": projections,
                "effect_profile": effects,
                "simulated_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.78,
            rationale=(
                f"Simulated {change_type} of {medication_class} over 90 days with "
                f"stochastic variation (dosage factor {dosage_factor})"
            ),
        )

    # ── simulate_lifestyle_change ─────────────────────────────────────────────

    def _simulate_lifestyle_change(self, input_data: AgentInput) -> AgentOutput:
        """Model exercise, diet, smoking cessation impacts on health metrics."""
        ctx = input_data.context
        scenario = ctx.get("scenario", {})
        baseline = ctx.get("baseline_vitals", {})

        interventions = scenario.get("interventions", [])
        adherence_rate = scenario.get("adherence_rate", 0.8)

        if not baseline:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No baseline vitals provided"},
                confidence=0.0,
                rationale="Cannot simulate without baseline vitals",
                status=AgentStatus.FAILED,
            )

        # Aggregate effects from all interventions
        combined_monthly_effects: dict[str, float] = {}
        applied_interventions: list[str] = []
        for intervention in interventions:
            effects = LIFESTYLE_EFFECTS.get(intervention, {})
            if effects:
                applied_interventions.append(intervention)
                for vital, monthly_delta in effects.items():
                    combined_monthly_effects[vital] = (
                        combined_monthly_effects.get(vital, 0.0) + monthly_delta
                    )

        projections: list[dict[str, Any]] = []
        for days in PROJECTION_HORIZONS:
            months = days / 30.0
            projected: dict[str, Any] = {}
            for vital, base_val in baseline.items():
                if not isinstance(base_val, (int, float)):
                    projected[vital] = base_val
                    continue
                monthly_effect = combined_monthly_effects.get(vital, 0.0)
                total_effect = monthly_effect * months * adherence_rate
                noise = random.gauss(0, abs(total_effect) * 0.15) if total_effect != 0 else 0
                projected[vital] = round(base_val + total_effect + noise, 2)

            projections.append({
                "day": days,
                "projected_vitals": projected,
                "cumulative_months": round(months, 1),
            })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "scenario_type": "lifestyle_change",
                "interventions": applied_interventions,
                "adherence_rate": adherence_rate,
                "baseline_vitals": baseline,
                "projections": projections,
                "monthly_effects": combined_monthly_effects,
                "simulated_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.72,
            rationale=(
                f"Simulated {len(applied_interventions)} lifestyle intervention(s) "
                f"at {adherence_rate:.0%} adherence over 90 days"
            ),
        )

    # ── simulate_treatment_stop ───────────────────────────────────────────────

    def _simulate_treatment_stop(self, input_data: AgentInput) -> AgentOutput:
        """Project deterioration curves if a patient stops a treatment."""
        ctx = input_data.context
        scenario = ctx.get("scenario", {})
        baseline = ctx.get("baseline_vitals", {})

        treatment_category = scenario.get("treatment_category", "")

        if not baseline:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No baseline vitals provided"},
                confidence=0.0,
                rationale="Cannot simulate without baseline vitals",
                status=AgentStatus.FAILED,
            )

        deterioration = TREATMENT_STOP_DETERIORATION.get(treatment_category, {})
        if not deterioration:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": f"Unknown treatment category: {treatment_category}",
                    "supported_categories": list(TREATMENT_STOP_DETERIORATION.keys()),
                },
                confidence=0.0,
                rationale=f"No deterioration profile for '{treatment_category}'",
                status=AgentStatus.FAILED,
            )

        projections: list[dict[str, Any]] = []
        for days in PROJECTION_HORIZONS:
            months = days / 30.0
            # Deterioration accelerates slightly over time
            accel = 1.0 + 0.1 * months
            projected: dict[str, Any] = {}
            for vital, base_val in baseline.items():
                if not isinstance(base_val, (int, float)):
                    projected[vital] = base_val
                    continue
                monthly_decay = deterioration.get(vital, 0.0)
                total_decay = monthly_decay * months * accel
                noise = random.gauss(0, abs(total_decay) * 0.1) if total_decay != 0 else 0
                projected[vital] = round(base_val + total_decay + noise, 2)

            projections.append({
                "day": days,
                "projected_vitals": projected,
                "deterioration_factor": round(accel, 2),
            })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "scenario_type": "treatment_stop",
                "treatment_category": treatment_category,
                "baseline_vitals": baseline,
                "projections": projections,
                "monthly_deterioration_rates": deterioration,
                "warning": (
                    "Stopping treatment may lead to significant clinical deterioration. "
                    "This simulation is for clinical decision support only."
                ),
                "simulated_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.74,
            rationale=(
                f"Simulated cessation of {treatment_category} treatment — "
                f"projected deterioration over 90 days with accelerating decay"
            ),
        )

    # ── compare_scenarios ─────────────────────────────────────────────────────

    def _compare_scenarios(self, input_data: AgentInput) -> AgentOutput:
        """Run multiple scenarios side by side and rank by projected outcome."""
        ctx = input_data.context
        scenarios = ctx.get("scenarios", [])
        baseline = ctx.get("baseline_vitals", {})
        ranking_metric = ctx.get("ranking_metric", "bp_systolic")

        if not scenarios:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No scenarios provided for comparison"},
                confidence=0.0,
                rationale="At least one scenario is required",
                status=AgentStatus.FAILED,
            )

        results: list[dict[str, Any]] = []
        for idx, scenario in enumerate(scenarios):
            scenario_type = scenario.get("type", "medication_change")
            scenario_input = AgentInput(
                trace_id=input_data.trace_id,
                org_id=input_data.org_id,
                patient_id=input_data.patient_id,
                trigger=input_data.trigger,
                context={
                    "action": f"simulate_{scenario_type}",
                    "scenario": scenario,
                    "baseline_vitals": baseline,
                },
            )

            if scenario_type == "medication_change":
                sim_output = self._simulate_medication_change(scenario_input)
            elif scenario_type == "lifestyle_change":
                sim_output = self._simulate_lifestyle_change(scenario_input)
            elif scenario_type == "treatment_stop":
                sim_output = self._simulate_treatment_stop(scenario_input)
            else:
                continue

            # Extract 90-day projection for ranking
            projections = sim_output.result.get("projections", [])
            day90 = projections[-1] if projections else {}
            metric_value = day90.get("projected_vitals", {}).get(ranking_metric)

            results.append({
                "scenario_index": idx,
                "scenario": scenario,
                "projections": projections,
                "day90_metric_value": metric_value,
                "label": scenario.get("label", f"Scenario {idx + 1}"),
            })

        # Rank: for vitals like bp_systolic lower is better; use absolute distance from optimal
        optimal_values = {"bp_systolic": 120, "bp_diastolic": 80, "hba1c": 5.4,
                          "cholesterol_ldl": 100, "bmi": 22, "heart_rate": 72, "egfr": 90}
        optimal = optimal_values.get(ranking_metric, 0)
        results.sort(
            key=lambda r: abs((r["day90_metric_value"] or 999) - optimal),
        )
        for rank, r in enumerate(results, 1):
            r["rank"] = rank

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "comparison_count": len(results),
                "ranking_metric": ranking_metric,
                "ranked_scenarios": results,
                "best_scenario": results[0]["label"] if results else None,
                "compared_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.76,
            rationale=(
                f"Compared {len(results)} scenarios ranked by {ranking_metric}; "
                f"best: {results[0]['label'] if results else 'N/A'}"
            ),
        )

    # ── risk_impact ───────────────────────────────────────────────────────────

    def _risk_impact(self, input_data: AgentInput) -> AgentOutput:
        """Estimate change in risk score from a proposed intervention."""
        ctx = input_data.context
        scenario = ctx.get("scenario", {})
        current_risk_score = ctx.get("current_risk_score", 0.5)
        baseline = ctx.get("baseline_vitals", {})

        intervention_type = scenario.get("intervention_type", "medication_change")
        medication_class = scenario.get("medication_class", "")
        interventions = scenario.get("interventions", [])

        # Calculate projected impact on risk
        risk_reduction = 0.0

        if intervention_type == "medication_change" and medication_class:
            effects = MEDICATION_EFFECTS.get(medication_class, {})
            for vital, effect in effects.items():
                # Each unit of improvement in critical vitals reduces risk
                if vital == "bp_systolic":
                    risk_reduction += abs(effect) * 0.003
                elif vital == "hba1c":
                    risk_reduction += abs(effect) * 0.05
                elif vital == "cholesterol_ldl":
                    risk_reduction += abs(effect) * 0.001
                elif vital == "egfr":
                    risk_reduction += abs(effect) * 0.002
                elif vital == "bmi":
                    risk_reduction += abs(effect) * 0.008

        elif intervention_type == "lifestyle_change":
            for intervention in interventions:
                effects = LIFESTYLE_EFFECTS.get(intervention, {})
                # Sum 3-month effect
                for vital, monthly_delta in effects.items():
                    cumulative = abs(monthly_delta) * 3
                    if vital == "bp_systolic":
                        risk_reduction += cumulative * 0.003
                    elif vital == "hba1c":
                        risk_reduction += cumulative * 0.05
                    elif vital == "cholesterol_ldl":
                        risk_reduction += cumulative * 0.001
                    elif vital == "bmi":
                        risk_reduction += cumulative * 0.008

        projected_risk = max(0.0, min(1.0, current_risk_score - risk_reduction))
        absolute_change = projected_risk - current_risk_score
        relative_change = (absolute_change / current_risk_score * 100) if current_risk_score > 0 else 0.0

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "current_risk_score": round(current_risk_score, 4),
                "projected_risk_score": round(projected_risk, 4),
                "absolute_risk_change": round(absolute_change, 4),
                "relative_risk_change_pct": round(relative_change, 2),
                "risk_reduction": round(risk_reduction, 4),
                "intervention_type": intervention_type,
                "scenario": scenario,
                "interpretation": (
                    "significant_improvement" if risk_reduction > 0.1
                    else "moderate_improvement" if risk_reduction > 0.05
                    else "mild_improvement" if risk_reduction > 0.01
                    else "minimal_impact"
                ),
                "assessed_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.70,
            rationale=(
                f"Risk impact assessment: {intervention_type} projected to change risk "
                f"from {current_risk_score:.2f} to {projected_risk:.2f} "
                f"({relative_change:+.1f}%)"
            ),
        )
