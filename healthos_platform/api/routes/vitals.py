"""
Eminence HealthOS — Vitals API Routes
Handles vital sign ingestion and retrieval.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.api.schemas import VitalBatchRequest, VitalCreateRequest, VitalResponse
from healthos_platform.database import get_db
from healthos_platform.models import Patient, Vital
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/vitals", tags=["Vitals"])


def _parse_patient_id(raw: str) -> uuid.UUID:
    """Accept both UUID and short IDs like 'pt-002'."""
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"patient:{raw}")


@router.get("/{patient_id}", response_model=list[VitalResponse])
async def get_patient_vitals(
    patient_id: str,
    vital_type: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get vitals for a patient, ordered by most recent."""
    ctx.require_permission(Permission.VITALS_READ)

    pid = _parse_patient_id(patient_id)
    query = (
        select(Vital)
        .where(Vital.patient_id == pid, Vital.org_id == ctx.org_id)
        .order_by(Vital.recorded_at.desc())
        .limit(limit)
    )
    if vital_type:
        query = query.where(Vital.vital_type == vital_type)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=VitalResponse, status_code=201)
async def create_vital(
    request: VitalCreateRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a single vital reading."""
    ctx.require_permission(Permission.VITALS_WRITE)

    # Verify patient belongs to org
    result = await db.execute(
        select(Patient).where(Patient.id == request.patient_id, Patient.org_id == ctx.org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")

    vital = Vital(
        patient_id=request.patient_id,
        org_id=ctx.org_id,
        device_id=request.device_id,
        vital_type=request.vital_type,
        value=request.value,
        unit=request.unit,
        recorded_at=request.recorded_at,
        source=request.source,
    )
    db.add(vital)
    await db.flush()
    await db.refresh(vital)
    return vital


@router.post("/batch", response_model=list[VitalResponse], status_code=201)
async def batch_create_vitals(
    request: VitalBatchRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch upload vitals from a device."""
    ctx.require_permission(Permission.VITALS_WRITE)

    vitals = []
    for v in request.vitals:
        vital = Vital(
            patient_id=v.patient_id,
            org_id=ctx.org_id,
            device_id=v.device_id,
            vital_type=v.vital_type,
            value=v.value,
            unit=v.unit,
            recorded_at=v.recorded_at,
            source=v.source,
        )
        db.add(vital)
        vitals.append(vital)

    await db.flush()
    for v in vitals:
        await db.refresh(v)
    return vitals
