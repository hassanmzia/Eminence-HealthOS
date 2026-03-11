"""Patient CRUD endpoints — FHIR R4 compatible."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.config.database import get_db
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id
from services.api.schemas.common import PaginatedResponse
from services.api.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientSummary,
    PatientUpdate,
)
from shared.models.patient import Patient

logger = logging.getLogger("healthos.routes.patients")
router = APIRouter()


@router.get("", response_model=PaginatedResponse[PatientSummary])
async def list_patients(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or MRN"),
    risk_level: Optional[str] = Query(None),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    query = select(Patient).where(
        Patient.tenant_id == tenant_id,
        Patient.is_deleted == False,
    )

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Patient.first_name.ilike(pattern))
            | (Patient.last_name.ilike(pattern))
            | (Patient.mrn.ilike(pattern))
        )
    if risk_level:
        query = query.where(Patient.risk_level == risk_level)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = await db.execute(
        query.order_by(Patient.last_name, Patient.first_name)
        .offset(offset)
        .limit(limit)
    )
    patients = rows.scalars().all()

    return PaginatedResponse(
        items=[PatientSummary.model_validate(p) for p in patients],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    patient = Patient(tenant_id=tenant_id, **body.model_dump())
    db.add(patient)
    await db.flush()
    await db.refresh(patient)
    return PatientResponse.model_validate(patient)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(Patient).where(
            Patient.id == str(patient_id),
            Patient.tenant_id == tenant_id,
            Patient.is_deleted == False,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(Patient).where(
            Patient.id == str(patient_id),
            Patient.tenant_id == tenant_id,
            Patient.is_deleted == False,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(patient, field, value)

    await db.flush()
    await db.refresh(patient)
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(Patient).where(
            Patient.id == str(patient_id),
            Patient.tenant_id == tenant_id,
            Patient.is_deleted == False,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.is_deleted = True
    await db.flush()
