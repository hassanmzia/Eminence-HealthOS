"""
Scheduling Agent — manages appointment scheduling and optimization.

Handles appointment booking, provider availability, scheduling conflicts,
and intelligent slot recommendations based on urgency and preferences.
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
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger("healthos.agent.scheduler")


class SchedulerAgent(HealthOSAgent):
    """AI-powered appointment scheduling and optimization."""

    def __init__(self):
        super().__init__(
            name="scheduler",
            tier=AgentTier.ACTION,
            description="Manages intelligent appointment scheduling and provider matching",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.PATIENT_COMMUNICATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        action = data.get("action", "suggest_slots")

        if action == "suggest_slots":
            return await self._suggest_slots(data)
        elif action == "book":
            return self._book_appointment(data)
        elif action == "reschedule":
            return self._reschedule(data)
        else:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="unknown_action",
                rationale=f"Unknown scheduling action: {action}",
                confidence=0.5,
            )

    async def _suggest_slots(self, data: dict) -> AgentOutput:
        urgency = data.get("urgency", "routine")
        visit_type = data.get("visit_type", "follow_up")
        preferred_times = data.get("preferred_times", [])

        # Generate slot suggestions (in production, queries provider availability)
        slots = self._generate_slots(urgency, visit_type)

        # --- LLM: generate scheduling rationale ---
        scheduling_rationale = None
        try:
            pref_desc = ", ".join(preferred_times) if preferred_times else "none stated"
            slot_desc = "\n".join(
                f"- {s['datetime']} ({s['duration_minutes']} min, provider: {s['provider']})"
                for s in slots
            )
            prompt = (
                f"A patient needs a {visit_type} appointment with urgency '{urgency}'.\n"
                f"Preferred times: {pref_desc}.\n\n"
                f"Suggested slots:\n{slot_desc}\n\n"
                f"Explain why these time slots and providers are recommended, "
                f"considering urgency, visit type, and patient preferences."
            )
            llm_response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=(
                        "You are a healthcare scheduling assistant. Provide clear, "
                        "concise rationale for appointment slot recommendations. "
                        "Consider clinical urgency, visit type requirements, and "
                        "patient preferences. Be specific and actionable."
                    ),
                    temperature=0.3,
                    max_tokens=1024,
                )
            )
            scheduling_rationale = llm_response.content
        except Exception:
            logger.warning(
                "LLM scheduling rationale generation failed; "
                "returning slots without narrative rationale",
                exc_info=True,
            )

        result_data = {
            "available_slots": slots,
            "urgency": urgency,
            "visit_type": visit_type,
        }
        if scheduling_rationale is not None:
            result_data["scheduling_rationale"] = scheduling_rationale

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="slots_suggested",
            rationale=f"Generated {len(slots)} slot suggestions for {urgency} {visit_type}",
            confidence=0.85,
            data=result_data,
            feature_contributions=[
                {"feature": "urgency", "contribution": 0.4, "value": urgency},
                {"feature": "visit_type", "contribution": 0.3, "value": visit_type},
                {"feature": "availability", "contribution": 0.3, "value": len(slots)},
            ],
        )

    def _book_appointment(self, data: dict) -> AgentOutput:
        slot = data.get("slot", {})
        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="appointment_booked",
            rationale=f"Appointment booked for slot: {slot.get('datetime', 'TBD')}",
            confidence=0.95,
            data={"appointment": slot, "status": "confirmed"},
        )

    def _reschedule(self, data: dict) -> AgentOutput:
        appointment_id = data.get("appointment_id")
        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="reschedule_initiated",
            rationale=f"Reschedule initiated for appointment {appointment_id}",
            confidence=0.90,
            data={"appointment_id": appointment_id, "status": "pending_reschedule"},
        )

    def _generate_slots(self, urgency: str, visit_type: str) -> list:
        from datetime import timedelta
        now = datetime.now(timezone.utc)

        offsets = {
            "emergency": [timedelta(hours=1), timedelta(hours=2)],
            "urgent": [timedelta(hours=4), timedelta(hours=8), timedelta(days=1)],
            "same_day": [timedelta(hours=2), timedelta(hours=4), timedelta(hours=6)],
            "routine": [timedelta(days=1), timedelta(days=3), timedelta(days=5), timedelta(days=7)],
        }

        return [
            {
                "datetime": (now + offset).isoformat(),
                "duration_minutes": 30 if visit_type != "new_patient" else 60,
                "provider": "auto_assigned",
                "visit_type": visit_type,
            }
            for offset in offsets.get(urgency, offsets["routine"])
        ]
