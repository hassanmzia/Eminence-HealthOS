"""Digital Twin event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.digital_twin.events")

DIGITAL_TWIN_TOPIC = "digital_twin.events"


class DigitalTwinEventType:
    TWIN_CREATED = "digital_twin.twin.created"
    TWIN_UPDATED = "digital_twin.twin.updated"
    SCENARIO_SIMULATED = "digital_twin.scenario.simulated"
    TRAJECTORY_FORECAST = "digital_twin.trajectory.forecast"
    DETERIORATION_DETECTED = "digital_twin.deterioration.detected"
    CARE_OPTIMIZED = "digital_twin.care.optimized"


class DigitalTwinEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="digital_twin",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(DIGITAL_TWIN_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def twin_created(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(DigitalTwinEventType.TWIN_CREATED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def scenario_simulated(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(DigitalTwinEventType.SCENARIO_SIMULATED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def deterioration_detected(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(DigitalTwinEventType.DETERIORATION_DETECTED, patient_id=patient_id, tenant_id=tenant_id, data=data))
