"""
Eminence HealthOS — RPM Module API Routes
Endpoints specific to Remote Patient Monitoring.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from platform.api.middleware.tenant import TenantContext, get_current_user
from platform.api.schemas import AgentTriggerRequest, PipelineResultResponse
from platform.orchestrator.engine import ExecutionEngine
from platform.security.rbac import Permission

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
):
    """Get RPM dashboard data for a patient (latest vitals, risk, alerts)."""
    ctx.require_permission(Permission.VITALS_READ)

    # This will be populated from DB queries in production
    return {
        "patient_id": str(patient_id),
        "latest_vitals": {},
        "risk_score": None,
        "active_alerts": [],
        "adherence": {},
        "trends": [],
    }
