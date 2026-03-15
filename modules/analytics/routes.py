"""Analytics module API routes — population health, outcomes, costs, cohorts, readmission risk, and executive intelligence.

All endpoints are covered by HIPAA audit trails via ``analytics_audit_middleware``.
Endpoints that return patient-level data additionally log PHI access records.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.agents.types import AgentInput
from healthos_platform.database import get_db
from modules.analytics.audit import (
    AnalyticsAuditLogger,
    _AuditContext,
    analytics_audit_middleware,
)
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/analytics", tags=["analytics"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Population Health ────────────────────────────────────────────────────────

@router.post("/population-health")
async def population_health_analysis(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
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

    # PHI access — risk stratification exposes patient-level risk scores
    patient_ids = [
        p.get("patient_id", "")
        for p in (output.result or {}).get("patients", [])
        if p.get("patient_id")
    ]
    if patient_ids:
        await AnalyticsAuditLogger.log_phi_access(
            db, user.user_id, tenant_id, patient_ids,
            reason="population risk stratification",
            endpoint="/analytics/population-health/risk-stratification",
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


@router.post("/population-health/quality-metrics")
async def quality_metrics(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Track clinical outcomes for a patient."""
    from modules.analytics.agents.outcome_tracker import OutcomeTrackerAgent

    agent = OutcomeTrackerAgent()
    patient_id_str = body.get("patient_id")
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id_str) if patient_id_str else None,
        trigger="analytics.outcome.track",
        context={"action": body.get("action", "track"), **body},
    ))

    # PHI access — patient-level outcome data
    if patient_id_str:
        await AnalyticsAuditLogger.log_phi_access(
            db, user.user_id, tenant_id, [patient_id_str],
            reason="clinical outcome tracking",
            endpoint="/analytics/outcomes",
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


@router.post("/outcomes/adherence")
async def check_adherence(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check care plan adherence for a patient."""
    from modules.analytics.agents.outcome_tracker import OutcomeTrackerAgent

    agent = OutcomeTrackerAgent()
    patient_id_str = body.get("patient_id")
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id_str) if patient_id_str else None,
        trigger="analytics.outcome.adherence",
        context={"action": "adherence", **body},
    ))

    # PHI access — patient adherence data
    if patient_id_str:
        await AnalyticsAuditLogger.log_phi_access(
            db, user.user_id, tenant_id, [patient_id_str],
            reason="care plan adherence check",
            endpoint="/analytics/outcomes/adherence",
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


@router.post("/outcomes/effectiveness")
async def treatment_effectiveness(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
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

    # PHI access — may contain patient-level effectiveness data
    patient_ids = [
        p.get("patient_id", "")
        for p in (output.result or {}).get("patients", [])
        if p.get("patient_id")
    ]
    if patient_ids:
        await AnalyticsAuditLogger.log_phi_access(
            db, user.user_id, tenant_id, patient_ids,
            reason="treatment effectiveness assessment",
            endpoint="/analytics/outcomes/effectiveness",
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


# ── Cost Analysis ────────────────────────────────────────────────────────────

@router.post("/costs")
async def cost_analysis(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
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

    # Cohort access — log patient exposure
    result = output.result or {}
    cohort_id = result.get("cohort_id", "unknown")
    patient_count = result.get("patient_count", 0)
    if patient_count:
        await AnalyticsAuditLogger.log_cohort_access(
            db, user.user_id, tenant_id, str(cohort_id), patient_count,
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


@router.get("/cohorts/templates")
async def list_cohort_templates(
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
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

    # PHI access — cohort comparison exposes patient-level data
    result = output.result or {}
    for cohort_key in ("cohort_a", "cohort_b"):
        cohort = result.get(cohort_key, {})
        cohort_id = cohort.get("cohort_id") or body.get(f"{cohort_key}_id", "unknown")
        patient_count = cohort.get("patient_count", 0)
        if patient_count:
            await AnalyticsAuditLogger.log_cohort_access(
                db, user.user_id, tenant_id, str(cohort_id), patient_count,
                ip_address=audit.request.client.host if audit.request.client else None,
            )

    return output.result


# ── Readmission Risk ─────────────────────────────────────────────────────────

@router.post("/readmission-risk")
async def predict_readmission_risk(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Predict 30-day readmission risk for a patient."""
    from modules.analytics.agents.readmission_risk import ReadmissionRiskAgent

    agent = ReadmissionRiskAgent()
    patient_id_str = body.get("patient_id")
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id_str) if patient_id_str else None,
        trigger="analytics.readmission.predict",
        context={"action": body.get("action", "predict"), **body},
    ))

    # PHI access — individual readmission risk prediction
    if patient_id_str:
        await AnalyticsAuditLogger.log_phi_access(
            db, user.user_id, tenant_id, [patient_id_str],
            reason="readmission risk prediction",
            endpoint="/analytics/readmission-risk",
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


@router.post("/readmission-risk/batch")
async def batch_readmission_risk(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
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

    # PHI access — batch patient data
    patient_ids = body.get("patient_ids", [])
    if not patient_ids:
        patient_ids = [
            p.get("patient_id", "")
            for p in (output.result or {}).get("predictions", [])
            if p.get("patient_id")
        ]
    if patient_ids:
        await AnalyticsAuditLogger.log_phi_access(
            db, user.user_id, tenant_id, patient_ids,
            reason="batch readmission risk prediction",
            endpoint="/analytics/readmission-risk/batch",
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


@router.post("/readmission-risk/explain")
async def explain_readmission_risk(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Explain a readmission risk prediction."""
    from modules.analytics.agents.readmission_risk import ReadmissionRiskAgent

    agent = ReadmissionRiskAgent()
    patient_id_str = body.get("patient_id")
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id_str) if patient_id_str else None,
        trigger="analytics.readmission.explain",
        context={"action": "explain", **body},
    ))

    # PHI access — individual risk explanation
    if patient_id_str:
        await AnalyticsAuditLogger.log_phi_access(
            db, user.user_id, tenant_id, [patient_id_str],
            reason="readmission risk explanation",
            endpoint="/analytics/readmission-risk/explain",
            ip_address=audit.request.client.host if audit.request.client else None,
        )

    return output.result


# ── Cost/Risk Insight ────────────────────────────────────────────────────────

@router.post("/cost-risk/drivers")
async def cost_drivers(
    body: dict[str, Any],
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
    audit: _AuditContext = Depends(analytics_audit_middleware),
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
