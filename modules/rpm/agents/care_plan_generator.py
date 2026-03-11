"""
Care Plan Generator Agent — Tier 4 (Intervention).

Generates AI-assisted care plans based on patient risk scores,
conditions, and agent pipeline outputs. Requires HITL approval.
"""

import logging
from datetime import datetime, timezone

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.care_plan_generator")


class CarePlanGeneratorAgent(HealthOSAgent):
    """Generates structured care plans from clinical data and agent outputs."""

    def __init__(self):
        super().__init__(
            name="care_plan_generator",
            tier=AgentTier.INTERVENTION,
            description="Generates AI-assisted care plans with goals and activities",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CARE_PLAN_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])

        # Extract risk information from prior agents
        risk_data = {}
        alerts = []
        for output in prior_outputs:
            if isinstance(output, dict):
                if output.get("agent") == "risk_scorer":
                    risk_data = output.get("data", {})
                elif output.get("decision", "").endswith("_alert"):
                    alerts.append(output)

        risk_level = risk_data.get("risk_level", data.get("risk_level", "UNKNOWN"))
        conditions = data.get("conditions", [])

        # Generate care plan components
        goals = self._generate_goals(risk_level, conditions, alerts)
        activities = self._generate_activities(risk_level, conditions, alerts)
        monitoring = self._generate_monitoring_plan(risk_level)

        care_plan = {
            "status": "draft",
            "intent": "plan",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "risk_level": risk_level,
            "goals": goals,
            "activities": activities,
            "monitoring": monitoring,
            "review_interval_days": self._review_interval(risk_level),
        }

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="care_plan_generated",
            rationale=f"Generated care plan for {risk_level} risk patient with {len(conditions)} conditions and {len(goals)} goals",
            confidence=0.75,
            data=care_plan,
            feature_contributions=[
                {"feature": "risk_level", "contribution": 0.4, "value": risk_level},
                {"feature": "conditions", "contribution": 0.3, "value": len(conditions)},
                {"feature": "active_alerts", "contribution": 0.2, "value": len(alerts)},
                {"feature": "prior_agents", "contribution": 0.1, "value": len(prior_outputs)},
            ],
            requires_hitl=True,  # Care plans always require clinician approval
            alternatives=[
                {"option": "conservative", "description": "Minimal intervention with close monitoring"},
                {"option": "aggressive", "description": "Intensive intervention with frequent follow-up"},
            ],
        )

    def _generate_goals(self, risk_level: str, conditions: list, alerts: list) -> list:
        goals = []

        if risk_level in ("HIGH", "CRITICAL"):
            goals.append({
                "description": "Stabilize clinical status within 24-48 hours",
                "priority": "high",
                "target_date_offset_days": 2,
            })

        if any("diabetes" in str(c).lower() for c in conditions):
            goals.append({
                "description": "Achieve HbA1c < 7.0% within 3 months",
                "priority": "medium",
                "target_date_offset_days": 90,
            })

        if any("hypertension" in str(c).lower() for c in conditions):
            goals.append({
                "description": "Maintain blood pressure < 140/90 mmHg",
                "priority": "medium",
                "target_date_offset_days": 30,
            })

        # Default monitoring goal
        goals.append({
            "description": "Complete all scheduled vital sign monitoring",
            "priority": "medium",
            "target_date_offset_days": 7,
        })

        return goals

    def _generate_activities(self, risk_level: str, conditions: list, alerts: list) -> list:
        activities = []

        activities.append({
            "type": "monitoring",
            "description": "Daily vital signs collection",
            "frequency": "daily" if risk_level in ("HIGH", "CRITICAL") else "weekly",
        })

        if risk_level in ("HIGH", "CRITICAL"):
            activities.append({
                "type": "consultation",
                "description": "Provider review of clinical status",
                "frequency": "daily",
            })

        activities.append({
            "type": "education",
            "description": "Patient education on condition management",
            "frequency": "weekly",
        })

        if any("diabetes" in str(c).lower() for c in conditions):
            activities.append({
                "type": "monitoring",
                "description": "Blood glucose monitoring",
                "frequency": "twice_daily" if risk_level == "CRITICAL" else "daily",
            })

        return activities

    def _generate_monitoring_plan(self, risk_level: str) -> dict:
        freq_map = {
            "CRITICAL": {"vitals": "q4h", "labs": "daily", "provider_review": "q12h"},
            "HIGH": {"vitals": "q8h", "labs": "twice_weekly", "provider_review": "daily"},
            "MEDIUM": {"vitals": "daily", "labs": "weekly", "provider_review": "twice_weekly"},
            "LOW": {"vitals": "weekly", "labs": "monthly", "provider_review": "monthly"},
        }
        return freq_map.get(risk_level, freq_map["MEDIUM"])

    def _review_interval(self, risk_level: str) -> int:
        return {"CRITICAL": 1, "HIGH": 3, "MEDIUM": 7, "LOW": 14}.get(risk_level, 7)
