"""
Patient Communication Agent — Tier 5 (Action).

Generates patient-friendly messages, education content, reminders,
and notification delivery. Adapts language to patient health literacy.
"""

import json
import logging

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.patient_communicator")


class PatientCommunicatorAgent(HealthOSAgent):
    """Generates and delivers patient-facing communications."""

    def __init__(self):
        super().__init__(
            name="patient_communicator",
            tier=AgentTier.ACTION,
            description="Generates patient-friendly messages, reminders, and education content",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.PATIENT_COMMUNICATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])
        comm_type = data.get("type", "auto")  # auto, reminder, education, alert_summary, results

        messages = []

        if comm_type == "auto":
            # Auto-generate based on pipeline outputs
            messages = self._auto_generate(prior_outputs, data)
        elif comm_type == "reminder":
            messages = [self._medication_reminder(data)]
        elif comm_type == "education":
            messages = [self._education_content(data)]
        elif comm_type == "alert_summary":
            messages = [self._alert_summary_for_patient(prior_outputs)]
        elif comm_type == "results":
            messages = [self._results_notification(data)]

        if not messages:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_communication_needed",
                rationale="No patient communications generated from current context",
                confidence=0.90,
            )

        # --- LLM: generate empathetic, health-literate patient message ---
        patient_message = None
        try:
            prompt = (
                "You are a compassionate patient communication specialist. "
                "Given the following messages that will be sent to a patient, "
                "generate a single cohesive, empathetic, health-literate summary message "
                "that a patient can easily understand. Use plain language (6th-grade reading level), "
                "show empathy, and include clear next steps.\n\n"
                f"Messages to combine:\n{json.dumps(messages, indent=2)}\n\n"
                f"Communication type: {comm_type}\n"
                f"Number of prior clinical outputs: {len(prior_outputs)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a patient communication specialist for a healthcare system. "
                    "Write warm, clear messages that patients can understand regardless of "
                    "health literacy level. Avoid medical jargon. Be reassuring but accurate."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            patient_message = resp.content
        except Exception:
            logger.warning("LLM patient_message generation failed; continuing without it")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="communications_generated",
            rationale=f"Generated {len(messages)} patient communication(s)",
            confidence=0.85,
            data={
                "messages": messages,
                "count": len(messages),
                "channels": list(set(m.get("channel", "in_app") for m in messages)),
                "patient_message": patient_message,
            },
            feature_contributions=[
                {"feature": "pipeline_events", "contribution": 0.4, "value": len(prior_outputs)},
                {"feature": "comm_type", "contribution": 0.3, "value": comm_type},
                {"feature": "patient_context", "contribution": 0.3, "value": "demographics"},
            ],
        )

    def _auto_generate(self, prior_outputs: list, data: dict) -> list:
        messages = []
        for output in prior_outputs:
            if not isinstance(output, dict):
                continue
            decision = output.get("decision", "")
            if decision == "care_plan_generated":
                messages.append({
                    "title": "Your Care Plan Has Been Updated",
                    "body": "Your care team has created an updated care plan. "
                           "Please review the goals and activities in your patient portal.",
                    "channel": "push_notification",
                    "priority": "normal",
                })
            elif "alert" in decision and output.get("data", {}).get("severity") in ("HIGH", "CRITICAL"):
                messages.append({
                    "title": "Important Health Update",
                    "body": "Your care team has been notified about a change in your health readings. "
                           "Please follow any instructions provided and contact your care team if you have questions.",
                    "channel": "sms",
                    "priority": "high",
                })
        return messages

    def _medication_reminder(self, data: dict) -> dict:
        med = data.get("medication", "your medication")
        time = data.get("time", "as scheduled")
        return {
            "title": "Medication Reminder",
            "body": f"It's time to take {med} ({time}). "
                   "If you have any side effects, please contact your care team.",
            "channel": "push_notification",
            "priority": "normal",
        }

    def _education_content(self, data: dict) -> dict:
        topic = data.get("topic", "general health")
        return {
            "title": f"Health Education: {topic.title()}",
            "body": f"Your care team has shared educational resources about {topic}. "
                   "Please review them in your patient portal.",
            "channel": "in_app",
            "priority": "low",
        }

    def _alert_summary_for_patient(self, prior_outputs: list) -> dict:
        alert_count = sum(
            1 for o in prior_outputs
            if isinstance(o, dict) and "alert" in o.get("decision", "")
        )
        return {
            "title": "Health Monitoring Update",
            "body": f"Your monitoring devices recorded {alert_count} reading(s) that "
                   "your care team is reviewing. No action is needed from you at this time.",
            "channel": "push_notification",
            "priority": "normal",
        }

    def _results_notification(self, data: dict) -> dict:
        result_type = data.get("result_type", "lab results")
        return {
            "title": f"New {result_type.title()} Available",
            "body": f"Your {result_type} are now available in your patient portal. "
                   "Your care team will follow up if any action is needed.",
            "channel": "push_notification",
            "priority": "normal",
        }
