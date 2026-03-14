"""
Eminence HealthOS — Readmission Risk Agent
Layer 3 (Decisioning): Predicts 30-day hospital readmission risk using
patient demographics, clinical history, prior admissions, social determinants,
and discharge characteristics. Generates risk scores and intervention recommendations.
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


# Risk factor weights (simplified HOSPITAL/LACE-inspired model)
RISK_FACTORS = {
    "age_over_65": 0.08,
    "age_over_75": 0.05,
    "prior_admissions_6m": 0.12,  # per admission
    "length_of_stay_gt_5": 0.10,
    "ed_visits_prior_6m": 0.08,  # per visit
    "chronic_conditions_gt_3": 0.10,
    "heart_failure": 0.12,
    "copd": 0.10,
    "diabetes_uncontrolled": 0.08,
    "ckd_stage_4_5": 0.10,
    "polypharmacy_gt_5": 0.06,
    "lives_alone": 0.05,
    "no_pcp_follow_up": 0.08,
    "medication_non_adherence": 0.10,
    "discharge_against_advice": 0.15,
    "unplanned_admission": 0.06,
}

# Intervention recommendations by risk tier
INTERVENTIONS = {
    "critical": [
        "Transition care nurse visit within 24 hours post-discharge",
        "Daily phone follow-up for first 7 days",
        "Medication reconciliation with pharmacist",
        "PCP follow-up within 48 hours",
        "Home health assessment",
        "Enroll in remote patient monitoring",
    ],
    "high": [
        "Transition care nurse call within 48 hours",
        "Twice-weekly phone follow-up for 2 weeks",
        "Medication review and reconciliation",
        "PCP follow-up within 7 days",
        "Enroll in remote patient monitoring",
    ],
    "moderate": [
        "Follow-up phone call within 72 hours",
        "Weekly check-in for 2 weeks",
        "PCP follow-up within 14 days",
        "Medication adherence support",
    ],
    "low": [
        "Standard discharge follow-up",
        "PCP follow-up within 30 days",
    ],
}


class ReadmissionRiskAgent(BaseAgent):
    """Predicts 30-day readmission risk and recommends interventions."""

    name = "readmission_risk"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Predicts 30-day readmission risk with intervention recommendations"
    min_confidence = 0.70

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "predict")

        if action == "predict":
            return self._predict_risk(input_data)
        elif action == "batch_predict":
            return self._batch_predict(input_data)
        elif action == "explain":
            return await self._explain_prediction(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown readmission risk action: {action}",
                status=AgentStatus.FAILED,
            )

    def _predict_risk(self, input_data: AgentInput) -> AgentOutput:
        """Predict readmission risk for a single patient."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")

        # Extract risk factors
        factors = self._extract_factors(ctx)
        risk_score = self._calculate_risk_score(factors)
        risk_level = self._risk_level(risk_score)
        interventions = INTERVENTIONS.get(risk_level, INTERVENTIONS["low"])

        result = {
            "patient_id": patient_id,
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "risk_percentile": self._score_to_percentile(risk_score),
            "contributing_factors": factors,
            "top_factors": sorted(factors, key=lambda f: f["contribution"], reverse=True)[:5],
            "recommended_interventions": interventions,
            "model_version": "lace_enhanced_v1",
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82 if len(factors) >= 5 else 0.65,
            rationale=(
                f"Readmission risk: {risk_score:.1%} ({risk_level}) — "
                f"{len(factors)} risk factors, {len(interventions)} interventions"
            ),
        )

    def _batch_predict(self, input_data: AgentInput) -> AgentOutput:
        """Predict readmission risk for multiple patients."""
        ctx = input_data.context
        patients = ctx.get("patients", [])

        predictions = []
        for p in patients:
            factors = self._extract_factors(p)
            score = self._calculate_risk_score(factors)
            level = self._risk_level(score)
            predictions.append({
                "patient_id": p.get("patient_id", ""),
                "risk_score": round(score, 3),
                "risk_level": level,
                "top_factor": factors[0]["factor"] if factors else "none",
            })

        # Sort by risk score descending
        predictions.sort(key=lambda p: p["risk_score"], reverse=True)

        distribution = {}
        for p in predictions:
            level = p["risk_level"]
            distribution[level] = distribution.get(level, 0) + 1

        result = {
            "total_patients": len(predictions),
            "predictions": predictions,
            "risk_distribution": distribution,
            "avg_risk_score": round(
                sum(p["risk_score"] for p in predictions) / max(len(predictions), 1), 3
            ),
            "high_risk_count": sum(
                1 for p in predictions if p["risk_level"] in ("high", "critical")
            ),
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.80,
            rationale=(
                f"Batch prediction: {len(predictions)} patients, "
                f"avg risk {result['avg_risk_score']:.1%}, "
                f"{result['high_risk_count']} high/critical"
            ),
        )

    async def _explain_prediction(self, input_data: AgentInput) -> AgentOutput:
        """Explain a readmission risk prediction with factor breakdown."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")

        factors = self._extract_factors(ctx)
        risk_score = self._calculate_risk_score(factors)
        risk_level = self._risk_level(risk_score)

        # Build explanation
        explanation = {
            "patient_id": patient_id,
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "factor_breakdown": [
                {
                    "factor": f["factor"],
                    "present": f["present"],
                    "contribution": f["contribution"],
                    "weight": f["weight"],
                    "explanation": f["explanation"],
                }
                for f in sorted(factors, key=lambda f: f["contribution"], reverse=True)
            ],
            "baseline_risk": 0.10,
            "total_risk_increase": round(risk_score - 0.10, 3),
            "model_info": {
                "model": "LACE Enhanced v1",
                "factors_evaluated": len(RISK_FACTORS),
                "factors_present": sum(1 for f in factors if f["present"]),
            },
        }

        # Generate LLM narrative explanation
        try:
            active_factors = [f for f in factors if f["present"]]
            factor_summary = "\n".join(
                f"- {f['factor']}: {f['explanation']} (contribution: {f['contribution']:.2f})"
                for f in sorted(active_factors, key=lambda f: f["contribution"], reverse=True)
            )

            prompt = (
                f"Patient {patient_id} has a 30-day readmission risk score of "
                f"{risk_score:.1%} ({risk_level} risk).\n\n"
                f"Active risk factors:\n{factor_summary}\n\n"
                f"Baseline risk is 10%. Total risk increase from factors: "
                f"{risk_score - 0.10:.1%}.\n\n"
                f"Provide a concise clinical explanation of why this patient is at "
                f"{risk_level} risk for readmission, how the factors interact, and "
                f"what the care team should prioritize."
            )

            response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=(
                        "You are a clinical decision-support assistant integrated into "
                        "a hospital care management platform. Explain readmission risk "
                        "factors in clear, precise clinical language suitable for care "
                        "team members including physicians, nurses, and case managers. "
                        "Be concise but thorough. Focus on actionable clinical insights "
                        "and how risk factors compound each other. Do not include "
                        "disclaimers or general medical advice."
                    ),
                    temperature=0.3,
                    max_tokens=1024,
                )
            )

            explanation["narrative_explanation"] = response.content
        except Exception:
            logger.warning(
                "LLM narrative generation failed for patient %s; "
                "returning explanation without narrative",
                patient_id,
                exc_info=True,
            )

        return self.build_output(
            trace_id=input_data.trace_id,
            result=explanation,
            confidence=0.85,
            rationale=f"Risk explanation: {sum(1 for f in factors if f['present'])} active factors",
        )

    def _extract_factors(self, ctx: dict) -> list[dict[str, Any]]:
        """Extract risk factors from patient context."""
        factors = []
        age = ctx.get("age", 0)
        conditions = [c.lower() if isinstance(c, str) else c.get("code", "").lower()
                       for c in ctx.get("conditions", [])]

        def add(name: str, present: bool, explanation: str):
            weight = RISK_FACTORS.get(name, 0)
            factors.append({
                "factor": name,
                "present": present,
                "weight": weight,
                "contribution": weight if present else 0,
                "explanation": explanation,
            })

        add("age_over_65", age >= 65, f"Patient age: {age}")
        add("age_over_75", age >= 75, f"Patient age: {age}")

        prior_admissions = ctx.get("prior_admissions_6m", 0)
        add("prior_admissions_6m", prior_admissions > 0,
            f"{prior_admissions} admission(s) in prior 6 months")

        los = ctx.get("length_of_stay_days", 0)
        add("length_of_stay_gt_5", los > 5, f"Length of stay: {los} days")

        ed_visits = ctx.get("ed_visits_6m", 0)
        add("ed_visits_prior_6m", ed_visits > 0, f"{ed_visits} ED visit(s) in prior 6 months")

        condition_count = len(conditions)
        add("chronic_conditions_gt_3", condition_count > 3,
            f"{condition_count} chronic conditions")

        add("heart_failure", any("i50" in c or "heart_failure" in c for c in conditions),
            "Heart failure diagnosis present")
        add("copd", any("j44" in c or "copd" in c for c in conditions),
            "COPD diagnosis present")
        add("diabetes_uncontrolled", ctx.get("hba1c", 0) > 9.0,
            f"HbA1c: {ctx.get('hba1c', 'N/A')}")
        add("ckd_stage_4_5", any("n18.4" in c or "n18.5" in c for c in conditions),
            "CKD Stage 4/5 present")

        meds = ctx.get("medication_count", 0)
        add("polypharmacy_gt_5", meds > 5, f"{meds} medications")

        add("lives_alone", ctx.get("lives_alone", False), "Patient lives alone")
        add("no_pcp_follow_up", not ctx.get("pcp_follow_up_scheduled", True),
            "No PCP follow-up scheduled")
        add("medication_non_adherence", ctx.get("medication_adherence", 1.0) < 0.8,
            f"Adherence: {ctx.get('medication_adherence', 'N/A')}")

        return factors

    @staticmethod
    def _calculate_risk_score(factors: list[dict]) -> float:
        """Calculate composite risk score from factors."""
        baseline = 0.10
        total = baseline + sum(f["contribution"] for f in factors)
        return min(total, 0.99)

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 0.70:
            return "critical"
        elif score >= 0.50:
            return "high"
        elif score >= 0.30:
            return "moderate"
        return "low"

    @staticmethod
    def _score_to_percentile(score: float) -> int:
        """Approximate percentile from risk score."""
        return min(99, int(score * 100))
