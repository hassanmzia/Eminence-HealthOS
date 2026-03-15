"""
Scheduling Agent — Tier 5 (Action / Measurement).

Auto-schedules follow-up appointments based on clinical urgency,
matches specialist type to condition, and generates patient-friendly
preparation guidance.

Adapted from InHealth scheduling_agent (Tier 5 Action).
"""

from __future__ import annotations

import logging
from typing import Any

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.scheduling")

# Urgency to timing mapping
URGENCY_TIMING = {
    "CRITICAL": {"target": "same-day", "hours_max": 4},
    "URGENT": {"target": "24-48 hours", "hours_max": 48},
    "SOON": {"target": "1-2 weeks", "hours_max": 336},
    "ROUTINE": {"target": "2-4 weeks", "hours_max": 672},
}

# Condition-to-specialist mapping
SPECIALIST_MAP = {
    "diabetes": ["endocrinologist", "primary_care"],
    "hypertension": ["primary_care", "cardiologist"],
    "ckd": ["nephrologist", "primary_care"],
    "heart_failure": ["cardiologist", "heart_failure_specialist"],
    "copd": ["pulmonologist", "primary_care"],
    "afib": ["cardiologist", "electrophysiologist"],
    "stroke": ["neurologist", "primary_care"],
    "cancer": ["oncologist"],
    "mental_health": ["psychiatrist", "psychologist"],
    "depression": ["psychiatrist", "primary_care"],
    "nutrition": ["dietitian", "diabetes_educator"],
    "wound_care": ["wound_care_specialist", "primary_care"],
    "default": ["primary_care"],
}


class SchedulingAgent(HealthOSAgent):
    """Automated appointment scheduling with urgency-based routing."""

    def __init__(self) -> None:
        super().__init__(
            name="scheduling",
            tier=AgentTier.ACTION,
            description=(
                "Auto-schedules follow-up appointments based on clinical urgency, "
                "matches specialist type to condition"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.SCHEDULING, AgentCapability.PATIENT_COMMUNICATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        alerts: list[dict[str, Any]] = data.get("alerts", [])
        risk_level: str = data.get("risk_level", "MEDIUM")
        conditions_needing_followup: list[str] = data.get("conditions_needing_followup", [])

        # Determine urgency
        urgency = self._determine_urgency(alerts, risk_level)

        # Identify specialists
        if not conditions_needing_followup:
            conditions_needing_followup = self._identify_conditions_needing_followup(data)
        specialists_needed = self._match_specialists(conditions_needing_followup)

        # Build scheduling requests (actual scheduling is done by the platform)
        scheduling_requests: list[dict[str, Any]] = []
        for specialist_type in specialists_needed[:3]:
            reason = self._generate_appointment_reason(conditions_needing_followup, specialist_type)
            scheduling_requests.append({
                "specialist_type": specialist_type,
                "urgency": urgency,
                "timing_target": URGENCY_TIMING.get(urgency, {}).get("target", "TBD"),
                "hours_max": URGENCY_TIMING.get(urgency, {}).get("hours_max", 672),
                "reason": reason,
            })

        out_alerts: list[dict[str, Any]] = []
        if urgency == "CRITICAL":
            out_alerts.append({
                "severity": "HIGH",
                "message": (
                    f"CRITICAL urgency appointment required. "
                    f"Specialists needed: {', '.join(specialists_needed[:3])}. "
                    "Schedule within 4 hours."
                ),
            })

        # LLM scheduling guidance
        scheduling_guidance = None
        try:
            scheduled_str = "\n".join([
                f"  - {s['specialist_type'].replace('_', ' ').title()}: {s['timing_target']} ({s['urgency']})"
                for s in scheduling_requests
            ])
            prompt = (
                f"Appointment scheduling summary:\n\n"
                f"Urgency: {urgency} - target: {URGENCY_TIMING.get(urgency, {}).get('target', 'TBD')}\n"
                f"Conditions requiring follow-up: {conditions_needing_followup}\n"
                f"Appointments to schedule:\n{scheduled_str}\n\n"
                "Generate:\n"
                "1. Patient-friendly appointment reminder message\n"
                "2. Preparation instructions for each appointment type\n"
                "3. What to bring (medications list, lab results, glucose log)\n"
                "4. Questions to ask at each appointment (3 per visit)"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system="You are a patient appointment coordinator. Provide clear, helpful scheduling guidance.",
                temperature=0.4,
                max_tokens=768,
            ))
            scheduling_guidance = resp.content
        except Exception:
            logger.warning("LLM scheduling guidance failed; continuing without it")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=f"schedule_{urgency.lower()}",
            rationale=(
                f"Urgency: {urgency}; Specialists: {', '.join(specialists_needed[:3])}; "
                f"Conditions: {', '.join(conditions_needing_followup)}"
            ),
            confidence=0.85,
            data={
                "urgency": urgency,
                "timing_target": URGENCY_TIMING.get(urgency, {}).get("target"),
                "specialists_needed": specialists_needed,
                "scheduling_requests": scheduling_requests,
                "scheduling_guidance": scheduling_guidance,
                "alerts": out_alerts,
                "recommendations": [
                    f"Appointments requested for {', '.join(specialists_needed[:3])} - urgency: {urgency}.",
                    "Patient will receive confirmation via push notification and portal message.",
                ],
            },
            requires_hitl=urgency == "CRITICAL",
            hitl_reason="CRITICAL urgency scheduling requires clinical coordinator review" if urgency == "CRITICAL" else None,
        )

    # -- Scheduling logic (preserved from source) ----------------------------------

    def _determine_urgency(self, alerts: list[dict[str, Any]], risk_level: str) -> str:
        if any(a.get("severity") in ("EMERGENCY", "CRITICAL") for a in alerts) or risk_level == "CRITICAL":
            return "CRITICAL"
        if any(a.get("severity") == "HIGH" for a in alerts) or risk_level == "HIGH":
            return "URGENT"
        if risk_level == "MEDIUM":
            return "SOON"
        return "ROUTINE"

    def _identify_conditions_needing_followup(self, data: dict[str, Any]) -> list[str]:
        conditions: list[str] = []
        monitoring = data.get("monitoring_results", {})
        diagnostics = data.get("diagnostic_results", {})

        if monitoring.get("glucose_agent", {}).get("alerts"):
            conditions.append("diabetes")
        if monitoring.get("cardiac_agent", {}).get("alerts"):
            conditions.append("hypertension")
        if diagnostics.get("kidney_agent", {}).get("findings", {}).get("aki_detected"):
            conditions.append("ckd")
        if diagnostics.get("ecg_agent", {}).get("findings", {}).get("ecg_features", {}).get("afib"):
            conditions.append("afib")

        return list(set(conditions)) if conditions else ["default"]

    def _match_specialists(self, conditions: list[str]) -> list[str]:
        specialists: set[str] = set()
        for condition in conditions:
            mapped = SPECIALIST_MAP.get(condition, SPECIALIST_MAP["default"])
            specialists.add(mapped[0])
        return list(specialists) or ["primary_care"]

    def _generate_appointment_reason(self, conditions: list[str], specialist: str) -> str:
        cond_str = ", ".join(conditions[:3]).replace("_", " ").title()
        return f"Follow-up for {cond_str} management. AI-detected abnormalities requiring clinical evaluation."
