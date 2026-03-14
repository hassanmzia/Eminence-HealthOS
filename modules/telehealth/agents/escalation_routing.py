"""
Eminence HealthOS — Escalation Routing Agent
Layer 4 (Action): Smart routing logic that determines where to escalate
clinical concerns — to specific providers, care team roles, or external
services based on severity, specialty needs, and availability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    AlertType,
    Severity,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger(__name__)

# System → specialist mapping
SYSTEM_SPECIALISTS: dict[str, str] = {
    "cardiovascular": "cardiology",
    "respiratory": "pulmonology",
    "neurological": "neurology",
    "gastrointestinal": "gastroenterology",
    "musculoskeletal": "orthopedics",
    "psychiatric": "psychiatry",
    "genitourinary": "urology",
    "dermatological": "dermatology",
    "ophthalmological": "ophthalmology",
    "ent": "otolaryngology",
    "endocrine": "endocrinology",
}

# Escalation rules by severity
ESCALATION_RULES: dict[str, dict[str, Any]] = {
    "critical": {
        "target_role": "physician",
        "alert_type": "emergency",
        "response_window_minutes": 15,
        "notify_supervisor": True,
    },
    "high": {
        "target_role": "physician",
        "alert_type": "physician_review",
        "response_window_minutes": 60,
        "notify_supervisor": False,
    },
    "moderate": {
        "target_role": "nurse",
        "alert_type": "nurse_review",
        "response_window_minutes": 240,
        "notify_supervisor": False,
    },
    "low": {
        "target_role": "care_coordinator",
        "alert_type": "patient_notification",
        "response_window_minutes": 1440,
        "notify_supervisor": False,
    },
}


class EscalationRoutingAgent(BaseAgent):
    name = "escalation_routing"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Smart clinical escalation routing based on severity, specialty, and care team"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context

        severity: str = ctx.get("severity", "low")
        systems_affected: list[str] = ctx.get("systems_affected", [])
        red_flags: list[str] = ctx.get("red_flags", [])
        risk_score: float = ctx.get("risk_score", 0.0)
        care_team: list[dict[str, Any]] = ctx.get("care_team", [])
        urgency: str = ctx.get("urgency", "routine")

        # Override severity based on red flags
        if red_flags:
            severity = "critical"
        elif risk_score >= 0.75:
            severity = "critical"
        elif risk_score >= 0.5:
            severity = max(severity, "high", key=lambda s: ["low", "moderate", "high", "critical"].index(s))

        # Determine escalation target
        escalation = self._build_escalation(severity, systems_affected, care_team, urgency)

        is_emergency = severity == "critical"

        # ── LLM: generate escalation rationale narrative ──────────────
        escalation_rationale: str | None = None
        try:
            prompt = (
                f"Severity: {severity}.\n"
                f"Systems affected: {', '.join(systems_affected) or 'none specified'}.\n"
                f"Red flags: {', '.join(red_flags) or 'none'}.\n"
                f"Risk score: {risk_score}.\n"
                f"Target role: {escalation['target_role']}.\n"
                f"Specialist: {escalation.get('specialist', 'none')}.\n"
                f"Response window: {escalation['response_window_minutes']} minutes.\n"
                f"Urgency: {urgency}.\n\n"
                "Explain why this clinical escalation is recommended. Include the key "
                "clinical factors driving the severity determination and why the chosen "
                "escalation target is appropriate."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical decision-support system explaining escalation "
                    "routing decisions to care team members. Be precise, cite the "
                    "relevant clinical factors, and keep the explanation concise."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            escalation_rationale = resp.content
        except Exception:
            logger.warning("LLM unavailable for escalation rationale; continuing without it.")

        if escalation_rationale:
            escalation["escalation_rationale"] = escalation_rationale

        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            status=AgentStatus.WAITING_HITL if is_emergency else AgentStatus.COMPLETED,
            confidence=0.90,
            result=escalation,
            rationale=(
                f"Escalation: {severity} severity \u2192 {escalation['target_role']} "
                f"({escalation.get('specialist', 'general')}), "
                f"response window {escalation['response_window_minutes']}min"
            ),
            requires_hitl=is_emergency,
            hitl_reason="Critical escalation requires immediate provider acknowledgement" if is_emergency else None,
        )

    def _build_escalation(
        self,
        severity: str,
        systems_affected: list[str],
        care_team: list[dict[str, Any]],
        urgency: str,
    ) -> dict[str, Any]:
        rules = ESCALATION_RULES.get(severity, ESCALATION_RULES["low"])

        # Determine specialist need
        specialist = None
        for system in systems_affected:
            if system in SYSTEM_SPECIALISTS:
                specialist = SYSTEM_SPECIALISTS[system]
                break

        # Find best care team match
        assigned_to = self._find_care_team_member(care_team, rules["target_role"], specialist)

        # Build escalation path
        escalation_path = [{"role": rules["target_role"], "assigned_to": assigned_to}]
        if rules.get("notify_supervisor"):
            supervisor = self._find_care_team_member(care_team, "attending_physician")
            escalation_path.append({"role": "supervisor", "assigned_to": supervisor})

        return {
            "severity": severity,
            "target_role": rules["target_role"],
            "alert_type": rules["alert_type"],
            "specialist": specialist,
            "assigned_to": assigned_to,
            "escalation_path": escalation_path,
            "response_window_minutes": rules["response_window_minutes"],
            "notify_supervisor": rules.get("notify_supervisor", False),
            "urgency": urgency,
            "routed_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _find_care_team_member(
        care_team: list[dict[str, Any]],
        target_role: str,
        specialist: str | None = None,
    ) -> str | None:
        """Find the best matching care team member."""
        # Try specialist match first
        if specialist:
            for member in care_team:
                role = member.get("role", "").lower()
                if specialist.lower() in role:
                    return member.get("name") or member.get("user_id")

        # Fall back to role match
        for member in care_team:
            role = member.get("role", "").lower()
            if target_role.lower() in role:
                return member.get("name") or member.get("user_id")

        return None  # No match — will need manual assignment
