"""
Eminence HealthOS — Dashboard API Routes
Aggregated data endpoints for the clinician dashboard.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.database import get_db
from healthos_platform.models import AgentAuditLog, Alert, Patient, Vital
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate counts for the dashboard summary cards."""
    ctx.require_permission(Permission.PATIENT_READ)
    org_id = ctx.org_id
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active patients
    patient_count = (
        await db.execute(
            select(func.count()).select_from(Patient).where(Patient.org_id == org_id)
        )
    ).scalar() or 0

    # Vitals recorded today
    vitals_today = (
        await db.execute(
            select(func.count())
            .select_from(Vital)
            .where(Vital.org_id == org_id, Vital.created_at >= today_start)
        )
    ).scalar() or 0

    # Open alerts breakdown
    alert_rows = (
        await db.execute(
            select(Alert.priority, func.count())
            .where(Alert.org_id == org_id, Alert.status.in_(["pending", "acknowledged"]))
            .group_by(Alert.priority)
        )
    ).all()
    alert_map = {row[0]: row[1] for row in alert_rows}
    open_alerts = sum(alert_map.values())
    critical_alerts = alert_map.get("critical", 0)
    high_alerts = alert_map.get("high", 0)

    # Agent decisions today
    agent_decisions = (
        await db.execute(
            select(func.count())
            .select_from(AgentAuditLog)
            .where(AgentAuditLog.org_id == org_id, AgentAuditLog.created_at >= today_start)
        )
    ).scalar() or 0

    return {
        "active_patients": patient_count,
        "vitals_today": vitals_today,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "high_alerts": high_alerts,
        "agent_decisions": agent_decisions,
    }


@router.get("/agent-activity")
async def recent_agent_activity(
    limit: int = Query(10, ge=1, le=50),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recent agent audit log entries for the activity feed."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    result = await db.execute(
        select(AgentAuditLog)
        .where(AgentAuditLog.org_id == ctx.org_id)
        .order_by(AgentAuditLog.created_at.desc())
        .limit(limit)
    )
    entries = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "agent_name": e.agent_name,
            "action": e.action,
            "patient_id": str(e.patient_id) if e.patient_id else None,
            "confidence_score": e.confidence_score,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
