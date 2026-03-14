"""
Telehealth event publisher.

Publishes session lifecycle, clinical note, escalation, and follow-up
events to the Kafka event bus.  Falls back to logging when Kafka is
unavailable so callers are never blocked.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.telehealth.events")

# ── Topic ────────────────────────────────────────────────────────────
TELEHEALTH_TOPIC = "telehealth.events"

# ── Event type constants ─────────────────────────────────────────────


class TelehealthEventType:
    SESSION_CREATED = "telehealth.session.created"
    SESSION_STARTED = "telehealth.session.started"
    SESSION_ENDED = "telehealth.session.ended"
    SESSION_CANCELLED = "telehealth.session.cancelled"
    NOTE_GENERATED = "telehealth.note.generated"
    NOTE_SIGNED = "telehealth.note.signed"
    ESCALATION_TRIGGERED = "telehealth.escalation.triggered"
    FOLLOW_UP_CREATED = "telehealth.follow_up.created"


# ── Publisher ────────────────────────────────────────────────────────


class TelehealthEventPublisher:
    """Publishes structured telehealth events to the Kafka event bus.

    Every public method builds a :class:`HealthOSEvent` envelope and
    delegates to :meth:`EventProducer.publish`.  If the producer is
    ``None`` or the publish call raises, the event is logged at *warning*
    level so the request path is never interrupted.
    """

    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    # ── helpers ───────────────────────────────────────────────────────

    def _build_event(
        self,
        event_type: str,
        *,
        session_id: str,
        patient_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        tenant_id: str = "default",
        data: Optional[dict[str, Any]] = None,
    ) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type,
            payload={
                "session_id": session_id,
                "data": data or {},
            },
            event_id=str(uuid4()),
            tenant_id=tenant_id,
            patient_id=patient_id,
            source="telehealth",
            timestamp=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id or str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        """Publish with graceful fallback on failure."""
        if self._producer is None:
            logger.warning(
                "Kafka producer not available — logging event locally: "
                "[%s] %s",
                event.event_type,
                event.event_id,
            )
            return

        try:
            await self._producer.publish(TELEHEALTH_TOPIC, event)
        except Exception:
            logger.warning(
                "Failed to publish event %s (%s) — continuing without Kafka",
                event.event_id,
                event.event_type,
                exc_info=True,
            )

    # ── session lifecycle ─────────────────────────────────────────────

    async def session_created(
        self,
        session_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            TelehealthEventType.SESSION_CREATED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)

    async def session_started(
        self,
        session_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            TelehealthEventType.SESSION_STARTED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)

    async def session_ended(
        self,
        session_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            TelehealthEventType.SESSION_ENDED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)

    async def session_cancelled(
        self,
        session_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            TelehealthEventType.SESSION_CANCELLED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)

    # ── clinical notes ────────────────────────────────────────────────

    async def note_generated(
        self,
        session_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            TelehealthEventType.NOTE_GENERATED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)

    async def note_signed(
        self,
        session_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            TelehealthEventType.NOTE_SIGNED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)

    # ── escalation & follow-up ────────────────────────────────────────

    async def escalation_triggered(
        self,
        session_id: str,
        patient_id: str,
        *,
        reason: str = "",
        severity: str = "high",
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        payload = {**(data or {}), "reason": reason, "severity": severity}
        event = self._build_event(
            TelehealthEventType.ESCALATION_TRIGGERED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=payload,
        )
        await self._publish(event)

    async def follow_up_created(
        self,
        session_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            TelehealthEventType.FOLLOW_UP_CREATED,
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)
