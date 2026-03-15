"""
Eminence HealthOS — Telehealth API Routes
Endpoints for telehealth sessions, symptom checks, visit prep, and scheduling.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.telehealth.schemas.session import (
    SessionCreate,
    SessionResponse,
    SymptomCheckRequest,
    SymptomCheckResponse,
)
from healthos_platform.agents.types import AgentInput
from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.config.database import get_db as get_shared_db
from healthos_platform.security.rbac import Permission
from modules.telehealth.events import TelehealthEventPublisher
from shared.models.clinical_note import ClinicalNote

logger = logging.getLogger("healthos.telehealth.routes")

router = APIRouter(prefix="/telehealth", tags=["telehealth"])


# ── HITL Clinical Note schemas ────────────────────────────────────────────────

class NoteAmendment(BaseModel):
    section: str
    content: str


class AmendNoteRequest(BaseModel):
    note_id: str
    amendments: list[NoteAmendment]


class SignNoteRequest(BaseModel):
    note_id: str
    amendments: str | None = None


# Shared publisher — the producer is injected at app startup; until then
# the publisher gracefully logs events instead of sending them to Kafka.
_event_publisher = TelehealthEventPublisher()


def _note_to_dict(note: ClinicalNote) -> dict[str, Any]:
    """Convert a ClinicalNote ORM object to the HITL response dict."""
    sections = []
    for section_name in ("subjective", "objective", "assessment", "plan"):
        content = getattr(note, section_name, None)
        if content is not None:
            sections.append({"section": section_name, "content": content})
    return {
        "note_id": str(note.id),
        "session_id": str(note.session_id) if note.session_id else None,
        "status": note.status,
        "sections": sections,
        "generated_at": note.created_at.isoformat() if note.created_at else None,
        "generated_by": "Clinical Note Agent",
        "overall_confidence": note.ai_confidence,
        "amendments": note.amendments or [],
        "note_type": note.note_type,
        "signed_at": note.signed_at.isoformat() if note.signed_at else None,
        "signed_by": str(note.signed_by) if note.signed_by else None,
    }


@router.post("/sessions", response_model=SessionResponse)
async def create_telehealth_session(
    body: SessionCreate,
    ctx: TenantContext = Depends(get_current_user),
):
    """Create a new telehealth session."""
    from modules.telehealth.agents.session_manager import SessionManagerAgent

    ctx.require_permission(Permission.ENCOUNTERS_WRITE)

    agent = SessionManagerAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        patient_id=body.patient_id,
        trigger="telehealth.session.create",
        context={
            "action": "create",
            "visit_type": body.visit_type,
            "urgency": body.urgency,
            "chief_complaint": body.chief_complaint,
            "symptoms": body.symptoms,
        },
    )

    output = await agent.run(agent_input)
    result = output.result

    # Emit session.created event
    await _event_publisher.session_created(
        session_id=result.get("session_id", ""),
        patient_id=str(body.patient_id),
        tenant_id=ctx.org_id or "default",
        data={
            "visit_type": body.visit_type,
            "urgency": body.urgency,
            "chief_complaint": body.chief_complaint,
        },
    )

    return SessionResponse(**result)


@router.post("/symptom-check", response_model=SymptomCheckResponse)
async def check_symptoms(
    body: SymptomCheckRequest,
    ctx: TenantContext = Depends(get_current_user),
):
    """Pre-visit symptom assessment."""
    from modules.telehealth.agents.symptom_checker import SymptomCheckerAgent

    agent = SymptomCheckerAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        trigger="telehealth.symptom_check",
        context={
            "symptoms": body.symptoms,
            "duration": body.duration,
            "severity_rating": body.severity_rating,
            "additional_notes": body.additional_notes,
        },
    )

    output = await agent.run(agent_input)
    return SymptomCheckResponse(**output.result)


@router.post("/sessions/{session_id}/prepare")
async def prepare_visit(
    session_id: str,
    ctx: TenantContext = Depends(get_current_user),
):
    """Generate pre-visit summary for a session."""
    from modules.telehealth.agents.visit_preparation import VisitPreparationAgent

    ctx.require_permission(Permission.ENCOUNTERS_READ)

    agent = VisitPreparationAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        trigger="telehealth.visit.prepare",
        context={"session_id": session_id},
    )

    output = await agent.run(agent_input)
    return output.result


@router.post("/sessions/{session_id}/note")
async def generate_clinical_note(
    session_id: str,
    body: dict[str, Any],
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_shared_db),
):
    """Generate clinical note (SOAP) for a telehealth encounter."""
    from modules.telehealth.agents.clinical_note import ClinicalNoteAgent

    ctx.require_permission(Permission.ENCOUNTERS_WRITE)

    agent = ClinicalNoteAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        trigger="telehealth.note.generate",
        context={
            "session_id": session_id,
            "symptoms": body.get("symptoms", []),
            "vitals": body.get("vitals", {}),
            "assessment": body.get("assessment", ""),
            "plan": body.get("plan", []),
            "medications": body.get("medications", []),
            "prior_outputs": body.get("prior_outputs", []),
            "encounter_type": "telehealth",
        },
    )

    output = await agent.run(agent_input)
    result = output.result

    # Map sections from the agent result to SOAP fields
    sections = result.get("sections", [])
    soap_fields: dict[str, str | None] = {
        "subjective": None, "objective": None, "assessment": None, "plan": None,
    }
    for section in sections:
        name = section.get("section", "").lower()
        if name in soap_fields:
            soap_fields[name] = section.get("content")

    # Persist to DB via ClinicalNote model
    note = ClinicalNote(
        session_id=uuid.UUID(session_id) if session_id else None,
        encounter_id=None,
        tenant_id=str(ctx.org_id) if ctx.org_id else "default",
        note_type="soap",
        status="draft",
        subjective=soap_fields["subjective"],
        objective=soap_fields["objective"],
        assessment=soap_fields["assessment"],
        plan=soap_fields["plan"],
        ai_generated=True,
        ai_confidence=result.get("overall_confidence"),
        amendments=[],
    )
    db.add(note)
    await db.flush()

    response = _note_to_dict(note)

    # Emit note.generated event
    await _event_publisher.note_generated(
        session_id=session_id,
        patient_id=str(body.get("patient_id", "")),
        tenant_id=ctx.org_id or "default",
        data={"encounter_type": "telehealth"},
    )

    return response


@router.post("/sessions/{session_id}/follow-up")
async def generate_follow_up(
    session_id: str,
    body: dict[str, Any],
    ctx: TenantContext = Depends(get_current_user),
):
    """Generate follow-up care plan after a visit."""
    from modules.telehealth.agents.follow_up_plan import FollowUpPlanAgent

    ctx.require_permission(Permission.CARE_PLANS_WRITE)

    agent = FollowUpPlanAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        trigger="telehealth.follow_up.generate",
        context={
            "session_id": session_id,
            "conditions": body.get("conditions", []),
            "risk_assessments": body.get("risk_assessments", []),
            "symptoms": body.get("symptoms", []),
            "plan": body.get("plan", []),
            "medications": body.get("medications", []),
        },
    )

    output = await agent.run(agent_input)

    # Emit follow_up.created event
    await _event_publisher.follow_up_created(
        session_id=session_id,
        patient_id=str(body.get("patient_id", "")),
        tenant_id=ctx.org_id or "default",
        data={
            "conditions": body.get("conditions", []),
        },
    )

    return output.result


@router.post("/medication-review")
async def review_medications(
    body: dict[str, Any],
    ctx: TenantContext = Depends(get_current_user),
):
    """Review medications for interactions and contraindications."""
    from modules.telehealth.agents.medication_review import MedicationReviewAgent

    ctx.require_permission(Permission.ENCOUNTERS_READ)

    agent = MedicationReviewAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        trigger="telehealth.medication_review",
        context={
            "medications": body.get("medications", []),
            "conditions": body.get("conditions", []),
        },
    )

    output = await agent.run(agent_input)
    return output.result


@router.post("/schedule")
async def schedule_appointment(
    body: dict[str, Any],
    ctx: TenantContext = Depends(get_current_user),
):
    """Schedule a telehealth appointment."""
    from modules.telehealth.agents.scheduling import SchedulingAgent

    ctx.require_permission(Permission.ENCOUNTERS_WRITE)

    agent = SchedulingAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="telehealth.schedule",
        context={
            "action": body.get("action", "schedule"),
            "visit_type": body.get("visit_type", "follow_up"),
            "urgency": body.get("urgency", "routine"),
            "preferred_provider": body.get("preferred_provider"),
            "preferred_times": body.get("preferred_times", []),
            "follow_up_days": body.get("follow_up_days", 14),
        },
    )

    output = await agent.run(agent_input)
    return output.result


@router.get("/sessions")
async def list_sessions(ctx: TenantContext = Depends(get_current_user)):
    """List recent telehealth sessions (queue view)."""
    from modules.telehealth.services.session_service import TelehealthSessionService

    ctx.require_permission(Permission.ENCOUNTERS_READ)

    service = TelehealthSessionService()
    sessions = list(service._sessions.values())
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    ctx: TenantContext = Depends(get_current_user),
):
    """Get session status."""
    from modules.telehealth.services.session_service import TelehealthSessionService

    ctx.require_permission(Permission.ENCOUNTERS_READ)

    service = TelehealthSessionService()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── HITL Clinical Note Endpoints ──────────────────────────────────────────────


@router.get("/sessions/{session_id}/notes")
async def list_clinical_notes(
    session_id: str,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_shared_db),
):
    """List all clinical notes for a telehealth session."""
    ctx.require_permission(Permission.ENCOUNTERS_READ)

    result = await db.execute(
        select(ClinicalNote)
        .where(ClinicalNote.session_id == uuid.UUID(session_id))
        .order_by(ClinicalNote.created_at.desc())
    )
    notes = result.scalars().all()

    return {"notes": [_note_to_dict(n) for n in notes]}


@router.put("/sessions/{session_id}/note")
async def amend_clinical_note(
    session_id: str,
    body: AmendNoteRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_shared_db),
):
    """Update / amend a clinical note. Applies provider edits to specific sections."""
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)

    result = await db.execute(
        select(ClinicalNote).where(ClinicalNote.id == uuid.UUID(body.note_id))
    )
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.status == "signed":
        raise HTTPException(status_code=400, detail="Cannot amend a signed note")

    now = datetime.now(timezone.utc).isoformat()
    amendment_history = list(note.amendments or [])

    # Apply each amendment to the matching SOAP section
    for amendment in body.amendments:
        section_name = amendment.section.lower()
        if section_name in ("subjective", "objective", "assessment", "plan"):
            setattr(note, section_name, amendment.content)

        amendment_history.append({
            "section": amendment.section,
            "content": amendment.content,
            "amended_at": now,
            "amended_by": str(ctx.user_id) if ctx.user_id else "unknown",
        })

    note.amendments = amendment_history
    note.status = "pending_review"
    await db.flush()

    logger.info(
        "Clinical note %s amended for session %s by %s",
        body.note_id,
        session_id,
        ctx.user_id,
    )

    return _note_to_dict(note)


@router.post("/sessions/{session_id}/note/sign")
async def sign_clinical_note(
    session_id: str,
    body: SignNoteRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_shared_db),
):
    """Sign and finalize a clinical note."""
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)

    result = await db.execute(
        select(ClinicalNote).where(ClinicalNote.id == uuid.UUID(body.note_id))
    )
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.status == "signed":
        raise HTTPException(status_code=400, detail="Note is already signed")

    now = datetime.now(timezone.utc)

    note.status = "signed"
    note.signed_at = now
    note.signed_by = ctx.user_id

    if body.amendments:
        amendment_history = list(note.amendments or [])
        amendment_history.append({
            "section": "_attestation",
            "content": body.amendments,
            "amended_at": now.isoformat(),
            "amended_by": str(ctx.user_id) if ctx.user_id else "unknown",
        })
        note.amendments = amendment_history

    await db.flush()

    logger.info(
        "Clinical note %s signed for session %s by %s",
        body.note_id,
        session_id,
        ctx.user_id,
    )

    # Emit note.signed event
    await _event_publisher.note_signed(
        session_id=session_id,
        patient_id="",
        tenant_id=ctx.org_id or "default",
        data={
            "note_id": body.note_id,
            "signed_by": str(ctx.user_id),
            "signed_at": now.isoformat(),
        },
    )

    return _note_to_dict(note)
