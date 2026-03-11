"""
WebSocket endpoint for real-time updates.

Streams live alerts, agent decisions, and vital signs to the
clinician dashboard.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("healthos.routes.websocket")
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections per tenant."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str) -> None:
        await websocket.accept()
        self._connections.setdefault(tenant_id, []).append(websocket)
        logger.info("WebSocket connected for tenant=%s (total: %d)",
                    tenant_id, len(self._connections[tenant_id]))

    def disconnect(self, websocket: WebSocket, tenant_id: str) -> None:
        if tenant_id in self._connections:
            self._connections[tenant_id] = [
                ws for ws in self._connections[tenant_id] if ws != websocket
            ]
            logger.info("WebSocket disconnected for tenant=%s", tenant_id)

    async def broadcast(self, tenant_id: str, message: dict) -> None:
        """Broadcast a message to all connections for a tenant."""
        connections = self._connections.get(tenant_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, tenant_id)

    @property
    def connection_count(self) -> dict[str, int]:
        return {tid: len(conns) for tid, conns in self._connections.items()}


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    """
    WebSocket endpoint for real-time dashboard updates.

    Clients connect with their tenant_id and receive:
    - alert.created / alert.acknowledged / alert.resolved
    - agent.decision
    - vital.recorded
    - patient.risk_updated
    """
    await manager.connect(websocket, tenant_id)

    try:
        while True:
            # Receive messages from client (e.g., subscription preferences)
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
                    # Client can subscribe to specific event types
                    await websocket.send_json({
                        "type": "subscribed",
                        "events": message.get("events", ["*"]),
                    })
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)


async def broadcast_event(tenant_id: str, event_type: str, data: dict) -> None:
    """Helper to broadcast events from anywhere in the application."""
    await manager.broadcast(tenant_id, {
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
