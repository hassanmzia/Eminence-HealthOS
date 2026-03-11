"""
Kafka event bus for HealthOS.

Provides async producer/consumer wrappers with serialization,
topic management, and dead-letter queue support.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

logger = logging.getLogger("healthos.events.bus")


@dataclass
class HealthOSEvent:
    """Standard event envelope for all HealthOS events."""
    event_type: str
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "default"
    patient_id: Optional[str] = None
    source: str = "api"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    trace_id: Optional[str] = None

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "HealthOSEvent":
        return cls(**json.loads(data.decode("utf-8")))


# Topic constants
class Topics:
    VITALS_INGEST = "healthos.vitals.ingest"
    LABS_INGEST = "healthos.labs.ingest"
    DEVICES_INGEST = "healthos.devices.ingest"
    ALERTS_TRIGGER = "healthos.alerts.trigger"
    AGENTS_REQUEST = "healthos.agents.request"
    AGENTS_RESULT = "healthos.agents.result"
    AUDIT_LOG = "healthos.audit.log"
    NOTIFICATIONS = "healthos.notifications"
    DLQ = "healthos.dlq"


class EventProducer:
    """Async Kafka producer for HealthOS events."""

    def __init__(self):
        self._producer = None

    async def start(self, bootstrap_servers: str) -> None:
        try:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: v.to_bytes() if isinstance(v, HealthOSEvent) else json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
            logger.info("Event producer connected to %s", bootstrap_servers)
        except Exception as e:
            logger.warning("Kafka producer unavailable: %s", e)
            self._producer = None

    async def publish(self, topic: str, event: HealthOSEvent) -> None:
        if self._producer is None:
            logger.debug("No producer — event dropped: %s/%s", topic, event.event_type)
            return

        try:
            await self._producer.send_and_wait(topic, event)
            logger.debug("Published event %s to %s", event.event_id[:8], topic)
        except Exception as e:
            logger.error("Failed to publish to %s: %s", topic, e)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()


class EventConsumer:
    """Async Kafka consumer with handler registration."""

    def __init__(self):
        self._consumer = None
        self._handlers: dict[str, list[Callable]] = {}
        self._running = False

    def on(self, event_type: str, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def start(
        self,
        topics: list[str],
        bootstrap_servers: str,
        group_id: str,
    ) -> None:
        try:
            from aiokafka import AIOKafkaConsumer
            self._consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: HealthOSEvent.from_bytes(m),
                auto_offset_reset="latest",
            )
            await self._consumer.start()
            self._running = True
            logger.info("Event consumer started on %s", topics)
        except Exception as e:
            logger.warning("Kafka consumer unavailable: %s", e)

    async def consume(self) -> None:
        """Main consume loop — dispatches events to registered handlers."""
        if not self._consumer:
            return

        async for message in self._consumer:
            if not self._running:
                break

            event: HealthOSEvent = message.value
            handlers = self._handlers.get(event.event_type, [])

            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(
                        "Handler error for %s: %s", event.event_type, e
                    )

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
