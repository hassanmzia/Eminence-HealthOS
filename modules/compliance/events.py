"""Compliance & Governance event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.compliance.events")

COMPLIANCE_TOPIC = "compliance.events"


class ComplianceEventType:
    SCAN_COMPLETED = "compliance.scan.completed"
    VIOLATION_DETECTED = "compliance.violation.detected"
    CONSENT_CAPTURED = "compliance.consent.captured"
    CONSENT_REVOKED = "compliance.consent.revoked"
    AI_MODEL_AUDITED = "compliance.ai_model.audited"
    DRIFT_DETECTED = "compliance.ai_model.drift_detected"
    REPORT_GENERATED = "compliance.report.generated"


class ComplianceEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     patient_id: Optional[str] = None, data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, patient_id=patient_id, source="compliance",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(COMPLIANCE_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def scan_completed(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ComplianceEventType.SCAN_COMPLETED, tenant_id=tenant_id, data=data))

    async def violation_detected(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ComplianceEventType.VIOLATION_DETECTED, tenant_id=tenant_id, data=data))

    async def consent_captured(self, patient_id: str, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(ComplianceEventType.CONSENT_CAPTURED, patient_id=patient_id, tenant_id=tenant_id, data=data))
