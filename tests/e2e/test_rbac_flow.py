"""
E2E Test: Role-Based Access Control Flow

Verifies multi-role access patterns across the platform:
1. Admin can access everything
2. Clinician can manage patients and vitals
3. Nurse has read-only patient access + vitals write
4. Unauthenticated requests are rejected
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.integration.conftest import auth_header


@pytest.mark.asyncio
async def test_admin_full_access(client: AsyncClient, admin_token: str, seed_patient):
    """Admin role has unrestricted access to all endpoints."""
    headers = auth_header(admin_token)

    # Can list patients
    resp = await client.get("/api/v1/patients", headers=headers)
    assert resp.status_code == 200

    # Can create patients
    resp = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"demographics": {"name": "Admin Created"}, "conditions": [], "medications": []},
    )
    assert resp.status_code == 201

    # Can view dashboard
    resp = await client.get("/api/v1/dashboard/summary", headers=headers)
    assert resp.status_code == 200

    # Can view agent activity
    resp = await client.get("/api/v1/dashboard/agent-activity", headers=headers)
    assert resp.status_code == 200

    # Can list alerts
    resp = await client.get("/api/v1/alerts", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_clinician_patient_management(client: AsyncClient, clinician_token: str, seed_patient):
    """Clinician can perform full patient management lifecycle."""
    headers = auth_header(clinician_token)
    patient_id = str(seed_patient.id)

    # Create patient
    resp = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "mrn": "RBAC-CLN-001",
            "demographics": {"name": "Clinician Patient"},
            "conditions": [],
            "medications": [],
        },
    )
    assert resp.status_code == 201
    new_pid = resp.json()["id"]

    # Read patient
    resp = await client.get(f"/api/v1/patients/{new_pid}", headers=headers)
    assert resp.status_code == 200

    # Update patient
    resp = await client.put(
        f"/api/v1/patients/{new_pid}",
        headers=headers,
        json={"demographics": {"name": "Updated Name"}, "conditions": [], "medications": []},
    )
    assert resp.status_code == 200

    # Create vitals
    resp = await client.post(
        "/api/v1/vitals",
        headers=headers,
        json={
            "patient_id": new_pid,
            "vital_type": "heart_rate",
            "value": {"bpm": 72},
            "unit": "bpm",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_nurse_limited_access(client: AsyncClient, nurse_token: str, seed_patient):
    """Nurse can read patients and manage vitals, but cannot write patients."""
    headers = auth_header(nurse_token)

    # Can read patients
    resp = await client.get("/api/v1/patients", headers=headers)
    assert resp.status_code == 200

    # Cannot create patients
    resp = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={"demographics": {"name": "Nurse Cannot Create"}},
    )
    assert resp.status_code == 403

    # Can create vitals
    resp = await client.post(
        "/api/v1/vitals",
        headers=headers,
        json={
            "patient_id": str(seed_patient.id),
            "vital_type": "weight",
            "value": {"kg": 75.5},
            "unit": "kg",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201

    # Can read vitals
    resp = await client.get(
        f"/api/v1/vitals/{seed_patient.id}",
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient):
    """All protected endpoints reject requests without auth tokens."""
    endpoints = [
        ("GET", "/api/v1/patients"),
        ("POST", "/api/v1/patients"),
        ("GET", "/api/v1/alerts"),
        ("GET", "/api/v1/dashboard/summary"),
        ("GET", "/api/v1/dashboard/agent-activity"),
        ("POST", "/api/v1/vitals"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = await client.get(path)
        else:
            resp = await client.post(path, json={})
        assert resp.status_code in (401, 403, 422), f"{method} {path} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    """Requests with invalid JWT tokens are rejected."""
    headers = auth_header("invalid.jwt.token")
    resp = await client.get("/api/v1/patients", headers=headers)
    assert resp.status_code == 401
