"""Labs event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.labs.events")

LABS_TOPIC = "labs.events"


class LabsEventType:
    ORDER_CREATED = "labs.order.created"
    ORDER_CANCELLED = "labs.order.cancelled"
    RESULTS_RECEIVED = "labs.results.received"
    CRITICAL_VALUE = "labs.critical_value.detected"
    CRITICAL_ACKNOWLEDGED = "labs.critical_value.acknowledged"


class LabsEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="labs",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(LABS_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def order_created(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(LabsEventType.ORDER_CREATED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def results_received(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(LabsEventType.RESULTS_RECEIVED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def critical_value(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(LabsEventType.CRITICAL_VALUE, patient_id=patient_id, tenant_id=tenant_id, data=data))
