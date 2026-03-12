"""
Integration tests for the Patient Portal API endpoints.
Tests /portal/me/summary, /me/vitals, /me/care-plans, /me/appointments, /me/alerts.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.models import Alert, CarePlan, Encounter, Patient, Vital
from tests.integration.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures — seed portal-specific data
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def _portal_vitals(db_session: AsyncSession, seed_patient: Patient, seed_org):
    """Seed vitals for the portal patient."""
    now = datetime.now(timezone.utc)
    vitals = [
        Vital(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            vital_type="heart_rate",
            value={"bpm": 72},
            unit="bpm",
            recorded_at=now - timedelta(hours=i),
            source="wearable",
        )
        for i in range(3)
    ]
    vitals.append(
        Vital(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            vital_type="glucose",
            value={"mg_dl": 110},
            unit="mg/dL",
            recorded_at=now - timedelta(hours=1),
            source="home_device",
        )
    )
    for v in vitals:
        db_session.add(v)
    return vitals


@pytest.fixture
def _portal_alerts(db_session: AsyncSession, seed_patient: Patient, seed_org):
    """Seed alerts for the portal patient."""
    alerts = [
        Alert(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            alert_type="patient_notification",
            priority="moderate",
            status="pending",
            message="Your blood pressure reading was elevated.",
        ),
        Alert(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            alert_type="telehealth_trigger",
            priority="high",
            status="acknowledged",
            message="Telehealth visit recommended based on recent trends.",
        ),
        Alert(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            alert_type="nurse_review",
            priority="low",
            status="pending",
            message="Nurse review only — should not appear in patient alerts.",
        ),
    ]
    for a in alerts:
        db_session.add(a)
    return alerts


@pytest.fixture
def _portal_care_plans(db_session: AsyncSession, seed_patient: Patient, seed_org):
    """Seed care plans for the portal patient."""
    plans = [
        CarePlan(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            plan_type="diabetes_management",
            goals=[{"description": "HbA1c < 7%"}],
            interventions=[{"description": "Daily glucose monitoring"}],
            monitoring_cadence={"frequency": "weekly"},
            status="active",
        ),
        CarePlan(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            plan_type="weight_management",
            goals=[{"description": "Reduce BMI by 2 points"}],
            interventions=[],
            monitoring_cadence=None,
            status="completed",
        ),
    ]
    for p in plans:
        db_session.add(p)
    return plans


@pytest.fixture
def _portal_encounters(db_session: AsyncSession, seed_patient: Patient, seed_org):
    """Seed encounters / appointments for the portal patient."""
    now = datetime.now(timezone.utc)
    encounters = [
        Encounter(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            encounter_type="telehealth",
            status="scheduled",
            reason="Follow-up on glucose levels",
            scheduled_at=now + timedelta(days=3),
        ),
        Encounter(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            encounter_type="in_person",
            status="completed",
            reason="Annual checkup",
            scheduled_at=now - timedelta(days=30),
            started_at=now - timedelta(days=30),
            ended_at=now - timedelta(days=30) + timedelta(hours=1),
        ),
    ]
    for e in encounters:
        db_session.add(e)
    return encounters


# ═══════════════════════════════════════════════════════════════════════════════
# GET /portal/me/summary
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_my_summary(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_vitals,
    _portal_alerts,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/summary",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()

    # Patient info
    assert body["patient"]["id"] == str(seed_patient.id)
    assert body["patient"]["name"] == "Jane Doe"
    assert body["patient"]["risk_level"] == "moderate"

    # Conditions and medications from seed
    assert len(body["conditions"]) >= 1
    assert len(body["medications"]) >= 1

    # Vitals present
    assert isinstance(body["latest_vitals"], list)
    assert len(body["latest_vitals"]) >= 1

    # Active alerts present
    assert isinstance(body["active_alerts"], list)
    assert len(body["active_alerts"]) >= 1
    for alert in body["active_alerts"]:
        assert "id" in alert
        assert "type" in alert
        assert "priority" in alert


@pytest.mark.asyncio
async def test_summary_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/portal/me/summary")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /portal/me/vitals
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_my_vitals(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_vitals,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/vitals",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_id"] == str(seed_patient.id)
    assert body["period_days"] == 30
    assert body["total"] >= 1
    assert isinstance(body["vitals"], list)
    for v in body["vitals"]:
        assert "type" in v
        assert "value" in v
        assert "recorded_at" in v


@pytest.mark.asyncio
async def test_get_my_vitals_filter_by_type(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_vitals,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/vitals?vital_type=glucose",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    for v in body["vitals"]:
        assert v["type"] == "glucose"


@pytest.mark.asyncio
async def test_get_my_vitals_custom_days(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_vitals,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/vitals?days=7",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_days"] == 7


@pytest.mark.asyncio
async def test_get_my_vitals_invalid_days(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
):
    resp = await client.get(
        "/api/v1/portal/me/vitals?days=0",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_vitals_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/portal/me/vitals")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /portal/me/care-plans
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_my_care_plans(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_care_plans,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/care-plans",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Only active plans should be returned
    for plan in body:
        assert plan["status"] == "active"
        assert "id" in plan
        assert "type" in plan
        assert "goals" in plan
        assert "interventions" in plan


@pytest.mark.asyncio
async def test_care_plans_only_active(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_care_plans,
    db_session,
):
    """Completed care plans should be excluded from the response."""
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/care-plans",
        headers=auth_header(clinician_token),
    )
    body = resp.json()
    plan_types = [p["type"] for p in body]
    assert "diabetes_management" in plan_types
    assert "weight_management" not in plan_types


@pytest.mark.asyncio
async def test_care_plans_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/portal/me/care-plans")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /portal/me/appointments
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_my_appointments(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_encounters,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/appointments",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    for appt in body:
        assert "id" in appt
        assert "type" in appt
        assert "status" in appt
        assert "scheduled_at" in appt


@pytest.mark.asyncio
async def test_appointments_filter_by_status(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_encounters,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/appointments?status=scheduled",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    for appt in body:
        assert appt["status"] == "scheduled"


@pytest.mark.asyncio
async def test_appointments_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/portal/me/appointments")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /portal/me/alerts
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_my_alerts(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_alerts,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/alerts",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Only patient_notification and telehealth_trigger types are returned
    for alert in body:
        assert alert["type"] in ("patient_notification", "telehealth_trigger")
        assert "id" in alert
        assert "priority" in alert
        assert "status" in alert
        assert "message" in alert


@pytest.mark.asyncio
async def test_alerts_excludes_non_patient_types(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _portal_alerts,
    db_session,
):
    """nurse_review alerts should not appear in patient portal alerts."""
    await db_session.flush()
    resp = await client.get(
        "/api/v1/portal/me/alerts",
        headers=auth_header(clinician_token),
    )
    body = resp.json()
    alert_types = {a["type"] for a in body}
    assert "nurse_review" not in alert_types


@pytest.mark.asyncio
async def test_alerts_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/portal/me/alerts")
    assert resp.status_code in (401, 403)
