"""
Triage Agent — Tier 3 (Risk).

Performs clinical triage based on symptom assessment, vital signs,
and risk scores. Routes patients to appropriate care levels.
"""

import logging
from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.triage")

# ESI (Emergency Severity Index) levels
ESI_LEVELS = {
    1: {"name": "Resuscitation", "description": "Immediate life-saving intervention", "response": "immediate"},
    2: {"name": "Emergent", "description": "High risk or confused/lethargic/disoriented", "response": "within_10min"},
    3: {"name": "Urgent", "description": "Two or more resources needed", "response": "within_30min"},
    4: {"name": "Less Urgent", "description": "One resource needed", "response": "within_60min"},
    5: {"name": "Non-Urgent", "description": "No resources needed", "response": "within_120min"},
}


class TriageAgent(HealthOSAgent):
    """Performs clinical triage and care-level routing."""

    def __init__(self):
        super().__init__(
            name="triage_agent",
            tier=AgentTier.RISK,
            description="Clinical triage assessment with ESI-based severity classification",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.TRIAGE, AgentCapability.RISK_SCORING]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])

        # Gather signals
        chief_complaint = data.get("chief_complaint", "")
        symptoms = data.get("symptoms", [])
        risk_score = None
        max_alert_severity = "LOW"

        for output in prior_outputs:
            if isinstance(output, dict):
                if output.get("agent") == "risk_scorer":
                    risk_score = output.get("data", {}).get("news2_score")
                alert_sev = output.get("data", {}).get("severity")
                if alert_sev and self._severity_rank(alert_sev) > self._severity_rank(max_alert_severity):
                    max_alert_severity = alert_sev

        # Determine ESI level
        esi_level = self._determine_esi(
            chief_complaint, symptoms, risk_score, max_alert_severity
        )
        esi_info = ESI_LEVELS[esi_level]

        # Route to care level
        care_level = self._route_care_level(esi_level)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=f"triage_esi_{esi_level}",
            rationale=f"ESI Level {esi_level} ({esi_info['name']}): {esi_info['description']}. "
                      f"Recommended care: {care_level['description']}",
            confidence=0.80,
            data={
                "esi_level": esi_level,
                "esi_name": esi_info["name"],
                "response_time": esi_info["response"],
                "care_level": care_level,
                "chief_complaint": chief_complaint,
                "contributing_factors": {
                    "risk_score": risk_score,
                    "alert_severity": max_alert_severity,
                    "symptom_count": len(symptoms),
                },
            },
            feature_contributions=[
                {"feature": "risk_score", "contribution": 0.35, "value": risk_score},
                {"feature": "alert_severity", "contribution": 0.30, "value": max_alert_severity},
                {"feature": "symptoms", "contribution": 0.20, "value": len(symptoms)},
                {"feature": "chief_complaint", "contribution": 0.15, "value": chief_complaint},
            ],
            requires_hitl=esi_level <= 2,
            risk_level=["low", "low", "medium", "high", "critical"][min(5 - esi_level, 4)],
            downstream_agents=["care_plan_generator", "alert_manager"] if esi_level <= 3 else [],
        )

    def _determine_esi(self, complaint: str, symptoms: list, risk_score, max_severity: str) -> int:
        # Critical signals → ESI 1
        critical_keywords = ["unresponsive", "cardiac arrest", "not breathing", "seizure", "hemorrhage"]
        if any(kw in complaint.lower() for kw in critical_keywords):
            return 1

        # High risk → ESI 2
        if max_severity in ("CRITICAL", "EMERGENCY") or (risk_score and risk_score >= 7):
            return 2

        # Multiple urgent signals → ESI 3
        urgent_keywords = ["chest pain", "shortness of breath", "severe pain", "confusion", "fever"]
        urgent_count = sum(1 for kw in urgent_keywords if kw in complaint.lower())
        if urgent_count >= 1 or max_severity == "HIGH" or (risk_score and risk_score >= 5):
            return 3

        # Some concerns → ESI 4
        if symptoms or max_severity == "MEDIUM" or (risk_score and risk_score >= 3):
            return 4

        # Otherwise → ESI 5
        return 5

    def _route_care_level(self, esi_level: int) -> dict:
        routing = {
            1: {"level": "emergency", "description": "Emergency department — immediate physician"},
            2: {"level": "emergency", "description": "Emergency department — urgent evaluation"},
            3: {"level": "urgent_care", "description": "Urgent care or same-day clinic visit"},
            4: {"level": "primary_care", "description": "Primary care appointment within 24-48h"},
            5: {"level": "self_care", "description": "Self-care with telehealth follow-up"},
        }
        return routing.get(esi_level, routing[5])

    def _severity_rank(self, severity: str) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3, "EMERGENCY": 4}.get(severity, 0)
