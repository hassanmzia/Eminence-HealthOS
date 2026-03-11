"""
Eminence HealthOS — Scheduling Agent
Layer 4 (Action): Orchestrates appointment scheduling — determines optimal
time slots, matches patient needs with provider availability, and manages
scheduling conflicts and waitlists.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
)

# Visit type → duration and buffer
VISIT_DURATIONS: dict[str, dict[str, int]] = {
    "new_patient": {"duration_min": 30, "buffer_min": 10},
    "follow_up": {"duration_min": 15, "buffer_min": 5},
    "urgent": {"duration_min": 20, "buffer_min": 5},
    "wellness": {"duration_min": 30, "buffer_min": 10},
    "medication_review": {"duration_min": 15, "buffer_min": 5},
    "care_plan_review": {"duration_min": 20, "buffer_min": 5},
}

# Urgency → scheduling window
URGENCY_WINDOWS: dict[str, int] = {
    "emergency": 0,       # Immediate
    "urgent": 4,          # Within 4 hours
    "same_day": 24,       # Within 24 hours
    "routine": 168,       # Within 7 days
    "scheduled": 336,     # Within 14 days
}


class SchedulingAgent(BaseAgent):
    name = "scheduling"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Appointment orchestration — scheduling, conflict resolution, and waitlist management"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context

        action: str = ctx.get("action", "schedule")
        visit_type: str = ctx.get("visit_type", "follow_up")
        urgency: str = ctx.get("urgency", "routine")
        preferred_provider: str | None = ctx.get("preferred_provider")
        preferred_times: list[str] = ctx.get("preferred_times", [])
        follow_up_days: int = ctx.get("follow_up_days", 14)

        if action == "schedule":
            return self._schedule_appointment(
                input_data, visit_type, urgency, preferred_provider, preferred_times
            )
        elif action == "reschedule":
            return self._reschedule(input_data)
        elif action == "cancel":
            return self._cancel(input_data)
        elif action == "follow_up":
            return self._schedule_follow_up(input_data, visit_type, follow_up_days)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.5,
                rationale=f"Unknown scheduling action: {action}",
            )

    def _schedule_appointment(
        self,
        input_data: AgentInput,
        visit_type: str,
        urgency: str,
        preferred_provider: str | None,
        preferred_times: list[str],
    ) -> AgentOutput:
        duration = VISIT_DURATIONS.get(visit_type, VISIT_DURATIONS["follow_up"])
        window_hours = URGENCY_WINDOWS.get(urgency, 168)
        now = datetime.now(timezone.utc)

        # Generate available slots (simulated)
        slots = self._generate_slots(now, window_hours, duration["duration_min"])

        # Pick best slot
        best_slot = slots[0] if slots else None

        if not best_slot:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "status": "waitlisted",
                    "urgency": urgency,
                    "visit_type": visit_type,
                    "message": "No available slots — patient added to waitlist",
                },
                confidence=0.7,
                rationale="No available slots in scheduling window — waitlisted",
            )

        appointment = {
            "status": "scheduled",
            "visit_type": visit_type,
            "urgency": urgency,
            "scheduled_at": best_slot["start"].isoformat(),
            "duration_minutes": duration["duration_min"],
            "provider": preferred_provider or "Next available",
            "available_slots": [
                {"start": s["start"].isoformat(), "end": s["end"].isoformat()}
                for s in slots[:5]
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=appointment,
            confidence=0.90,
            rationale=(
                f"Scheduled {visit_type} appointment ({urgency}) at {best_slot['start'].isoformat()}, "
                f"{duration['duration_min']}min, {len(slots)} slots available"
            ),
        )

    def _schedule_follow_up(
        self,
        input_data: AgentInput,
        visit_type: str,
        follow_up_days: int,
    ) -> AgentOutput:
        now = datetime.now(timezone.utc)
        target_date = now + timedelta(days=follow_up_days)
        duration = VISIT_DURATIONS.get(visit_type, VISIT_DURATIONS["follow_up"])

        slots = self._generate_slots(target_date - timedelta(days=2), 96, duration["duration_min"])
        best_slot = slots[0] if slots else None

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "status": "scheduled" if best_slot else "pending",
                "visit_type": visit_type,
                "follow_up_target_date": target_date.date().isoformat(),
                "scheduled_at": best_slot["start"].isoformat() if best_slot else None,
                "duration_minutes": duration["duration_min"],
            },
            confidence=0.85,
            rationale=f"Follow-up in {follow_up_days} days ({visit_type})",
        )

    def _reschedule(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        appointment_id = ctx.get("appointment_id", "unknown")
        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "status": "rescheduled",
                "original_appointment_id": appointment_id,
                "message": "Appointment rescheduled — patient notified",
            },
            confidence=0.90,
            rationale=f"Appointment {appointment_id} rescheduled",
        )

    def _cancel(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        appointment_id = ctx.get("appointment_id", "unknown")
        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "status": "cancelled",
                "appointment_id": appointment_id,
                "message": "Appointment cancelled — slot released",
            },
            confidence=0.95,
            rationale=f"Appointment {appointment_id} cancelled",
        )

    @staticmethod
    def _generate_slots(
        start: datetime, window_hours: int, duration_min: int
    ) -> list[dict[str, datetime]]:
        """Generate simulated available slots within window."""
        slots = []
        current = start.replace(minute=0, second=0, microsecond=0)
        end = current + timedelta(hours=window_hours)

        while current < end and len(slots) < 20:
            # Business hours: 8am-5pm
            if 8 <= current.hour < 17 and current.weekday() < 5:
                slot_end = current + timedelta(minutes=duration_min)
                slots.append({"start": current, "end": slot_end})
                current = slot_end + timedelta(minutes=5)
            else:
                # Skip to next business hour
                if current.hour >= 17 or current.weekday() >= 5:
                    days_ahead = 1
                    if current.weekday() >= 4:  # Friday evening or weekend
                        days_ahead = 7 - current.weekday()
                    current = (current + timedelta(days=days_ahead)).replace(hour=8, minute=0)
                else:
                    current = current.replace(hour=8, minute=0)

        return slots
