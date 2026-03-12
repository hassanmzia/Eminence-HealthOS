"""
Eminence HealthOS — Mental Health Screening Agent (#76)
Layer 2 (Interpretation): Automated PHQ-9, GAD-7, and AUDIT-C screening
and scoring for depression, anxiety, and alcohol misuse detection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)


# ── Scoring Thresholds ───────────────────────────────────────────────────────

PHQ9_THRESHOLDS: list[tuple[int, int, str, str]] = [
    # (min_score, max_score, severity, recommended_action)
    (0, 4, "minimal", "no_action"),
    (5, 9, "mild", "watchful_waiting"),
    (10, 14, "moderate", "treatment_plan_consideration"),
    (15, 19, "moderately_severe", "active_treatment_recommended"),
    (20, 27, "severe", "immediate_treatment_and_referral"),
]

GAD7_THRESHOLDS: list[tuple[int, int, str, str]] = [
    (0, 4, "minimal", "no_action"),
    (5, 9, "mild", "watchful_waiting"),
    (10, 14, "moderate", "treatment_plan_consideration"),
    (15, 21, "severe", "active_treatment_and_referral"),
]

AUDIT_C_THRESHOLDS: dict[str, int] = {
    "male": 4,
    "female": 3,
}


class MentalHealthScreeningAgent(BaseAgent):
    """Automated PHQ-9, GAD-7, and AUDIT-C screening and scoring."""

    name = "mental_health_screening"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = (
        "Administers and scores standardized mental health screening instruments "
        "(PHQ-9, GAD-7, AUDIT-C) for depression, anxiety, and alcohol misuse"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "comprehensive_screen")

        if action == "phq9_screen":
            return self._score_phq9(input_data)
        elif action == "gad7_screen":
            return self._score_gad7(input_data)
        elif action == "audit_c_screen":
            return self._score_audit_c(input_data)
        elif action == "comprehensive_screen":
            return self._comprehensive_screen(input_data)
        elif action == "screening_history":
            return self._screening_history(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown screening action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── PHQ-9 Depression Screening ───────────────────────────────────────────

    def _score_phq9(self, input_data: AgentInput) -> AgentOutput:
        """Score the Patient Health Questionnaire-9 for depression."""
        ctx = input_data.context
        responses = ctx.get("responses", [])

        if len(responses) != 9:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": "PHQ-9 requires exactly 9 responses",
                    "received": len(responses),
                },
                confidence=0.95,
                rationale=f"Invalid PHQ-9 input: expected 9 responses, got {len(responses)}",
                status=AgentStatus.FAILED,
            )

        # Validate each response is 0-3
        for i, r in enumerate(responses):
            if not isinstance(r, int) or r < 0 or r > 3:
                return self.build_output(
                    trace_id=input_data.trace_id,
                    result={
                        "error": f"Response {i + 1} must be an integer 0-3, got: {r}",
                    },
                    confidence=0.95,
                    rationale=f"Invalid PHQ-9 response at item {i + 1}",
                    status=AgentStatus.FAILED,
                )

        total_score = sum(responses)
        severity, recommended_action = self._classify_phq9(total_score)

        # Item 9 (index 8) assesses suicidal ideation
        suicidal_ideation_flag = responses[8] > 0
        clinical_flags = []
        if suicidal_ideation_flag:
            clinical_flags.append({
                "type": "suicidal_ideation",
                "item": 9,
                "score": responses[8],
                "message": (
                    "Patient endorsed thoughts of self-harm or being better off dead. "
                    "Immediate safety assessment recommended."
                ),
                "urgency": "high",
            })

        # Flag if score suggests possible major depression
        if total_score >= 10:
            clinical_flags.append({
                "type": "possible_major_depression",
                "message": "PHQ-9 score suggests possible major depressive disorder evaluation warranted",
                "urgency": "moderate",
            })

        result = {
            "instrument": "PHQ-9",
            "total_score": total_score,
            "max_score": 27,
            "severity": severity,
            "recommended_action": recommended_action,
            "suicidal_ideation_flag": suicidal_ideation_flag,
            "clinical_flags": clinical_flags,
            "item_scores": {f"item_{i + 1}": r for i, r in enumerate(responses)},
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

        # Lower confidence if borderline between categories
        confidence = 0.92
        for low, high, _, _ in PHQ9_THRESHOLDS:
            if total_score == low or total_score == high:
                confidence = 0.85
                break

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"PHQ-9 total score {total_score}/27 — severity: {severity}. "
                f"{'Suicidal ideation flagged (item 9 > 0). ' if suicidal_ideation_flag else ''}"
                f"Recommended: {recommended_action}"
            ),
        )

    # ── GAD-7 Anxiety Screening ──────────────────────────────────────────────

    def _score_gad7(self, input_data: AgentInput) -> AgentOutput:
        """Score the Generalized Anxiety Disorder 7-item scale."""
        ctx = input_data.context
        responses = ctx.get("responses", [])

        if len(responses) != 7:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": "GAD-7 requires exactly 7 responses",
                    "received": len(responses),
                },
                confidence=0.95,
                rationale=f"Invalid GAD-7 input: expected 7 responses, got {len(responses)}",
                status=AgentStatus.FAILED,
            )

        for i, r in enumerate(responses):
            if not isinstance(r, int) or r < 0 or r > 3:
                return self.build_output(
                    trace_id=input_data.trace_id,
                    result={
                        "error": f"Response {i + 1} must be an integer 0-3, got: {r}",
                    },
                    confidence=0.95,
                    rationale=f"Invalid GAD-7 response at item {i + 1}",
                    status=AgentStatus.FAILED,
                )

        total_score = sum(responses)
        severity, recommended_action = self._classify_gad7(total_score)

        result = {
            "instrument": "GAD-7",
            "total_score": total_score,
            "max_score": 21,
            "severity": severity,
            "recommended_action": recommended_action,
            "item_scores": {f"item_{i + 1}": r for i, r in enumerate(responses)},
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

        confidence = 0.92
        for low, high, _, _ in GAD7_THRESHOLDS:
            if total_score == low or total_score == high:
                confidence = 0.85
                break

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"GAD-7 total score {total_score}/21 — severity: {severity}. "
                f"Recommended: {recommended_action}"
            ),
        )

    # ── AUDIT-C Alcohol Screening ────────────────────────────────────────────

    def _score_audit_c(self, input_data: AgentInput) -> AgentOutput:
        """Score the Alcohol Use Disorders Identification Test - Concise."""
        ctx = input_data.context
        responses = ctx.get("responses", [])
        sex = ctx.get("sex", "").lower()

        if len(responses) != 3:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": "AUDIT-C requires exactly 3 responses",
                    "received": len(responses),
                },
                confidence=0.95,
                rationale=f"Invalid AUDIT-C input: expected 3 responses, got {len(responses)}",
                status=AgentStatus.FAILED,
            )

        if sex not in ("male", "female"):
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": "Sex must be 'male' or 'female' for AUDIT-C threshold determination",
                },
                confidence=0.95,
                rationale="AUDIT-C requires sex for threshold determination",
                status=AgentStatus.FAILED,
            )

        # AUDIT-C item ranges: item 1 (0-4), item 2 (0-4), item 3 (0-4)
        total_score = sum(responses)
        threshold = AUDIT_C_THRESHOLDS[sex]
        at_risk = total_score >= threshold

        recommended_action = "brief_intervention_and_referral" if at_risk else "no_action"
        if total_score >= 8:
            recommended_action = "full_audit_and_referral"

        result = {
            "instrument": "AUDIT-C",
            "total_score": total_score,
            "max_score": 12,
            "sex": sex,
            "threshold": threshold,
            "at_risk": at_risk,
            "recommended_action": recommended_action,
            "item_scores": {f"item_{i + 1}": r for i, r in enumerate(responses)},
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=(
                f"AUDIT-C score {total_score}/12 for {sex} patient "
                f"(threshold: {threshold}). "
                f"{'At-risk drinking detected. ' if at_risk else 'Not at risk. '}"
                f"Recommended: {recommended_action}"
            ),
        )

    # ── Comprehensive Screen ─────────────────────────────────────────────────

    def _comprehensive_screen(self, input_data: AgentInput) -> AgentOutput:
        """Run all three screening instruments and produce a combined assessment."""
        ctx = input_data.context
        phq9_responses = ctx.get("phq9_responses", [])
        gad7_responses = ctx.get("gad7_responses", [])
        audit_c_responses = ctx.get("audit_c_responses", [])
        sex = ctx.get("sex", "").lower()

        results: dict[str, Any] = {
            "comprehensive": True,
            "screens_completed": [],
            "screens_skipped": [],
            "priority_flags": [],
            "overall_risk_level": "low",
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

        risk_levels: list[str] = []

        # PHQ-9
        if len(phq9_responses) == 9:
            phq9_score = sum(phq9_responses)
            phq9_severity, phq9_action = self._classify_phq9(phq9_score)
            results["phq9"] = {
                "total_score": phq9_score,
                "severity": phq9_severity,
                "recommended_action": phq9_action,
                "suicidal_ideation_flag": phq9_responses[8] > 0,
            }
            results["screens_completed"].append("PHQ-9")

            if phq9_responses[8] > 0:
                results["priority_flags"].append({
                    "type": "suicidal_ideation",
                    "source": "PHQ-9 item 9",
                    "urgency": "high",
                })
            if phq9_severity in ("moderately_severe", "severe"):
                risk_levels.append("high")
            elif phq9_severity == "moderate":
                risk_levels.append("moderate")
            else:
                risk_levels.append("low")
        else:
            results["screens_skipped"].append("PHQ-9")

        # GAD-7
        if len(gad7_responses) == 7:
            gad7_score = sum(gad7_responses)
            gad7_severity, gad7_action = self._classify_gad7(gad7_score)
            results["gad7"] = {
                "total_score": gad7_score,
                "severity": gad7_severity,
                "recommended_action": gad7_action,
            }
            results["screens_completed"].append("GAD-7")

            if gad7_severity == "severe":
                risk_levels.append("high")
            elif gad7_severity == "moderate":
                risk_levels.append("moderate")
            else:
                risk_levels.append("low")
        else:
            results["screens_skipped"].append("GAD-7")

        # AUDIT-C
        if len(audit_c_responses) == 3 and sex in ("male", "female"):
            audit_score = sum(audit_c_responses)
            threshold = AUDIT_C_THRESHOLDS[sex]
            at_risk = audit_score >= threshold
            results["audit_c"] = {
                "total_score": audit_score,
                "at_risk": at_risk,
                "threshold": threshold,
            }
            results["screens_completed"].append("AUDIT-C")

            if at_risk:
                risk_levels.append("moderate")
                results["priority_flags"].append({
                    "type": "at_risk_drinking",
                    "source": "AUDIT-C",
                    "urgency": "moderate",
                })
        else:
            results["screens_skipped"].append("AUDIT-C")

        # Determine overall risk
        if "high" in risk_levels or any(
            f["urgency"] == "high" for f in results["priority_flags"]
        ):
            results["overall_risk_level"] = "high"
        elif "moderate" in risk_levels:
            results["overall_risk_level"] = "moderate"
        else:
            results["overall_risk_level"] = "low"

        completed_count = len(results["screens_completed"])
        confidence = 0.90 if completed_count == 3 else (0.80 if completed_count >= 1 else 0.50)

        return self.build_output(
            trace_id=input_data.trace_id,
            result=results,
            confidence=confidence,
            rationale=(
                f"Comprehensive screening: {completed_count}/3 instruments completed. "
                f"Overall risk: {results['overall_risk_level']}. "
                f"{len(results['priority_flags'])} priority flag(s)."
            ),
        )

    # ── Screening History ────────────────────────────────────────────────────

    def _screening_history(self, input_data: AgentInput) -> AgentOutput:
        """Return screening history for a patient showing trends over time."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        instrument = ctx.get("instrument")  # optional filter
        period_days = ctx.get("period_days", 90)

        # In production, this would query the screening results store
        result = {
            "patient_id": patient_id,
            "instrument_filter": instrument,
            "period_days": period_days,
            "history": [],
            "trends": {
                "phq9": {"direction": "stable", "data_points": 0},
                "gad7": {"direction": "stable", "data_points": 0},
                "audit_c": {"direction": "stable", "data_points": 0},
            },
            "next_screening_due": None,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=(
                f"Retrieved screening history for patient {patient_id} "
                f"over {period_days} days"
            ),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _classify_phq9(score: int) -> tuple[str, str]:
        """Classify PHQ-9 score into severity and recommended action."""
        for low, high, severity, action in PHQ9_THRESHOLDS:
            if low <= score <= high:
                return severity, action
        return "severe", "immediate_treatment_and_referral"

    @staticmethod
    def _classify_gad7(score: int) -> tuple[str, str]:
        """Classify GAD-7 score into severity and recommended action."""
        for low, high, severity, action in GAD7_THRESHOLDS:
            if low <= score <= high:
                return severity, action
        return "severe", "active_treatment_and_referral"
