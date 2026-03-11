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
from healthos_platform.models import Patient
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


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single patient by ID."""
    ctx.require_permission(Permission.PATIENT_READ)

    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.org_id == ctx.org_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


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
    patient_id: uuid.UUID,
    request: PatientCreateRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing patient."""
    ctx.require_permission(Permission.PATIENT_WRITE)

    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.org_id == ctx.org_id)
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
