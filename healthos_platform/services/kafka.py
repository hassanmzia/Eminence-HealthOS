"""
Eminence HealthOS — Kafka Event Bus
Producers and consumers for the HealthOS event-driven architecture.
Topics: vitals.ingested, alerts.generated, agent.events
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

import structlog
from pydantic import BaseModel, Field

from healthos_platform.config import get_settings

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# Event Schema
# ═══════════════════════════════════════════════════════════════════════════════


class HealthOSEvent(BaseModel):
    """Standard event envelope for all Kafka messages."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    source: str  # e.g., "api", "agent:risk_scoring", "device:apple_watch"
    org_id: str
    patient_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# Topics
# ═══════════════════════════════════════════════════════════════════════════════

TOPIC_VITALS_INGESTED = "healthos.vitals.ingested"
TOPIC_ALERTS_GENERATED = "healthos.alerts.generated"
TOPIC_AGENT_EVENTS = "healthos.agent.events"
TOPIC_PATIENT_EVENTS = "healthos.patient.events"
TOPIC_WORKFLOW_EVENTS = "healthos.workflow.events"

ALL_TOPICS = [
    TOPIC_VITALS_INGESTED,
    TOPIC_ALERTS_GENERATED,
    TOPIC_AGENT_EVENTS,
    TOPIC_PATIENT_EVENTS,
    TOPIC_WORKFLOW_EVENTS,
]


# ═══════════════════════════════════════════════════════════════════════════════
# Producer
# ═══════════════════════════════════════════════════════════════════════════════

_producer = None


async def get_producer():
    """Get or create the singleton Kafka producer."""
    global _producer
    if _producer is None:
        from aiokafka import AIOKafkaProducer

        settings = get_settings()
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            max_request_size=1048576,  # 1MB
        )
        await _producer.start()
        logger.info("kafka.producer.started", servers=settings.kafka_bootstrap_servers)
    return _producer


async def close_producer():
    """Shut down the Kafka producer."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("kafka.producer.stopped")


async def publish_event(event: HealthOSEvent, topic: str | None = None) -> None:
    """Publish an event to Kafka."""
    target_topic = topic or _route_event(event.event_type)
    producer = await get_producer()
    key = event.patient_id or event.org_id

    await producer.send_and_wait(
        target_topic,
        value=event.model_dump(),
        key=key,
    )

    logger.info(
        "kafka.event.published",
        topic=target_topic,
        event_type=event.event_type,
        event_id=event.event_id,
        patient_id=event.patient_id,
    )


async def publish_vital_ingested(
    org_id: str, patient_id: str, vital_data: dict[str, Any], trace_id: str | None = None
) -> None:
    """Convenience: publish a vitals.ingested event."""
    await publish_event(
        HealthOSEvent(
            event_type="vitals.ingested",
            source="api",
            org_id=org_id,
            patient_id=patient_id,
            payload=vital_data,
            trace_id=trace_id,
        ),
        topic=TOPIC_VITALS_INGESTED,
    )


async def publish_alert_generated(
    org_id: str, patient_id: str, alert_data: dict[str, Any], trace_id: str | None = None
) -> None:
    """Convenience: publish an alerts.generated event."""
    await publish_event(
        HealthOSEvent(
            event_type="alert.generated",
            source="agent",
            org_id=org_id,
            patient_id=patient_id,
            payload=alert_data,
            trace_id=trace_id,
        ),
        topic=TOPIC_ALERTS_GENERATED,
    )


async def publish_agent_event(
    org_id: str, agent_name: str, action: str, payload: dict[str, Any], trace_id: str | None = None
) -> None:
    """Convenience: publish an agent execution event."""
    await publish_event(
        HealthOSEvent(
            event_type=f"agent.{action}",
            source=f"agent:{agent_name}",
            org_id=org_id,
            payload=payload,
            trace_id=trace_id,
        ),
        topic=TOPIC_AGENT_EVENTS,
    )


def _route_event(event_type: str) -> str:
    """Route event types to topics."""
    if event_type.startswith("vitals."):
        return TOPIC_VITALS_INGESTED
    if event_type.startswith("alert."):
        return TOPIC_ALERTS_GENERATED
    if event_type.startswith("agent."):
        return TOPIC_AGENT_EVENTS
    if event_type.startswith("patient."):
        return TOPIC_PATIENT_EVENTS
    if event_type.startswith("workflow.") or event_type.startswith("operations."):
        return TOPIC_WORKFLOW_EVENTS
    return TOPIC_AGENT_EVENTS  # default


# ═══════════════════════════════════════════════════════════════════════════════
# Consumer
# ═══════════════════════════════════════════════════════════════════════════════

EventHandler = Callable[[HealthOSEvent], Awaitable[None]]


class EventConsumer:
    """
    Kafka consumer that routes events to registered handlers.

    Usage:
        consumer = EventConsumer(topics=["healthos.vitals.ingested"])
        consumer.register("vitals.ingested", handle_vitals)
        await consumer.start()
    """

    def __init__(
        self,
        topics: list[str],
        group_id: str | None = None,
    ) -> None:
        self._topics = topics
        self._group_id = group_id
        self._handlers: dict[str, list[EventHandler]] = {}
        self._consumer = None
        self._running = False

    def register(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def start(self) -> None:
        """Start consuming messages."""
        from aiokafka import AIOKafkaConsumer

        settings = get_settings()
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self._group_id or settings.kafka_group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info("kafka.consumer.started", topics=self._topics, group=self._group_id)

        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                await self._dispatch(msg.value)
        finally:
            await self._consumer.stop()
            logger.info("kafka.consumer.stopped")

    async def stop(self) -> None:
        """Signal the consumer to stop."""
        self._running = False

    async def _dispatch(self, raw: dict[str, Any]) -> None:
        """Dispatch a message to registered handlers."""
        try:
            event = HealthOSEvent(**raw)
        except Exception as exc:
            logger.error("kafka.consumer.parse_error", error=str(exc), raw=str(raw)[:200])
            return

        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            # Try wildcard prefix match (e.g., "vitals.*")
            for pattern, pattern_handlers in self._handlers.items():
                if pattern.endswith("*") and event.event_type.startswith(pattern[:-1]):
                    handlers.extend(pattern_handlers)

        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.error(
                    "kafka.consumer.handler_error",
                    event_type=event.event_type,
                    handler=handler.__name__,
                    error=str(exc),
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Default consumer for agent pipeline integration
# ═══════════════════════════════════════════════════════════════════════════════


async def handle_vitals_event(event: HealthOSEvent) -> None:
    """Process incoming vitals events through the agent pipeline."""
    from healthos_platform.orchestrator.engine import ExecutionEngine

    engine = ExecutionEngine()
    await engine.execute_event(
        event_type="vitals.ingested",
        org_id=uuid.UUID(event.org_id),
        patient_id=uuid.UUID(event.patient_id) if event.patient_id else uuid.uuid4(),
        payload=event.payload,
    )


def create_vitals_consumer() -> EventConsumer:
    """Factory: create a consumer for vitals events."""
    consumer = EventConsumer(
        topics=[TOPIC_VITALS_INGESTED],
        group_id="healthos-vitals-processor",
    )
    consumer.register("vitals.ingested", handle_vitals_event)
    return consumer
