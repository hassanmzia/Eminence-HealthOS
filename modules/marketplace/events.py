"""AI Marketplace event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.marketplace.events")

MARKETPLACE_TOPIC = "marketplace.events"


class MarketplaceEventType:
    AGENT_PUBLISHED = "marketplace.agent.published"
    AGENT_INSTALLED = "marketplace.agent.installed"
    AGENT_UNINSTALLED = "marketplace.agent.uninstalled"
    SECURITY_SCAN_COMPLETED = "marketplace.security_scan.completed"
    AGENT_DEPRECATED = "marketplace.agent.deprecated"


class MarketplaceEventPublisher:
    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(self, event_type: str, *, tenant_id: str = "default",
                     data: Optional[dict[str, Any]] = None) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type, payload=data or {}, event_id=str(uuid4()),
            tenant_id=tenant_id, source="marketplace",
            timestamp=datetime.now(timezone.utc).isoformat(), trace_id=str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.warning("Kafka producer not available — logging event: [%s] %s", event.event_type, event.event_id)
            return
        try:
            await self._producer.publish(MARKETPLACE_TOPIC, event)
        except Exception:
            logger.warning("Failed to publish event %s", event.event_id, exc_info=True)

    async def agent_published(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(MarketplaceEventType.AGENT_PUBLISHED, tenant_id=tenant_id, data=data))

    async def agent_installed(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(MarketplaceEventType.AGENT_INSTALLED, tenant_id=tenant_id, data=data))

    async def security_scan_completed(self, *, tenant_id: str = "default", data: Optional[dict] = None) -> None:
        await self._publish(self._build_event(MarketplaceEventType.SECURITY_SCAN_COMPLETED, tenant_id=tenant_id, data=data))
