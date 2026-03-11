"""
Clinician Dashboard API — aggregated views for clinical workflows.

Provides endpoints for dashboard widgets: patient overview, alert summary,
agent pipeline status, risk distribution, and real-time monitoring.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.config.database import get_db
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id
from shared.models.agent import AgentDecision
from shared.models.alert import ClinicalAlert
from shared.models.observation import Observation
from shared.models.patient import Patient

logger = logging.getLogger("healthos.routes.dashboard")
router = APIRouter()


@router.get("/overview")
async def dashboard_overview(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """High-level dashboard overview — key metrics."""
    # Patient counts
    patient_count = (
        await db.execute(
            select(func.count()).select_from(Patient).where(
                Patient.tenant_id == tenant_id,
                Patient.is_deleted == False,
            )
        )
    ).scalar() or 0

    # Active alerts by severity
    alert_query = (
        select(ClinicalAlert.severity, func.count().label("count"))
        .where(
            ClinicalAlert.tenant_id == tenant_id,
            ClinicalAlert.status == "active",
        )
        .group_by(ClinicalAlert.severity)
    )
    alert_rows = await db.execute(alert_query)
    alerts_by_severity = {row.severity: row.count for row in alert_rows.all()}

    # Risk distribution
    risk_query = (
        select(Patient.risk_level, func.count().label("count"))
        .where(
            Patient.tenant_id == tenant_id,
            Patient.is_deleted == False,
            Patient.risk_level.isnot(None),
        )
        .group_by(Patient.risk_level)
    )
    risk_rows = await db.execute(risk_query)
    risk_distribution = {row.risk_level: row.count for row in risk_rows.all()}

    # Agent activity (last 24 hours)
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    agent_count = (
        await db.execute(
            select(func.count()).select_from(AgentDecision).where(
                AgentDecision.tenant_id == tenant_id,
                AgentDecision.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    # HITL pending
    hitl_pending = (
        await db.execute(
            select(func.count()).select_from(AgentDecision).where(
                AgentDecision.tenant_id == tenant_id,
                AgentDecision.requires_hitl == True,
                AgentDecision.created_at >= cutoff,
            )
        )
    ).scalar() or 0

    return {
        "patients": {
            "total": patient_count,
            "risk_distribution": risk_distribution,
        },
        "alerts": {
            "active_total": sum(alerts_by_severity.values()),
            "by_severity": alerts_by_severity,
        },
        "agents": {
            "decisions_24h": agent_count,
            "hitl_pending": hitl_pending,
        },
    }


@router.get("/patients/at-risk")
async def patients_at_risk(
    limit: int = Query(10, ge=1, le=50),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Get highest-risk patients for the dashboard watchlist."""
    query = (
        select(Patient)
        .where(
            Patient.tenant_id == tenant_id,
            Patient.is_deleted == False,
            Patient.risk_score.isnot(None),
        )
        .order_by(Patient.risk_score.desc())
        .limit(limit)
    )
    rows = await db.execute(query)
    patients = rows.scalars().all()

    return [
        {
            "id": str(p.id),
            "mrn": p.mrn,
            "name": f"{p.first_name} {p.last_name}",
            "risk_score": p.risk_score,
            "risk_level": p.risk_level,
        }
        for p in patients
    ]


@router.get("/alerts/recent")
async def recent_alerts(
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Recent alerts for the dashboard feed."""
    query = (
        select(ClinicalAlert)
        .where(ClinicalAlert.tenant_id == tenant_id)
        .order_by(ClinicalAlert.created_at.desc())
        .limit(limit)
    )
    rows = await db.execute(query)
    alerts = rows.scalars().all()

    return [
        {
            "id": str(a.id),
            "patient_id": str(a.patient_id),
            "severity": a.severity,
            "category": a.category,
            "title": a.title,
            "status": a.status,
            "source_agent": a.source_agent,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.get("/agents/performance")
async def agent_performance(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Agent performance metrics for the dashboard."""
    query = (
        select(
            AgentDecision.agent_name,
            AgentDecision.agent_tier,
            func.count().label("total"),
            func.avg(AgentDecision.confidence).label("avg_confidence"),
            func.avg(AgentDecision.duration_ms).label("avg_duration_ms"),
            func.sum(AgentDecision.input_tokens).label("total_input_tokens"),
            func.sum(AgentDecision.output_tokens).label("total_output_tokens"),
            func.sum(AgentDecision.cost_usd).label("total_cost"),
            func.sum(case((AgentDecision.requires_hitl == True, 1), else_=0)).label("hitl_count"),
        )
        .where(AgentDecision.tenant_id == tenant_id)
        .group_by(AgentDecision.agent_name, AgentDecision.agent_tier)
        .order_by(AgentDecision.agent_tier)
    )
    rows = await db.execute(query)

    return [
        {
            "agent_name": row.agent_name,
            "agent_tier": row.agent_tier,
            "total_decisions": row.total,
            "avg_confidence": round(float(row.avg_confidence or 0), 3),
            "avg_duration_ms": round(float(row.avg_duration_ms or 0), 1),
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            "total_cost_usd": round(float(row.total_cost or 0), 4),
            "hitl_rate": round(float(row.hitl_count or 0) / max(row.total, 1), 3),
        }
        for row in rows.all()
    ]
