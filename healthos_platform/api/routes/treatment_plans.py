"""
Eminence HealthOS — Treatment Plans Routes
AI-proposed and doctor-created treatment plans with review workflow.
Imported from InhealthUSA AIProposedTreatmentPlan / DoctorTreatmentPlan models.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_clinical_staff,
)
from healthos_platform.database import get_db
from healthos_platform.models import AIProposedTreatmentPlan, DoctorTreatmentPlan

router = APIRouter(prefix="/treatment-plans", tags=["treatment-plans"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class AIProposalResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None
    proposed_treatment: str
    medications_suggested: str | None
    lifestyle_recommendations: str | None
    follow_up_recommendations: str | None
    warnings_and_precautions: str | None
    ai_model_name: str | None
    status: str
    doctor_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class AIProposalReviewRequest(BaseModel):
    status: str  # approved, rejected, reviewed
    doctor_notes: str | None = None


class DoctorPlanCreate(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID | None = None
    ai_proposal_id: uuid.UUID | None = None
    plan_title: str
    chief_complaint: str | None = None
    assessment: str | None = None
    treatment_goals: str
    medications: str | None = None
    procedures: str | None = None
    lifestyle_modifications: str | None = None
    dietary_recommendations: str | None = None
    exercise_recommendations: str | None = None
    follow_up_instructions: str | None = None
    warning_signs: str | None = None
    emergency_instructions: str | None = None
    plan_start_date: date | None = None
    plan_end_date: date | None = None
    next_review_date: date | None = None
    additional_notes: str | None = None


class DoctorPlanResponse(BaseModel):
    id: uuid.UUID
    plan_title: str
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None
    encounter_id: uuid.UUID | None
    ai_proposal_id: uuid.UUID | None
    treatment_goals: str
    status: str
    is_visible_to_patient: bool
    plan_start_date: date | None
    plan_end_date: date | None
    next_review_date: date | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── AI Proposal Endpoints ────────────────────────────────────────────────────


@router.get("/ai-proposals", response_model=list[AIProposalResponse])
async def list_ai_proposals(
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    q = select(AIProposedTreatmentPlan).where(AIProposedTreatmentPlan.org_id == ctx.org_id)
    if patient_id:
        q = q.where(AIProposedTreatmentPlan.patient_id == patient_id)
    if status:
        q = q.where(AIProposedTreatmentPlan.status == status)
    offset = (page - 1) * page_size
    result = await db.execute(q.order_by(AIProposedTreatmentPlan.created_at.desc()).offset(offset).limit(page_size))
    return result.scalars().all()


@router.get("/ai-proposals/{proposal_id}", response_model=AIProposalResponse)
async def get_ai_proposal(
    proposal_id: uuid.UUID,
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIProposedTreatmentPlan).where(
            AIProposedTreatmentPlan.id == proposal_id,
            AIProposedTreatmentPlan.org_id == ctx.org_id,
        )
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "AI proposal not found")
    return proposal


@router.post("/ai-proposals/{proposal_id}/review", response_model=AIProposalResponse)
async def review_ai_proposal(
    proposal_id: uuid.UUID,
    body: AIProposalReviewRequest,
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role not in ("doctor", "admin"):
        raise HTTPException(403, "Only doctors can review AI proposals")

    result = await db.execute(
        select(AIProposedTreatmentPlan).where(
            AIProposedTreatmentPlan.id == proposal_id,
            AIProposedTreatmentPlan.org_id == ctx.org_id,
        )
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "AI proposal not found")

    if body.status not in ("approved", "rejected", "reviewed"):
        raise HTTPException(400, "Status must be approved, rejected, or reviewed")

    from datetime import timezone
    proposal.status = body.status
    proposal.doctor_notes = body.doctor_notes
    proposal.reviewed_at = datetime.now(timezone.utc)
    proposal.provider_id = ctx.user_id
    await db.flush()
    return proposal


# ── Doctor Treatment Plan Endpoints ──────────────────────────────────────────


@router.get("/doctor-plans", response_model=list[DoctorPlanResponse])
async def list_doctor_plans(
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(DoctorTreatmentPlan).where(DoctorTreatmentPlan.org_id == ctx.org_id)
    if patient_id:
        q = q.where(DoctorTreatmentPlan.patient_id == patient_id)
    if status:
        q = q.where(DoctorTreatmentPlan.status == status)
    # Patients can only see plans shared with them
    if ctx.role == "patient":
        q = q.where(DoctorTreatmentPlan.is_visible_to_patient.is_(True))
    offset = (page - 1) * page_size
    result = await db.execute(q.order_by(DoctorTreatmentPlan.created_at.desc()).offset(offset).limit(page_size))
    return result.scalars().all()


@router.post("/doctor-plans", response_model=DoctorPlanResponse, status_code=201)
async def create_doctor_plan(
    body: DoctorPlanCreate,
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role not in ("doctor", "admin"):
        raise HTTPException(403, "Only doctors can create treatment plans")

    plan = DoctorTreatmentPlan(
        org_id=ctx.org_id,
        provider_id=ctx.user_id,
        **body.model_dump(),
    )
    db.add(plan)
    await db.flush()
    return plan


@router.get("/doctor-plans/{plan_id}", response_model=DoctorPlanResponse)
async def get_doctor_plan(
    plan_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorTreatmentPlan).where(
            DoctorTreatmentPlan.id == plan_id,
            DoctorTreatmentPlan.org_id == ctx.org_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Treatment plan not found")
    if ctx.role == "patient" and not plan.is_visible_to_patient:
        raise HTTPException(403, "Not authorized")
    return plan


@router.put("/doctor-plans/{plan_id}", response_model=DoctorPlanResponse)
async def update_doctor_plan(
    plan_id: uuid.UUID,
    body: DoctorPlanCreate,
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorTreatmentPlan).where(
            DoctorTreatmentPlan.id == plan_id,
            DoctorTreatmentPlan.org_id == ctx.org_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Treatment plan not found")
    for k, v in body.model_dump().items():
        setattr(plan, k, v)
    await db.flush()
    return plan


@router.post("/doctor-plans/{plan_id}/publish")
async def publish_to_patient(
    plan_id: uuid.UUID,
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorTreatmentPlan).where(
            DoctorTreatmentPlan.id == plan_id,
            DoctorTreatmentPlan.org_id == ctx.org_id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Treatment plan not found")
    plan.is_visible_to_patient = True
    plan.status = "active"
    await db.flush()
    return {"status": "published"}


@router.post("/doctor-plans/{plan_id}/acknowledge")
async def patient_acknowledge(
    plan_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patient acknowledges they've read the treatment plan."""
    result = await db.execute(
        select(DoctorTreatmentPlan).where(
            DoctorTreatmentPlan.id == plan_id,
            DoctorTreatmentPlan.org_id == ctx.org_id,
            DoctorTreatmentPlan.is_visible_to_patient.is_(True),
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Treatment plan not found")

    from datetime import timezone
    plan.patient_acknowledged_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "acknowledged"}
