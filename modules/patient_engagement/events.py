"""Patient Engagement event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.patient_engagement.events")

ENGAGEMENT_TOPIC = "patient_engagement.events"


class EngagementEventType:
    TRIAGE_COMPLETED = "engagement.triage.completed"
    SDOH_SCREENED = "engagement.sdoh.screened"
    RESOURCE_REFERRED = "engagement.resource.referred"
    NUDGE_SENT = "engagement.nudge.sent"
    CONTENT_ADAPTED = "engagement.content.adapted"


class EngagementEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="patient_engagement",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(ENGAGEMENT_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def triage_completed(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(EngagementEventType.TRIAGE_COMPLETED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def sdoh_screened(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(EngagementEventType.SDOH_SCREENED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def nudge_sent(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(EngagementEventType.NUDGE_SENT, patient_id=patient_id, tenant_id=tenant_id, data=data))
