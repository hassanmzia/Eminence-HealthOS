"""Provider CRUD endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.config.database import get_db
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id
from services.api.schemas.common import PaginatedResponse
from services.api.schemas.provider import (
    ProviderCreate,
    ProviderResponse,
    ProviderSummary,
    ProviderUpdate,
)
from shared.models.provider import Provider

logger = logging.getLogger("healthos.routes.providers")
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ProviderSummary])
async def list_providers(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    query = select(Provider).where(Provider.tenant_id == tenant_id, Provider.is_active == True)

    if role:
        query = query.where(Provider.role == role)
    if specialty:
        query = query.where(Provider.specialty == specialty)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = await db.execute(
        query.order_by(Provider.last_name).offset(offset).limit(limit)
    )
    providers = rows.scalars().all()

    return PaginatedResponse(
        items=[ProviderSummary.model_validate(p) for p in providers],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: ProviderCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
):
    provider = Provider(tenant_id=tenant_id, **body.model_dump())
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return ProviderResponse.model_validate(provider)


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(Provider).where(
            Provider.id == str(provider_id),
            Provider.tenant_id == tenant_id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse.model_validate(provider)


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: UUID,
    body: ProviderUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(
        select(Provider).where(
            Provider.id == str(provider_id),
            Provider.tenant_id == tenant_id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)

    await db.flush()
    await db.refresh(provider)
    return ProviderResponse.model_validate(provider)
