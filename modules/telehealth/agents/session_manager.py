"""
Eminence HealthOS — Telehealth Session Manager Agent
Layer 4 (Action): Manages virtual visit lifecycle — session creation,
provider matching, waiting room management, and post-visit routing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    PipelineState,
)


class SessionManagerAgent(BaseAgent):
    name = "session_manager"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Manages telehealth session creation, routing, and documentation"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        data = input_data.context
        action = data.get("action", "create")

        if action == "create":
            return self._create_session(input_data)
        elif action == "end":
            return self._end_session(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"action": action, "session_id": data.get("session_id")},
                confidence=0.90,
                rationale=f"Session status check for action: {action}",
            )

    def _create_session(self, input_data: AgentInput) -> AgentOutput:
        data = input_data.context
        session_id = str(uuid.uuid4())
        visit_type = data.get("visit_type", "follow_up")
        urgency = data.get("urgency", "routine")

        session: dict[str, Any] = {
            "session_id": session_id,
            "patient_id": str(input_data.patient_id),
            "visit_type": visit_type,
            "urgency": urgency,
            "status": "waiting",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "estimated_wait_minutes": self._estimate_wait(urgency),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=session,
            confidence=0.95,
            rationale=f"Telehealth session created (type: {visit_type}, urgency: {urgency})",
        )

    def _end_session(self, input_data: AgentInput) -> AgentOutput:
        data = input_data.context
        session_id = data.get("session_id", "unknown")

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "session_id": session_id,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "next_steps": ["generate_visit_summary", "schedule_follow_up"],
            },
            confidence=0.95,
            rationale=f"Session {session_id} ended — routing to documentation",
        )

    @staticmethod
    def _estimate_wait(urgency: str) -> int:
        return {"urgent": 5, "same_day": 15, "routine": 30, "scheduled": 0}.get(urgency, 30)
