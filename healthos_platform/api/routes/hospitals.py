"""
Eminence HealthOS — Hospital & Department API Routes
Imported from InhealthUSA hospital/department management.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_admin,
)
from healthos_platform.database import get_db
from healthos_platform.models import Department, Hospital, Patient, ProviderProfile, NurseProfile

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class HospitalCreate(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None


class HospitalResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    phone: str | None
    email: str | None
    website: str | None
    is_active: bool
    created_at: datetime
    department_count: int = 0
    provider_count: int = 0
    nurse_count: int = 0
    patient_count: int = 0

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    hospital_id: uuid.UUID
    name: str
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    head_of_department: str | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    hospital_id: uuid.UUID
    name: str
    location: str | None
    phone: str | None
    email: str | None
    head_of_department: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Hospital Endpoints ───────────────────────────────────────────────────────


async def _hospital_with_counts(hospital: Hospital, db: AsyncSession) -> dict:
    """Build a HospitalResponse dict with aggregated counts."""
    dept_count = (await db.execute(
        select(func.count(Department.id)).where(Department.hospital_id == hospital.id)
    )).scalar() or 0
    provider_count = (await db.execute(
        select(func.count(ProviderProfile.id)).where(ProviderProfile.hospital_id == hospital.id)
    )).scalar() or 0
    nurse_count = (await db.execute(
        select(func.count(NurseProfile.id)).where(NurseProfile.hospital_id == hospital.id)
    )).scalar() or 0
    patient_count = (await db.execute(
        select(func.count(Patient.id)).where(Patient.hospital_id == hospital.id)
    )).scalar() or 0
    return HospitalResponse(
        id=hospital.id,
        name=hospital.name,
        address=hospital.address,
        city=hospital.city,
        state=hospital.state,
        zip_code=hospital.zip_code,
        phone=hospital.phone,
        email=hospital.email,
        website=hospital.website,
        is_active=hospital.is_active,
        created_at=hospital.created_at,
        department_count=dept_count,
        provider_count=provider_count,
        nurse_count=nurse_count,
        patient_count=patient_count,
    )


@router.get("", response_model=list[HospitalResponse])
async def list_hospitals(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Hospital).where(Hospital.org_id == ctx.org_id, Hospital.is_active.is_(True))
    )
    hospitals = result.scalars().all()
    return [await _hospital_with_counts(h, db) for h in hospitals]


@router.post("", response_model=HospitalResponse, status_code=201)
async def create_hospital(
    body: HospitalCreate,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    hospital = Hospital(org_id=ctx.org_id, **body.model_dump())
    db.add(hospital)
    await db.flush()
    return hospital


@router.get("/{hospital_id}", response_model=HospitalResponse)
async def get_hospital(
    hospital_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Hospital).where(Hospital.id == hospital_id, Hospital.org_id == ctx.org_id)
    )
    hospital = result.scalar_one_or_none()
    if not hospital:
        raise HTTPException(404, "Hospital not found")
    return await _hospital_with_counts(hospital, db)


@router.get("/{hospital_id}/departments", response_model=list[DepartmentResponse])
async def list_departments(
    hospital_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Department).where(
            Department.hospital_id == hospital_id,
            Department.org_id == ctx.org_id,
            Department.is_active.is_(True),
        )
    )
    return result.scalars().all()


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: DepartmentCreate,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    dept = Department(org_id=ctx.org_id, **body.model_dump())
    db.add(dept)
    await db.flush()
    return dept
