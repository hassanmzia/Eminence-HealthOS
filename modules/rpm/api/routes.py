"""
Eminence HealthOS — RPM Module API Routes
Endpoints specific to Remote Patient Monitoring.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.api.schemas import AgentTriggerRequest, PipelineResultResponse
from healthos_platform.database import get_db
from healthos_platform.models import Alert, RiskScore, Vital
from healthos_platform.orchestrator.engine import ExecutionEngine
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/rpm", tags=["RPM"])

engine = ExecutionEngine()


@router.post("/ingest", response_model=PipelineResultResponse)
async def ingest_device_data(
    patient_id: uuid.UUID,
    vitals: list[dict[str, Any]],
    ctx: TenantContext = Depends(get_current_user),
):
    """
    Ingest device data and run through the full RPM agent pipeline:
    device_ingestion → vitals_normalization → anomaly_detection →
    risk_scoring → trend_analysis → adherence_monitoring
    """
    ctx.require_permission(Permission.VITALS_WRITE)

    state = await engine.execute_event(
        event_type="vitals.ingested",
        org_id=ctx.org_id,
        patient_id=patient_id,
        payload={"raw_vitals": vitals},
    )

    return PipelineResultResponse(
        trace_id=state.trace_id,
        trigger_event=state.trigger_event,
        executed_agents=state.executed_agents,
        requires_hitl=state.requires_hitl,
        hitl_reason=state.hitl_reason,
        anomalies_detected=len(state.anomalies),
        alerts_generated=len(state.alert_requests),
    )


@router.get("/dashboard/{patient_id}")
async def patient_rpm_dashboard(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get RPM dashboard data for a patient (latest vitals, risk, alerts)."""
    ctx.require_permission(Permission.VITALS_READ)

    # Latest vitals (most recent per type)
    vitals_result = await db.execute(
        select(Vital)
        .where(Vital.patient_id == patient_id, Vital.org_id == ctx.org_id)
        .order_by(Vital.recorded_at.desc())
        .limit(20)
    )
    vitals = vitals_result.scalars().all()

    # Group by type, keep latest per type
    latest_vitals: dict[str, dict] = {}
    trends: list[dict] = []
    for v in vitals:
        entry = {
            "type": v.vital_type,
            "value": v.value,
            "unit": v.unit,
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            "quality_score": v.quality_score,
        }
        if v.vital_type not in latest_vitals:
            latest_vitals[v.vital_type] = entry
        trends.append(entry)

    # Latest risk score
    risk_result = await db.execute(
        select(RiskScore)
        .where(RiskScore.patient_id == patient_id, RiskScore.org_id == ctx.org_id)
        .order_by(RiskScore.created_at.desc())
        .limit(1)
    )
    risk = risk_result.scalar_one_or_none()

    # Active alerts
    alerts_result = await db.execute(
        select(Alert)
        .where(
            Alert.patient_id == patient_id,
            Alert.org_id == ctx.org_id,
            Alert.status.in_(["pending", "acknowledged"]),
        )
        .order_by(Alert.created_at.desc())
        .limit(10)
    )
    active_alerts = alerts_result.scalars().all()

    return {
        "patient_id": str(patient_id),
        "latest_vitals": latest_vitals,
        "risk_score": {
            "score": risk.score,
            "level": risk.risk_level,
            "type": risk.score_type,
            "factors": risk.factors,
            "calculated_at": risk.created_at.isoformat() if risk.created_at else None,
        } if risk else None,
        "active_alerts": [
            {
                "id": str(a.id),
                "type": a.alert_type,
                "priority": a.priority,
                "status": a.status,
                "message": a.message,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in active_alerts
        ],
        "trends": trends,
    }
