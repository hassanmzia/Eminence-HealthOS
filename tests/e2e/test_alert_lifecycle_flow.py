"""
E2E Test: Alert Lifecycle Flow

Simulates the full alert workflow:
1. Login as clinician
2. Create a patient
3. Seed an alert (simulating agent-generated alert)
4. List alerts and verify it appears
5. Acknowledge the alert as nurse
6. Resolve the alert as clinician
7. Verify alert no longer appears in open alerts
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.models import Alert
from tests.integration.conftest import auth_header


@pytest.mark.asyncio
async def test_alert_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    clinician_token: str,
    nurse_token: str,
    seed_patient,
):
    """End-to-end: alert created → listed → acknowledged → resolved."""

    patient_id = seed_patient.id
    org_id = seed_patient.org_id

    # ── Step 1: Create alerts (simulating agent pipeline output) ─────
    alert_critical = Alert(
        patient_id=patient_id,
        org_id=org_id,
        alert_type="physician_review",
        priority="critical",
        status="pending",
        message="Critical BP spike: 180/110 detected",
    )
    alert_moderate = Alert(
        patient_id=patient_id,
        org_id=org_id,
        alert_type="nurse_review",
        priority="moderate",
        status="pending",
        message="Glucose trending upward over 3 days",
    )
    db_session.add(alert_critical)
    db_session.add(alert_moderate)
    await db_session.flush()
    await db_session.refresh(alert_critical)
    await db_session.refresh(alert_moderate)

    # ── Step 2: Clinician lists all alerts ───────────────────────────
    list_resp = await client.get(
        "/api/v1/alerts",
        headers=auth_header(clinician_token),
    )
    assert list_resp.status_code == 200
    alerts = list_resp.json()
    alert_ids = {a["id"] for a in alerts}
    assert str(alert_critical.id) in alert_ids
    assert str(alert_moderate.id) in alert_ids

    # ── Step 3: Filter by priority ───────────────────────────────────
    critical_resp = await client.get(
        "/api/v1/alerts?priority=critical",
        headers=auth_header(clinician_token),
    )
    assert critical_resp.status_code == 200
    for a in critical_resp.json():
        assert a["priority"] == "critical"

    # ── Step 4: Nurse acknowledges the moderate alert ────────────────
    ack_resp = await client.post(
        f"/api/v1/alerts/{alert_moderate.id}/acknowledge",
        headers=auth_header(nurse_token),
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"
    assert ack_resp.json()["acknowledged_at"] is not None

    # ── Step 5: Nurse cannot resolve (only manage perm can) ──────────
    resolve_resp = await client.post(
        f"/api/v1/alerts/{alert_moderate.id}/resolve",
        headers=auth_header(nurse_token),
    )
    assert resolve_resp.status_code == 403

    # ── Step 6: Clinician resolves both alerts ───────────────────────
    for alert in [alert_critical, alert_moderate]:
        resp = await client.post(
            f"/api/v1/alerts/{alert.id}/resolve",
            headers=auth_header(clinician_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    # ── Step 7: Verify no pending alerts remain ──────────────────────
    pending_resp = await client.get(
        f"/api/v1/alerts?status=pending&patient_id={patient_id}",
        headers=auth_header(clinician_token),
    )
    assert pending_resp.status_code == 200
    assert len(pending_resp.json()) == 0
