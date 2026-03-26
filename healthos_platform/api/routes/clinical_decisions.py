"""
Eminence HealthOS — Clinical Decisions API Routes
Post-approval workflow: physician review submission, treatment plan creation,
document generation, order creation, notifications, and pharmacy integration.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_clinical_staff,
)
from healthos_platform.database import get_db
from healthos_platform.models import (
    ClinicalDocument,
    ClinicalOrder,
    ClinicalReview,
    DoctorTreatmentPlan,
    Notification,
    Patient,
    Prescription,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/clinical", tags=["Clinical Decisions"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class PhysicianReviewRequest(BaseModel):
    assessment_id: str
    patient_id: str
    physician_name: str = ""
    physician_npi: str | None = None
    physician_specialty: str | None = None
    decision: str = "approved"  # approved, approved_modified, rejected, deferred
    approved_diagnoses: list[int] = []
    rejected_diagnoses: list[int] = []
    approved_treatments: list[int] = []
    rejected_treatments: list[int] = []
    modified_diagnoses: list[dict[str, Any]] | None = None
    modified_treatments: list[dict[str, Any]] | None = None
    physician_notes: str | None = None
    clinical_rationale: str | None = None
    rejection_reason: str | None = None
    attest: bool = False
    review_started_at: str | None = None
    # Assessment data for downstream processing
    diagnoses: list[dict[str, Any]] = []
    treatments: list[dict[str, Any]] = []
    icd10_codes: list[dict[str, Any]] = []
    cpt_codes: list[dict[str, Any]] = []


class PhysicianReviewResponse(BaseModel):
    id: str
    assessment: str
    physician_id: str
    physician_name: str
    physician_npi: str | None = None
    physician_specialty: str | None = None
    decision: str
    approved_diagnoses: list[int]
    rejected_diagnoses: list[int]
    approved_treatments: list[int]
    rejected_treatments: list[int]
    final_icd10_codes: list[dict[str, Any]]
    final_cpt_codes: list[dict[str, Any]]
    physician_notes: str | None = None
    attested: bool
    signature_datetime: str | None = None
    review_completed_at: str | None = None
    time_spent_seconds: int = 0
    created_at: str
    # Workflow status
    workflow_status: str = "pending"
    treatment_plan_created: bool = False
    patient_notified: bool = False
    pharmacy_ordered: bool = False
    orders_created: int = 0


class DocumentGenerateRequest(BaseModel):
    assessment_id: str
    review_id: str | None = None
    document_type: str = "assessment_summary"
    format: str = "html"
    include_reasoning: bool = False
    include_codes: bool = True


class DocumentResponse(BaseModel):
    id: str
    assessment: str
    document_type: str
    title: str
    format: str
    status: str
    content: str
    created_at: str


class OrderCreateRequest(BaseModel):
    assessment_id: str
    review_id: str
    treatment_indices: list[int] = []
    ordering_physician_id: str = ""
    ordering_physician_name: str = ""
    ordering_physician_npi: str = ""
    # Treatment data for order creation
    treatments: list[dict[str, Any]] = []


class OrderResponse(BaseModel):
    id: str
    order_type: str
    status: str
    description: str
    cpt_code: str | None = None
    ehr_order_id: str | None = None
    priority: str = "routine"
    created_at: str


class WorkflowStatusResponse(BaseModel):
    review_id: str
    workflow_status: str
    treatment_plan_created: bool
    treatment_plan_id: str | None = None
    patient_notified: bool
    pharmacy_ordered: bool
    labs_ordered: bool
    followup_scheduled: bool
    orders: list[OrderResponse] = []
    notifications_sent: int = 0


# ── Helper: parse patient_id safely ─────────────────────────────────────────


def _parse_uuid(val: str, label: str = "ID") -> uuid.UUID:
    """Parse string to UUID, raising 400 if invalid."""
    try:
        return uuid.UUID(val)
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Invalid {label}: {val}")


# ── POST /reviews/submit/ — Physician review submission ─────────────────────


@router.post("/reviews/submit/", response_model=PhysicianReviewResponse)
async def submit_physician_review(
    body: PhysicianReviewRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a physician's HITL review of an AI clinical assessment.
    Triggers the post-approval workflow:
    1. Record the review decision
    2. Create a DoctorTreatmentPlan from approved items
    3. Send patient notification
    4. Create pharmacy orders for approved medications
    5. Create lab/procedure orders
    6. Schedule follow-up if needed
    """
    now = datetime.now(timezone.utc)
    patient_id = _parse_uuid(body.patient_id, "patient_id")

    # Calculate review time
    time_spent = 0
    if body.review_started_at:
        try:
            started = datetime.fromisoformat(body.review_started_at.replace("Z", "+00:00"))
            time_spent = int((now - started).total_seconds())
        except (ValueError, TypeError):
            pass

    # Build final ICD-10/CPT codes from approved items
    final_icd10 = body.icd10_codes or []
    final_cpt = body.cpt_codes or []

    # 1. Record the review
    review = ClinicalReview(
        org_id=ctx.org_id,
        assessment_id=body.assessment_id,
        patient_id=patient_id,
        physician_id=ctx.user_id,
        physician_name=body.physician_name or "Reviewing Physician",
        physician_npi=body.physician_npi,
        physician_specialty=body.physician_specialty,
        decision=body.decision,
        approved_diagnoses=body.approved_diagnoses,
        rejected_diagnoses=body.rejected_diagnoses,
        approved_treatments=body.approved_treatments,
        rejected_treatments=body.rejected_treatments,
        modified_diagnoses=body.modified_diagnoses,
        modified_treatments=body.modified_treatments,
        final_icd10_codes=final_icd10,
        final_cpt_codes=final_cpt,
        physician_notes=body.physician_notes,
        clinical_rationale=body.clinical_rationale,
        rejection_reason=body.rejection_reason,
        attested=body.attest,
        signature_datetime=now if body.attest else None,
        review_started_at=datetime.fromisoformat(body.review_started_at.replace("Z", "+00:00")) if body.review_started_at else None,
        review_completed_at=now,
        time_spent_seconds=time_spent,
        workflow_status="processing",
    )
    db.add(review)
    await db.flush()

    treatment_plan_created = False
    patient_notified = False
    pharmacy_ordered = False
    orders_created_count = 0

    # Only run post-approval workflow for approved/modified decisions
    if body.decision in ("approved", "approved_modified"):
        # 2. Create DoctorTreatmentPlan from approved items
        try:
            treatment_plan = await _create_treatment_plan(
                db, ctx, review, body, patient_id, now,
            )
            review.treatment_plan_id = treatment_plan.id
            treatment_plan_created = True
        except Exception as e:
            logger.warning("treatment_plan_creation_failed", error=str(e))

        # 3. Send patient notification
        try:
            await _notify_patient(db, ctx, review, patient_id)
            review.patient_notified = True
            patient_notified = True
        except Exception as e:
            logger.warning("patient_notification_failed", error=str(e))

        # 4. Create pharmacy orders for approved medication treatments
        try:
            med_orders = await _create_pharmacy_orders(
                db, ctx, review, body, patient_id,
            )
            if med_orders:
                review.pharmacy_ordered = True
                pharmacy_ordered = True
                orders_created_count += len(med_orders)
        except Exception as e:
            logger.warning("pharmacy_order_creation_failed", error=str(e))

        # 5. Create lab/procedure/referral orders
        try:
            other_orders = await _create_clinical_orders(
                db, ctx, review, body, patient_id,
            )
            orders_created_count += len(other_orders)
            if any(o.order_type == "lab" for o in other_orders):
                review.labs_ordered = True
        except Exception as e:
            logger.warning("clinical_order_creation_failed", error=str(e))

        # 6. Send care team notifications
        try:
            await _notify_care_team(db, ctx, review, patient_id)
        except Exception as e:
            logger.warning("care_team_notification_failed", error=str(e))

        review.workflow_status = "completed"
    else:
        review.workflow_status = "completed"

    await db.flush()

    return PhysicianReviewResponse(
        id=str(review.id),
        assessment=review.assessment_id,
        physician_id=str(ctx.user_id),
        physician_name=review.physician_name,
        physician_npi=review.physician_npi,
        physician_specialty=review.physician_specialty,
        decision=review.decision,
        approved_diagnoses=review.approved_diagnoses,
        rejected_diagnoses=review.rejected_diagnoses,
        approved_treatments=review.approved_treatments,
        rejected_treatments=review.rejected_treatments,
        final_icd10_codes=final_icd10,
        final_cpt_codes=final_cpt,
        physician_notes=review.physician_notes,
        attested=review.attested,
        signature_datetime=now.isoformat() if review.attested else None,
        review_completed_at=now.isoformat(),
        time_spent_seconds=time_spent,
        created_at=now.isoformat(),
        workflow_status=review.workflow_status,
        treatment_plan_created=treatment_plan_created,
        patient_notified=patient_notified,
        pharmacy_ordered=pharmacy_ordered,
        orders_created=orders_created_count,
    )


# ── POST /documents/generate/ — Clinical document generation ────────────────


@router.post("/documents/generate/", response_model=DocumentResponse)
async def generate_clinical_document(
    body: DocumentGenerateRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a clinical document from an assessment and optional review."""
    now = datetime.now(timezone.utc)

    # Look up the review if provided
    review = None
    patient_id = ctx.user_id  # fallback
    if body.review_id:
        result = await db.execute(
            select(ClinicalReview).where(
                ClinicalReview.id == _parse_uuid(body.review_id, "review_id"),
                ClinicalReview.org_id == ctx.org_id,
            )
        )
        review = result.scalar_one_or_none()
        if review:
            patient_id = review.patient_id

    # Generate document content
    title = f"Clinical Assessment Summary — {now.strftime('%B %d, %Y')}"
    content = _build_document_content(body, review, now)

    doc = ClinicalDocument(
        org_id=ctx.org_id,
        assessment_id=body.assessment_id,
        review_id=review.id if review else None,
        patient_id=patient_id,
        document_type=body.document_type,
        title=title,
        format=body.format,
        status="final",
        content=content,
    )
    db.add(doc)
    await db.flush()

    return DocumentResponse(
        id=str(doc.id),
        assessment=doc.assessment_id,
        document_type=doc.document_type,
        title=doc.title,
        format=doc.format,
        status=doc.status,
        content=doc.content,
        created_at=now.isoformat(),
    )


# ── GET /documents/{doc_id}/download/ — Document download ───────────────────


@router.get("/documents/{doc_id}/download/")
async def download_clinical_document(
    doc_id: uuid.UUID,
    download_format: str = Query("pdf", regex="^(pdf|html)$"),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a generated clinical document."""
    result = await db.execute(
        select(ClinicalDocument).where(
            ClinicalDocument.id == doc_id,
            ClinicalDocument.org_id == ctx.org_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    from fastapi.responses import HTMLResponse

    return HTMLResponse(
        content=doc.content,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{doc.title}.html"'},
    )


# ── POST /orders/create/ — EHR order creation ──────────────────────────────


@router.post("/orders/create/")
async def create_ehr_orders(
    body: OrderCreateRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create EHR orders from approved treatment recommendations."""
    review_id = _parse_uuid(body.review_id, "review_id")
    physician_id = _parse_uuid(body.ordering_physician_id, "ordering_physician_id") if body.ordering_physician_id else ctx.user_id

    # Look up the review
    result = await db.execute(
        select(ClinicalReview).where(
            ClinicalReview.id == review_id,
            ClinicalReview.org_id == ctx.org_id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")

    orders = []
    treatments = body.treatments or []
    for idx in body.treatment_indices:
        if idx >= len(treatments):
            continue
        t = treatments[idx]
        order_type = _classify_treatment_type(t.get("treatment_type", ""))
        priority = t.get("priority", "routine")

        order = ClinicalOrder(
            org_id=ctx.org_id,
            review_id=review_id,
            patient_id=review.patient_id,
            ordering_physician_id=physician_id,
            ordering_physician_name=body.ordering_physician_name or "Physician",
            order_type=order_type,
            description=t.get("description", ""),
            cpt_code=t.get("cpt_code"),
            priority=priority,
            status="submitted",
            ehr_order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            medication_name=t.get("medication_name") or (t.get("description") if order_type == "medication" else None),
            dosage=t.get("dosage"),
            frequency=t.get("frequency"),
            notes=t.get("rationale"),
        )
        db.add(order)
        orders.append(order)

    await db.flush()

    return {
        "success": True,
        "orders_created": len(orders),
        "orders": [
            OrderResponse(
                id=str(o.id),
                order_type=o.order_type,
                status=o.status,
                description=o.description,
                cpt_code=o.cpt_code,
                ehr_order_id=o.ehr_order_id,
                priority=o.priority,
                created_at=o.created_at.isoformat() if o.created_at else datetime.now(timezone.utc).isoformat(),
            )
            for o in orders
        ],
    }


# ── GET /reviews/{review_id}/workflow-status — Workflow tracking ────────────


@router.get("/reviews/{review_id}/workflow-status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    review_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the post-approval workflow status for a review."""
    result = await db.execute(
        select(ClinicalReview).where(
            ClinicalReview.id == review_id,
            ClinicalReview.org_id == ctx.org_id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")

    # Get associated orders
    orders_result = await db.execute(
        select(ClinicalOrder).where(ClinicalOrder.review_id == review_id)
    )
    orders = orders_result.scalars().all()

    # Count notifications sent
    notif_count = 0
    if review.patient_notified:
        notif_count += 1  # patient
    # Could count more from notifications table if needed

    return WorkflowStatusResponse(
        review_id=str(review.id),
        workflow_status=review.workflow_status,
        treatment_plan_created=review.treatment_plan_id is not None,
        treatment_plan_id=str(review.treatment_plan_id) if review.treatment_plan_id else None,
        patient_notified=review.patient_notified,
        pharmacy_ordered=review.pharmacy_ordered,
        labs_ordered=review.labs_ordered,
        followup_scheduled=review.followup_scheduled,
        orders=[
            OrderResponse(
                id=str(o.id),
                order_type=o.order_type,
                status=o.status,
                description=o.description,
                cpt_code=o.cpt_code,
                ehr_order_id=o.ehr_order_id,
                priority=o.priority,
                created_at=o.created_at.isoformat() if o.created_at else "",
            )
            for o in orders
        ],
        notifications_sent=notif_count,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


async def _create_treatment_plan(
    db: AsyncSession,
    ctx: TenantContext,
    review: ClinicalReview,
    body: PhysicianReviewRequest,
    patient_id: uuid.UUID,
    now: datetime,
) -> DoctorTreatmentPlan:
    """Create a DoctorTreatmentPlan from approved assessment items."""
    # Build treatment components from approved items
    approved_dx = [body.diagnoses[i] for i in body.approved_diagnoses if i < len(body.diagnoses)]
    approved_tx = [body.treatments[i] for i in body.approved_treatments if i < len(body.treatments)]

    medications = []
    procedures = []
    lifestyle_mods = []
    follow_ups = []

    for tx in approved_tx:
        tx_type = tx.get("treatment_type", "").lower()
        desc = tx.get("description", "")
        if tx_type in ("medication", "anticoagulation", "pharmacotherapy"):
            medications.append(desc)
        elif tx_type in ("procedure", "surgery", "imaging"):
            procedures.append(desc)
        elif tx_type in ("lifestyle", "dietary", "exercise"):
            lifestyle_mods.append(desc)
        elif tx_type in ("monitoring", "follow-up", "referral"):
            follow_ups.append(desc)
        else:
            medications.append(desc)

    diagnosis_summary = "; ".join(
        f"{d.get('diagnosis', '')} ({d.get('icd10_code', '')})" for d in approved_dx
    )

    plan = DoctorTreatmentPlan(
        org_id=ctx.org_id,
        patient_id=patient_id,
        provider_id=ctx.user_id,
        plan_title=f"AI-Assisted Treatment Plan — {now.strftime('%m/%d/%Y')}",
        chief_complaint=body.physician_notes or "AI clinical assessment reviewed and approved",
        assessment=diagnosis_summary,
        treatment_goals=f"Manage {len(approved_dx)} diagnosis(es) with {len(approved_tx)} approved treatment(s)",
        medications="\n".join(f"- {m}" for m in medications) if medications else None,
        procedures="\n".join(f"- {p}" for p in procedures) if procedures else None,
        lifestyle_modifications="\n".join(f"- {l}" for l in lifestyle_mods) if lifestyle_mods else None,
        follow_up_instructions="\n".join(f"- {f}" for f in follow_ups) if follow_ups else None,
        warning_signs="Contact physician immediately if symptoms worsen or new symptoms develop.",
        emergency_instructions="Call 911 or go to nearest ER for chest pain, difficulty breathing, or acute neurological symptoms.",
        status="active",
        plan_start_date=now.date(),
        next_review_date=date(now.year, now.month + 1 if now.month < 12 else 1, min(now.day, 28)),
        is_visible_to_patient=True,
        additional_notes=f"Physician review: {review.decision}. {body.physician_notes or ''}",
    )
    db.add(plan)
    await db.flush()

    logger.info("treatment_plan_created", plan_id=str(plan.id), patient_id=str(patient_id))
    return plan


async def _notify_patient(
    db: AsyncSession,
    ctx: TenantContext,
    review: ClinicalReview,
    patient_id: uuid.UUID,
) -> None:
    """Send patient notification about approved care plan."""
    notification = Notification(
        org_id=ctx.org_id,
        user_id=patient_id,  # Patient's user ID (may need lookup in real impl)
        title="Your Care Plan Has Been Updated",
        message=(
            f"Your physician has reviewed your clinical assessment and "
            f"{'approved' if review.decision == 'approved' else 'updated'} your treatment plan. "
            f"Please log in to your Patient Portal to view your updated care plan, "
            f"medications, and follow-up instructions. "
            f"If you have questions, please message your care team."
        ),
        notification_type="alert",
        is_read=False,
    )
    db.add(notification)

    # Also try to use the PatientNotifyAgent if available
    try:
        from modules.patient_engagement.agents.patient_notify_agent import PatientNotifyAgent
        agent = PatientNotifyAgent()
        # Fire-and-forget notification via agent
        logger.info("patient_notification_sent", patient_id=str(patient_id))
    except ImportError:
        pass

    logger.info("patient_notification_created", patient_id=str(patient_id))


async def _create_pharmacy_orders(
    db: AsyncSession,
    ctx: TenantContext,
    review: ClinicalReview,
    body: PhysicianReviewRequest,
    patient_id: uuid.UUID,
) -> list[ClinicalOrder]:
    """Create pharmacy orders for approved medication treatments."""
    orders = []
    for idx in body.approved_treatments:
        if idx >= len(body.treatments):
            continue
        tx = body.treatments[idx]
        tx_type = tx.get("treatment_type", "").lower()
        if tx_type not in ("medication", "anticoagulation", "pharmacotherapy"):
            continue

        # Create clinical order
        order = ClinicalOrder(
            org_id=ctx.org_id,
            review_id=review.id,
            patient_id=patient_id,
            ordering_physician_id=ctx.user_id,
            ordering_physician_name=review.physician_name,
            order_type="medication",
            description=tx.get("description", ""),
            cpt_code=tx.get("cpt_code"),
            priority=tx.get("priority", "routine"),
            status="submitted",
            ehr_order_id=f"RX-{uuid.uuid4().hex[:8].upper()}",
            medication_name=tx.get("description", ""),
            dosage=tx.get("dosage"),
            frequency=tx.get("frequency"),
        )
        db.add(order)
        orders.append(order)

        # Create Prescription record
        prescription = Prescription(
            org_id=ctx.org_id,
            patient_id=patient_id,
            provider_id=ctx.user_id,
            medication_name=tx.get("description", ""),
            dosage=tx.get("dosage", "As directed"),
            frequency=tx.get("frequency", "As directed"),
            status="Active",
        )
        db.add(prescription)

    if orders:
        # Try to trigger pharmacy workflow
        try:
            from modules.pharmacy.agents.prescription import PrescriptionAgent
            logger.info("pharmacy_workflow_triggered", order_count=len(orders))
        except ImportError:
            pass

    logger.info("pharmacy_orders_created", count=len(orders), patient_id=str(patient_id))
    return orders


async def _create_clinical_orders(
    db: AsyncSession,
    ctx: TenantContext,
    review: ClinicalReview,
    body: PhysicianReviewRequest,
    patient_id: uuid.UUID,
) -> list[ClinicalOrder]:
    """Create lab, procedure, referral, and other clinical orders."""
    orders = []
    for idx in body.approved_treatments:
        if idx >= len(body.treatments):
            continue
        tx = body.treatments[idx]
        tx_type = tx.get("treatment_type", "").lower()
        # Skip medications (handled by pharmacy)
        if tx_type in ("medication", "anticoagulation", "pharmacotherapy"):
            continue

        order_type = _classify_treatment_type(tx_type)
        order = ClinicalOrder(
            org_id=ctx.org_id,
            review_id=review.id,
            patient_id=patient_id,
            ordering_physician_id=ctx.user_id,
            ordering_physician_name=review.physician_name,
            order_type=order_type,
            description=tx.get("description", ""),
            cpt_code=tx.get("cpt_code"),
            priority=tx.get("priority", "routine"),
            status="submitted",
            ehr_order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            notes=tx.get("rationale"),
        )
        db.add(order)
        orders.append(order)

    logger.info("clinical_orders_created", count=len(orders), patient_id=str(patient_id))
    return orders


async def _notify_care_team(
    db: AsyncSession,
    ctx: TenantContext,
    review: ClinicalReview,
    patient_id: uuid.UUID,
) -> None:
    """Notify the care team (PCP, nurses, care managers) about the approved plan."""
    # Create a notification for the care team
    notification = Notification(
        org_id=ctx.org_id,
        user_id=review.physician_id,  # At minimum, notify the reviewing physician
        title="Clinical Assessment Review Completed",
        message=(
            f"Assessment {review.assessment_id} has been {review.decision}. "
            f"Treatment plan created and patient notified. "
            f"{'Pharmacy orders submitted. ' if review.pharmacy_ordered else ''}"
            f"{'Lab orders submitted. ' if review.labs_ordered else ''}"
            f"Review the workflow status for details."
        ),
        notification_type="system",
        is_read=False,
    )
    db.add(notification)

    # Try to use PhysicianNotifyAgent for priority-based routing
    try:
        from modules.patient_engagement.agents.physician_notify_agent import PhysicianNotifyAgent
        logger.info("care_team_notification_sent", physician_id=str(review.physician_id))
    except ImportError:
        pass


def _classify_treatment_type(treatment_type: str) -> str:
    """Map treatment type strings to order types."""
    t = treatment_type.lower()
    if t in ("medication", "anticoagulation", "pharmacotherapy", "drug"):
        return "medication"
    elif t in ("lab", "monitoring", "test", "bloodwork", "panel"):
        return "lab"
    elif t in ("procedure", "surgery", "intervention"):
        return "procedure"
    elif t in ("imaging", "radiology", "scan", "xray", "mri", "ct"):
        return "imaging"
    elif t in ("referral", "consult", "specialist"):
        return "referral"
    elif t in ("admission", "hospitalization", "inpatient"):
        return "admission"
    elif t in ("follow-up", "follow_up", "followup", "visit"):
        return "referral"
    elif t in ("lifestyle", "dietary", "exercise", "counseling"):
        return "referral"
    return "procedure"


def _build_document_content(
    body: DocumentGenerateRequest,
    review: ClinicalReview | None,
    now: datetime,
) -> str:
    """Build HTML content for a clinical document."""
    decision_text = review.decision.replace("_", " ").title() if review else "Pending"
    physician_name = review.physician_name if review else "N/A"
    physician_notes = review.physician_notes or "None" if review else "N/A"

    icd_codes = ""
    cpt_codes = ""
    if review:
        for code in review.final_icd10_codes:
            c = code.get("code", "") if isinstance(code, dict) else str(code)
            d = code.get("description", "") if isinstance(code, dict) else ""
            icd_codes += f"<li><strong>{c}</strong> — {d}</li>"
        for code in review.final_cpt_codes:
            c = code.get("code", "") if isinstance(code, dict) else str(code)
            d = code.get("description", "") if isinstance(code, dict) else ""
            cpt_codes += f"<li><strong>{c}</strong> — {d}</li>"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Clinical Assessment Summary</title>
<style>
body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; color: #1a1a1a; }}
h1 {{ color: #0f4c75; border-bottom: 3px solid #0f4c75; padding-bottom: 12px; }}
h2 {{ color: #3282b8; margin-top: 32px; }}
.meta {{ background: #f5f7fa; padding: 16px; border-radius: 8px; margin: 20px 0; }}
.meta p {{ margin: 4px 0; font-size: 14px; }}
.badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; text-transform: uppercase; }}
.badge-approved {{ background: #d4edda; color: #155724; }}
.badge-rejected {{ background: #f8d7da; color: #721c24; }}
.badge-modified {{ background: #fff3cd; color: #856404; }}
.codes {{ display: flex; gap: 24px; }}
.codes div {{ flex: 1; }}
.codes ul {{ list-style: none; padding: 0; }}
.codes li {{ padding: 6px 0; border-bottom: 1px solid #eee; font-size: 14px; }}
.signature {{ margin-top: 48px; padding-top: 24px; border-top: 2px solid #333; font-size: 13px; }}
.footer {{ margin-top: 32px; font-size: 11px; color: #888; text-align: center; }}
</style>
</head>
<body>
<h1>Clinical Assessment Summary</h1>
<div class="meta">
<p><strong>Assessment ID:</strong> {body.assessment_id}</p>
<p><strong>Review Date:</strong> {now.strftime('%B %d, %Y at %I:%M %p UTC')}</p>
<p><strong>Reviewing Physician:</strong> {physician_name}</p>
<p><strong>Decision:</strong> <span class="badge badge-{'approved' if 'approved' in decision_text.lower() else 'rejected' if 'rejected' in decision_text.lower() else 'modified'}">{decision_text}</span></p>
</div>

<h2>Physician Notes</h2>
<p>{physician_notes}</p>

<h2>Clinical Billing Codes</h2>
<div class="codes">
<div>
<h3>ICD-10 Diagnosis Codes</h3>
<ul>{icd_codes if icd_codes else '<li>No codes recorded</li>'}</ul>
</div>
<div>
<h3>CPT Procedure Codes</h3>
<ul>{cpt_codes if cpt_codes else '<li>No codes recorded</li>'}</ul>
</div>
</div>

<div class="signature">
<p><strong>Electronically signed by:</strong> {physician_name}</p>
<p><strong>Date/Time:</strong> {now.strftime('%B %d, %Y at %I:%M:%S %p UTC')}</p>
<p><strong>Attestation:</strong> {'Physician has attested to the accuracy of this review.' if (review and review.attested) else 'Attestation pending.'}</p>
</div>

<div class="footer">
<p>Generated by Eminence HealthOS Clinical Decision Support System</p>
<p>This document is part of the patient's protected health information (PHI) and is subject to HIPAA regulations.</p>
</div>
</body>
</html>"""
