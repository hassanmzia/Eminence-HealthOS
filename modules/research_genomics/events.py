"""Research & Genomics event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.research_genomics.events")

RESEARCH_TOPIC = "research_genomics.events"


class ResearchEventType:
    TRIAL_MATCHED = "research.trial.matched"
    COHORT_BUILT = "research.cohort.built"
    DATASET_DEIDENTIFIED = "research.dataset.deidentified"
    PGX_ALERT = "research.pgx.alert"
    GENETIC_RISK_CALCULATED = "research.genetic_risk.calculated"


class ResearchEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="research_genomics",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(RESEARCH_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def trial_matched(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ResearchEventType.TRIAL_MATCHED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def cohort_built(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ResearchEventType.COHORT_BUILT, tenant_id=tenant_id, data=data))

    async def pgx_alert(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ResearchEventType.PGX_ALERT, patient_id=patient_id, tenant_id=tenant_id, data=data))
