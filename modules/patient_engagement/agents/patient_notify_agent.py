"""
Eminence HealthOS -- Patient Notification Agent (#59)
Layer 4 (Action): Health-literacy-adapted patient notifications.

Responsibilities:
  - Health literacy-adapted patient messages (5 levels)
  - Multi-language support (English, Spanish, Mandarin, Portuguese, Tagalog)
  - Positive, encouraging tone -- never alarming or condescending
  - Include action items and clear guidance on when to seek emergency care
  - Multi-channel: patient portal (in-app) + push + SMS + email
  - LLM-generated content with fallback templates

Adapted from InHealth Agent 21 (patient_notify_agent).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router
from healthos_platform.services.notifications.notification_manager import (
    NotificationManager,
    NotificationType,
    SendNotificationRequest,
)

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH LITERACY & LANGUAGE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

LITERACY_GUIDANCE: dict[int, str] = {
    1: (
        "Grade 1-3 reading level. Use simple pictures/diagrams if possible. "
        "Single concept per sentence. Use 'you' and 'your doctor'. Max 3 action items."
    ),
    2: (
        "Grade 4-6 reading level. Short sentences. Common everyday words. "
        "Avoid medical jargon. Clear action steps."
    ),
    3: (
        "Grade 7-9 reading level. Plain language. Brief explanations of "
        "medical terms. Numbered steps."
    ),
    4: (
        "Grade 10-12 reading level. Standard health information language. "
        "Include clinical context."
    ),
    5: (
        "College level. Full medical terminology. Detailed information. "
        "Patient is highly health-literate."
    ),
}

LANGUAGE_MAP: dict[str, str] = {
    "english": "English",
    "spanish": "Espanol (Spanish)",
    "mandarin": "Mandarin Chinese",
    "portuguese": "Portuguese",
    "tagalog": "Tagalog",
}


class PatientNotifyAgent(BaseAgent):
    """
    Agent #59: Health-literacy-adapted patient notification.

    Generates warm, supportive, and clear health messages tailored to each
    patient's reading level and preferred language.  Delivers via push,
    in-app portal, SMS, and email based on alert severity.
    """

    name = "patient_notify"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Health-literacy-adapted patient notifications -- warm, supportive "
        "messages tailored to reading level and preferred language with clear "
        "action items and emergency guidance"
    )
    min_confidence = 0.82

    def __init__(self) -> None:
        super().__init__()
        self._notification_manager = NotificationManager()

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "notify_patient")

        if action == "notify_patient":
            return await self._notify_patient(input_data)
        elif action == "send_educational":
            return await self._send_educational(input_data)
        elif action == "send_appointment_reminder":
            return await self._send_appointment_reminder(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown patient notification action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Core: Patient Health Update Notification ─────────────────────────────

    async def _notify_patient(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        patient_id = str(input_data.patient_id) if input_data.patient_id else ctx.get("patient_id", "")
        tenant_id = str(input_data.org_id)

        patient = ctx.get("patient", {})
        literacy_level = patient.get("health_literacy_level", 3)
        preferred_language = patient.get("preferred_language", "english").lower()
        patient_name = (
            patient.get("name", "there").split()[0] if patient.get("name") else "there"
        )

        alerts = ctx.get("alerts", [])
        monitoring = ctx.get("monitoring_results", {})
        interventions = ctx.get("interventions", [])
        risk_data = (
            ctx.get("risk_scores", {})
            .get("ml_ensemble_agent", {})
            .get("findings", {})
        )

        # Categorize alerts
        critical_alerts = [
            a for a in alerts if a.get("severity") in ("EMERGENCY", "CRITICAL")
        ]
        high_alerts = [a for a in alerts if a.get("severity") == "HIGH"]
        routine_alerts = [a for a in alerts if a.get("severity") in ("NORMAL", "LOW")]

        # Build enriched context
        monitoring_highlights = self._extract_monitoring_highlights(monitoring)
        action_items = self._extract_action_items(interventions, alerts)
        emergency_guidance = self._build_emergency_guidance(critical_alerts, literacy_level)

        # Generate patient message via LLM
        patient_message = await self._generate_patient_message(
            patient_id=patient_id,
            patient_name=patient_name,
            literacy_level=literacy_level,
            preferred_language=preferred_language,
            critical_alerts=critical_alerts,
            high_alerts=high_alerts,
            routine_alerts=routine_alerts,
            monitoring_highlights=monitoring_highlights,
            action_items=action_items,
            emergency_guidance=emergency_guidance,
            risk_data=risk_data,
        )

        # Determine channels based on severity
        channels_to_use = ["push", "ehr"]
        notification_type = NotificationType.ROUTINE
        if critical_alerts:
            channels_to_use.append("sms")
            notification_type = NotificationType.CRITICAL
        elif high_alerts:
            channels_to_use.append("sms")
            notification_type = NotificationType.URGENT

        request = SendNotificationRequest(
            patient_id=patient_id,
            tenant_id=tenant_id,
            notification_type=notification_type,
            title=f"Health Update for {patient_name}",
            body=patient_message[:2000],
            metadata={
                "literacy_level": literacy_level,
                "language": preferred_language,
                "critical_alert_count": len(critical_alerts),
                "high_alert_count": len(high_alerts),
            },
            agent_source=self.name,
        )

        result = await self._notification_manager.dispatch(
            request,
            patient_contacts=patient.get("contacts", {}),
        )

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_message": patient_message,
                "literacy_level": literacy_level,
                "language": preferred_language,
                "channels_sent": result.channels_sent,
                "channels_failed": result.channels_failed,
                "action_items": action_items,
                "critical_alerts_count": len(critical_alerts),
                "notification_id": result.notification_id,
            },
            confidence=0.88,
            rationale=(
                f"Patient notified via {', '.join(result.channels_sent) or 'no channels'} "
                f"(literacy level {literacy_level}, language: {preferred_language})"
            ),
        )

    # ── Educational Content ──────────────────────────────────────────────────

    async def _send_educational(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        patient_id = str(input_data.patient_id) if input_data.patient_id else ctx.get("patient_id", "")
        tenant_id = str(input_data.org_id)

        content = ctx.get("content", "")
        topic = ctx.get("topic", "health education")
        literacy_level = ctx.get("health_literacy_level", 3)

        request = SendNotificationRequest(
            patient_id=patient_id,
            tenant_id=tenant_id,
            notification_type=NotificationType.EDUCATIONAL,
            title=f"Health Education: {topic}",
            body=content[:2000],
            metadata={"topic": topic, "literacy_level": literacy_level},
            agent_source=self.name,
        )

        result = await self._notification_manager.dispatch(request)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "notification_id": result.notification_id,
                "channels_sent": result.channels_sent,
                "topic": topic,
            },
            confidence=0.90,
            rationale=f"Educational content sent: {topic}",
        )

    # ── Appointment Reminders ────────────────────────────────────────────────

    async def _send_appointment_reminder(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        patient_id = str(input_data.patient_id) if input_data.patient_id else ctx.get("patient_id", "")
        tenant_id = str(input_data.org_id)

        appointment_date = ctx.get("appointment_date", "")
        provider_name = ctx.get("provider_name", "your provider")
        location = ctx.get("location", "")
        patient_name = ctx.get("patient_name", "there")

        body = (
            f"Hello {patient_name}, this is a reminder about your upcoming "
            f"appointment with {provider_name} on {appointment_date}."
        )
        if location:
            body += f" Location: {location}."
        body += " Please arrive 15 minutes early. Contact us if you need to reschedule."

        request = SendNotificationRequest(
            patient_id=patient_id,
            tenant_id=tenant_id,
            notification_type=NotificationType.APPOINTMENT,
            title=f"Appointment Reminder - {appointment_date}",
            body=body,
            metadata={
                "appointment_date": appointment_date,
                "provider_name": provider_name,
                "location": location,
            },
            agent_source=self.name,
        )

        result = await self._notification_manager.dispatch(request)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "notification_id": result.notification_id,
                "channels_sent": result.channels_sent,
                "appointment_date": appointment_date,
            },
            confidence=0.95,
            rationale=f"Appointment reminder sent for {appointment_date}",
        )

    # ── LLM Content Generation ───────────────────────────────────────────────

    async def _generate_patient_message(
        self,
        patient_id: str,
        patient_name: str,
        literacy_level: int,
        preferred_language: str,
        critical_alerts: list[dict[str, Any]],
        high_alerts: list[dict[str, Any]],
        routine_alerts: list[dict[str, Any]],
        monitoring_highlights: str,
        action_items: list[str],
        emergency_guidance: str,
        risk_data: dict[str, Any],
    ) -> str:
        """Generate a patient-appropriate health message via LLM."""
        literacy_guidance = LITERACY_GUIDANCE.get(literacy_level, LITERACY_GUIDANCE[3])
        language_name = LANGUAGE_MAP.get(preferred_language, "English")
        language_instruction = (
            f"Write in {language_name}." if preferred_language != "english" else ""
        )

        action_items_str = "\n".join(
            [f"  {i + 1}. {item}" for i, item in enumerate(action_items[:5])]
        )

        prompt = (
            f"Generate a patient health update message for patient {patient_id} "
            f"(call them '{patient_name}'):\n\n"
            f"Literacy guidance: {literacy_guidance}\n"
            f"Language: {language_instruction}\n\n"
            f"Health update context:\n"
            f"  Today's monitoring highlights: {monitoring_highlights}\n"
            f"  Critical concerns: {len(critical_alerts)} (severe, needing immediate action)\n"
            f"  Health alerts: {len(high_alerts)} (important, need attention today)\n"
            f"  Routine updates: {len(routine_alerts)}\n"
            f"  Risk level: {risk_data.get('risk_level', 'Not assessed')}\n\n"
            f"Action items for patient:\n{action_items_str}\n\n"
            f"Emergency guidance to include:\n{emergency_guidance}\n\n"
            f"Create a patient message with:\n"
            f"1. Warm, personal greeting using patient's first name\n"
            f"2. Brief summary of their health today (positive framing where appropriate)\n"
            f"3. What's going well (celebrate progress!)\n"
            f"4. What needs attention (clear, calm, specific)\n"
            f"5. Action items (3-5 maximum, numbered, simple)\n"
            f"6. When to call 911 or go to ER (clear criteria)\n"
            f"7. Encouraging closing message\n\n"
            f"Tone: warm, supportive, empowering. Never alarming. Never condescending."
        )

        try:
            llm_response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=(
                        "You are the Patient Notification AI Agent for HealthOS. "
                        "You generate warm, supportive, and clear health messages for patients. "
                        "Adapt your language to the patient's health literacy level and preferred language. "
                        "Always end with specific action items and clear guidance on when to call 911 "
                        "or seek emergency care. Use motivational, empowering language. Avoid medical "
                        "jargon unless literacy level is high. Never create fear or panic -- be calm, "
                        "informative, and solution-focused."
                    ),
                    temperature=0.3,
                    max_tokens=1024,
                )
            )
            return llm_response.content
        except Exception as exc:
            logger.warning("patient_notify.llm_failed", error=str(exc))
            return self._fallback_patient_message(
                patient_name, literacy_level, critical_alerts, action_items
            )

    # ── Helper Methods ───────────────────────────────────────────────────────

    def _extract_monitoring_highlights(self, monitoring: dict[str, Any]) -> str:
        highlights: list[str] = []

        glucose = monitoring.get("glucose_agent", {}).get("findings", {})
        if glucose:
            tir = glucose.get("tir_stats", {}).get("tir_percent", "N/A")
            current = glucose.get("current_glucose_mgdl", "N/A")
            highlights.append(f"Blood sugar: {current} mg/dL (time in range: {tir}%)")

        activity = monitoring.get("activity_agent", {}).get("findings", {})
        if activity:
            steps = activity.get("today_steps", 0)
            highlights.append(f"Steps today: {steps:,.0f}")

        cardiac = monitoring.get("cardiac_agent", {}).get("findings", {})
        if cardiac:
            bp_s = cardiac.get("blood_pressure_systolic", "?")
            bp_d = cardiac.get("blood_pressure_diastolic", "?")
            highlights.append(f"Blood pressure: {bp_s}/{bp_d} mmHg")

        return "; ".join(highlights) or "Monitoring data collected"

    def _extract_action_items(
        self,
        interventions: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
    ) -> list[str]:
        items: list[str] = []
        for intervention in interventions:
            if intervention.get("type") == "lifestyle":
                recs = intervention.get("recommendations", [])
                items.extend(recs[:2])
        for alert in alerts[:3]:
            if alert.get("severity") in ("HIGH", "NORMAL"):
                items.append(alert.get("message", "")[:80])
        return items[:5]

    def _build_emergency_guidance(
        self,
        critical_alerts: list[dict[str, Any]],
        literacy_level: int,
    ) -> str:
        if literacy_level <= 2:
            return (
                "Call 911 if you: can't breathe, have chest pain, "
                "feel very dizzy, or pass out."
            )
        elif literacy_level <= 3:
            return (
                "Go to the ER or call 911 if you have: chest pain or pressure, "
                "difficulty breathing, sudden severe headache, signs of low blood "
                "sugar that don't improve with sugar intake."
            )
        return (
            "Seek emergency care (call 911) for: chest pain/pressure, dyspnea at "
            "rest, severe hypoglycemia unresponsive to treatment, neurological "
            "symptoms (FAST: face drooping, arm weakness, speech difficulty, time "
            "to call 911), or any rapidly worsening symptom."
        )

    def _fallback_patient_message(
        self,
        name: str,
        literacy: int,
        critical: list[dict[str, Any]],
        actions: list[str],
    ) -> str:
        if literacy <= 2:
            msg = f"Hello {name}! We checked your health today. "
            if critical:
                msg += "Something needs attention right away. Call your doctor now. "
            else:
                msg += "Things look okay. Keep taking your medicine. "
            msg += "We are here for you!"
            return msg
        return (
            f"Hello {name}, your HealthOS care team has reviewed your health data today. "
            + (
                "We've identified some areas that need attention. "
                if critical
                else "Your readings are being monitored. "
            )
            + "Action items: "
            + "; ".join(actions[:3])
            + ". "
            + "Contact us or call 911 if you feel unsafe."
        )
