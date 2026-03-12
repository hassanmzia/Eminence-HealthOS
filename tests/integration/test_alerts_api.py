"""
Integration tests for the Alerts API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.models import Alert
from tests.integration.conftest import auth_header


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seed_alert(db_session: AsyncSession, seed_patient) -> Alert:
    alert = Alert(
        patient_id=seed_patient.id,
        org_id=seed_patient.org_id,
        alert_type="nurse_review",
        priority="high",
        status="pending",
        message="Heart rate anomaly detected",
    )
    db_session.add(alert)
    await db_session.flush()
    await db_session.refresh(alert)
    return alert


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/alerts
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient, clinician_token: str, seed_alert):
    resp = await client.get(
        "/api/v1/alerts",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_list_alerts_filter_by_status(client: AsyncClient, clinician_token: str, seed_alert):
    resp = await client.get(
        "/api/v1/alerts?status=pending",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    for a in body:
        assert a["status"] == "pending"


@pytest.mark.asyncio
async def test_list_alerts_filter_by_priority(client: AsyncClient, clinician_token: str, seed_alert):
    resp = await client.get(
        "/api/v1/alerts?priority=high",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    for a in body:
        assert a["priority"] == "high"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/alerts/{id}/acknowledge
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_acknowledge_alert(client: AsyncClient, clinician_token: str, seed_alert):
    resp = await client.post(
        f"/api/v1/alerts/{seed_alert.id}/acknowledge",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "acknowledged"
    assert body["acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_acknowledge_alert_not_found(client: AsyncClient, clinician_token: str, seed_users):
    resp = await client.post(
        f"/api/v1/alerts/{uuid.uuid4()}/acknowledge",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/alerts/{id}/resolve
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_resolve_alert(client: AsyncClient, clinician_token: str, seed_alert):
    resp = await client.post(
        f"/api/v1/alerts/{seed_alert.id}/resolve",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"


# ═══════════════════════════════════════════════════════════════════════════════
# RBAC — Nurse can acknowledge but not resolve/manage
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_nurse_can_acknowledge_alert(client: AsyncClient, nurse_token: str, seed_alert):
    resp = await client.post(
        f"/api/v1/alerts/{seed_alert.id}/acknowledge",
        headers=auth_header(nurse_token),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_nurse_cannot_resolve_alert(client: AsyncClient, nurse_token: str, seed_alert):
    resp = await client.post(
        f"/api/v1/alerts/{seed_alert.id}/resolve",
        headers=auth_header(nurse_token),
    )
    assert resp.status_code == 403
