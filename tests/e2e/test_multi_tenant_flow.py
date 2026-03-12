"""
E2E Test: Multi-Tenant Isolation Flow

Verifies that data created by one org is not visible to another:
1. Create two separate organizations
2. Register users in each org
3. Create patients in each org
4. Verify cross-tenant isolation
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.models import Organization, User
from healthos_platform.security.auth import create_access_token, hash_password
from tests.integration.conftest import _override_settings, auth_header


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    """Patients from org A are not visible to users of org B."""

    # ── Create two orgs ──────────────────────────────────────────────
    org_a = Organization(
        name="Hospital Alpha",
        slug="hospital-alpha",
        tier="enterprise",
        hipaa_baa_signed=True,
    )
    org_b = Organization(
        name="Clinic Beta",
        slug="clinic-beta",
        tier="starter",
    )
    db_session.add(org_a)
    db_session.add(org_b)
    await db_session.flush()

    # ── Create users in each org ─────────────────────────────────────
    user_a = User(
        org_id=org_a.id,
        email="doc@alpha.health",
        hashed_password=hash_password("alpha123"),
        role="clinician",
        full_name="Dr. Alpha",
    )
    user_b = User(
        org_id=org_b.id,
        email="doc@beta.health",
        hashed_password=hash_password("beta123"),
        role="clinician",
        full_name="Dr. Beta",
    )
    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.flush()

    # ── Get tokens ───────────────────────────────────────────────────
    import healthos_platform.config.settings as settings_mod
    import healthos_platform.config as config_mod

    original = settings_mod.get_settings
    settings_mod.get_settings = _override_settings
    config_mod.get_settings = _override_settings

    try:
        token_a = create_access_token(user_a.id, org_a.id, "clinician")
        token_b = create_access_token(user_b.id, org_b.id, "clinician")
    finally:
        settings_mod.get_settings = original
        config_mod.get_settings = original

    headers_a = auth_header(token_a)
    headers_b = auth_header(token_b)

    # ── Org A creates a patient ──────────────────────────────────────
    create_resp = await client.post(
        "/api/v1/patients",
        headers=headers_a,
        json={
            "mrn": "ALPHA-001",
            "demographics": {"name": "Alpha Patient"},
            "conditions": [],
            "medications": [],
        },
    )
    assert create_resp.status_code == 201
    alpha_patient_id = create_resp.json()["id"]

    # ── Org A can see its patient ────────────────────────────────────
    resp = await client.get("/api/v1/patients", headers=headers_a)
    assert resp.status_code == 200
    a_patients = resp.json()
    a_ids = {p["id"] for p in a_patients["patients"]}
    assert alpha_patient_id in a_ids

    # ── Org B cannot see Org A's patient ─────────────────────────────
    resp = await client.get("/api/v1/patients", headers=headers_b)
    assert resp.status_code == 200
    b_patients = resp.json()
    b_ids = {p["id"] for p in b_patients["patients"]}
    assert alpha_patient_id not in b_ids

    # ── Org B cannot directly access Org A's patient ─────────────────
    resp = await client.get(
        f"/api/v1/patients/{alpha_patient_id}",
        headers=headers_b,
    )
    assert resp.status_code == 404
