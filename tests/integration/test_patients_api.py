"""
Integration tests for the Patients API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/patients
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_patient(client: AsyncClient, clinician_token: str):
    resp = await client.post(
        "/api/v1/patients",
        headers=auth_header(clinician_token),
        json={
            "mrn": "INT-001",
            "demographics": {"name": "Alice Smith", "dob": "1970-05-20", "gender": "female"},
            "conditions": [{"code": "I10", "display": "Hypertension"}],
            "medications": [],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["mrn"] == "INT-001"
    assert body["demographics"]["name"] == "Alice Smith"
    assert body["risk_level"] == "low"


@pytest.mark.asyncio
async def test_create_patient_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/api/v1/patients",
        json={
            "demographics": {"name": "No Auth"},
        },
    )
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/patients
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_patients(client: AsyncClient, clinician_token: str, seed_patient):
    resp = await client.get(
        "/api/v1/patients",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "patients" in body
    assert body["total"] >= 1
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_list_patients_pagination(client: AsyncClient, clinician_token: str, seed_patient):
    resp = await client.get(
        "/api/v1/patients?page=1&page_size=1",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page_size"] == 1
    assert len(body["patients"]) <= 1


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/patients/{id}
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_patient(client: AsyncClient, clinician_token: str, seed_patient):
    patient_id = str(seed_patient.id)
    resp = await client.get(
        f"/api/v1/patients/{patient_id}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == patient_id
    assert body["mrn"] == "TEST-001"


@pytest.mark.asyncio
async def test_get_patient_not_found(client: AsyncClient, clinician_token: str):
    import uuid

    resp = await client.get(
        f"/api/v1/patients/{uuid.uuid4()}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /api/v1/patients/{id}
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_patient(client: AsyncClient, clinician_token: str, seed_patient):
    patient_id = str(seed_patient.id)
    resp = await client.put(
        f"/api/v1/patients/{patient_id}",
        headers=auth_header(clinician_token),
        json={
            "demographics": {"name": "Jane Doe Updated", "dob": "1980-01-15", "gender": "female"},
            "conditions": [],
            "medications": [{"name": "Insulin", "dose": "10u", "frequency": "daily"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["demographics"]["name"] == "Jane Doe Updated"


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/patients/{id}/risk-score
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_patient_risk_score(client: AsyncClient, clinician_token: str, seed_patient):
    patient_id = str(seed_patient.id)
    resp = await client.get(
        f"/api/v1/patients/{patient_id}/risk-score",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body
    assert "risk_level" in body
    # seed_patient has risk_level="moderate" → score ~0.40
    assert body["risk_level"] == "moderate"


# ═══════════════════════════════════════════════════════════════════════════════
# RBAC — Nurse can read but not write patients
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_nurse_can_read_patients(client: AsyncClient, nurse_token: str, seed_patient):
    resp = await client.get(
        "/api/v1/patients",
        headers=auth_header(nurse_token),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_nurse_cannot_create_patient(client: AsyncClient, nurse_token: str):
    resp = await client.post(
        "/api/v1/patients",
        headers=auth_header(nurse_token),
        json={
            "demographics": {"name": "Unauthorized"},
        },
    )
    assert resp.status_code == 403
