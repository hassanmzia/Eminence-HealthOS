"""
Eminence HealthOS — Patient API Routes
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.api.schemas import (
    PatientCreateRequest,
    PatientListResponse,
    PatientResponse,
)
from healthos_platform.database import get_db
from healthos_platform.models import Patient, RiskScore
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: str | None = None,
    search: str | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List patients for the current organization."""
    ctx.require_permission(Permission.PATIENT_READ)

    query = select(Patient).where(Patient.org_id == ctx.org_id)

    if risk_level:
        query = query.where(Patient.risk_level == risk_level)

    if search:
        query = query.where(
            Patient.demographics["name"].astext.ilike(f"%{search}%")
            | Patient.mrn.ilike(f"%{search}%")
        )

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    patients = result.scalars().all()

    return PatientListResponse(
        patients=[PatientResponse.model_validate(p) for p in patients],
        total=total,
        page=page,
        page_size=page_size,
    )


def _parse_patient_id(raw: str) -> uuid.UUID:
    """Accept both UUID and short IDs like 'pt-002'."""
    try:
        return uuid.UUID(raw)
    except ValueError:
        # Derive a deterministic UUID from short IDs so demo links work
        return uuid.uuid5(uuid.NAMESPACE_URL, f"patient:{raw}")


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single patient by ID."""
    ctx.require_permission(Permission.PATIENT_READ)

    pid = _parse_patient_id(patient_id)
    result = await db.execute(
        select(Patient).where(Patient.id == pid, Patient.org_id == ctx.org_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/{patient_id}/risk-score")
async def get_patient_risk_score(
    patient_id: str,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest risk score for a patient."""
    ctx.require_permission(Permission.PATIENT_READ)

    pid = _parse_patient_id(patient_id)
    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.patient_id == pid, RiskScore.org_id == ctx.org_id)
        .order_by(RiskScore.created_at.desc())
        .limit(1)
    )
    risk = result.scalar_one_or_none()

    if not risk:
        # Fall back to patient's risk_level field
        pat_result = await db.execute(
            select(Patient).where(Patient.id == pid, Patient.org_id == ctx.org_id)
        )
        patient = pat_result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        level_scores = {"critical": 0.85, "high": 0.65, "moderate": 0.40, "low": 0.15}
        return {
            "score": level_scores.get(patient.risk_level, 0.15),
            "risk_level": patient.risk_level,
            "factors": [],
            "recommendations": [],
        }

    return {
        "score": risk.score,
        "risk_level": risk.risk_level,
        "factors": risk.factors or [],
        "recommendations": [],
    }


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    request: PatientCreateRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new patient."""
    ctx.require_permission(Permission.PATIENT_WRITE)

    patient = Patient(
        org_id=ctx.org_id,
        mrn=request.mrn,
        demographics=request.demographics,
        conditions=request.conditions,
        medications=request.medications,
    )
    db.add(patient)
    await db.flush()
    await db.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    request: PatientCreateRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing patient."""
    ctx.require_permission(Permission.PATIENT_WRITE)

    pid = _parse_patient_id(patient_id)
    result = await db.execute(
        select(Patient).where(Patient.id == pid, Patient.org_id == ctx.org_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.demographics = request.demographics
    patient.conditions = request.conditions
    patient.medications = request.medications
    if request.mrn:
        patient.mrn = request.mrn

    await db.flush()
    await db.refresh(patient)
    return patient
