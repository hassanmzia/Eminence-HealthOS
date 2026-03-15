"""
Eminence HealthOS -- Unified Notification Manager

Orchestrates multi-channel notification delivery with:
  - Priority-based channel routing (CRITICAL -> SMS+Push+EHR, etc.)
  - Escalation scheduling for unacknowledged critical alerts
  - Patient preference filtering
  - Tenant-level channel configuration
  - Health-literacy-aware template rendering
  - Delivery tracking & retry logic

Adapted from InHealth notification dispatcher / tasks / models, re-implemented
as an async FastAPI-native service using Pydantic models.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import structlog
from pydantic import BaseModel, Field

from .email_service import EmailService
from .push_service import EHRAlertService, PushService
from .sms_service import SMSService

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════


class NotificationType(str, Enum):
    CRITICAL = "CRITICAL"       # Immediate action required
    URGENT = "URGENT"           # Action required today
    SOON = "SOON"               # Action required this week
    ROUTINE = "ROUTINE"         # General information
    EDUCATIONAL = "EDUCATIONAL" # Educational content
    APPOINTMENT = "APPOINTMENT" # Appointment reminder


class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    EHR = "ehr"       # In-app EHR alert (WebSocket / Redis Pub/Sub)
    PHONE = "phone"
    ALL = "all"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"


class HealthLiteracyLevel(int, Enum):
    MINIMAL = 1       # < 6th grade
    LIMITED = 2       # 6th-8th grade
    ADEQUATE = 3      # High school
    PROFICIENT = 4    # College
    EXPERT = 5        # Healthcare professional


# Priority -> channel routing map (from InHealth dispatcher)
PRIORITY_ROUTING: dict[str, list[str]] = {
    NotificationType.CRITICAL: ["sms", "push", "ehr"],
    NotificationType.URGENT: ["sms", "email"],
    NotificationType.SOON: ["email"],
    NotificationType.ROUTINE: ["email"],
    NotificationType.EDUCATIONAL: ["email"],
    NotificationType.APPOINTMENT: ["sms", "email"],
}

# Escalation delay schedules in minutes
ESCALATION_DELAYS_MINUTES: dict[str, list[int]] = {
    NotificationType.CRITICAL: [5, 15, 30],
    NotificationType.URGENT: [30, 120],
    NotificationType.SOON: [],
    NotificationType.ROUTINE: [],
    NotificationType.EDUCATIONAL: [],
    NotificationType.APPOINTMENT: [],
}

# Task priority mapping (higher = more important)
TASK_PRIORITY: dict[str, int] = {
    NotificationType.CRITICAL: 9,
    NotificationType.URGENT: 7,
    NotificationType.APPOINTMENT: 4,
    NotificationType.SOON: 5,
    NotificationType.ROUTINE: 3,
    NotificationType.EDUCATIONAL: 2,
}


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class NotificationTemplate(BaseModel):
    """Templated notification with health-literacy-level variants."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    notification_type: str = "ROUTINE"
    health_literacy_level: int = HealthLiteracyLevel.ADEQUATE
    language: str = "en"
    subject_template: str
    body_template: str
    channel: str = "all"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def render(self, context: dict[str, Any]) -> tuple[str, str]:
        """Render subject and body with the given context variables."""
        subject = self.subject_template.format(**context)
        body = self.body_template.format(**context)
        return subject, body


class NotificationRecord(BaseModel):
    """
    Individual notification instance -- one per patient per alert event.
    Mirrors the InHealth Notification model as a Pydantic schema.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: str = "default"
    patient_id: str

    notification_type: NotificationType = NotificationType.ROUTINE
    channel: NotificationChannel = NotificationChannel.EMAIL

    title: str
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    status: NotificationStatus = NotificationStatus.PENDING

    # AI source
    agent_source: str = ""

    # Delivery tracking
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: str = ""
    retry_count: int = 0
    max_retries: int = 3
    external_message_id: str = ""

    # Acknowledgement
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    # Escalation
    escalation_level: int = 0
    escalated_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_sent(self, external_id: str = "") -> None:
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now(timezone.utc)
        self.external_message_id = external_id
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: str) -> None:
        self.status = NotificationStatus.FAILED
        self.failed_at = datetime.now(timezone.utc)
        self.failure_reason = reason
        self.retry_count += 1
        self.updated_at = datetime.now(timezone.utc)

    def mark_delivered(self) -> None:
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def acknowledge(self, user_id: Optional[str] = None) -> None:
        self.status = NotificationStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now(timezone.utc)
        self.acknowledged_by = user_id
        self.updated_at = datetime.now(timezone.utc)

    def escalate(self, level: int) -> None:
        self.status = NotificationStatus.ESCALATED
        self.escalation_level = level
        self.escalated_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class SendNotificationRequest(BaseModel):
    """API-level request to dispatch a notification."""

    patient_id: str
    tenant_id: str = "default"
    notification_type: NotificationType = NotificationType.ROUTINE
    title: str
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_source: str = ""
    # Override channels -- if empty, routing rules decide
    channels: list[NotificationChannel] = Field(default_factory=list)


class NotificationResult(BaseModel):
    """Result of a send operation."""

    notification_id: str
    channels_sent: list[str] = Field(default_factory=list)
    channels_failed: list[str] = Field(default_factory=list)
    escalation_scheduled: bool = False
    escalation_delays_minutes: list[int] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════


class NotificationManager:
    """
    Unified notification orchestrator.

    Wraps EmailService, SMSService, PushService, and EHRAlertService behind
    a single ``send()`` / ``dispatch()`` interface with priority routing,
    patient preference filtering, escalation scheduling, and delivery tracking.
    """

    def __init__(
        self,
        email_service: Optional[EmailService] = None,
        sms_service: Optional[SMSService] = None,
        push_service: Optional[PushService] = None,
        ehr_service: Optional[EHRAlertService] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        self._email = email_service or EmailService()
        self._sms = sms_service or SMSService()
        self._push = push_service or PushService()
        self._ehr = ehr_service or EHRAlertService(redis_url=redis_url)
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── Public API ───────────────────────────────────────────────────────────

    async def dispatch(
        self,
        request: SendNotificationRequest,
        *,
        patient_preferences: Optional[dict[str, bool]] = None,
        tenant_config: Optional[dict[str, Any]] = None,
        patient_contacts: Optional[dict[str, str]] = None,
    ) -> NotificationResult:
        """
        Create a notification record and dispatch it across all required channels
        based on priority routing, patient preferences, and tenant config.
        """
        # Create notification record
        record = NotificationRecord(
            tenant_id=request.tenant_id,
            patient_id=request.patient_id,
            notification_type=request.notification_type,
            title=request.title,
            body=request.body,
            metadata=request.metadata,
            agent_source=request.agent_source,
        )

        # Determine channels
        channels = self._resolve_channels(
            request=request,
            patient_preferences=patient_preferences,
            tenant_config=tenant_config,
        )

        contacts = patient_contacts or {}
        channels_sent: list[str] = []
        channels_failed: list[str] = []

        for channel in channels:
            recipient = self._get_recipient(channel, contacts, request.patient_id)
            if not recipient:
                logger.warning(
                    "notification.no_recipient",
                    channel=channel,
                    patient_id=request.patient_id,
                )
                channels_failed.append(channel)
                continue

            success, ext_id = await self._send_via_channel(
                channel=channel,
                recipient=recipient,
                subject=record.title,
                body=record.body,
                metadata=record.metadata,
            )

            if success:
                record.mark_sent(ext_id)
                channels_sent.append(channel)
            else:
                record.mark_failed(ext_id)
                channels_failed.append(channel)

        # Persist notification record to Redis for tracking
        await self._track_notification(record)

        # Schedule escalation for critical / urgent
        escalation_delays = ESCALATION_DELAYS_MINUTES.get(
            request.notification_type, []
        )
        escalation_scheduled = False
        if escalation_delays:
            await self._schedule_escalation(record, escalation_delays)
            escalation_scheduled = True

        return NotificationResult(
            notification_id=str(record.id),
            channels_sent=channels_sent,
            channels_failed=channels_failed,
            escalation_scheduled=escalation_scheduled,
            escalation_delays_minutes=escalation_delays,
        )

    async def send_single(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """Low-level send on a specific channel (no routing / tracking)."""
        return await self._send_via_channel(
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            metadata=metadata,
        )

    async def acknowledge(
        self,
        notification_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Mark a notification as acknowledged in the tracking store."""
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._redis_url, decode_responses=True)
            key = f"notification:{notification_id}"
            raw = await r.get(key)
            if raw:
                data = json.loads(raw)
                data["status"] = NotificationStatus.ACKNOWLEDGED
                data["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                data["acknowledged_by"] = user_id
                await r.setex(key, 86400 * 7, json.dumps(data))
                await r.aclose()
                logger.info(
                    "notification.acknowledged",
                    notification_id=notification_id,
                    user_id=user_id,
                )
                return True
            await r.aclose()
        except Exception as exc:
            logger.error("notification.acknowledge_failed", error=str(exc))
        return False

    async def check_acknowledgement(
        self,
        notification_id: str,
        escalation_level: int,
    ) -> dict[str, Any]:
        """
        Check if a critical notification was acknowledged.
        If not, escalate to the care team.
        """
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._redis_url, decode_responses=True)
            key = f"notification:{notification_id}"
            raw = await r.get(key)
            await r.aclose()

            if not raw:
                return {"status": "not_found"}

            data = json.loads(raw)
            if data.get("status") == NotificationStatus.ACKNOWLEDGED:
                return {"status": "already_acknowledged"}

            # Escalate
            logger.warning(
                "notification.escalation",
                notification_id=notification_id,
                level=escalation_level,
            )
            data["status"] = NotificationStatus.ESCALATED
            data["escalation_level"] = escalation_level
            data["escalated_at"] = datetime.now(timezone.utc).isoformat()

            r = aioredis.from_url(self._redis_url, decode_responses=True)
            await r.setex(key, 86400 * 7, json.dumps(data))
            await r.aclose()

            return {"status": "escalated", "level": escalation_level}

        except Exception as exc:
            logger.error("notification.escalation_check_failed", error=str(exc))
            return {"status": "error", "error": str(exc)}

    def get_channels_for_priority(self, notification_type: str) -> list[str]:
        """Return the default channel list for a notification type."""
        return PRIORITY_ROUTING.get(notification_type, ["email"])

    def get_escalation_delays(self, notification_type: str) -> list[int]:
        """Return escalation delay schedule (in minutes) for a notification type."""
        return ESCALATION_DELAYS_MINUTES.get(notification_type, [])

    def get_task_priority(self, notification_type: str) -> int:
        """Return the task queue priority for a notification type."""
        return TASK_PRIORITY.get(notification_type, 3)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _resolve_channels(
        self,
        request: SendNotificationRequest,
        patient_preferences: Optional[dict[str, bool]],
        tenant_config: Optional[dict[str, Any]],
    ) -> list[str]:
        """Determine which channels to use for this notification."""
        if request.channels:
            channels = [c.value for c in request.channels]
        else:
            channels = list(
                PRIORITY_ROUTING.get(request.notification_type, ["email"])
            )

        # Filter by patient preferences
        if patient_preferences:
            channels = [c for c in channels if patient_preferences.get(c, True)]

        # Filter by tenant config
        if tenant_config:
            allowed = tenant_config.get("notification_channels", {})
            if allowed:
                channels = [c for c in channels if allowed.get(c, True)]

        return channels

    @staticmethod
    def _get_recipient(
        channel: str,
        contacts: dict[str, str],
        patient_id: str,
    ) -> Optional[str]:
        """Extract the recipient address/token for the given channel."""
        if channel == "sms":
            return contacts.get("phone") or None
        elif channel == "email":
            return contacts.get("email") or None
        elif channel == "push":
            return contacts.get("fcm_token") or None
        elif channel == "ehr":
            return contacts.get("fhir_id") or patient_id
        return None

    async def _send_via_channel(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """Route to the appropriate service adapter."""
        if channel == "sms":
            return await self._sms.send(recipient, body, subject=subject, metadata=metadata)
        elif channel == "email":
            return await self._email.send(recipient, subject, body, metadata=metadata)
        elif channel == "push":
            return await self._push.send(recipient, subject, body, metadata=metadata)
        elif channel == "ehr":
            return await self._ehr.send(recipient, subject, body, metadata=metadata)
        else:
            logger.warning("notification.unknown_channel", channel=channel)
            return False, f"Unknown channel: {channel}"

    async def _track_notification(self, record: NotificationRecord) -> None:
        """Persist notification record in Redis for 7 days."""
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._redis_url, decode_responses=True)
            key = f"notification:{record.id}"
            await r.setex(key, 86400 * 7, record.model_dump_json())

            # Also add to patient's notification list
            patient_key = f"notifications:patient:{record.patient_id}"
            await r.lpush(patient_key, str(record.id))
            await r.ltrim(patient_key, 0, 99)  # Keep last 100
            await r.expire(patient_key, 86400 * 30)

            await r.aclose()
        except Exception as exc:
            logger.debug("notification.tracking_failed", error=str(exc))

    async def _schedule_escalation(
        self,
        record: NotificationRecord,
        delays: list[int],
    ) -> None:
        """
        Schedule escalation checks.  In production this would use Temporal
        workflows or Celery beat.  For now we store the schedule in Redis so
        the Temporal worker or a cron job can pick it up.
        """
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._redis_url, decode_responses=True)
            for level, delay_minutes in enumerate(delays, start=1):
                escalation_key = f"escalation:{record.id}:level:{level}"
                escalation_data = json.dumps(
                    {
                        "notification_id": str(record.id),
                        "patient_id": record.patient_id,
                        "tenant_id": record.tenant_id,
                        "escalation_level": level,
                        "delay_minutes": delay_minutes,
                        "notification_type": record.notification_type,
                        "title": record.title,
                        "scheduled_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                await r.setex(escalation_key, delay_minutes * 60 + 300, escalation_data)

            await r.aclose()
            logger.info(
                "notification.escalation_scheduled",
                notification_id=str(record.id),
                levels=len(delays),
                delays=delays,
            )
        except Exception as exc:
            logger.warning("notification.escalation_schedule_failed", error=str(exc))
