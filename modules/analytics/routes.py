"""Analytics module API routes — cost/risk insight and executive intelligence."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

logger = logging.getLogger("healthos.routes.analytics")
router = APIRouter()

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Cost/Risk Insight ────────────────────────────────────────────────────────


@router.post("/cost-risk/drivers")
async def cost_drivers(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Analyze cost drivers across the population."""
    from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent

    agent = CostRiskInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cost_risk.analyze",
        context={"action": "cost_drivers", **body},
    ))
    return output.result


@router.post("/cost-risk/correlation")
async def risk_cost_correlation(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Analyze risk-cost correlations."""
    from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent

    agent = CostRiskInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cost_risk.analyze",
        context={"action": "risk_cost_correlation", **body},
    ))
    return output.result


@router.post("/cost-risk/intervention")
async def intervention_impact(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Model the financial impact of an intervention."""
    from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent

    agent = CostRiskInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cost_risk.intervention",
        context={"action": "intervention_impact", **body},
    ))
    return output.result


@router.post("/cost-risk/opportunities")
async def cost_opportunities(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Scan for cost reduction opportunities."""
    from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent

    agent = CostRiskInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cost_risk.analyze",
        context={"action": "opportunity_scan", **body},
    ))
    return output.result


# ── Executive Intelligence ───────────────────────────────────────────────────


@router.get("/executive/summary")
async def executive_summary(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Generate executive summary."""
    from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

    agent = ExecutiveInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.executive.summary",
        context={"action": "executive_summary"},
    ))
    return output.result


@router.post("/executive/scorecard")
async def kpi_scorecard(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Generate KPI scorecard."""
    from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

    agent = ExecutiveInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.executive.scorecard",
        context={"action": "kpi_scorecard", **body},
    ))
    return output.result


@router.post("/executive/brief")
async def strategic_brief(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Generate strategic briefing."""
    from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

    agent = ExecutiveInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.executive.brief",
        context={"action": "strategic_brief", **body},
    ))
    return output.result


@router.post("/executive/department")
async def department_report(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Generate department-specific report."""
    from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

    agent = ExecutiveInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.executive.summary",
        context={"action": "department_report", **body},
    ))
    return output.result


@router.get("/executive/trends")
async def trend_digest(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Generate executive trend digest."""
    from modules.analytics.agents.executive_insight import ExecutiveInsightAgent

    agent = ExecutiveInsightAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.executive.summary",
        context={"action": "trend_digest"},
    ))
    return output.result
