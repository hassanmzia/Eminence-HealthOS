"""RPM event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.rpm.events")

RPM_TOPIC = "rpm.events"


class RPMEventType:
    DATA_INGESTED = "rpm.data.ingested"
    VITALS_NORMALIZED = "rpm.vitals.normalized"
    ANOMALY_DETECTED = "rpm.anomaly.detected"
    ALERT_TRIGGERED = "rpm.alert.triggered"
    ALERT_RESOLVED = "rpm.alert.resolved"
    ADHERENCE_UPDATE = "rpm.adherence.updated"
    ESCALATION_TRIGGERED = "rpm.escalation.triggered"


class RPMEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="rpm",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(RPM_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def data_ingested(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(RPMEventType.DATA_INGESTED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def anomaly_detected(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(RPMEventType.ANOMALY_DETECTED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def alert_triggered(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(RPMEventType.ALERT_TRIGGERED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def escalation_triggered(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(RPMEventType.ESCALATION_TRIGGERED, patient_id=patient_id, tenant_id=tenant_id, data=data))
