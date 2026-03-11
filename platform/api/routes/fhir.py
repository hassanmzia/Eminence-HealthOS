"""
Eminence HealthOS — FHIR R4 API Routes
Provides FHIR-compatible endpoints for healthcare interoperability.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.api.middleware.tenant import TenantContext, get_current_user
from platform.database import get_db
from platform.models import Encounter, Patient, Vital
from platform.security.rbac import Permission

router = APIRouter(prefix="/fhir/r4", tags=["FHIR R4"])


def to_fhir_patient(patient: Patient) -> dict[str, Any]:
    """Convert HealthOS Patient to FHIR R4 Patient resource."""
    demographics = patient.demographics or {}
    name_parts = demographics.get("name", "").split(" ", 1)

    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(patient.id),
        "identifier": [],
        "active": True,
        "name": [
            {
                "use": "official",
                "family": name_parts[1] if len(name_parts) > 1 else name_parts[0],
                "given": [name_parts[0]] if len(name_parts) > 1 else [],
            }
        ],
        "gender": demographics.get("gender", "unknown"),
        "birthDate": demographics.get("dob", ""),
    }

    if patient.mrn:
        resource["identifier"].append({
            "use": "usual",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
            "value": patient.mrn,
        })

    if patient.fhir_id:
        resource["identifier"].append({
            "system": "urn:eminence:healthos",
            "value": patient.fhir_id,
        })

    contact = demographics.get("contact", {})
    if contact.get("phone"):
        resource["telecom"] = [{"system": "phone", "value": contact["phone"], "use": "mobile"}]
    if contact.get("email"):
        resource.setdefault("telecom", []).append(
            {"system": "email", "value": contact["email"]}
        )

    return resource


def to_fhir_observation(vital: Vital) -> dict[str, Any]:
    """Convert HealthOS Vital to FHIR R4 Observation resource."""
    value_data = vital.value or {}

    # Map vital types to LOINC codes
    loinc_map = {
        "heart_rate": ("8867-4", "Heart rate"),
        "blood_pressure": ("85354-9", "Blood pressure panel"),
        "glucose": ("2339-0", "Glucose [Mass/volume] in Blood"),
        "spo2": ("2708-6", "Oxygen saturation in Arterial blood"),
        "weight": ("29463-7", "Body weight"),
        "temperature": ("8310-5", "Body temperature"),
        "respiratory_rate": ("9279-1", "Respiratory rate"),
    }

    loinc_code, display = loinc_map.get(vital.vital_type, ("unknown", vital.vital_type))

    observation: dict[str, Any] = {
        "resourceType": "Observation",
        "id": str(vital.id),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display,
                }
            ]
        },
        "subject": {"reference": f"Patient/{vital.patient_id}"},
        "effectiveDateTime": vital.recorded_at.isoformat(),
    }

    # Handle different value structures
    if "systolic" in value_data and "diastolic" in value_data:
        observation["component"] = [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": value_data["systolic"], "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": value_data["diastolic"], "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
            },
        ]
    else:
        val = value_data.get("value", 0)
        observation["valueQuantity"] = {
            "value": val,
            "unit": vital.unit or "",
            "system": "http://unitsofmeasure.org",
        }

    return observation


@router.get("/Patient", response_model=dict)
async def search_patients(
    _count: int = Query(20, alias="_count"),
    name: str | None = None,
    identifier: str | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """FHIR Patient search endpoint."""
    ctx.require_permission(Permission.PATIENT_READ)

    query = select(Patient).where(Patient.org_id == ctx.org_id).limit(_count)

    if name:
        query = query.where(Patient.demographics["name"].astext.ilike(f"%{name}%"))
    if identifier:
        query = query.where(Patient.mrn == identifier)

    result = await db.execute(query)
    patients = result.scalars().all()

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(patients),
        "entry": [
            {"resource": to_fhir_patient(p), "fullUrl": f"Patient/{p.id}"}
            for p in patients
        ],
    }


@router.get("/Patient/{patient_id}", response_model=dict)
async def get_fhir_patient(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get FHIR Patient resource by ID."""
    ctx.require_permission(Permission.PATIENT_READ)

    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.org_id == ctx.org_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return to_fhir_patient(patient)


@router.get("/Observation", response_model=dict)
async def search_observations(
    subject: str | None = None,
    code: str | None = None,
    _count: int = Query(50, alias="_count"),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """FHIR Observation search endpoint."""
    ctx.require_permission(Permission.VITALS_READ)

    query = (
        select(Vital)
        .where(Vital.org_id == ctx.org_id)
        .order_by(Vital.recorded_at.desc())
        .limit(_count)
    )

    if subject:
        # Support "Patient/uuid" format
        patient_id_str = subject.replace("Patient/", "")
        try:
            pid = uuid.UUID(patient_id_str)
            query = query.where(Vital.patient_id == pid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid subject reference")

    result = await db.execute(query)
    vitals = result.scalars().all()

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(vitals),
        "entry": [
            {"resource": to_fhir_observation(v), "fullUrl": f"Observation/{v.id}"}
            for v in vitals
        ],
    }
