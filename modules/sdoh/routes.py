"""
SDOH module API routes — screening assessments, risk scoring, intervention
tracking, and AI-powered community resource matching.

Follows the Eminence HealthOS module pattern (see modules/analytics/routes.py).
All endpoints are tenant-scoped and require authentication.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id

from modules.sdoh.schemas.assessment import (
    InterventionStatusUpdate,
    SDOHAssessmentCreate,
    SDOHAssessmentResponse,
    SDOHAssessmentUpdate,
    SDOHHighRiskResponse,
    SDOHRecommendationsResponse,
    SDOHScreeningSummary,
)
from modules.sdoh.services.assessment_service import (
    create_assessment,
    delete_assessment,
    generate_intervention_recommendations,
    get_assessment,
    get_high_risk_assessments,
    get_screening_summary,
    list_assessments,
    update_assessment,
    update_intervention_status,
)

router = APIRouter(prefix="/sdoh", tags=["sdoh"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── CRUD ─────────────────────────────────────────────────────────────────────


@router.post("/assessments", response_model=SDOHAssessmentResponse, status_code=201)
async def create_sdoh_assessment(
    body: SDOHAssessmentCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a new SDOH screening assessment.

    Risk level and total score are computed automatically from domain scores.
    Intervention recommendations are generated based on score thresholds.
    """
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    if body.assessed_by_id is None:
        body.assessed_by_id = uuid.UUID(str(user.user_id))

    record = await create_assessment(tid, body)
    return record


@router.get("/assessments", response_model=list[SDOHAssessmentResponse])
async def list_sdoh_assessments(
    patient_id: Optional[str] = Query(None, description="Filter by patient UUID"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: low, medium, high"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """List SDOH assessments for the tenant, with optional filters."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    pid = uuid.UUID(patient_id) if patient_id else None
    records = await list_assessments(tid, patient_id=pid, risk_level=risk_level, limit=limit, offset=offset)
    return records


@router.get("/assessments/{assessment_id}", response_model=SDOHAssessmentResponse)
async def get_sdoh_assessment(
    assessment_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Retrieve a single SDOH assessment by ID."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    record = await get_assessment(tid, assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return record


@router.patch("/assessments/{assessment_id}", response_model=SDOHAssessmentResponse)
async def update_sdoh_assessment(
    assessment_id: uuid.UUID,
    body: SDOHAssessmentUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Partially update an SDOH assessment. Risk is recalculated automatically."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    record = await update_assessment(tid, assessment_id, body)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return record


@router.delete("/assessments/{assessment_id}", status_code=204)
async def delete_sdoh_assessment(
    assessment_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Delete an SDOH assessment."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    deleted = await delete_assessment(tid, assessment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return None


# ── Recommendations & Interventions ──────────────────────────────────────────


@router.get(
    "/assessments/{assessment_id}/recommendations",
    response_model=SDOHRecommendationsResponse,
)
async def get_assessment_recommendations(
    assessment_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get intervention recommendations for a specific assessment."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    record = await get_assessment(tid, assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")

    recs = generate_intervention_recommendations(
        record["food_security_score"],
        record["housing_stability_score"],
        record["transportation_score"],
        record["social_support_score"],
        record["financial_stress_score"],
    )
    return {
        "assessment_id": record["id"],
        "overall_risk": record["overall_sdoh_risk"],
        "total_score": record["total_score"],
        "recommendations": recs,
    }


@router.post("/assessments/{assessment_id}/interventions/status")
async def update_assessment_intervention_status(
    assessment_id: uuid.UUID,
    body: InterventionStatusUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Update the status of a specific intervention within an assessment."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    record = await update_intervention_status(tid, assessment_id, body.domain, body.status)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"message": "Intervention status updated."}


# ── Population-Level Endpoints ───────────────────────────────────────────────


@router.get("/high-risk", response_model=SDOHHighRiskResponse)
async def high_risk_patients(
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Return assessments with high SDOH risk, sorted by severity."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    records = await get_high_risk_assessments(tid, limit=limit)
    return {"count": len(records), "assessments": records}


@router.get("/summary", response_model=SDOHScreeningSummary)
async def screening_summary(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Aggregate SDOH screening statistics for the tenant."""
    tid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    return await get_screening_summary(tid)


# ── AI Agent Endpoints ───────────────────────────────────────────────────────


@router.post("/agent/assess")
async def agent_assess_patient(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run the SDOH Risk Agent for a full AI-powered assessment.

    Accepts FHIR observations, questionnaire responses, and/or direct domain
    flags.  Returns composite risk score, alerts, recommendations, and an
    LLM-generated intervention plan.
    """
    from modules.sdoh.agents.sdoh_risk_agent import SDOHRiskAgent

    patient_id_str = body.get("patient_id")
    agent = SDOHRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id_str) if patient_id_str else None,
        trigger="sdoh.agent.assess",
        context={"action": "assess", **body},
    ))
    return output.result


@router.post("/agent/score")
async def agent_score(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Calculate weighted SDOH composite score from domain flags.

    Pass domain booleans (e.g. ``food_insecurity: true``) in the request body.
    """
    from modules.sdoh.agents.sdoh_risk_agent import SDOHRiskAgent

    agent = SDOHRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="sdoh.agent.score",
        context={"action": "score", **body},
    ))
    return output.result


@router.post("/agent/recommendations")
async def agent_recommendations(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate SDOH intervention recommendations from domain flags."""
    from modules.sdoh.agents.sdoh_risk_agent import SDOHRiskAgent

    agent = SDOHRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="sdoh.agent.recommendations",
        context={"action": "recommendations", **body},
    ))
    return output.result
