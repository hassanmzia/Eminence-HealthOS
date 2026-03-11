"""Telehealth API routes."""

import logging

from fastapi import APIRouter, Depends

from platform.agents.base import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id
from modules.telehealth.schemas.session import (
    SessionCreate,
    SessionResponse,
    SymptomCheckRequest,
    SymptomCheckResponse,
)

logger = logging.getLogger("healthos.routes.telehealth")
router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def create_telehealth_session(
    body: SessionCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a new telehealth session."""
    from modules.telehealth.agents.session_manager import SessionManagerAgent

    agent = SessionManagerAgent()
    agent_input = AgentInput(
        patient_id=str(body.patient_id),
        tenant_id=tenant_id,
        data={
            "action": "create",
            "visit_type": body.visit_type,
            "urgency": body.urgency,
            "chief_complaint": body.chief_complaint,
            "symptoms": body.symptoms,
        },
    )

    output = await agent.execute(agent_input)
    return SessionResponse(**output.data)


@router.post("/symptom-check", response_model=SymptomCheckResponse)
async def check_symptoms(
    body: SymptomCheckRequest,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Pre-visit symptom assessment."""
    from modules.telehealth.agents.symptom_checker import SymptomCheckerAgent

    agent = SymptomCheckerAgent()
    agent_input = AgentInput(
        tenant_id=tenant_id,
        data={
            "symptoms": body.symptoms,
            "duration": body.duration,
            "severity_rating": body.severity_rating,
            "additional_notes": body.additional_notes,
        },
    )

    output = await agent.execute(agent_input)
    return SymptomCheckResponse(**output.data)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: CurrentUser = Depends(require_auth),
):
    """Get session status."""
    from modules.telehealth.services.session_service import TelehealthSessionService
    service = TelehealthSessionService()
    session = await service.get_session(session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    return session
