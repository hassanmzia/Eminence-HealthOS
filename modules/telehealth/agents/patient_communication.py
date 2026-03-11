"""
Eminence HealthOS — Patient Communication Agent
Layer 4 (Action): Automates patient messaging — appointment reminders,
follow-up instructions, medication reminders, and care plan notifications.
Generates multi-channel messages (SMS, email, in-app) using templates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
)

# Message templates
TEMPLATES: dict[str, str] = {
    "appointment_reminder": (
        "Hi {patient_name}, this is a reminder about your {visit_type} appointment "
        "scheduled for {scheduled_time}. Please ensure you have a stable internet "
        "connection for your telehealth visit."
    ),
    "follow_up_instructions": (
        "Hi {patient_name}, following your recent visit, please remember to: "
        "{instructions}. Contact us if your symptoms worsen."
    ),
    "vitals_reminder": (
        "Hi {patient_name}, it's time to submit your {vital_types} readings. "
        "Regular monitoring helps your care team track your progress."
    ),
    "medication_reminder": (
        "Hi {patient_name}, this is a reminder to take your medication: "
        "{medication_name} ({dosage}). Please log your adherence."
    ),
    "care_plan_update": (
        "Hi {patient_name}, your care plan has been updated by your provider. "
        "Key changes: {changes}. Please review in your patient portal."
    ),
    "alert_notification": (
        "Hi {patient_name}, your care team has been notified about a change in "
        "your health readings. A team member will follow up with you shortly."
    ),
}

# Communication channel selection by urgency
CHANNEL_BY_URGENCY: dict[str, list[str]] = {
    "emergency": ["phone", "sms", "in_app"],
    "urgent": ["sms", "in_app", "email"],
    "routine": ["in_app", "email"],
    "informational": ["in_app"],
}


class PatientCommunicationAgent(BaseAgent):
    name = "patient_communication"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Automated multi-channel patient messaging and communication"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context

        message_type: str = ctx.get("message_type", "follow_up_instructions")
        urgency: str = ctx.get("urgency", "routine")
        patient_name: str = ctx.get("patient_name", "Patient")
        template_vars: dict[str, str] = ctx.get("template_vars", {})
        preferred_channels: list[str] = ctx.get("preferred_channels", [])

        # Select channels
        channels = preferred_channels or CHANNEL_BY_URGENCY.get(urgency, ["in_app"])

        # Generate message
        message = self._render_message(message_type, patient_name, template_vars)

        # Build communication plan
        comm_plan: list[dict[str, Any]] = []
        for channel in channels:
            comm_plan.append({
                "channel": channel,
                "message": message,
                "status": "queued",
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
            })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "message_type": message_type,
                "message": message,
                "channels": channels,
                "communication_plan": comm_plan,
                "urgency": urgency,
            },
            confidence=0.92,
            rationale=(
                f"Communication queued: {message_type} via {', '.join(channels)} "
                f"({urgency} priority)"
            ),
        )

    @staticmethod
    def _render_message(
        message_type: str,
        patient_name: str,
        template_vars: dict[str, str],
    ) -> str:
        template = TEMPLATES.get(message_type, TEMPLATES["follow_up_instructions"])
        vars_with_name = {"patient_name": patient_name, **template_vars}
        try:
            return template.format(**vars_with_name)
        except KeyError:
            # Fallback: fill what we can
            for key in vars_with_name:
                template = template.replace(f"{{{key}}}", vars_with_name[key])
            return template
