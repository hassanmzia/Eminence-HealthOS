"""
WebSocket endpoint for real-time updates.

Streams live alerts, agent decisions, vital signs, patient changes,
and workflow events to the clinician dashboard.

Features:
- Per-connection subscription filtering (default: all events)
- Kafka-to-WebSocket bridge via EventConsumer
- Redis pub/sub for multi-instance HA broadcasting
- Per-tenant connection metrics
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from healthos_platform.config import get_settings
from healthos_platform.services.kafka import (
    ALL_TOPICS,
    EventConsumer,
    HealthOSEvent,
)

logger = logging.getLogger("healthos.routes.websocket")
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Supported event types
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_EVENT_TYPES: set[str] = {
    "vital.recorded",
    "alert.created",
    "alert.acknowledged",
    "alert.resolved",
    "agent.decision",
    "patient.risk_updated",
    "patient.enrolled",
    "patient.updated",
    "workflow.task_created",
    "workflow.task_completed",
}

# Redis channel prefix for cross-instance broadcasting
_REDIS_CHANNEL_PREFIX = "healthos:ws:broadcast"


def _redis_channel(tenant_id: str) -> str:
    return f"{_REDIS_CHANNEL_PREFIX}:{tenant_id}"


# ─────────────────────────────────────────────────────────────────────────────
# Connection wrapper — holds socket + subscription filter
# ─────────────────────────────────────────────────────────────────────────────


class _ClientConnection:
    """Wraps a WebSocket with its subscription filter."""

    __slots__ = ("ws", "subscriptions")

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self.subscriptions: set[str] = {"*"}  # default: receive everything

    def is_subscribed(self, event_type: str) -> bool:
        """Return True if this client should receive *event_type*."""
        if "*" in self.subscriptions:
            return True
        # Exact match
        if event_type in self.subscriptions:
            return True
        # Prefix/wildcard match — e.g. "alert.*" matches "alert.created"
        prefix = event_type.rsplit(".", 1)[0] + ".*"
        return prefix in self.subscriptions


# ─────────────────────────────────────────────────────────────────────────────
# ConnectionManager
# ─────────────────────────────────────────────────────────────────────────────


class ConnectionManager:
    """Manages active WebSocket connections per tenant with subscription
    filtering and Redis-backed cross-instance broadcasting."""

    def __init__(self) -> None:
        # tenant_id -> list of client connections
        self._connections: dict[str, list[_ClientConnection]] = {}
        self._redis: aioredis.Redis | None = None
        self._redis_listeners: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    # ── Redis helpers ────────────────────────────────────────────────────

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        return self._redis

    async def _ensure_redis_listener(self, tenant_id: str) -> None:
        """Start a Redis pub/sub listener for *tenant_id* if not running."""
        if tenant_id in self._redis_listeners:
            return
        task = asyncio.create_task(self._redis_subscribe_loop(tenant_id))
        self._redis_listeners[tenant_id] = task

    async def _redis_subscribe_loop(self, tenant_id: str) -> None:
        """Listen on the Redis channel and broadcast locally."""
        try:
            r = await self._get_redis()
            pubsub = r.pubsub()
            channel = _redis_channel(tenant_id)
            await pubsub.subscribe(channel)
            logger.info("Redis pub/sub subscribed channel=%s", channel)

            async for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue
                try:
                    message = json.loads(raw_message["data"])
                    # Broadcast locally — skip re-publishing to Redis
                    await self._local_broadcast(tenant_id, message)
                except Exception:
                    logger.exception("Error handling Redis message on %s", channel)
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled for tenant=%s", tenant_id)
        except Exception:
            logger.exception("Redis subscribe loop failed for tenant=%s", tenant_id)
        finally:
            self._redis_listeners.pop(tenant_id, None)

    async def _publish_to_redis(self, tenant_id: str, message: dict) -> None:
        """Publish a message to Redis so other instances can relay it."""
        try:
            r = await self._get_redis()
            channel = _redis_channel(tenant_id)
            await r.publish(channel, json.dumps(message, default=str))
        except Exception:
            logger.exception("Failed to publish to Redis for tenant=%s", tenant_id)

    # ── Connection lifecycle ─────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, tenant_id: str) -> _ClientConnection:
        await websocket.accept()
        client = _ClientConnection(websocket)
        async with self._lock:
            self._connections.setdefault(tenant_id, []).append(client)
        await self._ensure_redis_listener(tenant_id)
        logger.info(
            "WebSocket connected tenant=%s (total: %d)",
            tenant_id,
            len(self._connections.get(tenant_id, [])),
        )
        return client

    async def disconnect(self, websocket: WebSocket, tenant_id: str) -> None:
        async with self._lock:
            if tenant_id in self._connections:
                self._connections[tenant_id] = [
                    c for c in self._connections[tenant_id] if c.ws is not websocket
                ]
                # Clean up empty tenant lists and their Redis listeners
                if not self._connections[tenant_id]:
                    del self._connections[tenant_id]
                    task = self._redis_listeners.pop(tenant_id, None)
                    if task is not None:
                        task.cancel()
        logger.info("WebSocket disconnected tenant=%s", tenant_id)

    # ── Broadcasting ─────────────────────────────────────────────────────

    async def _local_broadcast(self, tenant_id: str, message: dict) -> None:
        """Send *message* to locally-connected clients whose subscriptions match."""
        event_type = message.get("type", "")
        clients = list(self._connections.get(tenant_id, []))
        dead: list[_ClientConnection] = []

        for client in clients:
            if not client.is_subscribed(event_type):
                continue
            try:
                await client.ws.send_json(message)
            except Exception:
                dead.append(client)

        if dead:
            async with self._lock:
                for client in dead:
                    if tenant_id in self._connections:
                        self._connections[tenant_id] = [
                            c for c in self._connections[tenant_id] if c is not client
                        ]

    async def broadcast(self, tenant_id: str, message: dict) -> None:
        """Broadcast to all matching clients across all instances via Redis."""
        # Publish to Redis — the local listener will pick it up and broadcast locally
        await self._publish_to_redis(tenant_id, message)

    # ── Metrics ──────────────────────────────────────────────────────────

    def get_metrics(self) -> dict[str, Any]:
        """Return per-tenant connection counts and total."""
        per_tenant = {tid: len(conns) for tid, conns in self._connections.items()}
        return {
            "connections_per_tenant": per_tenant,
            "total_connections": sum(per_tenant.values()),
        }

    # ── Shutdown ─────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Cancel all Redis listeners and close the Redis connection."""
        for task in self._redis_listeners.values():
            task.cancel()
        self._redis_listeners.clear()

        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        logger.info("ConnectionManager shut down")


# ─────────────────────────────────────────────────────────────────────────────
# Global manager instance
# ─────────────────────────────────────────────────────────────────────────────

manager = ConnectionManager()

# ─────────────────────────────────────────────────────────────────────────────
# Kafka → WebSocket bridge
# ─────────────────────────────────────────────────────────────────────────────

# Mapping from Kafka event_type prefixes to WebSocket event types.
# Kafka events use slightly different naming (e.g. "vitals.ingested")
# whereas the WS layer uses the client-facing names.
_KAFKA_TO_WS_EVENT: dict[str, str] = {
    "vitals.ingested": "vital.recorded",
    "alert.generated": "alert.created",
    "alert.created": "alert.created",
    "alert.acknowledged": "alert.acknowledged",
    "alert.resolved": "alert.resolved",
    "agent.decision": "agent.decision",
    "patient.risk_updated": "patient.risk_updated",
    "patient.enrolled": "patient.enrolled",
    "patient.updated": "patient.updated",
    "workflow.task_created": "workflow.task_created",
    "workflow.task_completed": "workflow.task_completed",
}


async def _handle_kafka_event(event: HealthOSEvent) -> None:
    """Route a Kafka event to the appropriate tenant's WebSocket clients."""
    ws_event_type = _KAFKA_TO_WS_EVENT.get(event.event_type, event.event_type)

    message = {
        "type": ws_event_type,
        "data": {
            "event_id": event.event_id,
            "source": event.source,
            "patient_id": event.patient_id,
            "payload": event.payload,
            "trace_id": event.trace_id,
            "correlation_id": event.correlation_id,
        },
        "timestamp": event.timestamp,
    }

    tenant_id = event.org_id
    await manager.broadcast(tenant_id, message)


_bridge_consumer: EventConsumer | None = None
_bridge_task: asyncio.Task | None = None


async def start_kafka_bridge() -> None:
    """Start a background Kafka consumer that bridges events to WebSocket.

    Consumes from ALL Kafka topics and forwards every event to the
    ConnectionManager for subscription-filtered delivery.
    """
    global _bridge_consumer, _bridge_task

    if _bridge_task is not None:
        logger.warning("Kafka-WS bridge already running; skipping duplicate start")
        return

    _bridge_consumer = EventConsumer(
        topics=ALL_TOPICS,
        group_id="healthos-ws-bridge",
    )

    # Register a wildcard handler for every known event type
    for kafka_event_type in _KAFKA_TO_WS_EVENT:
        _bridge_consumer.register(kafka_event_type, _handle_kafka_event)

    # Also register prefix-wildcard patterns so new sub-types are caught
    for prefix in ("vitals.*", "alert.*", "agent.*", "patient.*", "workflow.*"):
        _bridge_consumer.register(prefix, _handle_kafka_event)

    _bridge_task = asyncio.create_task(_run_bridge())
    logger.info("kafka_ws_bridge.started", extra={"topics": ALL_TOPICS})


async def _run_bridge() -> None:
    """Wrapper that logs bridge failures and allows restart."""
    try:
        await _bridge_consumer.start()
    except asyncio.CancelledError:
        logger.info("kafka_ws_bridge.cancelled")
    except Exception:
        logger.exception("kafka_ws_bridge.crashed")
    finally:
        global _bridge_task
        _bridge_task = None


async def stop_kafka_bridge() -> None:
    """Gracefully stop the Kafka-WS bridge."""
    global _bridge_consumer, _bridge_task

    if _bridge_consumer is not None:
        await _bridge_consumer.stop()

    if _bridge_task is not None:
        _bridge_task.cancel()
        try:
            await _bridge_task
        except asyncio.CancelledError:
            pass
        _bridge_task = None

    _bridge_consumer = None
    logger.info("kafka_ws_bridge.stopped")


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str) -> None:
    """
    WebSocket endpoint for real-time dashboard updates.

    Clients connect with their tenant_id and receive events filtered by
    their subscription preferences.

    **Client messages**:

    - ``{"type": "ping"}`` — server replies with ``{"type": "pong", ...}``
    - ``{"type": "subscribe", "events": ["alert.*", "vital.recorded"]}``
      — update subscription filter; server confirms with ``subscribed``.
    - ``{"type": "unsubscribe", "events": ["vital.recorded"]}``
      — remove specific subscriptions.

    **Supported event types**:
        vital.recorded, alert.created, alert.acknowledged, alert.resolved,
        agent.decision, patient.risk_updated, patient.enrolled,
        patient.updated, workflow.task_created, workflow.task_completed
    """
    client = await manager.connect(websocket, tenant_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                elif msg_type == "subscribe":
                    events = message.get("events", ["*"])
                    client.subscriptions = set(events)
                    await websocket.send_json({
                        "type": "subscribed",
                        "events": sorted(client.subscriptions),
                    })

                elif msg_type == "unsubscribe":
                    events = set(message.get("events", []))
                    client.subscriptions -= events
                    if not client.subscriptions:
                        client.subscriptions = {"*"}
                    await websocket.send_json({
                        "type": "subscribed",
                        "events": sorted(client.subscriptions),
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, tenant_id)


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────


async def broadcast_event(tenant_id: str, event_type: str, data: dict) -> None:
    """Broadcast an event to WebSocket clients from anywhere in the application.

    This goes through Redis pub/sub so the event reaches clients connected
    to any instance in a multi-node deployment.
    """
    await manager.broadcast(tenant_id, {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
