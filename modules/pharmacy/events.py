"""Pharmacy event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.pharmacy.events")

PHARMACY_TOPIC = "pharmacy.events"


class PharmacyEventType:
    PRESCRIPTION_CREATED = "pharmacy.prescription.created"
    PRESCRIPTION_TRANSMITTED = "pharmacy.prescription.transmitted"
    INTERACTION_DETECTED = "pharmacy.interaction.detected"
    REFILL_INITIATED = "pharmacy.refill.initiated"
    ADHERENCE_ALERT = "pharmacy.adherence.alert"


class PharmacyEventPublisher:
    """Publishes pharmacy events to the Kafka event bus."""

    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type,
            payload=data or {},
            event_id=str(uuid4()),
            tenant_id=tenant_id,
            patient_id=patient_id,
            source="pharmacy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(PHARMACY_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s (%s)", event.event_id, event.event_type, exc_info=True)

    async def prescription_created(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(PharmacyEventType.PRESCRIPTION_CREATED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def prescription_transmitted(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(PharmacyEventType.PRESCRIPTION_TRANSMITTED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def interaction_detected(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(PharmacyEventType.INTERACTION_DETECTED, patient_id=patient_id, tenant_id=tenant_id, data=data))
