"""
Eminence HealthOS — Provider / Nurse / OfficeAdmin Profile Routes
Phase 1 RBAC: Role-specific profile management.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_admin,
    require_clinical_staff,
)
from healthos_platform.database import get_db
from healthos_platform.models import NurseProfile, OfficeAdminProfile, ProviderProfile, User

router = APIRouter(prefix="/providers", tags=["providers"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class ProviderProfileCreate(BaseModel):
    user_id: uuid.UUID
    specialty: str
    npi: str
    license_number: str | None = None
    hospital_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


class ProviderProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    specialty: str
    npi: str
    license_number: str | None
    hospital_id: uuid.UUID | None
    department_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NurseProfileCreate(BaseModel):
    user_id: uuid.UUID
    specialty: str = "General"
    license_number: str
    hospital_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


class NurseProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    specialty: str
    license_number: str
    hospital_id: uuid.UUID | None
    department_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OfficeAdminProfileCreate(BaseModel):
    user_id: uuid.UUID
    position: str = "Office Administrator"
    employee_id: str
    hospital_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


class OfficeAdminProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    position: str
    employee_id: str
    hospital_id: uuid.UUID | None
    department_id: uuid.UUID | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Provider Endpoints ───────────────────────────────────────────────────────


@router.get("", response_model=list[ProviderProfileResponse])
async def list_providers(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProviderProfile).where(
            ProviderProfile.org_id == ctx.org_id, ProviderProfile.is_active.is_(True)
        )
    )
    return result.scalars().all()


@router.post("", response_model=ProviderProfileResponse, status_code=201)
async def create_provider(
    body: ProviderProfileCreate,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    profile = ProviderProfile(org_id=ctx.org_id, **body.model_dump())
    db.add(profile)
    await db.flush()
    return profile


@router.get("/{provider_id}", response_model=ProviderProfileResponse)
async def get_provider(
    provider_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProviderProfile).where(
            ProviderProfile.id == provider_id, ProviderProfile.org_id == ctx.org_id
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Provider not found")
    return profile


# ── Nurse Endpoints ──────────────────────────────────────────────────────────


@router.get("/nurses", response_model=list[NurseProfileResponse])
async def list_nurses(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NurseProfile).where(NurseProfile.org_id == ctx.org_id, NurseProfile.is_active.is_(True))
    )
    return result.scalars().all()


@router.post("/nurses", response_model=NurseProfileResponse, status_code=201)
async def create_nurse(
    body: NurseProfileCreate,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    profile = NurseProfile(org_id=ctx.org_id, **body.model_dump())
    db.add(profile)
    await db.flush()
    return profile


# ── Office Admin Endpoints ───────────────────────────────────────────────────


@router.get("/office-admins", response_model=list[OfficeAdminProfileResponse])
async def list_office_admins(
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OfficeAdminProfile).where(
            OfficeAdminProfile.org_id == ctx.org_id, OfficeAdminProfile.is_active.is_(True)
        )
    )
    return result.scalars().all()


@router.post("/office-admins", response_model=OfficeAdminProfileResponse, status_code=201)
async def create_office_admin(
    body: OfficeAdminProfileCreate,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    profile = OfficeAdminProfile(org_id=ctx.org_id, **body.model_dump())
    db.add(profile)
    await db.flush()
    return profile


# ── Role-Specific Dashboard ─────────────────────────────────────────────────


@router.get("/dashboard", tags=["dashboard"])
async def provider_dashboard(
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    """Role-specific dashboard data for clinical staff."""
    from healthos_platform.models import Alert, Encounter, Patient

    patient_count = await db.execute(
        select(func.count()).select_from(Patient).where(Patient.org_id == ctx.org_id)
    )
    alert_count = await db.execute(
        select(func.count())
        .select_from(Alert)
        .where(Alert.org_id == ctx.org_id, Alert.status == "pending")
    )
    encounter_count = await db.execute(
        select(func.count())
        .select_from(Encounter)
        .where(Encounter.org_id == ctx.org_id, Encounter.status == "scheduled")
    )

    return {
        "role": ctx.role,
        "total_patients": patient_count.scalar() or 0,
        "pending_alerts": alert_count.scalar() or 0,
        "scheduled_encounters": encounter_count.scalar() or 0,
    }


from sqlalchemy import func
