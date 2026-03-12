"""
Integration tests for the FHIR R4 API endpoints.
Tests /fhir/r4/Patient, /fhir/r4/Patient/{id}, /fhir/r4/Observation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.models import Patient, Vital
from tests.integration.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures — seed FHIR-specific data
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def _fhir_patient_with_mrn(db_session: AsyncSession, seed_org) -> Patient:
    """Seed a second patient with MRN and fhir_id for FHIR identifier testing."""
    patient = Patient(
        org_id=seed_org.id,
        mrn="FHIR-MRN-001",
        fhir_id="fhir-ext-12345",
        demographics={
            "name": "John Smith",
            "dob": "1975-03-22",
            "gender": "male",
            "contact": {"phone": "555-0199", "email": "john@example.com"},
        },
        conditions=[{"code": "I10", "display": "Hypertension"}],
        medications=[],
        risk_level="high",
    )
    db_session.add(patient)
    return patient


@pytest.fixture
def _fhir_vitals(db_session: AsyncSession, seed_patient: Patient, seed_org):
    """Seed vitals for FHIR Observation queries."""
    now = datetime.now(timezone.utc)
    vitals = [
        Vital(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            vital_type="heart_rate",
            value={"value": 72},
            unit="bpm",
            recorded_at=now - timedelta(hours=1),
            source="wearable",
        ),
        Vital(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            vital_type="blood_pressure",
            value={"systolic": 140, "diastolic": 90},
            unit="mmHg",
            recorded_at=now - timedelta(hours=2),
            source="home_device",
        ),
        Vital(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            vital_type="glucose",
            value={"value": 110},
            unit="mg/dL",
            recorded_at=now - timedelta(hours=3),
            source="home_device",
        ),
        Vital(
            patient_id=seed_patient.id,
            org_id=seed_org.id,
            vital_type="spo2",
            value={"value": 97},
            unit="%",
            recorded_at=now - timedelta(hours=4),
            source="wearable",
        ),
    ]
    for v in vitals:
        db_session.add(v)
    return vitals


# ═══════════════════════════════════════════════════════════════════════════════
# GET /fhir/r4/Patient  (search)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fhir_search_patients(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/fhir/r4/Patient",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "Bundle"
    assert body["type"] == "searchset"
    assert body["total"] >= 1
    assert isinstance(body["entry"], list)

    # Each entry should have a valid FHIR Patient resource
    for entry in body["entry"]:
        resource = entry["resource"]
        assert resource["resourceType"] == "Patient"
        assert "id" in resource
        assert "name" in resource
        assert resource["active"] is True


@pytest.mark.asyncio
async def test_fhir_search_patients_by_identifier(
    client: AsyncClient,
    clinician_token: str,
    _fhir_patient_with_mrn,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/fhir/r4/Patient?identifier=FHIR-MRN-001",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    # The patient with matching MRN should be in results
    mrns = []
    for entry in body["entry"]:
        for ident in entry["resource"].get("identifier", []):
            if ident.get("value"):
                mrns.append(ident["value"])
    assert "FHIR-MRN-001" in mrns


@pytest.mark.asyncio
async def test_fhir_search_patients_with_count(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/fhir/r4/Patient?_count=1",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["entry"]) <= 1


@pytest.mark.asyncio
async def test_fhir_search_patients_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/fhir/r4/Patient")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /fhir/r4/Patient/{patient_id}
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fhir_get_patient_by_id(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    db_session,
):
    await db_session.flush()
    patient_id = str(seed_patient.id)
    resp = await client.get(
        f"/api/v1/fhir/r4/Patient/{patient_id}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "Patient"
    assert body["id"] == patient_id
    assert body["active"] is True

    # Name mapping: "Jane Doe" -> family=Doe, given=[Jane]
    name = body["name"][0]
    assert name["use"] == "official"
    assert name["family"] == "Doe"
    assert "Jane" in name["given"]

    # Gender and birthDate from demographics
    assert body["gender"] == "female"
    assert body["birthDate"] == "1980-01-15"


@pytest.mark.asyncio
async def test_fhir_get_patient_with_identifiers(
    client: AsyncClient,
    clinician_token: str,
    _fhir_patient_with_mrn,
    db_session,
):
    """Patient with MRN and fhir_id should have both identifiers populated."""
    await db_session.flush()
    await db_session.refresh(_fhir_patient_with_mrn)
    patient_id = str(_fhir_patient_with_mrn.id)
    resp = await client.get(
        f"/api/v1/fhir/r4/Patient/{patient_id}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()

    identifier_values = [i["value"] for i in body["identifier"]]
    assert "FHIR-MRN-001" in identifier_values
    assert "fhir-ext-12345" in identifier_values

    # Telecom should have phone and email
    assert "telecom" in body
    telecom_systems = {t["system"] for t in body["telecom"]}
    assert "phone" in telecom_systems
    assert "email" in telecom_systems


@pytest.mark.asyncio
async def test_fhir_get_patient_not_found(
    client: AsyncClient,
    clinician_token: str,
):
    resp = await client.get(
        f"/api/v1/fhir/r4/Patient/{uuid.uuid4()}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_fhir_get_patient_unauthenticated(client: AsyncClient, seed_patient):
    resp = await client.get(f"/api/v1/fhir/r4/Patient/{seed_patient.id}")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /fhir/r4/Observation  (search)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fhir_search_observations(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _fhir_vitals,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/fhir/r4/Observation",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resourceType"] == "Bundle"
    assert body["type"] == "searchset"
    assert body["total"] >= 1

    for entry in body["entry"]:
        obs = entry["resource"]
        assert obs["resourceType"] == "Observation"
        assert obs["status"] == "final"
        assert "code" in obs
        assert "category" in obs
        # Category should be vital-signs
        cat_codes = [
            c["code"]
            for cat in obs["category"]
            for c in cat.get("coding", [])
        ]
        assert "vital-signs" in cat_codes


@pytest.mark.asyncio
async def test_fhir_search_observations_by_subject(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _fhir_vitals,
    db_session,
):
    await db_session.flush()
    patient_id = str(seed_patient.id)
    resp = await client.get(
        f"/api/v1/fhir/r4/Observation?subject=Patient/{patient_id}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for entry in body["entry"]:
        assert entry["resource"]["subject"]["reference"] == f"Patient/{seed_patient.id}"


@pytest.mark.asyncio
async def test_fhir_observation_blood_pressure_components(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _fhir_vitals,
    db_session,
):
    """Blood pressure observations should have systolic/diastolic components."""
    await db_session.flush()
    patient_id = str(seed_patient.id)
    resp = await client.get(
        f"/api/v1/fhir/r4/Observation?subject=Patient/{patient_id}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()

    bp_observations = [
        entry["resource"]
        for entry in body["entry"]
        if any(
            c.get("code") == "85354-9"
            for c in entry["resource"]["code"].get("coding", [])
        )
    ]
    assert len(bp_observations) >= 1

    bp = bp_observations[0]
    assert "component" in bp
    assert len(bp["component"]) == 2
    component_codes = [
        c["code"]
        for comp in bp["component"]
        for c in comp["code"].get("coding", [])
    ]
    assert "8480-6" in component_codes  # systolic
    assert "8462-4" in component_codes  # diastolic


@pytest.mark.asyncio
async def test_fhir_observation_simple_value(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _fhir_vitals,
    db_session,
):
    """Non-BP observations should have a valueQuantity."""
    await db_session.flush()
    patient_id = str(seed_patient.id)
    resp = await client.get(
        f"/api/v1/fhir/r4/Observation?subject=Patient/{patient_id}",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()

    hr_observations = [
        entry["resource"]
        for entry in body["entry"]
        if any(
            c.get("code") == "8867-4"
            for c in entry["resource"]["code"].get("coding", [])
        )
    ]
    assert len(hr_observations) >= 1

    hr = hr_observations[0]
    assert "valueQuantity" in hr
    assert hr["valueQuantity"]["value"] == 72
    assert hr["valueQuantity"]["unit"] == "bpm"


@pytest.mark.asyncio
async def test_fhir_observation_with_count_limit(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _fhir_vitals,
    db_session,
):
    await db_session.flush()
    resp = await client.get(
        "/api/v1/fhir/r4/Observation?_count=2",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["entry"]) <= 2


@pytest.mark.asyncio
async def test_fhir_observation_invalid_subject(
    client: AsyncClient,
    clinician_token: str,
):
    resp = await client.get(
        "/api/v1/fhir/r4/Observation?subject=Patient/not-a-uuid",
        headers=auth_header(clinician_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_fhir_search_observations_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/fhir/r4/Observation")
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR LOINC Code Mapping
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fhir_observation_loinc_codes(
    client: AsyncClient,
    clinician_token: str,
    seed_patient,
    _fhir_vitals,
    db_session,
):
    """Verify that known vital types map to correct LOINC codes."""
    await db_session.flush()
    patient_id = str(seed_patient.id)
    resp = await client.get(
        f"/api/v1/fhir/r4/Observation?subject=Patient/{patient_id}",
        headers=auth_header(clinician_token),
    )
    body = resp.json()

    expected_loinc = {
        "8867-4": "Heart rate",
        "85354-9": "Blood pressure panel",
        "2339-0": "Glucose [Mass/volume] in Blood",
        "2708-6": "Oxygen saturation in Arterial blood",
    }

    found_codes = set()
    for entry in body["entry"]:
        for coding in entry["resource"]["code"].get("coding", []):
            if coding["code"] in expected_loinc:
                found_codes.add(coding["code"])
                assert coding["system"] == "http://loinc.org"
                assert coding["display"] == expected_loinc[coding["code"]]

    # All four vital types were seeded, so all four LOINC codes should appear
    assert found_codes == set(expected_loinc.keys())
