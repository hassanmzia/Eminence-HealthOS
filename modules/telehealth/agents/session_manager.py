"""
Telehealth Session Manager Agent — manages virtual visit lifecycle.

Handles session creation, provider matching, waiting room management,
and post-visit documentation routing.
"""

import logging
import uuid
from datetime import datetime, timezone

from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.session_manager")


class SessionManagerAgent(HealthOSAgent):
    """Manages telehealth session lifecycle."""

    def __init__(self):
        super().__init__(
            name="session_manager",
            tier=AgentTier.ACTION,
            description="Manages telehealth session creation, routing, and documentation",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.PATIENT_COMMUNICATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        action = data.get("action", "create")  # create, join, end, status

        if action == "create":
            return await self._create_session(agent_input)
        elif action == "end":
            return await self._end_session(agent_input)
        else:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="session_status",
                rationale=f"Session status check for action: {action}",
                confidence=0.90,
                data={"action": action, "session_id": data.get("session_id")},
            )

    async def _create_session(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        session_id = str(uuid.uuid4())
        visit_type = data.get("visit_type", "follow_up")
        urgency = data.get("urgency", "routine")

        session = {
            "session_id": session_id,
            "patient_id": agent_input.patient_id,
            "visit_type": visit_type,
            "urgency": urgency,
            "status": "waiting",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "estimated_wait_minutes": self._estimate_wait(urgency),
        }

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="session_created",
            rationale=f"Telehealth session created (type: {visit_type}, urgency: {urgency})",
            confidence=0.95,
            data=session,
            feature_contributions=[
                {"feature": "visit_type", "contribution": 0.4, "value": visit_type},
                {"feature": "urgency", "contribution": 0.4, "value": urgency},
                {"feature": "availability", "contribution": 0.2, "value": "checked"},
            ],
        )

    async def _end_session(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        session_id = data.get("session_id", "unknown")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="session_ended",
            rationale=f"Session {session_id} ended — routing to documentation",
            confidence=0.95,
            data={
                "session_id": session_id,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "next_steps": ["generate_visit_summary", "schedule_follow_up"],
            },
            downstream_agents=["clinical_summarizer"],
        )

    def _estimate_wait(self, urgency: str) -> int:
        return {"urgent": 5, "same_day": 15, "routine": 30, "scheduled": 0}.get(urgency, 30)
