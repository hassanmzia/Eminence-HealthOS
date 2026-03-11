"""Observation endpoints — vitals, labs, device readings."""

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
from services.api.schemas.observation import (
    ObservationCreate,
    ObservationResponse,
    ObservationSummary,
)
from shared.models.observation import Observation

logger = logging.getLogger("healthos.routes.observations")
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ObservationSummary])
async def list_observations(
    patient_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    loinc_code: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    query = select(Observation).where(Observation.tenant_id == tenant_id)

    if patient_id:
        query = query.where(Observation.patient_id == str(patient_id))
    if category:
        query = query.where(Observation.category == category)
    if loinc_code:
        query = query.where(Observation.loinc_code == loinc_code)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = await db.execute(
        query.order_by(Observation.effective_datetime.desc())
        .offset(offset)
        .limit(limit)
    )
    observations = rows.scalars().all()

    return PaginatedResponse(
        items=[ObservationSummary.model_validate(o) for o in observations],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation(
    body: ObservationCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    observation = Observation(tenant_id=tenant_id, **body.model_dump())
    db.add(observation)
    await db.flush()
    await db.refresh(observation)
    return ObservationResponse.model_validate(observation)


@router.get("/{observation_id}", response_model=ObservationResponse)
async def get_observation(
    observation_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(Observation).where(
            Observation.id == str(observation_id),
            Observation.tenant_id == tenant_id,
        )
    )
    obs = result.scalar_one_or_none()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return ObservationResponse.model_validate(obs)


@router.get("/patient/{patient_id}/latest", response_model=list[ObservationSummary])
async def get_latest_vitals(
    patient_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get the latest observation for each LOINC code for a patient."""
    from sqlalchemy import distinct

    # Get distinct LOINC codes, then latest for each
    subq = (
        select(
            Observation.loinc_code,
            func.max(Observation.effective_datetime).label("max_dt"),
        )
        .where(
            Observation.patient_id == str(patient_id),
            Observation.tenant_id == tenant_id,
            Observation.category == "vital-signs",
        )
        .group_by(Observation.loinc_code)
        .subquery()
    )

    query = select(Observation).join(
        subq,
        (Observation.loinc_code == subq.c.loinc_code)
        & (Observation.effective_datetime == subq.c.max_dt),
    ).where(
        Observation.patient_id == str(patient_id),
        Observation.tenant_id == tenant_id,
    )

    rows = await db.execute(query)
    return [ObservationSummary.model_validate(o) for o in rows.scalars().all()]
