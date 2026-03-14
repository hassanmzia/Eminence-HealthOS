"""
Alert Manager Agent — Tier 5 (Action).

Manages clinical alert lifecycle: creation, escalation, routing,
and notification delivery based on severity and provider preferences.
"""

import logging
from datetime import datetime, timezone

from healthos_platform.ml.llm.router import llm_router, LLMRequest

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.alert_manager")

# Escalation timing by severity (minutes)
ESCALATION_TIMINGS = {
    "EMERGENCY": [0, 5, 10],     # Immediate, 5min, 10min
    "CRITICAL": [0, 15, 30],
    "HIGH": [5, 30, 60],
    "MEDIUM": [15, 60, 240],
    "LOW": [60, 480],
}


class AlertManagerAgent(HealthOSAgent):
    """Manages clinical alerts — creation, escalation, and routing."""

    def __init__(self):
        super().__init__(
            name="alert_manager",
            tier=AgentTier.ACTION,
            description="Creates, routes, and escalates clinical alerts",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.ALERT_GENERATION, AgentCapability.PATIENT_COMMUNICATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])

        # Collect alerts from prior agent outputs
        alerts_to_create = []
        for output in prior_outputs:
            if isinstance(output, dict):
                decision = output.get("decision", "")
                if decision in ("critical_alert", "abnormal_alert", "safety_concern", "critical_lab"):
                    alerts_to_create.append({
                        "source_agent": output.get("agent", "unknown"),
                        "severity": output.get("data", {}).get("severity", "MEDIUM"),
                        "title": self._generate_title(output),
                        "message": output.get("rationale", ""),
                        "category": self._categorize(output),
                        "data": output.get("data", {}),
                    })

        # Also accept direct alert requests
        if data.get("create_alert"):
            alerts_to_create.append({
                "source_agent": data.get("source", "manual"),
                "severity": data.get("severity", "MEDIUM"),
                "title": data.get("title", "Manual alert"),
                "message": data.get("message", ""),
                "category": data.get("category", "general"),
                "data": data,
            })

        if not alerts_to_create:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_alerts",
                rationale="No actionable alerts from pipeline outputs",
                confidence=0.95,
            )

        # Determine notification channels per alert
        for alert in alerts_to_create:
            alert["notifications"] = self._plan_notifications(alert["severity"])
            alert["escalation_plan"] = ESCALATION_TIMINGS.get(alert["severity"], [60])

        # Persist alerts
        created_count = await self._create_alerts(agent_input, alerts_to_create)

        max_severity = max(
            alerts_to_create,
            key=lambda a: self._severity_rank(a["severity"]),
        )["severity"]

        # LLM enhancement: generate recommended actions for the provider
        recommended_action = ""
        try:
            alert_summaries = [
                {
                    "severity": a["severity"],
                    "title": a["title"],
                    "category": a["category"],
                    "message": a["message"],
                }
                for a in alerts_to_create
            ]
            prompt = (
                f"Based on these clinical alerts, provide a concise recommended action "
                f"for the provider:\n\n"
                f"Patient ID: {agent_input.patient_id}\n"
                f"Alerts: {alert_summaries}\n"
                f"Maximum severity: {max_severity}\n\n"
                f"Provide specific, actionable next steps in 2-3 sentences."
            )
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system="You are a clinical decision support system. Recommend specific, "
                       "evidence-based actions for providers based on clinical alert severity "
                       "and patient context. Be concise and prioritize patient safety.",
                temperature=0.3,
                max_tokens=1024,
            ))
            recommended_action = llm_response.content
        except Exception as e:
            logger.warning("LLM call failed for recommended action, skipping enhancement: %s", e)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="alerts_created",
            rationale=f"Created {created_count} alert(s), max severity: {max_severity}",
            confidence=0.90,
            data={
                "alerts_created": created_count,
                "alerts": alerts_to_create,
                "max_severity": max_severity,
                "recommended_action": recommended_action,
            },
            feature_contributions=[
                {"feature": "pipeline_alerts", "contribution": 0.6, "value": len(alerts_to_create)},
                {"feature": "max_severity", "contribution": 0.3, "value": max_severity},
                {"feature": "patient_context", "contribution": 0.1, "value": agent_input.patient_id},
            ],
            requires_hitl=max_severity in ("CRITICAL", "EMERGENCY"),
        )

    async def _create_alerts(self, agent_input: AgentInput, alerts: list) -> int:
        """Persist alerts to the database."""
        created = 0
        try:
            from healthos_platform.config.database import get_db_context
            from shared.models.alert import ClinicalAlert

            async with get_db_context() as db:
                for alert_data in alerts:
                    alert = ClinicalAlert(
                        tenant_id=agent_input.tenant_id,
                        patient_id=agent_input.patient_id,
                        severity=alert_data["severity"],
                        category=alert_data["category"],
                        alert_type=f"{alert_data['source_agent']}_{alert_data['category']}",
                        title=alert_data["title"],
                        message=alert_data["message"],
                        details=alert_data.get("data", {}),
                        source_agent=alert_data["source_agent"],
                        status="active",
                        notifications_sent=alert_data.get("notifications", []),
                    )
                    db.add(alert)
                    created += 1
        except Exception as e:
            logger.error("Failed to persist alerts: %s", e)

        return created

    def _generate_title(self, output: dict) -> str:
        data = output.get("data", {})
        agent = output.get("agent", "unknown")
        if "vital_name" in data:
            return f"{data['vital_name']} {data.get('interpretation', 'abnormal')}"
        if "lab_name" in data:
            return f"{data['lab_name']} abnormal result"
        if "medication" in data:
            return f"Medication safety concern: {data['medication']}"
        return f"Clinical alert from {agent}"

    def _categorize(self, output: dict) -> str:
        agent = output.get("agent", "")
        if "vital" in agent:
            return "vital_sign"
        if "lab" in agent:
            return "lab_result"
        if "medication" in agent:
            return "medication"
        if "risk" in agent:
            return "risk_score"
        return "general"

    def _plan_notifications(self, severity: str) -> list:
        channels = ["in_app"]
        if severity in ("HIGH", "CRITICAL", "EMERGENCY"):
            channels.append("push_notification")
        if severity in ("CRITICAL", "EMERGENCY"):
            channels.extend(["sms", "pager"])
        return channels

    def _severity_rank(self, severity: str) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3, "EMERGENCY": 4}.get(severity, 0)
