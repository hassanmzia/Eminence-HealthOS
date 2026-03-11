"""
Eminence HealthOS — Alerts API Routes
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.api.middleware.tenant import TenantContext, get_current_user
from platform.api.schemas import AlertAcknowledgeRequest, AlertResponse
from platform.database import get_db
from platform.models import Alert
from platform.security.rbac import Permission

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    status: str | None = None,
    priority: str | None = None,
    patient_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts for the current organization."""
    ctx.require_permission(Permission.ALERTS_READ)

    query = (
        select(Alert)
        .where(Alert.org_id == ctx.org_id)
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(Alert.status == status)
    if priority:
        query = query.where(Alert.priority == priority)
    if patient_id:
        query = query.where(Alert.patient_id == patient_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    request: AlertAcknowledgeRequest | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an alert."""
    ctx.require_permission(Permission.ALERTS_ACKNOWLEDGE)

    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.org_id == ctx.org_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.assigned_to = ctx.user_id

    await db.flush()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an alert."""
    ctx.require_permission(Permission.ALERTS_MANAGE)

    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.org_id == ctx.org_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(alert)
    return alert
