"""
Unit tests for Kafka event bus — event schema, routing, and consumer dispatch.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from healthos_platform.services.kafka import (
    EventConsumer,
    HealthOSEvent,
    TOPIC_AGENT_EVENTS,
    TOPIC_ALERTS_GENERATED,
    TOPIC_PATIENT_EVENTS,
    TOPIC_VITALS_INGESTED,
    TOPIC_WORKFLOW_EVENTS,
    _route_event,
)


# ── HealthOSEvent Schema ─────────────────────────────────────────────────────


class TestHealthOSEvent:
    def test_create_event_with_defaults(self):
        event = HealthOSEvent(event_type="vitals.ingested", source="api", org_id="org-1")
        assert event.event_type == "vitals.ingested"
        assert event.source == "api"
        assert event.org_id == "org-1"
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_event_with_patient_and_payload(self):
        event = HealthOSEvent(
            event_type="alert.generated",
            source="agent:risk_scoring",
            org_id="org-1",
            patient_id="patient-1",
            payload={"severity": "critical", "alert_type": "vital_anomaly"},
            trace_id=str(uuid.uuid4()),
        )
        assert event.patient_id == "patient-1"
        assert event.payload["severity"] == "critical"

    def test_event_serialization(self):
        event = HealthOSEvent(
            event_type="test",
            source="test",
            org_id="org-1",
        )
        data = event.model_dump()
        assert "event_id" in data
        assert "event_type" in data
        assert "timestamp" in data

    def test_event_deserialization(self):
        raw = {
            "event_id": str(uuid.uuid4()),
            "event_type": "vitals.ingested",
            "source": "device",
            "org_id": "org-1",
            "timestamp": "2026-03-14T10:00:00+00:00",
            "payload": {"heart_rate": 72},
        }
        event = HealthOSEvent(**raw)
        assert event.payload["heart_rate"] == 72


# ── Event Routing ─────────────────────────────────────────────────────────────


class TestEventRouting:
    def test_vitals_route(self):
        assert _route_event("vitals.ingested") == TOPIC_VITALS_INGESTED
        assert _route_event("vitals.normalized") == TOPIC_VITALS_INGESTED

    def test_alert_route(self):
        assert _route_event("alert.generated") == TOPIC_ALERTS_GENERATED
        assert _route_event("alert.acknowledged") == TOPIC_ALERTS_GENERATED

    def test_agent_route(self):
        assert _route_event("agent.completed") == TOPIC_AGENT_EVENTS
        assert _route_event("agent.failed") == TOPIC_AGENT_EVENTS

    def test_patient_route(self):
        assert _route_event("patient.enrolled") == TOPIC_PATIENT_EVENTS
        assert _route_event("patient.updated") == TOPIC_PATIENT_EVENTS

    def test_workflow_route(self):
        assert _route_event("workflow.started") == TOPIC_WORKFLOW_EVENTS
        assert _route_event("operations.task_created") == TOPIC_WORKFLOW_EVENTS

    def test_unknown_defaults_to_agent_events(self):
        assert _route_event("unknown.something") == TOPIC_AGENT_EVENTS


# ── EventConsumer ─────────────────────────────────────────────────────────────


class TestEventConsumer:
    def test_register_handler(self):
        consumer = EventConsumer(topics=[TOPIC_VITALS_INGESTED])
        handler = AsyncMock()
        consumer.register("vitals.ingested", handler)
        assert "vitals.ingested" in consumer._handlers
        assert handler in consumer._handlers["vitals.ingested"]

    @pytest.mark.asyncio
    async def test_dispatch_to_exact_handler(self):
        consumer = EventConsumer(topics=[TOPIC_VITALS_INGESTED])
        handler = AsyncMock()
        consumer.register("vitals.ingested", handler)

        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "vitals.ingested",
            "source": "device",
            "org_id": "org-1",
            "timestamp": "2026-03-14T10:00:00+00:00",
            "payload": {"value": 72},
        }
        await consumer._dispatch(event_data)
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert called_event.event_type == "vitals.ingested"

    @pytest.mark.asyncio
    async def test_dispatch_wildcard_handler(self):
        consumer = EventConsumer(topics=[TOPIC_VITALS_INGESTED])
        handler = AsyncMock()
        consumer.register("vitals.*", handler)

        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "vitals.ingested",
            "source": "device",
            "org_id": "org-1",
            "timestamp": "2026-03-14T10:00:00+00:00",
            "payload": {},
        }
        await consumer._dispatch(event_data)
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_no_matching_handler(self):
        consumer = EventConsumer(topics=[TOPIC_VITALS_INGESTED])
        handler = AsyncMock()
        consumer.register("alert.generated", handler)

        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "vitals.ingested",
            "source": "device",
            "org_id": "org-1",
            "timestamp": "2026-03-14T10:00:00+00:00",
            "payload": {},
        }
        await consumer._dispatch(event_data)
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_handler_exception_doesnt_crash(self):
        consumer = EventConsumer(topics=[TOPIC_VITALS_INGESTED])
        bad_handler = AsyncMock(side_effect=RuntimeError("Handler crash"))
        good_handler = AsyncMock()
        consumer.register("vitals.ingested", bad_handler)
        consumer.register("vitals.ingested", good_handler)

        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "vitals.ingested",
            "source": "device",
            "org_id": "org-1",
            "timestamp": "2026-03-14T10:00:00+00:00",
            "payload": {},
        }
        # Should not raise
        await consumer._dispatch(event_data)
        # Good handler should still be called
        good_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_invalid_event_data(self):
        consumer = EventConsumer(topics=[TOPIC_VITALS_INGESTED])
        handler = AsyncMock()
        consumer.register("vitals.ingested", handler)

        # Invalid event data (missing required fields)
        await consumer._dispatch({"bad": "data"})
        handler.assert_not_called()
