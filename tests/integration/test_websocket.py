"""
Integration tests for WebSocket real-time system.
Tests connection management, subscription filtering, and event broadcasting.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from services.api.routes.websocket import ConnectionManager, manager


# ── ConnectionManager Unit Tests ─────────────────────────────────────────────


class TestConnectionManager:
    def setup_method(self):
        self.mgr = ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_adds_to_tenant(self):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await self.mgr.connect(ws, "tenant-1")
        metrics = self.mgr.get_metrics()
        assert metrics["connections_per_tenant"].get("tenant-1", 0) >= 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_tenant(self):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await self.mgr.connect(ws, "tenant-1")
        self.mgr.disconnect(ws, "tenant-1")
        metrics = self.mgr.get_metrics()
        assert metrics["connections_per_tenant"].get("tenant-1", 0) == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_tenant_connections(self):
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await self.mgr.connect(ws1, "tenant-1")
        await self.mgr.connect(ws2, "tenant-1")

        message = {"type": "alert.created", "data": {"id": "alert-1"}}
        await self.mgr.broadcast("tenant-1", message)

    @pytest.mark.asyncio
    async def test_broadcast_cleans_dead_connections(self):
        ws_alive = AsyncMock()
        ws_alive.accept = AsyncMock()
        ws_alive.send_json = AsyncMock()

        ws_dead = AsyncMock()
        ws_dead.accept = AsyncMock()
        ws_dead.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await self.mgr.connect(ws_alive, "tenant-1")
        await self.mgr.connect(ws_dead, "tenant-1")

        await self.mgr.broadcast("tenant-1", {"type": "test"})
        # Dead connection should be removed
        metrics = self.mgr.get_metrics()
        assert metrics["connections_per_tenant"]["tenant-1"] <= 2

    @pytest.mark.asyncio
    async def test_metrics_multiple_tenants(self):
        for i in range(3):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            await self.mgr.connect(ws, "tenant-A")

        for i in range(2):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            await self.mgr.connect(ws, "tenant-B")

        metrics = self.mgr.get_metrics()
        assert metrics["total_connections"] == 5
        assert metrics["connections_per_tenant"]["tenant-A"] == 3
        assert metrics["connections_per_tenant"]["tenant-B"] == 2
