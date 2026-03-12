"""
Integration tests for the Vitals API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.integration.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/vitals
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_vital(client: AsyncClient, clinician_token: str, seed_patient):
    resp = await client.post(
        "/api/v1/vitals",
        headers=auth_header(clinician_token),
        json={
            "patient_id": str(seed_patient.id),
            "vital_type": "heart_rate",
            "value": {"bpm": 72},
            "unit": "bpm",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "source": "wearable",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["vital_type"] == "heart_rate"
    assert body["value"]["bpm"] == 72


@pytest.mark.asyncio
async def test_create_vital_patient_not_found(client: AsyncClient, clinician_token: str):
    resp = await client.post(
        "/api/v1/vitals",
        headers=auth_header(clinician_token),
        json={
            "patient_id": str(uuid.uuid4()),
            "vital_type": "heart_rate",
            "value": {"bpm": 80},
            "unit": "bpm",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/vitals/batch
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_batch_create_vitals(client: AsyncClient, clinician_token: str, seed_patient):
    now = datetime.now(timezone.utc).isoformat()
    resp = await client.post(
        "/api/v1/vitals/batch",
        headers=auth_header(clinician_token),
        json={
            "vitals": [
                {
                    "patient_id": str(seed_patient.id),
                    "vital_type": "blood_pressure",
                    "value": {"systolic": 120, "diastolic": 80},
                    "unit": "mmHg",
                    "recorded_at": now,
                    "source": "cuff",
                },
                {
                    "patient_id": str(seed_patient.id),
                    "vital_type": "spo2",
                    "value": {"percent": 98},
                    "unit": "%",
                    "recorded_at": now,
                    "source": "pulse_oximeter",
                },
            ]
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body) == 2
    types = {v["vital_type"] for v in body}
    assert types == {"blood_pressure", "spo2"}


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/vitals/{patient_id}
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_patient_vitals(client: AsyncClient, clinician_token: str, seed_patient):
    # First create a vital
    await client.post(
        "/api/v1/vitals",
        headers=auth_header(clinician_token),
        json={
            "patient_id": str(seed_patient.id),
            "vital_type": "glucose",
            "value": {"mg_dl": 110},
            "unit": "mg/dL",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    resp = await client.get(
        f"/api/v1/vitals/{seed_patient.id}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_get_vitals_filter_by_type(client: AsyncClient, clinician_token: str, seed_patient):
    resp = await client.get(
        f"/api/v1/vitals/{seed_patient.id}?vital_type=glucose",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    for v in body:
        assert v["vital_type"] == "glucose"


# ═══════════════════════════════════════════════════════════════════════════════
# RBAC — Nurse can read and write vitals
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_nurse_can_create_vital(client: AsyncClient, nurse_token: str, seed_patient):
    resp = await client.post(
        "/api/v1/vitals",
        headers=auth_header(nurse_token),
        json={
            "patient_id": str(seed_patient.id),
            "vital_type": "temperature",
            "value": {"fahrenheit": 98.6},
            "unit": "F",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201
