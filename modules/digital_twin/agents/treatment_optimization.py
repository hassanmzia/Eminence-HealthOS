"""
Eminence HealthOS — Treatment Optimization Agent (#66)
Layer 3 (Decisioning): Simulates different care plans and recommends optimal
paths by ranking interventions, optimizing dosages, mapping care pathways,
and evaluating cost-effectiveness using QALY-based models.
"""

from __future__ import annotations

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
from healthos_platform.ml.llm.router import llm_router, LLMRequest

# Intervention catalog: efficacy scores, monthly cost, side-effect severity, adherence rate
INTERVENTION_CATALOG: dict[str, dict[str, Any]] = {
    "ace_inhibitor": {
        "category": "medication",
        "targets": ["hypertension", "ckd", "heart_failure"],
        "efficacy": 0.78,
        "monthly_cost": 25.0,
        "side_effect_score": 0.20,
        "typical_adherence": 0.82,
        "qaly_gain_annual": 0.06,
    },
    "arb": {
        "category": "medication",
        "targets": ["hypertension", "ckd"],
        "efficacy": 0.75,
        "monthly_cost": 35.0,
        "side_effect_score": 0.15,
        "typical_adherence": 0.85,
        "qaly_gain_annual": 0.055,
    },
    "statin": {
        "category": "medication",
        "targets": ["hyperlipidemia", "cardiovascular_risk"],
        "efficacy": 0.82,
        "monthly_cost": 15.0,
        "side_effect_score": 0.18,
        "typical_adherence": 0.80,
        "qaly_gain_annual": 0.07,
    },
    "metformin": {
        "category": "medication",
        "targets": ["diabetes", "prediabetes"],
        "efficacy": 0.80,
        "monthly_cost": 10.0,
        "side_effect_score": 0.22,
        "typical_adherence": 0.78,
        "qaly_gain_annual": 0.065,
    },
    "sglt2_inhibitor": {
        "category": "medication",
        "targets": ["diabetes", "heart_failure", "ckd"],
        "efficacy": 0.83,
        "monthly_cost": 350.0,
        "side_effect_score": 0.16,
        "typical_adherence": 0.80,
        "qaly_gain_annual": 0.08,
    },
    "glp1_agonist": {
        "category": "medication",
        "targets": ["diabetes", "obesity"],
        "efficacy": 0.85,
        "monthly_cost": 800.0,
        "side_effect_score": 0.25,
        "typical_adherence": 0.75,
        "qaly_gain_annual": 0.09,
    },
    "lifestyle_diet_exercise": {
        "category": "lifestyle",
        "targets": ["obesity", "diabetes", "hypertension", "hyperlipidemia"],
        "efficacy": 0.60,
        "monthly_cost": 50.0,
        "side_effect_score": 0.02,
        "typical_adherence": 0.45,
        "qaly_gain_annual": 0.04,
    },
    "cardiac_rehab": {
        "category": "program",
        "targets": ["heart_failure", "post_mi", "cardiovascular_risk"],
        "efficacy": 0.72,
        "monthly_cost": 200.0,
        "side_effect_score": 0.05,
        "typical_adherence": 0.55,
        "qaly_gain_annual": 0.06,
    },
    "rpm_monitoring": {
        "category": "program",
        "targets": ["hypertension", "diabetes", "heart_failure", "ckd"],
        "efficacy": 0.65,
        "monthly_cost": 120.0,
        "side_effect_score": 0.01,
        "typical_adherence": 0.70,
        "qaly_gain_annual": 0.035,
    },
    "behavioral_health": {
        "category": "program",
        "targets": ["depression", "anxiety", "substance_use"],
        "efficacy": 0.68,
        "monthly_cost": 180.0,
        "side_effect_score": 0.03,
        "typical_adherence": 0.50,
        "qaly_gain_annual": 0.05,
    },
}

# Pharmacokinetic dose-response parameters
DOSE_RESPONSE: dict[str, dict[str, float]] = {
    "ace_inhibitor": {"min_dose": 2.5, "max_dose": 40.0, "ec50": 10.0, "hill": 1.2},
    "arb": {"min_dose": 25.0, "max_dose": 320.0, "ec50": 80.0, "hill": 1.1},
    "statin": {"min_dose": 5.0, "max_dose": 80.0, "ec50": 20.0, "hill": 1.3},
    "metformin": {"min_dose": 500.0, "max_dose": 2550.0, "ec50": 1500.0, "hill": 1.0},
    "sglt2_inhibitor": {"min_dose": 5.0, "max_dose": 25.0, "ec50": 10.0, "hill": 1.4},
    "glp1_agonist": {"min_dose": 0.25, "max_dose": 2.0, "ec50": 1.0, "hill": 1.5},
    "beta_blocker": {"min_dose": 12.5, "max_dose": 200.0, "ec50": 50.0, "hill": 1.1},
}

# Standard QALY value for cost-effectiveness threshold (USD)
QALY_THRESHOLD = 50_000.0


class TreatmentOptimizationAgent(BaseAgent):
    name = "treatment_optimization"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Simulates different care plans and recommends optimal paths by ranking "
        "interventions, optimizing dosages, and evaluating cost-effectiveness"
    )
    min_confidence = 0.55

    async def process(self, input_data: AgentInput) -> AgentOutput:
        action = input_data.context.get("action", "optimize_plan")

        if action == "optimize_plan":
            return await self._optimize_plan(input_data)
        elif action == "rank_interventions":
            return self._rank_interventions(input_data)
        elif action == "dosage_optimization":
            return self._dosage_optimization(input_data)
        elif action == "care_pathway":
            return self._care_pathway(input_data)
        elif action == "cost_effectiveness":
            return self._cost_effectiveness(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unsupported action '{action}' requested",
                status=AgentStatus.FAILED,
            )

    # ── optimize_plan ─────────────────────────────────────────────────────────

    async def _optimize_plan(self, input_data: AgentInput) -> AgentOutput:
        """Generate top 3 optimized care plan alternatives with projected outcomes."""
        ctx = input_data.context
        current_medications = ctx.get("medications", [])
        conditions = ctx.get("conditions", [])
        current_vitals = ctx.get("current_vitals", {})
        preferences = ctx.get("preferences", {})

        if not conditions:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No conditions provided for care plan optimization"},
                confidence=0.0,
                rationale="Cannot optimize care plan without known conditions",
                status=AgentStatus.FAILED,
            )

        condition_set = {c.lower() for c in conditions}
        current_med_set = {m.lower() if isinstance(m, str) else m.get("name", "").lower()
                          for m in current_medications}

        # Score all applicable interventions
        candidates: list[dict[str, Any]] = []
        for name, profile in INTERVENTION_CATALOG.items():
            target_overlap = condition_set & {t.lower() for t in profile["targets"]}
            if not target_overlap:
                continue
            relevance = len(target_overlap) / len(condition_set)
            composite = (
                profile["efficacy"] * 0.35
                + (1 - profile["side_effect_score"]) * 0.20
                + profile["typical_adherence"] * 0.20
                + relevance * 0.15
                + (1 - min(1.0, profile["monthly_cost"] / 1000)) * 0.10
            )
            candidates.append({
                "intervention": name,
                "composite_score": round(composite, 4),
                "profile": profile,
                "relevance": round(relevance, 2),
                "already_prescribed": name in current_med_set,
            })

        candidates.sort(key=lambda c: c["composite_score"], reverse=True)

        # Build 3 plan alternatives
        plans: list[dict[str, Any]] = []
        plan_strategies = [
            ("optimal_efficacy", lambda c: c["profile"]["efficacy"], True),
            ("balanced", lambda c: c["composite_score"], True),
            ("cost_conscious", lambda c: -c["profile"]["monthly_cost"], True),
        ]

        for strategy_name, sort_key, _ in plan_strategies:
            sorted_candidates = sorted(candidates, key=sort_key, reverse=True)
            plan_interventions = []
            total_cost = 0.0
            total_qaly = 0.0
            for c in sorted_candidates[:5]:
                plan_interventions.append({
                    "intervention": c["intervention"],
                    "category": c["profile"]["category"],
                    "efficacy": c["profile"]["efficacy"],
                    "monthly_cost": c["profile"]["monthly_cost"],
                    "projected_adherence": c["profile"]["typical_adherence"],
                })
                total_cost += c["profile"]["monthly_cost"]
                total_qaly += c["profile"]["qaly_gain_annual"]

            plans.append({
                "strategy": strategy_name,
                "interventions": plan_interventions,
                "projected_monthly_cost": round(total_cost, 2),
                "projected_annual_qaly_gain": round(total_qaly, 4),
                "intervention_count": len(plan_interventions),
            })

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "conditions": conditions,
            "current_medications": current_medications,
            "plan_alternatives": plans,
            "candidate_count": len(candidates),
            "optimized_at": datetime.now(timezone.utc).isoformat(),
        }

        # --- LLM: generate optimization narrative ---
        try:
            prompt = (
                f"You are a clinical decision support specialist reviewing treatment optimization results.\n\n"
                f"Patient Conditions: {conditions}\n"
                f"Current Medications: {current_medications}\n"
                f"Current Vitals: {current_vitals}\n"
                f"Patient Preferences: {preferences}\n"
                f"Candidate Interventions Evaluated: {len(candidates)}\n"
                f"Plan Alternatives:\n"
            )
            for plan in plans:
                prompt += (
                    f"  - {plan['strategy']}: {plan['intervention_count']} interventions, "
                    f"${plan['projected_monthly_cost']}/mo, "
                    f"QALY gain {plan['projected_annual_qaly_gain']}/yr\n"
                )
            prompt += (
                f"\nProvide a concise clinical narrative explaining the treatment optimization "
                f"recommendations, comparing the three plan strategies, highlighting trade-offs "
                f"between efficacy, cost, and side-effect burden, and suggesting which plan "
                f"may be most appropriate given the patient's profile."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system="You are a clinical decision support AI that generates clear, evidence-based treatment optimization narratives.",
                temperature=0.3,
                max_tokens=1024,
            ))
            result["optimization_narrative"] = resp.content
        except Exception:
            result["optimization_narrative"] = (
                f"Treatment optimization generated 3 care plan alternatives from "
                f"{len(candidates)} candidate interventions targeting "
                f"{', '.join(conditions)}. Strategies include optimal efficacy, "
                f"balanced, and cost-conscious approaches."
            )

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.78,
            rationale=(
                f"Generated 3 care plan alternatives from {len(candidates)} candidate "
                f"interventions targeting {len(conditions)} condition(s)"
            ),
        )

    # ── rank_interventions ────────────────────────────────────────────────────

    def _rank_interventions(self, input_data: AgentInput) -> AgentOutput:
        """Score available interventions by efficacy, cost, side-effects, and adherence."""
        ctx = input_data.context
        conditions = ctx.get("conditions", [])
        weights = ctx.get("weights", {})
        patient_adherence = ctx.get("patient_adherence_factor", 1.0)

        w_efficacy = weights.get("efficacy", 0.35)
        w_cost = weights.get("cost", 0.15)
        w_side_effects = weights.get("side_effects", 0.20)
        w_adherence = weights.get("adherence", 0.30)

        condition_set = {c.lower() for c in conditions} if conditions else set()

        ranked: list[dict[str, Any]] = []
        for name, profile in INTERVENTION_CATALOG.items():
            target_overlap = condition_set & {t.lower() for t in profile["targets"]}
            if conditions and not target_overlap:
                continue

            adjusted_adherence = min(1.0, profile["typical_adherence"] * patient_adherence)
            cost_score = 1.0 - min(1.0, profile["monthly_cost"] / 1000)

            composite = (
                profile["efficacy"] * w_efficacy
                + cost_score * w_cost
                + (1 - profile["side_effect_score"]) * w_side_effects
                + adjusted_adherence * w_adherence
            )

            ranked.append({
                "intervention": name,
                "category": profile["category"],
                "composite_score": round(composite, 4),
                "efficacy_score": profile["efficacy"],
                "cost_score": round(cost_score, 3),
                "side_effect_score": profile["side_effect_score"],
                "adherence_score": round(adjusted_adherence, 3),
                "monthly_cost": profile["monthly_cost"],
                "targets": profile["targets"],
                "qaly_gain_annual": profile["qaly_gain_annual"],
            })

        ranked.sort(key=lambda r: r["composite_score"], reverse=True)
        for idx, item in enumerate(ranked, 1):
            item["rank"] = idx

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "ranked_interventions": ranked,
                "total_evaluated": len(ranked),
                "scoring_weights": {
                    "efficacy": w_efficacy,
                    "cost": w_cost,
                    "side_effects": w_side_effects,
                    "adherence": w_adherence,
                },
                "ranked_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.82,
            rationale=(
                f"Ranked {len(ranked)} interventions by composite score "
                f"(efficacy={w_efficacy}, cost={w_cost}, side_effects={w_side_effects}, "
                f"adherence={w_adherence})"
            ),
        )

    # ── dosage_optimization ───────────────────────────────────────────────────

    def _dosage_optimization(self, input_data: AgentInput) -> AgentOutput:
        """Suggest dosage adjustments based on response data and pharmacokinetic models."""
        ctx = input_data.context
        medication = ctx.get("medication", "")
        current_dose = ctx.get("current_dose", 0.0)
        response_data = ctx.get("response_data", {})
        target_response = ctx.get("target_response", 0.8)

        if not medication or medication not in DOSE_RESPONSE:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": f"No pharmacokinetic model for medication: {medication}",
                    "supported_medications": list(DOSE_RESPONSE.keys()),
                },
                confidence=0.0,
                rationale=f"No dose-response model available for '{medication}'",
                status=AgentStatus.FAILED,
            )

        pk = DOSE_RESPONSE[medication]
        min_dose = pk["min_dose"]
        max_dose = pk["max_dose"]
        ec50 = pk["ec50"]
        hill = pk["hill"]

        # Current response using Hill equation: E = D^n / (EC50^n + D^n)
        current_response = self._hill_response(current_dose, ec50, hill) if current_dose > 0 else 0.0
        observed_response = response_data.get("observed_efficacy", current_response)

        # Find optimal dose to achieve target response
        # Invert Hill equation: D = EC50 * (target / (1 - target))^(1/n)
        if target_response >= 1.0:
            optimal_dose = max_dose
        elif target_response <= 0.0:
            optimal_dose = min_dose
        else:
            ratio = target_response / (1.0 - target_response)
            optimal_dose = ec50 * (ratio ** (1.0 / hill))

        optimal_dose = max(min_dose, min(max_dose, optimal_dose))
        optimal_response = self._hill_response(optimal_dose, ec50, hill)

        # Compute dose-response curve for visualization
        dose_response_curve: list[dict[str, float]] = []
        steps = 10
        for i in range(steps + 1):
            dose = min_dose + (max_dose - min_dose) * i / steps
            response = self._hill_response(dose, ec50, hill)
            dose_response_curve.append({
                "dose": round(dose, 2),
                "predicted_response": round(response, 4),
            })

        recommendation = "maintain"
        if optimal_dose > current_dose * 1.1:
            recommendation = "increase"
        elif optimal_dose < current_dose * 0.9:
            recommendation = "decrease"

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "medication": medication,
                "current_dose": current_dose,
                "current_predicted_response": round(current_response, 4),
                "observed_response": round(observed_response, 4),
                "target_response": target_response,
                "optimal_dose": round(optimal_dose, 2),
                "optimal_predicted_response": round(optimal_response, 4),
                "recommendation": recommendation,
                "dose_range": {"min": min_dose, "max": max_dose},
                "pk_parameters": {"ec50": ec50, "hill_coefficient": hill},
                "dose_response_curve": dose_response_curve,
                "optimized_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.76,
            rationale=(
                f"Dosage optimization for {medication}: recommend {recommendation} "
                f"from {current_dose} to {optimal_dose:.1f} "
                f"(target response {target_response:.0%}, predicted {optimal_response:.0%})"
            ),
        )

    # ── care_pathway ──────────────────────────────────────────────────────────

    def _care_pathway(self, input_data: AgentInput) -> AgentOutput:
        """Map optimal care pathway with milestones, check-ins, and decision points."""
        ctx = input_data.context
        conditions = ctx.get("conditions", [])
        current_vitals = ctx.get("current_vitals", {})
        medications = ctx.get("medications", [])
        duration_months = ctx.get("duration_months", 12)

        if not conditions:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No conditions provided for pathway planning"},
                confidence=0.0,
                rationale="Cannot build care pathway without known conditions",
                status=AgentStatus.FAILED,
            )

        # Build phased pathway
        phases: list[dict[str, Any]] = []

        # Phase 1: Assessment & Initiation (Month 1)
        phases.append({
            "phase": 1,
            "name": "Assessment & Initiation",
            "duration_months": 1,
            "start_month": 1,
            "activities": [
                "Comprehensive health assessment",
                "Baseline vital collection",
                "Medication reconciliation",
                "Patient goal setting",
                "Care team alignment",
            ],
            "milestones": [
                {"name": "Baseline documented", "target_month": 1},
                {"name": "Care plan agreed", "target_month": 1},
            ],
            "check_ins": [
                {"type": "provider_visit", "week": 1},
                {"type": "care_coordinator_call", "week": 2},
            ],
            "decision_points": [
                {
                    "question": "Are current medications adequate?",
                    "if_yes": "Continue current regimen with monitoring",
                    "if_no": "Initiate medication optimization",
                },
            ],
        })

        # Phase 2: Optimization (Months 2-4)
        phases.append({
            "phase": 2,
            "name": "Treatment Optimization",
            "duration_months": 3,
            "start_month": 2,
            "activities": [
                "Medication titration as needed",
                "Lifestyle intervention initiation",
                "RPM device setup and monitoring",
                "Adherence support",
            ],
            "milestones": [
                {"name": "Target doses achieved", "target_month": 3},
                {"name": "Lifestyle plan active", "target_month": 2},
                {"name": "RPM data flowing", "target_month": 2},
            ],
            "check_ins": [
                {"type": "provider_visit", "frequency": "monthly"},
                {"type": "care_coordinator_call", "frequency": "biweekly"},
                {"type": "rpm_review", "frequency": "weekly"},
            ],
            "decision_points": [
                {
                    "question": "Is patient responding to current therapy?",
                    "if_yes": "Continue and advance to maintenance",
                    "if_no": "Adjust medications or add interventions",
                },
                {
                    "question": "Is adherence above 80%?",
                    "if_yes": "Maintain current support level",
                    "if_no": "Intensify adherence support",
                },
            ],
        })

        # Phase 3: Maintenance (Months 5-9)
        phases.append({
            "phase": 3,
            "name": "Maintenance & Monitoring",
            "duration_months": 5,
            "start_month": 5,
            "activities": [
                "Continued RPM monitoring",
                "Regular outcome assessments",
                "Medication adherence tracking",
                "Complication surveillance",
            ],
            "milestones": [
                {"name": "Clinical targets met", "target_month": 6},
                {"name": "Sustained adherence >80%", "target_month": 7},
            ],
            "check_ins": [
                {"type": "provider_visit", "frequency": "quarterly"},
                {"type": "care_coordinator_call", "frequency": "monthly"},
                {"type": "rpm_review", "frequency": "weekly"},
            ],
            "decision_points": [
                {
                    "question": "Are clinical targets being maintained?",
                    "if_yes": "Continue current plan",
                    "if_no": "Reassess and re-optimize",
                },
            ],
        })

        # Phase 4: Long-term Management (Months 10-12)
        phases.append({
            "phase": 4,
            "name": "Long-term Management & Transition",
            "duration_months": 3,
            "start_month": 10,
            "activities": [
                "Outcome evaluation",
                "Self-management skill assessment",
                "Care plan renewal planning",
                "Transition to sustained care model",
            ],
            "milestones": [
                {"name": "Annual outcomes review", "target_month": 12},
                {"name": "Self-management competency", "target_month": 11},
            ],
            "check_ins": [
                {"type": "provider_visit", "frequency": "quarterly"},
                {"type": "care_coordinator_call", "frequency": "monthly"},
            ],
            "decision_points": [
                {
                    "question": "Has patient achieved sustained improvement?",
                    "if_yes": "Transition to maintenance pathway",
                    "if_no": "Renew intensive care pathway",
                },
            ],
        })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
                "conditions": conditions,
                "pathway_duration_months": duration_months,
                "phases": phases,
                "total_milestones": sum(len(p["milestones"]) for p in phases),
                "total_decision_points": sum(len(p["decision_points"]) for p in phases),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.80,
            rationale=(
                f"Care pathway mapped for {len(conditions)} condition(s) over "
                f"{duration_months} months with {len(phases)} phases"
            ),
        )

    # ── cost_effectiveness ────────────────────────────────────────────────────

    def _cost_effectiveness(self, input_data: AgentInput) -> AgentOutput:
        """Compare treatment options by cost-effectiveness ratio (QALY-based)."""
        ctx = input_data.context
        interventions = ctx.get("interventions", [])
        time_horizon_years = ctx.get("time_horizon_years", 5)
        discount_rate = ctx.get("discount_rate", 0.03)

        if not interventions:
            # Default: evaluate all interventions in catalog
            interventions = list(INTERVENTION_CATALOG.keys())

        analyses: list[dict[str, Any]] = []
        for name in interventions:
            profile = INTERVENTION_CATALOG.get(name)
            if not profile:
                continue

            # Compute discounted costs and QALYs over time horizon
            total_cost = 0.0
            total_qaly = 0.0
            for year in range(1, time_horizon_years + 1):
                discount = 1.0 / ((1 + discount_rate) ** year)
                annual_cost = profile["monthly_cost"] * 12
                total_cost += annual_cost * discount
                total_qaly += profile["qaly_gain_annual"] * discount

            # Incremental cost-effectiveness ratio (vs. no treatment)
            icer = total_cost / total_qaly if total_qaly > 0 else float("inf")

            cost_effective = icer <= QALY_THRESHOLD

            analyses.append({
                "intervention": name,
                "category": profile["category"],
                "total_discounted_cost": round(total_cost, 2),
                "total_discounted_qaly": round(total_qaly, 4),
                "icer": round(icer, 2) if icer != float("inf") else None,
                "cost_effective": cost_effective,
                "threshold_used": QALY_THRESHOLD,
                "efficacy": profile["efficacy"],
                "monthly_cost": profile["monthly_cost"],
            })

        analyses.sort(key=lambda a: a["icer"] if a["icer"] is not None else float("inf"))
        for idx, item in enumerate(analyses, 1):
            item["rank"] = idx

        cost_effective_count = sum(1 for a in analyses if a["cost_effective"])

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "analyses": analyses,
                "time_horizon_years": time_horizon_years,
                "discount_rate": discount_rate,
                "qaly_threshold": QALY_THRESHOLD,
                "total_evaluated": len(analyses),
                "cost_effective_count": cost_effective_count,
                "most_cost_effective": analyses[0]["intervention"] if analyses else None,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.80,
            rationale=(
                f"Cost-effectiveness analysis of {len(analyses)} interventions over "
                f"{time_horizon_years} years: {cost_effective_count} are cost-effective "
                f"at ${QALY_THRESHOLD:,.0f}/QALY threshold"
            ),
        )

    # ── Internal Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _hill_response(dose: float, ec50: float, hill: float) -> float:
        """Hill equation: E = D^n / (EC50^n + D^n)."""
        if dose <= 0:
            return 0.0
        d_n = dose ** hill
        ec50_n = ec50 ** hill
        return d_n / (ec50_n + d_n)
