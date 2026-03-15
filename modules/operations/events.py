"""Operations event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.operations.events")

OPERATIONS_TOPIC = "operations.events"


class OperationsEventType:
    PRIOR_AUTH_SUBMITTED = "operations.prior_auth.submitted"
    PRIOR_AUTH_APPROVED = "operations.prior_auth.approved"
    PRIOR_AUTH_DENIED = "operations.prior_auth.denied"
    INSURANCE_VERIFIED = "operations.insurance.verified"
    REFERRAL_CREATED = "operations.referral.created"
    TASK_COMPLETED = "operations.task.completed"


class OperationsEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="operations",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(OPERATIONS_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def prior_auth_submitted(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(OperationsEventType.PRIOR_AUTH_SUBMITTED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def insurance_verified(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(OperationsEventType.INSURANCE_VERIFIED, patient_id=patient_id, tenant_id=tenant_id, data=data))

    async def referral_created(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(OperationsEventType.REFERRAL_CREATED, patient_id=patient_id, tenant_id=tenant_id, data=data))
