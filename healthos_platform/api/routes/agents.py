"""
Eminence HealthOS — Agent Control API Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.api.schemas import (
    AgentInfoResponse,
    AgentTriggerRequest,
    PipelineResultResponse,
)
from healthos_platform.orchestrator.engine import ExecutionEngine
from healthos_platform.orchestrator.registry import registry
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/agents", tags=["Agents"])

engine = ExecutionEngine()


@router.get("", response_model=list[AgentInfoResponse])
async def list_agents(ctx: TenantContext = Depends(get_current_user)):
    """List all registered agents."""
    ctx.require_permission(Permission.AGENTS_VIEW)
    return registry.list_agents()


@router.post("/trigger", response_model=PipelineResultResponse)
async def trigger_pipeline(
    request: AgentTriggerRequest,
    ctx: TenantContext = Depends(get_current_user),
):
    """Trigger an agent pipeline for a specific event."""
    ctx.require_permission(Permission.AGENTS_MANAGE)

    state = await engine.execute_event(
        event_type=request.event_type,
        org_id=ctx.org_id,
        patient_id=request.patient_id,
        payload=request.payload,
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


@router.get("/routes")
async def list_routes(ctx: TenantContext = Depends(get_current_user)):
    """List all event-to-agent routing rules."""
    ctx.require_permission(Permission.AGENTS_VIEW)
    return engine.router.list_routes()
