"""Ambient AI event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.ambient_ai.events")

AMBIENT_AI_TOPIC = "ambient_ai.events"


class AmbientAIEventType:
    SESSION_STARTED = "ambient_ai.session.started"
    SESSION_ENDED = "ambient_ai.session.ended"
    TRANSCRIPTION_COMPLETE = "ambient_ai.transcription.complete"
    SOAP_GENERATED = "ambient_ai.soap.generated"
    CODING_COMPLETE = "ambient_ai.coding.complete"
    ATTESTATION_SUBMITTED = "ambient_ai.attestation.submitted"
    ATTESTATION_APPROVED = "ambient_ai.attestation.approved"


class AmbientAIEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="ambient_ai",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(AMBIENT_AI_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def session_started(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(AmbientAIEventType.SESSION_STARTED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def soap_generated(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(AmbientAIEventType.SOAP_GENERATED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def attestation_approved(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(AmbientAIEventType.ATTESTATION_APPROVED, patient_id=patient_id, tenant_id=tenant_id, data=data))
