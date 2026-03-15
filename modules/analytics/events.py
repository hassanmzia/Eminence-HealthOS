"""Analytics event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.analytics.events")

ANALYTICS_TOPIC = "analytics.events"


class AnalyticsEventType:
    COHORT_ANALYZED = "analytics.cohort.analyzed"
    RISK_STRATIFIED = "analytics.risk.stratified"
    POPULATION_REPORT = "analytics.population.report_generated"
    EXECUTIVE_INSIGHT = "analytics.executive.insight_generated"
    READMISSION_RISK = "analytics.readmission.risk_calculated"


class AnalyticsEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="analytics",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(ANALYTICS_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def cohort_analyzed(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(AnalyticsEventType.COHORT_ANALYZED, tenant_id=tenant_id, data=data))

    async def risk_stratified(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(AnalyticsEventType.RISK_STRATIFIED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def population_report(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(AnalyticsEventType.POPULATION_REPORT, tenant_id=tenant_id, data=data))
