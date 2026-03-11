"""Clinical alert endpoints."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.config.database import get_db
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id
from services.api.schemas.alert import (
    AlertAcknowledge,
    AlertResolve,
    AlertResponse,
    AlertSummary,
)
from services.api.schemas.common import PaginatedResponse
from shared.models.alert import ClinicalAlert

logger = logging.getLogger("healthos.routes.alerts")
router = APIRouter()


@router.get("", response_model=PaginatedResponse[AlertSummary])
async def list_alerts(
    patient_id: Optional[UUID] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    query = select(ClinicalAlert).where(ClinicalAlert.tenant_id == tenant_id)

    if patient_id:
        query = query.where(ClinicalAlert.patient_id == str(patient_id))
    if severity:
        query = query.where(ClinicalAlert.severity == severity)
    if status_filter:
        query = query.where(ClinicalAlert.status == status_filter)
    if category:
        query = query.where(ClinicalAlert.category == category)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = await db.execute(
        query.order_by(ClinicalAlert.created_at.desc()).offset(offset).limit(limit)
    )
    alerts = rows.scalars().all()

    return PaginatedResponse(
        items=[AlertSummary.model_validate(a) for a in alerts],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(ClinicalAlert).where(
            ClinicalAlert.id == str(alert_id),
            ClinicalAlert.tenant_id == tenant_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    body: AlertAcknowledge,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(ClinicalAlert).where(
            ClinicalAlert.id == str(alert_id),
            ClinicalAlert.tenant_id == tenant_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status != "active":
        raise HTTPException(status_code=400, detail="Alert is not active")

    alert.status = "acknowledged"
    alert.acknowledged_by = str(body.acknowledged_by)
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    body: AlertResolve,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(ClinicalAlert).where(
            ClinicalAlert.id == str(alert_id),
            ClinicalAlert.tenant_id == tenant_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="Alert already resolved")

    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_notes = body.resolution_notes
    await db.flush()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.get("/active/count")
async def active_alert_counts(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get counts of active alerts grouped by severity."""
    query = (
        select(
            ClinicalAlert.severity,
            func.count().label("count"),
        )
        .where(
            ClinicalAlert.tenant_id == tenant_id,
            ClinicalAlert.status == "active",
        )
        .group_by(ClinicalAlert.severity)
    )
    rows = await db.execute(query)
    counts = {row.severity: row.count for row in rows.all()}
    return {
        "total": sum(counts.values()),
        "by_severity": counts,
    }
