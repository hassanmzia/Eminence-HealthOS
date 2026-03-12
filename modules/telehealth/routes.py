"""
Eminence HealthOS — Telehealth API Routes
Endpoints for telehealth sessions, symptom checks, visit prep, and scheduling.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from modules.telehealth.schemas.session import (
    SessionCreate,
    SessionResponse,
    SymptomCheckRequest,
    SymptomCheckResponse,
)
from healthos_platform.agents.types import AgentInput

router = APIRouter(prefix="/telehealth", tags=["telehealth"])


@router.post("/sessions", response_model=SessionResponse)
async def create_telehealth_session(body: SessionCreate):
    """Create a new telehealth session."""
    from modules.telehealth.agents.session_manager import SessionManagerAgent

    agent = SessionManagerAgent()
    agent_input = AgentInput(
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
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
    return SessionResponse(**output.result)


@router.post("/symptom-check", response_model=SymptomCheckResponse)
async def check_symptoms(body: SymptomCheckRequest):
    """Pre-visit symptom assessment."""
    from modules.telehealth.agents.symptom_checker import SymptomCheckerAgent

    agent = SymptomCheckerAgent()
    agent_input = AgentInput(
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
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
async def prepare_visit(session_id: str):
    """Generate pre-visit summary for a session."""
    from modules.telehealth.agents.visit_preparation import VisitPreparationAgent

    agent = VisitPreparationAgent()
    agent_input = AgentInput(
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        trigger="telehealth.visit.prepare",
        context={"session_id": session_id},
    )

    output = await agent.run(agent_input)
    return output.result


@router.post("/sessions/{session_id}/note")
async def generate_clinical_note(session_id: str, body: dict[str, Any]):
    """Generate clinical note (SOAP) for a telehealth encounter."""
    from modules.telehealth.agents.clinical_note import ClinicalNoteAgent

    agent = ClinicalNoteAgent()
    agent_input = AgentInput(
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
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
    return output.result


@router.post("/sessions/{session_id}/follow-up")
async def generate_follow_up(session_id: str, body: dict[str, Any]):
    """Generate follow-up care plan after a visit."""
    from modules.telehealth.agents.follow_up_plan import FollowUpPlanAgent

    agent = FollowUpPlanAgent()
    agent_input = AgentInput(
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
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
    return output.result


@router.post("/medication-review")
async def review_medications(body: dict[str, Any]):
    """Review medications for interactions and contraindications."""
    from modules.telehealth.agents.medication_review import MedicationReviewAgent

    agent = MedicationReviewAgent()
    agent_input = AgentInput(
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        trigger="telehealth.medication_review",
        context={
            "medications": body.get("medications", []),
            "conditions": body.get("conditions", []),
        },
    )

    output = await agent.run(agent_input)
    return output.result


@router.post("/schedule")
async def schedule_appointment(body: dict[str, Any]):
    """Schedule a telehealth appointment."""
    from modules.telehealth.agents.scheduling import SchedulingAgent

    agent = SchedulingAgent()
    agent_input = AgentInput(
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
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
async def list_sessions():
    """List recent telehealth sessions (queue view)."""
    from modules.telehealth.services.session_service import TelehealthSessionService

    service = TelehealthSessionService()
    # Return all in-memory sessions; in production this would filter by org/provider
    sessions = list(service._sessions.values())
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session status."""
    from modules.telehealth.services.session_service import TelehealthSessionService

    service = TelehealthSessionService()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
