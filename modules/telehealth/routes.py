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

from modules.telehealth.schemas.session import (
    SessionCreate,
    SessionResponse,
    SymptomCheckRequest,
    SymptomCheckResponse,
)
from healthos_platform.agents.types import AgentInput
from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.security.rbac import Permission
from modules.telehealth.events import TelehealthEventPublisher

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


# In-memory note store (in production, use a database)
_notes_store: dict[str, list[dict[str, Any]]] = {}

# Shared publisher — the producer is injected at app startup; until then
# the publisher gracefully logs events instead of sending them to Kafka.
_event_publisher = TelehealthEventPublisher()


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

    # Store the note for HITL review workflow
    note_id = result.get("note_id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    stored_note = {
        "note_id": note_id,
        "session_id": session_id,
        "status": "draft",
        "sections": result.get("sections", []),
        "generated_at": result.get("generated_at", now),
        "generated_by": result.get("generated_by", "Clinical Note Agent"),
        "overall_confidence": result.get("overall_confidence"),
        "amendments": [],
        **{k: v for k, v in result.items() if k not in (
            "note_id", "session_id", "status", "sections",
            "generated_at", "generated_by", "overall_confidence", "amendments",
        )},
    }
    _notes_store.setdefault(session_id, []).append(stored_note)

    # Emit note.generated event
    await _event_publisher.note_generated(
        session_id=session_id,
        patient_id=str(body.get("patient_id", "")),
        tenant_id=ctx.org_id or "default",
        data={"encounter_type": "telehealth"},
    )

    return result


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
):
    """List all clinical notes for a telehealth session."""
    ctx.require_permission(Permission.ENCOUNTERS_READ)

    notes = _notes_store.get(session_id, [])
    return {"notes": notes}


@router.put("/sessions/{session_id}/note")
async def amend_clinical_note(
    session_id: str,
    body: AmendNoteRequest,
    ctx: TenantContext = Depends(get_current_user),
):
    """Update / amend a clinical note. Applies provider edits to specific sections."""
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)

    notes = _notes_store.get(session_id, [])
    note = next((n for n in notes if n["note_id"] == body.note_id), None)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("status") == "signed":
        raise HTTPException(
            status_code=400,
            detail="Cannot amend a signed note",
        )

    now = datetime.now(timezone.utc).isoformat()

    # Apply each amendment to the matching section
    for amendment in body.amendments:
        for section in note.get("sections", []):
            if section["section"] == amendment.section:
                section["content"] = amendment.content
                break

        # Record the amendment in history
        note.setdefault("amendments", []).append(
            {
                "section": amendment.section,
                "content": amendment.content,
                "amended_at": now,
                "amended_by": ctx.user_id or "unknown",
            }
        )

    note["status"] = "pending_review"
    note["updated_at"] = now

    logger.info(
        "Clinical note %s amended for session %s by %s",
        body.note_id,
        session_id,
        ctx.user_id,
    )

    return note


@router.post("/sessions/{session_id}/note/sign")
async def sign_clinical_note(
    session_id: str,
    body: SignNoteRequest,
    ctx: TenantContext = Depends(get_current_user),
):
    """Sign and finalize a clinical note.

    Sets status to 'signed' and records signed_at / signed_by.
    """
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)

    notes = _notes_store.get(session_id, [])
    note = next((n for n in notes if n["note_id"] == body.note_id), None)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("status") == "signed":
        raise HTTPException(
            status_code=400,
            detail="Note is already signed",
        )

    now = datetime.now(timezone.utc).isoformat()

    note["status"] = "signed"
    note["signed_at"] = now
    note["signed_by"] = ctx.user_id or "unknown"

    if body.amendments:
        note.setdefault("amendments", []).append(
            {
                "section": "_attestation",
                "content": body.amendments,
                "amended_at": now,
                "amended_by": ctx.user_id or "unknown",
            }
        )

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
            "signed_by": ctx.user_id,
            "signed_at": now,
        },
    )

    return note
