"""
Eminence HealthOS — Follow-Up Plan Agent
Layer 4 (Action): Generates structured follow-up care plans after
telehealth encounters. Determines monitoring cadence, follow-up
scheduling, medication adjustments, and patient education items.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    Severity,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger(__name__)

# Condition → recommended monitoring cadence
CONDITION_CADENCE: dict[str, dict[str, Any]] = {
    "congestive_heart_failure": {"vitals_frequency": "daily", "follow_up_days": 7, "priority_vitals": ["weight", "blood_pressure", "heart_rate"]},
    "diabetes": {"vitals_frequency": "twice_daily", "follow_up_days": 14, "priority_vitals": ["glucose"]},
    "hypertension": {"vitals_frequency": "daily", "follow_up_days": 14, "priority_vitals": ["blood_pressure"]},
    "copd": {"vitals_frequency": "daily", "follow_up_days": 7, "priority_vitals": ["spo2", "respiratory_rate"]},
    "chronic_kidney_disease": {"vitals_frequency": "daily", "follow_up_days": 14, "priority_vitals": ["blood_pressure", "weight"]},
    "asthma": {"vitals_frequency": "as_needed", "follow_up_days": 30, "priority_vitals": ["spo2", "respiratory_rate"]},
}


class FollowUpPlanAgent(BaseAgent):
    name = "follow_up_plan"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Generates follow-up care plans with monitoring cadence and scheduling"
    min_confidence = 0.7

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context

        conditions: list[Any] = ctx.get("conditions", [])
        risk_assessments: list[dict[str, Any]] = ctx.get("risk_assessments", [])
        symptoms: list[str] = ctx.get("symptoms", [])
        encounter_type: str = ctx.get("encounter_type", "telehealth")
        plan_items: list[str] = ctx.get("plan", [])
        medications: list[str] = ctx.get("medications", [])

        # Determine risk level
        highest_risk = max(
            (r.get("score", 0) for r in risk_assessments if isinstance(r, dict)),
            default=0.0,
        )
        risk_level = self._score_to_severity(highest_risk)

        # Build follow-up plan
        plan = self._build_follow_up_plan(
            conditions, risk_level, symptoms, plan_items, medications
        )

        # ── LLM: generate personalized follow-up narrative ────────────
        follow_up_narrative: str | None = None
        try:
            prompt = (
                f"Patient conditions: {', '.join(str(c) for c in conditions) or 'none reported'}.\n"
                f"Risk level: {risk_level.value}.\n"
                f"Symptoms: {', '.join(symptoms) or 'none reported'}.\n"
                f"Medications: {', '.join(medications) or 'none'}.\n"
                f"Follow-up in {plan['follow_up_days']} days, "
                f"vitals frequency: {plan['monitoring_cadence']['vitals_frequency']}.\n"
                f"Action items: {'; '.join(plan['action_items'])}.\n\n"
                "Write a concise, patient-friendly follow-up instruction narrative "
                "covering monitoring expectations, medication adherence, warning signs, "
                "and when to seek immediate care."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical follow-up coordinator in a telehealth platform. "
                    "Produce clear, empathetic, and actionable follow-up instructions "
                    "for the patient. Keep the language at a 6th-grade reading level."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            follow_up_narrative = resp.content
        except Exception:
            logger.warning("LLM unavailable for follow-up narrative; continuing without it.")

        result = {"follow_up_plan": plan}
        if follow_up_narrative:
            result["follow_up_narrative"] = follow_up_narrative

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82,
            rationale=(
                f"Follow-up plan generated: {plan['follow_up_days']}d follow-up, "
                f"{plan['monitoring_cadence']['vitals_frequency']} vitals, "
                f"{len(plan['action_items'])} action items"
            ),
        )

    def _build_follow_up_plan(
        self,
        conditions: list[Any],
        risk_level: Severity,
        symptoms: list[str],
        plan_items: list[str],
        medications: list[str],
    ) -> dict[str, Any]:
        # Determine cadence from conditions
        cadence = self._determine_cadence(conditions, risk_level)

        # Build action items
        action_items = list(plan_items) if plan_items else []
        if not action_items:
            action_items.append("Follow up with primary care provider")

        # Add condition-specific education
        education: list[str] = []
        for c in conditions:
            cond_name = c.get("display", c) if isinstance(c, dict) else str(c)
            education.append(f"Continue monitoring for {cond_name}")

        # Risk-based additions
        if risk_level in (Severity.CRITICAL, Severity.HIGH):
            action_items.insert(0, "Priority follow-up within 48 hours")
            education.append("Seek immediate care if symptoms worsen")
        elif risk_level == Severity.MODERATE:
            action_items.append("Schedule follow-up within 1 week")

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "follow_up_days": cadence["follow_up_days"],
            "monitoring_cadence": {
                "vitals_frequency": cadence["vitals_frequency"],
                "priority_vitals": cadence["priority_vitals"],
            },
            "action_items": action_items,
            "medication_instructions": [
                {"medication": m, "instruction": "Continue as prescribed"} for m in medications
            ],
            "patient_education": education,
            "escalation_criteria": [
                "Vital signs outside monitored thresholds",
                "New or worsening symptoms",
                "Missed vitals submissions for 24+ hours",
            ],
            "risk_level": risk_level.value,
        }

    def _determine_cadence(self, conditions: list[Any], risk_level: Severity) -> dict[str, Any]:
        """Determine monitoring cadence from conditions and risk level."""
        best_cadence: dict[str, Any] = {
            "vitals_frequency": "daily",
            "follow_up_days": 14,
            "priority_vitals": ["heart_rate", "blood_pressure"],
        }

        min_follow_up = 30
        all_priority_vitals: set[str] = set()
        highest_frequency = "as_needed"
        freq_order = ["as_needed", "weekly", "daily", "twice_daily"]

        for c in conditions:
            cond_key = (c.get("display", "") if isinstance(c, dict) else str(c)).lower().replace(" ", "_")
            cadence = CONDITION_CADENCE.get(cond_key)
            if cadence:
                if cadence["follow_up_days"] < min_follow_up:
                    min_follow_up = cadence["follow_up_days"]
                all_priority_vitals.update(cadence["priority_vitals"])
                if freq_order.index(cadence["vitals_frequency"]) > freq_order.index(highest_frequency):
                    highest_frequency = cadence["vitals_frequency"]

        # Override based on risk level
        if risk_level == Severity.CRITICAL:
            min_follow_up = min(min_follow_up, 3)
            highest_frequency = "twice_daily"
        elif risk_level == Severity.HIGH:
            min_follow_up = min(min_follow_up, 7)
            highest_frequency = "daily"

        best_cadence["follow_up_days"] = min_follow_up
        best_cadence["vitals_frequency"] = highest_frequency
        if all_priority_vitals:
            best_cadence["priority_vitals"] = sorted(all_priority_vitals)

        return best_cadence

    @staticmethod
    def _score_to_severity(score: float) -> Severity:
        if score >= 0.75:
            return Severity.CRITICAL
        elif score >= 0.5:
            return Severity.HIGH
        elif score >= 0.25:
            return Severity.MODERATE
        return Severity.LOW
