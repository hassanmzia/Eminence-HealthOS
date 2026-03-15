"""
Eminence HealthOS -- Physician Notification Agent (#58)
Layer 4 (Action): Priority-based physician notification and escalation.

Responsibilities:
  - Priority-based physician notification (CRITICAL / URGENT / SOON / ROUTINE)
  - Multi-channel delivery: in-app, push, SMS, email, EHR inbox
  - Generate concise, actionable alerts with patient summary, findings,
    and recommended actions
  - Track acknowledgment and escalate if unacknowledged
    (CRITICAL: 5 min, URGENT: 30 min)
  - LLM-generated notification content with fallback templates

Adapted from InHealth Agent 20 (physician_notify_agent).
"""

from __future__ import annotations

import json
import logging
import os
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

# Escalation timeouts (seconds)
ESCALATION_TIMEOUTS: dict[str, int] = {
    "CRITICAL": 300,    # 5 minutes
    "URGENT": 1800,     # 30 minutes
    "SOON": 14400,      # 4 hours
    "ROUTINE": 86400,   # 24 hours
}

NOTIFICATION_PRIORITY_MAP: dict[str, str] = {
    "EMERGENCY": "CRITICAL",
    "HIGH": "URGENT",
    "NORMAL": "SOON",
    "LOW": "ROUTINE",
}

# Channel selection by priority
PHYSICIAN_CHANNEL_MAP: dict[str, list[str]] = {
    "CRITICAL": ["sms", "push", "ehr"],
    "URGENT": ["push", "ehr", "email"],
    "SOON": ["ehr", "email"],
    "ROUTINE": ["ehr", "email"],
}


class PhysicianNotifyAgent(BaseAgent):
    """
    Agent #58: Priority-based physician notification and escalation.

    Generates concise, clinically appropriate physician notifications from
    pipeline alerts and interventions, dispatches across appropriate channels,
    and schedules acknowledgment monitoring with escalation.
    """

    name = "physician_notify"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Priority-based physician notification -- generates actionable alerts "
        "with patient summary, key findings, and recommended actions.  Tracks "
        "acknowledgment and escalates unacknowledged critical/urgent alerts."
    )
    min_confidence = 0.80

    def __init__(self) -> None:
        super().__init__()
        self._notification_manager = NotificationManager()

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "notify_physician")

        if action == "notify_physician":
            return await self._notify_physician(input_data)
        elif action == "check_acknowledgement":
            return await self._check_acknowledgement(input_data)
        elif action == "escalate":
            return await self._escalate(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown physician notification action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Core: Physician Notification ─────────────────────────────────────────

    async def _notify_physician(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        patient_id = str(input_data.patient_id) if input_data.patient_id else ctx.get("patient_id", "")
        tenant_id = str(input_data.org_id)

        alerts = ctx.get("alerts", [])
        interventions = ctx.get("interventions", [])
        risk_scores = ctx.get("risk_scores", {})
        monitoring = ctx.get("monitoring_results", {})

        if not alerts and not interventions:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"message": "No actionable alerts requiring physician notification"},
                confidence=0.95,
                rationale="No alerts or interventions found -- no physician notification needed",
            )

        # Determine highest priority from alerts
        priority = self._determine_priority(alerts)

        # Look up responsible physician
        physician_data = await self._get_responsible_physician(patient_id, tenant_id)
        physician_id = physician_data.get("physician_id", "on_call")

        # Generate notification content via LLM
        notification_content = await self._generate_notification_content(
            patient_id=patient_id,
            priority=priority,
            alerts=alerts,
            interventions=interventions,
            risk_scores=risk_scores,
        )

        # Select channels and dispatch
        channels = PHYSICIAN_CHANNEL_MAP.get(priority, ["ehr"])

        request = SendNotificationRequest(
            patient_id=patient_id,
            tenant_id=tenant_id,
            notification_type=NotificationType(priority),
            title=f"[{priority}] Clinical Alert - Patient {patient_id[:8]}",
            body=notification_content[:2000],
            metadata={
                "physician_id": physician_id,
                "alert_count": len(alerts),
                "intervention_count": len(interventions),
                "priority": priority,
            },
            agent_source=self.name,
        )

        result = await self._notification_manager.dispatch(
            request,
            patient_contacts=physician_data.get("contacts", {}),
        )

        # Track the notification for acknowledgment monitoring
        notification_record = {
            "notification_id": result.notification_id,
            "patient_id": patient_id,
            "physician_id": physician_id,
            "priority": priority,
            "channels_sent": result.channels_sent,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "acknowledged": False,
            "escalation_timeout_seconds": ESCALATION_TIMEOUTS.get(priority, 86400),
            "content_preview": notification_content[:200],
        }

        await self._track_physician_notification(notification_record)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "priority": priority,
                "notification_id": result.notification_id,
                "notification_content": notification_content,
                "channels_sent": result.channels_sent,
                "channels_failed": result.channels_failed,
                "physician_notified": physician_id,
                "escalation_scheduled": result.escalation_scheduled,
                "escalation_in_seconds": ESCALATION_TIMEOUTS.get(priority),
            },
            confidence=0.90,
            rationale=(
                f"Physician notification sent ({priority}) via "
                f"{', '.join(result.channels_sent) or 'no channels'}. "
                f"Awaiting acknowledgment within "
                f"{ESCALATION_TIMEOUTS.get(priority, 86400) // 60} minutes."
            ),
        )

    # ── Acknowledgement Check ────────────────────────────────────────────────

    async def _check_acknowledgement(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        notification_id = ctx.get("notification_id", "")
        escalation_level = ctx.get("escalation_level", 1)

        result = await self._notification_manager.check_acknowledgement(
            notification_id, escalation_level
        )

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Acknowledgement check for {notification_id}: {result.get('status')}",
        )

    # ── Escalation ───────────────────────────────────────────────────────────

    async def _escalate(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        notification_id = ctx.get("notification_id", "")
        escalation_level = ctx.get("escalation_level", 1)
        patient_id = ctx.get("patient_id", "")
        title = ctx.get("title", "Patient Alert Escalation")

        # Send escalation SMS to on-call / care team
        escalation_body = (
            f"ESCALATION (Level {escalation_level}): Patient {patient_id[:8]} "
            f"-- {title}. Patient alert has not been acknowledged."
        )

        success, ext_id = await self._notification_manager.send_single(
            channel="sms",
            recipient=ctx.get("escalation_phone", ""),
            subject="Care Alert Escalation",
            body=escalation_body,
        )

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "escalated": success,
                "escalation_level": escalation_level,
                "external_id": ext_id,
            },
            confidence=0.90,
            rationale=f"Escalation level {escalation_level} {'sent' if success else 'failed'}",
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _determine_priority(self, alerts: list[dict[str, Any]]) -> str:
        """Map the highest alert severity to a notification priority."""
        priority = "ROUTINE"
        priority_order = list(NOTIFICATION_PRIORITY_MAP.values())

        for alert in alerts:
            alert_severity = alert.get("severity", "LOW")
            mapped = NOTIFICATION_PRIORITY_MAP.get(alert_severity, "ROUTINE")
            if priority_order.index(mapped) < priority_order.index(priority):
                priority = mapped

        return priority

    async def _generate_notification_content(
        self,
        patient_id: str,
        priority: str,
        alerts: list[dict[str, Any]],
        interventions: list[dict[str, Any]],
        risk_scores: dict[str, Any],
    ) -> str:
        """Generate physician notification content via LLM with fallback."""
        alerts_summary = "\n".join(
            [
                f"  [{a.get('severity', 'UNKNOWN')}] {a.get('message', '')[:150]}"
                for a in sorted(
                    alerts,
                    key=lambda x: {"EMERGENCY": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}.get(
                        x.get("severity", "LOW"), 4
                    ),
                )[:10]
            ]
        )

        ensemble_risk = risk_scores.get("ml_ensemble_agent", {}).get("findings", {})
        risk_str = (
            f"{ensemble_risk.get('risk_level', 'UNKNOWN')} "
            f"({ensemble_risk.get('unified_score', 0):.0%})"
            if ensemble_risk
            else "Not calculated"
        )

        hitl_count = len([i for i in interventions if i.get("requires_hitl")])

        prompt = (
            f"Generate a physician notification for patient {patient_id}:\n\n"
            f"Priority: {priority}\n"
            f"Overall risk level: {risk_str}\n\n"
            f"Active alerts:\n{alerts_summary}\n\n"
            f"Pending interventions requiring approval: {hitl_count}\n\n"
            f"Create a physician notification with:\n"
            f"1. Subject line (brief, priority-tagged)\n"
            f"2. Patient summary (2-3 sentences: age, gender, key conditions)\n"
            f"3. Key findings (bullet list, most critical first)\n"
            f"4. Recommended actions (numbered, specific, with urgency)\n"
            f"5. Required physician decisions (HITL items)\n"
            f"6. Contact information for follow-up\n\n"
            f"Format for EHR inbox message. Professional, concise, action-oriented."
        )

        try:
            llm_response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=(
                        "You are the Physician Notification AI Agent for HealthOS. "
                        "You generate concise, actionable physician notifications based on "
                        "clinical findings. Use clinical language appropriate for a physician. "
                        "Include patient context, key findings, and specific recommended actions."
                    ),
                    temperature=0.2,
                    max_tokens=1024,
                )
            )
            return llm_response.content
        except Exception as exc:
            logger.warning("physician_notify.llm_failed", error=str(exc))
            return self._fallback_notification(patient_id, priority, alerts[:3])

    def _fallback_notification(
        self,
        patient_id: str,
        priority: str,
        alerts: list[dict[str, Any]],
    ) -> str:
        """Rule-based fallback when LLM is unavailable."""
        alert_lines = "\n".join(
            [f"- {a.get('message', '')[:100]}" for a in alerts]
        )
        return (
            f"[{priority}] Patient {patient_id}\n"
            f"Active alerts:\n{alert_lines}\n"
            f"Please review patient chart and take appropriate action."
        )

    async def _get_responsible_physician(
        self,
        patient_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Look up the patient's primary care physician or on-call provider."""
        try:
            import httpx

            api_url = os.getenv("HEALTHOS_API_URL", "http://localhost:8000")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{api_url}/api/v1/patients/{patient_id}/physician/",
                    headers={
                        "X-Internal-Token": os.getenv("INTERNAL_API_TOKEN", ""),
                        "X-Tenant-ID": tenant_id,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.debug("physician_notify.physician_lookup_failed", error=str(exc))

        return {
            "physician_id": "on_call",
            "name": "On-Call Physician",
            "contacts": {},
        }

    async def _track_physician_notification(self, record: dict[str, Any]) -> None:
        """Store physician notification tracking record in Redis."""
        try:
            import redis.asyncio as aioredis

            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = aioredis.from_url(url, decode_responses=True)
            key = f"notification:physician:{record['notification_id']}"
            await r.setex(key, 86400 * 7, json.dumps(record))
            await r.aclose()
        except Exception as exc:
            logger.debug("physician_notify.tracking_failed", error=str(exc))
