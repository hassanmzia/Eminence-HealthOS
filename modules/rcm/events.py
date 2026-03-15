"""Revenue Cycle event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.rcm.events")

RCM_TOPIC = "rcm.events"


class RCMEventType:
    CHARGE_CAPTURED = "rcm.charge.captured"
    CLAIM_SUBMITTED = "rcm.claim.submitted"
    CLAIM_DENIED = "rcm.claim.denied"
    APPEAL_GENERATED = "rcm.appeal.generated"
    PAYMENT_POSTED = "rcm.payment.posted"
    REVENUE_LEAKAGE = "rcm.revenue.leakage_detected"


class RCMEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="rcm",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(RCM_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def charge_captured(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(RCMEventType.CHARGE_CAPTURED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def claim_denied(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(RCMEventType.CLAIM_DENIED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def payment_posted(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(RCMEventType.PAYMENT_POSTED, patient_id=patient_id, tenant_id=tenant_id, data=data))
