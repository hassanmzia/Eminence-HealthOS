"""
Telehealth event consumer.

Subscribes to the ``telehealth.events`` topic and dispatches events to
registered handlers (escalation alerting, follow-up scheduling, etc.).
"""

import logging
from typing import Any, Callable, Coroutine

from shared.events.bus import EventConsumer, HealthOSEvent
from modules.telehealth.events import TELEHEALTH_TOPIC, TelehealthEventType

logger = logging.getLogger("healthos.telehealth.consumers")

# Type alias for async event handlers
EventHandler = Callable[[HealthOSEvent], Coroutine[Any, Any, None]]


# ── Default handlers ─────────────────────────────────────────────────


async def handle_escalation_triggered(event: HealthOSEvent) -> None:
    """Create a system alert when an escalation is triggered."""
    payload = event.payload
    session_id = payload.get("session_id", "unknown")
    data = payload.get("data", {})
    reason = data.get("reason", "unspecified")
    severity = data.get("severity", "high")

    logger.info(
        "ESCALATION ALERT — session=%s reason=%s severity=%s patient=%s",
        session_id,
        reason,
        severity,
        event.patient_id,
    )

    # In production this would persist to an alerts table / send a
    # notification via the healthos.alerts.trigger topic.  For now we
    # emit a structured log that downstream observability can capture.
    try:
        from shared.events.bus import EventProducer, HealthOSEvent as HE, Topics  # noqa: F811
        # Forward a lightweight alert to the global alerts topic so the
        # notification pipeline picks it up.
        # NOTE: the producer must already be running in the application
        # lifecycle — this is a best-effort publish.
        pass  # placeholder for alert persistence / forwarding
    except Exception:
        logger.warning(
            "Could not forward escalation to alerts pipeline",
            exc_info=True,
        )


async def handle_session_ended(event: HealthOSEvent) -> None:
    """Trigger follow-up scheduling when a session ends."""
    payload = event.payload
    session_id = payload.get("session_id", "unknown")

    logger.info(
        "Session ended — scheduling follow-up: session=%s patient=%s",
        session_id,
        event.patient_id,
    )

    # In production this would invoke the SchedulingAgent or enqueue a
    # task for the follow-up workflow.  Structured log for now.
    try:
        pass  # placeholder for scheduling integration
    except Exception:
        logger.warning(
            "Could not trigger follow-up scheduling for session %s",
            session_id,
            exc_info=True,
        )


# ── Consumer factory ─────────────────────────────────────────────────


class TelehealthEventConsumer:
    """Wraps :class:`EventConsumer` with telehealth-specific handler
    registration and startup helpers.

    Usage::

        consumer = TelehealthEventConsumer()
        consumer.register_defaults()
        # optionally register custom handlers:
        consumer.register(TelehealthEventType.NOTE_GENERATED, my_handler)
        await consumer.start(bootstrap_servers="kafka:9092")
    """

    def __init__(self, consumer: EventConsumer | None = None) -> None:
        self._consumer = consumer or EventConsumer()

    # ── handler registration ──────────────────────────────────────────

    def register(self, event_type: str, handler: EventHandler) -> None:
        """Register an async handler for a specific event type."""
        self._consumer.on(event_type, handler)
        logger.debug("Registered handler for %s", event_type)

    def register_defaults(self) -> None:
        """Wire up the built-in handlers for escalation and session end."""
        self.register(
            TelehealthEventType.ESCALATION_TRIGGERED,
            handle_escalation_triggered,
        )
        self.register(
            TelehealthEventType.SESSION_ENDED,
            handle_session_ended,
        )

    # ── lifecycle ─────────────────────────────────────────────────────

    async def start(
        self,
        bootstrap_servers: str = "kafka:9092",
        group_id: str = "telehealth-consumer-group",
    ) -> None:
        """Start consuming from the telehealth events topic."""
        await self._consumer.start(
            topics=[TELEHEALTH_TOPIC],
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
        )
        logger.info("Telehealth consumer started (group=%s)", group_id)

    async def consume(self) -> None:
        """Block on the consume loop — delegates to the inner consumer."""
        await self._consumer.consume()

    async def stop(self) -> None:
        await self._consumer.stop()
        logger.info("Telehealth consumer stopped")
