"""
Integration tests for the Dashboard API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/dashboard/summary
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_dashboard_summary(client: AsyncClient, clinician_token: str, seed_patient):
    resp = await client.get(
        "/api/v1/dashboard/summary",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "active_patients" in body
    assert "vitals_today" in body
    assert "open_alerts" in body
    assert "critical_alerts" in body
    assert "agent_decisions" in body
    assert body["active_patients"] >= 1


@pytest.mark.asyncio
async def test_dashboard_summary_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/summary")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/dashboard/agent-activity
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_agent_activity(client: AsyncClient, clinician_token: str, seed_users):
    resp = await client.get(
        "/api/v1/dashboard/agent-activity",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


# ═══════════════════════════════════════════════════════════════════════════════
# Unauthenticated endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Eminence HealthOS"


@pytest.mark.asyncio
async def test_metrics(client: AsyncClient):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "healthos_up 1" in resp.text
