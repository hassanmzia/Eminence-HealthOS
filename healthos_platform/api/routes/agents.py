"""
Eminence HealthOS — Agent Control API Routes
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.api.schemas import (
    AgentActivityResponse,
    AgentExecutionEntry,
    AgentInfoResponse,
    AgentTriggerRequest,
    PipelineResultResponse,
    PipelineRunEntry,
)
from healthos_platform.database import get_db
from healthos_platform.models import AgentAuditLog
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


@router.get("/activity", response_model=AgentActivityResponse)
async def agent_activity(
    limit: int = Query(10, ge=1, le=50),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return recent agent execution logs, pipeline runs, and runtime statuses."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    # ── Recent individual agent executions ────────────────────────────────
    result = await db.execute(
        select(AgentAuditLog)
        .where(AgentAuditLog.org_id == ctx.org_id)
        .order_by(AgentAuditLog.created_at.desc())
        .limit(limit)
    )
    entries = result.scalars().all()

    executions: list[AgentExecutionEntry] = []
    for e in entries:
        # Derive status from output_summary or confidence
        status = "completed"
        if e.output_summary and isinstance(e.output_summary, dict):
            status = e.output_summary.get("status", "completed")
        elif e.human_review_required:
            status = "waiting_hitl"

        executions.append(
            AgentExecutionEntry(
                id=str(e.id),
                agent_name=e.agent_name,
                action=e.action,
                status=status,
                confidence_score=e.confidence_score,
                duration_ms=e.duration_ms,
                patient_id=str(e.patient_id) if e.patient_id else None,
                trace_id=str(e.trace_id),
                created_at=e.created_at.isoformat() if e.created_at else None,
            )
        )

    # ── Pipeline runs (group executions by trace_id) ─────────────────────
    trace_groups: dict[str, list[AgentExecutionEntry]] = defaultdict(list)
    for ex in executions:
        trace_groups[ex.trace_id].append(ex)

    pipeline_runs: list[PipelineRunEntry] = []
    for trace_id, group in trace_groups.items():
        agents_executed = [g.agent_name for g in group]
        total_duration = sum(g.duration_ms or 0 for g in group)
        trigger_event = group[0].action if group else ""
        started_at = group[-1].created_at if group else None  # oldest entry
        pipeline_runs.append(
            PipelineRunEntry(
                trace_id=trace_id,
                agents_executed=agents_executed,
                total_duration_ms=total_duration,
                trigger_event=trigger_event,
                started_at=started_at,
            )
        )

    # ── Runtime status per agent (from registry + most recent audit log) ─
    agent_statuses: dict[str, str] = {}
    registered = registry.list_agents()
    for agent_info in registered:
        name = agent_info["name"]
        # Check the most recent execution for this agent
        matching = [e for e in executions if e.agent_name == name]
        if matching:
            agent_statuses[name] = matching[0].status
        else:
            agent_statuses[name] = "idle"

    return AgentActivityResponse(
        executions=executions,
        pipeline_runs=pipeline_runs,
        agent_statuses=agent_statuses,
    )


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
