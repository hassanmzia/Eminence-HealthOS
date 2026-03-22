"""Ambient AI Documentation module API routes — transcription, diarization, SOAP notes, coding, attestation."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput, parse_patient_id
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/ambient-ai", tags=["ambient-ai"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Ambient Listening ──────────────────────────────────────────────────────


@router.post("/session/start")
async def start_session(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Start an ambient recording session for an encounter."""
    from modules.ambient_ai.agents.ambient_listening import AmbientListeningAgent

    agent = AmbientListeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="ambient.session.start",
        context={"action": "start_session", **body},
    ))
    return output.result


@router.post("/transcribe")
async def transcribe(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Transcribe audio data from an encounter."""
    from modules.ambient_ai.agents.ambient_listening import AmbientListeningAgent

    agent = AmbientListeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="ambient.transcribe",
        context={"action": "transcribe", **body},
    ))
    return output.result


@router.post("/session/end")
async def end_session(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """End a recording session."""
    from modules.ambient_ai.agents.ambient_listening import AmbientListeningAgent

    agent = AmbientListeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="ambient.session.end",
        context={"action": "end_session", **body},
    ))
    return output.result


# ── Speaker Diarization ────────────────────────────────────────────────────


@router.post("/diarize")
async def diarize(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Diarize transcript segments — identify and label speakers."""
    from modules.ambient_ai.agents.speaker_diarization import SpeakerDiarizationAgent

    agent = SpeakerDiarizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="ambient.diarize",
        context={"action": "diarize", **body},
    ))
    return output.result


# ── SOAP Note Generation ──────────────────────────────────────────────────


@router.post("/soap/generate")
async def generate_soap(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate a complete SOAP note from diarized transcript."""
    from modules.ambient_ai.agents.soap_note_generator import SOAPNoteGeneratorAgent

    agent = SOAPNoteGeneratorAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="ambient.soap.generate",
        context={"action": "generate_soap", **body},
    ))
    return output.result


@router.post("/soap/validate")
async def validate_soap(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Validate a SOAP note for completeness."""
    from modules.ambient_ai.agents.soap_note_generator import SOAPNoteGeneratorAgent

    agent = SOAPNoteGeneratorAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="ambient.soap.validate",
        context={"action": "validate_note", **body},
    ))
    return output.result


# ── Auto-Coding ───────────────────────────────────────────────────────────


@router.post("/coding/encounter")
async def code_encounter(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate ICD-10, CPT, and E&M codes for an encounter."""
    from modules.ambient_ai.agents.auto_coding import AutoCodingAgent

    agent = AutoCodingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="ambient.coding.encounter",
        context={"action": "code_encounter", **body},
    ))
    return output.result


@router.post("/coding/validate")
async def validate_codes(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Validate proposed billing codes."""
    from modules.ambient_ai.agents.auto_coding import AutoCodingAgent

    agent = AutoCodingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="ambient.coding.validate",
        context={"action": "validate_codes", **body},
    ))
    return output.result


# ── Provider Attestation ──────────────────────────────────────────────────


@router.post("/attestation/submit")
async def submit_attestation(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Submit AI-generated documentation for provider review and signature."""
    from modules.ambient_ai.agents.provider_attestation import ProviderAttestationAgent

    agent = ProviderAttestationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="ambient.attestation.submit",
        context={"action": "submit_for_review", **body},
    ))
    return output.result


@router.post("/attestation/approve")
async def approve_attestation(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Provider approves and digitally signs the documentation."""
    from modules.ambient_ai.agents.provider_attestation import ProviderAttestationAgent

    agent = ProviderAttestationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="ambient.attestation.approve",
        context={"action": "approve", **body},
    ))
    return output.result
