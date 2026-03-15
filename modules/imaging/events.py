"""Imaging event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.imaging.events")

IMAGING_TOPIC = "imaging.events"


class ImagingEventType:
    STUDY_RECEIVED = "imaging.study.received"
    STUDY_ASSIGNED = "imaging.study.assigned"
    ANALYSIS_COMPLETE = "imaging.analysis.complete"
    REPORT_GENERATED = "imaging.report.generated"
    CRITICAL_FINDING = "imaging.critical_finding.detected"
    CRITICAL_ESCALATED = "imaging.critical_finding.escalated"


class ImagingEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="imaging",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(IMAGING_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def study_received(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ImagingEventType.STUDY_RECEIVED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def critical_finding(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ImagingEventType.CRITICAL_FINDING, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def report_generated(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ImagingEventType.REPORT_GENERATED, patient_id=patient_id, tenant_id=tenant_id, data=data))
