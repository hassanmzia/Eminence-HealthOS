"""Mental Health event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.mental_health.events")

MENTAL_HEALTH_TOPIC = "mental_health.events"


class MentalHealthEventType:
    SCREENING_COMPLETED = "mental_health.screening.completed"
    CRISIS_DETECTED = "mental_health.crisis.detected"
    CRISIS_ESCALATED = "mental_health.crisis.escalated"
    SAFETY_PLAN_CREATED = "mental_health.safety_plan.created"
    TREATMENT_PLAN_CREATED = "mental_health.treatment_plan.created"
    MOOD_CHECK_IN = "mental_health.mood.check_in"


class MentalHealthEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="mental_health",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(MENTAL_HEALTH_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def screening_completed(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(MentalHealthEventType.SCREENING_COMPLETED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def crisis_detected(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(MentalHealthEventType.CRISIS_DETECTED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def crisis_escalated(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(MentalHealthEventType.CRISIS_ESCALATED, patient_id=patient_id, tenant_id=tenant_id, data=data))
