"""Analytics module API routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter()

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Population Health ────────────────────────────────────────────────────────

@router.post("/population-health")
async def population_health_analysis(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run population health analysis."""
    from modules.analytics.agents.population_health import PopulationHealthAgent

    agent = PopulationHealthAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.population_health",
        context={"action": body.get("action", "overview"), **body},
    ))
    return output.result


@router.post("/population-health/risk-stratification")
async def risk_stratification(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Stratify patient population by risk level."""
    from modules.analytics.agents.population_health import PopulationHealthAgent

    agent = PopulationHealthAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.risk_stratification",
        context={"action": "risk_stratification", **body},
    ))
    return output.result


@router.post("/population-health/quality-metrics")
async def quality_metrics(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate HEDIS-style quality metrics."""
    from modules.analytics.agents.population_health import PopulationHealthAgent

    agent = PopulationHealthAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.quality_metrics",
        context={"action": "quality_metrics", **body},
    ))
    return output.result


# ── Outcome Tracking ─────────────────────────────────────────────────────────

@router.post("/outcomes")
async def outcome_tracking(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Track clinical outcomes for a patient."""
    from modules.analytics.agents.outcome_tracker import OutcomeTrackerAgent

    agent = OutcomeTrackerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="analytics.outcome.track",
        context={"action": body.get("action", "track"), **body},
    ))
    return output.result


@router.post("/outcomes/adherence")
async def check_adherence(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check care plan adherence for a patient."""
    from modules.analytics.agents.outcome_tracker import OutcomeTrackerAgent

    agent = OutcomeTrackerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="analytics.outcome.adherence",
        context={"action": "adherence", **body},
    ))
    return output.result


@router.post("/outcomes/effectiveness")
async def treatment_effectiveness(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Assess treatment effectiveness across patients."""
    from modules.analytics.agents.outcome_tracker import OutcomeTrackerAgent

    agent = OutcomeTrackerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.outcome.effectiveness",
        context={"action": "effectiveness", **body},
    ))
    return output.result


# ── Cost Analysis ────────────────────────────────────────────────────────────

@router.post("/costs")
async def cost_analysis(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Run cost analysis and ROI calculations."""
    from modules.analytics.agents.cost_analyzer import CostAnalyzerAgent

    agent = CostAnalyzerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cost.analyze",
        context={"action": body.get("action", "summary"), **body},
    ))
    return output.result


@router.post("/costs/rpm-roi")
async def rpm_roi(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Calculate RPM program ROI."""
    from modules.analytics.agents.cost_analyzer import CostAnalyzerAgent

    agent = CostAnalyzerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cost.rpm_roi",
        context={"action": "rpm_roi", **body},
    ))
    return output.result


@router.post("/costs/forecast")
async def savings_forecast(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Project savings over multiple years."""
    from modules.analytics.agents.cost_analyzer import CostAnalyzerAgent

    agent = CostAnalyzerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cost.forecast",
        context={"action": "savings_forecast", **body},
    ))
    return output.result


# ── Cohort Segmentation ──────────────────────────────────────────────────────

@router.post("/cohorts")
async def create_cohort(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a patient cohort from criteria or template."""
    from modules.analytics.agents.cohort_segmentation import CohortSegmentationAgent

    agent = CohortSegmentationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cohort.create",
        context={"action": body.get("action", "create"), **body},
    ))
    return output.result


@router.get("/cohorts/templates")
async def list_cohort_templates(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """List available cohort templates."""
    from modules.analytics.agents.cohort_segmentation import CohortSegmentationAgent

    agent = CohortSegmentationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cohort.templates",
        context={"action": "list_templates"},
    ))
    return output.result


@router.post("/cohorts/compare")
async def compare_cohorts(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Compare two cohorts on key metrics."""
    from modules.analytics.agents.cohort_segmentation import CohortSegmentationAgent

    agent = CohortSegmentationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.cohort.compare",
        context={"action": "compare", **body},
    ))
    return output.result


# ── Readmission Risk ─────────────────────────────────────────────────────────

@router.post("/readmission-risk")
async def predict_readmission_risk(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Predict 30-day readmission risk for a patient."""
    from modules.analytics.agents.readmission_risk import ReadmissionRiskAgent

    agent = ReadmissionRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="analytics.readmission.predict",
        context={"action": body.get("action", "predict"), **body},
    ))
    return output.result


@router.post("/readmission-risk/batch")
async def batch_readmission_risk(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Predict readmission risk for multiple patients."""
    from modules.analytics.agents.readmission_risk import ReadmissionRiskAgent

    agent = ReadmissionRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="analytics.readmission.batch",
        context={"action": "batch_predict", **body},
    ))
    return output.result


@router.post("/readmission-risk/explain")
async def explain_readmission_risk(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Explain a readmission risk prediction."""
    from modules.analytics.agents.readmission_risk import ReadmissionRiskAgent

    agent = ReadmissionRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="analytics.readmission.explain",
        context={"action": "explain", **body},
    ))
    return output.result
