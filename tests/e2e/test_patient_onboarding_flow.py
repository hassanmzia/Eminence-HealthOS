"""
E2E Test: Patient Onboarding Flow

Simulates the full workflow of:
1. Register a new clinician
2. Login and get JWT token
3. Create a new patient
4. Record vitals for the patient
5. Retrieve patient and vitals
6. Check dashboard reflects new data
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.integration.conftest import auth_header


@pytest.mark.asyncio
async def test_full_patient_onboarding(client: AsyncClient, seed_org):
    """End-to-end: register user → login → create patient → record vitals → verify."""

    # ── Step 1: Register a new clinician ─────────────────────────────
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dr.e2e@test.health",
            "password": "e2e-secure-pass",
            "full_name": "Dr. E2E Tester",
            "role": "clinician",
            "org_slug": "test-hospital",
        },
    )
    assert register_resp.status_code == 201
    user = register_resp.json()
    assert user["email"] == "dr.e2e@test.health"

    # ── Step 2: Login ────────────────────────────────────────────────
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "dr.e2e@test.health", "password": "e2e-secure-pass"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    headers = auth_header(tokens["access_token"])

    # ── Step 3: Create a patient ─────────────────────────────────────
    patient_resp = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "mrn": "E2E-PAT-001",
            "demographics": {
                "name": "Robert E2E",
                "dob": "1965-08-22",
                "gender": "male",
                "phone": "+1-555-0199",
            },
            "conditions": [
                {"code": "I10", "display": "Essential hypertension", "onset": "2020-01-01"},
                {"code": "E11", "display": "Type 2 diabetes mellitus", "onset": "2019-06-15"},
            ],
            "medications": [
                {"name": "Lisinopril", "dose": "10mg", "frequency": "daily"},
                {"name": "Metformin", "dose": "500mg", "frequency": "twice daily"},
            ],
        },
    )
    assert patient_resp.status_code == 201
    patient = patient_resp.json()
    patient_id = patient["id"]
    assert patient["mrn"] == "E2E-PAT-001"

    # ── Step 4: Record vitals ────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()

    # Single vital
    vital_resp = await client.post(
        "/api/v1/vitals",
        headers=headers,
        json={
            "patient_id": patient_id,
            "vital_type": "heart_rate",
            "value": {"bpm": 78},
            "unit": "bpm",
            "recorded_at": now,
            "source": "wearable",
            "device_id": "APPLE-WATCH-E2E",
        },
    )
    assert vital_resp.status_code == 201
    assert vital_resp.json()["vital_type"] == "heart_rate"

    # Batch vitals
    batch_resp = await client.post(
        "/api/v1/vitals/batch",
        headers=headers,
        json={
            "vitals": [
                {
                    "patient_id": patient_id,
                    "vital_type": "blood_pressure",
                    "value": {"systolic": 138, "diastolic": 88},
                    "unit": "mmHg",
                    "recorded_at": now,
                    "source": "cuff",
                },
                {
                    "patient_id": patient_id,
                    "vital_type": "glucose",
                    "value": {"mg_dl": 145},
                    "unit": "mg/dL",
                    "recorded_at": now,
                    "source": "glucometer",
                },
                {
                    "patient_id": patient_id,
                    "vital_type": "spo2",
                    "value": {"percent": 97},
                    "unit": "%",
                    "recorded_at": now,
                    "source": "pulse_oximeter",
                },
            ]
        },
    )
    assert batch_resp.status_code == 201
    assert len(batch_resp.json()) == 3

    # ── Step 5: Retrieve patient and vitals ──────────────────────────
    get_patient_resp = await client.get(
        f"/api/v1/patients/{patient_id}",
        headers=headers,
    )
    assert get_patient_resp.status_code == 200
    assert get_patient_resp.json()["id"] == patient_id

    vitals_resp = await client.get(
        f"/api/v1/vitals/{patient_id}",
        headers=headers,
    )
    assert vitals_resp.status_code == 200
    vitals = vitals_resp.json()
    assert len(vitals) == 4  # 1 single + 3 batch
    vital_types = {v["vital_type"] for v in vitals}
    assert vital_types == {"heart_rate", "blood_pressure", "glucose", "spo2"}

    # ── Step 6: Risk score ───────────────────────────────────────────
    risk_resp = await client.get(
        f"/api/v1/patients/{patient_id}/risk-score",
        headers=headers,
    )
    assert risk_resp.status_code == 200
    risk = risk_resp.json()
    assert "score" in risk
    assert "risk_level" in risk

    # ── Step 7: Dashboard reflects the data ──────────────────────────
    dash_resp = await client.get(
        "/api/v1/dashboard/summary",
        headers=headers,
    )
    assert dash_resp.status_code == 200
    dash = dash_resp.json()
    assert dash["active_patients"] >= 1
