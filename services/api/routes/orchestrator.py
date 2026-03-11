"""Orchestrator API endpoints — pipeline execution and agent management."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

logger = logging.getLogger("healthos.routes.orchestrator")
router = APIRouter()

# Singleton orchestrator instance
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from healthos_platform.orchestrator.engine import OrchestratorEngine
        from modules.rpm.registry import register_rpm_agents

        _engine = OrchestratorEngine()
        register_rpm_agents(_engine)
    return _engine


class PipelineRequest(BaseModel):
    patient_id: str
    trigger: str = "manual"
    trigger_data: dict = {}
    tiers: Optional[list[str]] = None


class SingleAgentRequest(BaseModel):
    patient_id: Optional[str] = None
    data: dict = {}


@router.post("/pipeline/run")
async def run_pipeline(
    body: PipelineRequest,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Execute the full agent pipeline for a patient."""
    from healthos_platform.orchestrator.engine import OrchestratorContext
    from healthos_platform.agents.base import AgentTier

    engine = get_engine()

    tiers = None
    if body.tiers:
        tiers = [AgentTier(t) for t in body.tiers]

    context = OrchestratorContext(
        patient_id=body.patient_id,
        tenant_id=tenant_id,
        trigger=body.trigger,
        trigger_data=body.trigger_data,
    )

    result = await engine.run_pipeline(context, tiers=tiers)

    return {
        "trace_id": result.trace_id,
        "agents_run": len(result.agent_outputs),
        "requires_hitl": result.requires_hitl,
        "escalation_path": result.escalation_path,
        "errors": result.errors,
        "outputs": [
            {
                "agent": o.agent_name,
                "tier": o.agent_tier,
                "decision": o.decision,
                "confidence": o.confidence,
                "risk_level": o.risk_level,
                "duration_ms": o.duration_ms,
            }
            for o in result.agent_outputs
        ],
    }


@router.post("/agent/{agent_name}/execute")
async def execute_single_agent(
    agent_name: str,
    body: SingleAgentRequest,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Execute a single agent by name."""
    from healthos_platform.agents.base import AgentInput

    engine = get_engine()

    agent_input = AgentInput(
        patient_id=body.patient_id,
        tenant_id=tenant_id,
        data=body.data,
    )

    try:
        output = await engine.run_single_agent(agent_name, agent_input)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "agent_name": output.agent_name,
        "agent_tier": output.agent_tier,
        "decision": output.decision,
        "rationale": output.rationale,
        "confidence": output.confidence,
        "data": output.data,
        "feature_contributions": output.feature_contributions,
        "requires_hitl": output.requires_hitl,
        "risk_level": output.risk_level,
        "duration_ms": output.duration_ms,
    }


@router.get("/registry")
async def list_registered_agents(
    user: CurrentUser = Depends(require_auth),
):
    """List all registered agents and their capabilities."""
    engine = get_engine()
    return engine.registered_agents
