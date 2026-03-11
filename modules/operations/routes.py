"""Operations module API routes — scheduling, compliance, resources."""

import logging

from fastapi import APIRouter, Depends

from healthos_platform.agents.base import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

logger = logging.getLogger("healthos.routes.operations")
router = APIRouter()


@router.post("/schedule/suggest")
async def suggest_schedule_slots(
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get AI-suggested appointment slots."""
    from modules.operations.agents.scheduler import SchedulerAgent

    agent = SchedulerAgent()
    output = await agent.execute(AgentInput(
        patient_id=body.get("patient_id"),
        tenant_id=tenant_id,
        data={"action": "suggest_slots", **body},
    ))
    return output.data


@router.post("/compliance/check")
async def run_compliance_check(
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Run compliance audit check."""
    from modules.operations.agents.compliance_monitor import ComplianceMonitorAgent

    agent = ComplianceMonitorAgent()
    output = await agent.execute(AgentInput(
        tenant_id=tenant_id,
        data=body,
    ))
    return output.data


@router.post("/resources/optimize")
async def optimize_resources(
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Run resource optimization analysis."""
    from modules.operations.agents.resource_optimizer import ResourceOptimizerAgent

    agent = ResourceOptimizerAgent()
    output = await agent.execute(AgentInput(
        tenant_id=tenant_id,
        data=body,
    ))
    return output.data
