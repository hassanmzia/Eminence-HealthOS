"""Analytics module API routes."""

import logging

from fastapi import APIRouter, Depends

from platform.agents.base import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

logger = logging.getLogger("healthos.routes.analytics")
router = APIRouter()


@router.post("/population-health")
async def population_health_analysis(
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run population health analysis."""
    from modules.analytics.agents.population_health import PopulationHealthAgent

    agent = PopulationHealthAgent()
    output = await agent.execute(AgentInput(
        tenant_id=tenant_id,
        data=body,
    ))
    return output.data


@router.post("/outcomes")
async def outcome_tracking(
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Track clinical outcomes for a patient or cohort."""
    from modules.analytics.agents.outcome_tracker import OutcomeTrackerAgent

    agent = OutcomeTrackerAgent()
    output = await agent.execute(AgentInput(
        patient_id=body.get("patient_id"),
        tenant_id=tenant_id,
        data=body,
    ))
    return output.data


@router.post("/costs")
async def cost_analysis(
    body: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Run cost analysis and ROI calculations."""
    from modules.analytics.agents.cost_analyzer import CostAnalyzerAgent

    agent = CostAnalyzerAgent()
    output = await agent.execute(AgentInput(
        tenant_id=tenant_id,
        data=body,
    ))
    return output.data
