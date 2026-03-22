"""
Eminence HealthOS — Clinical Decision Support API Routes
Proxies to the clinical orchestrator service for AI-powered clinical assessments.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.config import get_settings
from healthos_platform.security.rbac import Permission

logger = structlog.get_logger()

router = APIRouter(prefix="/clinical-assessment", tags=["Clinical Assessment"])

_settings = get_settings()
ORCHESTRATOR_URL = _settings.clinical_orchestrator_url
IOT_SIMULATOR_URL = _settings.iot_simulator_url
ORCHESTRATOR_TIMEOUT = 60.0


# ── Schemas ──────────────────────────────────────────────────────────────────


class ClinicalAssessmentRequest(BaseModel):
    patient_id: str
    fhir_id: str | None = None
    include_diagnoses: bool = True
    include_treatments: bool = True
    include_codes: bool = True


class ClinicalAssessmentResponse(BaseModel):
    success: bool
    patient_id: str
    assessment: dict[str, Any] | None = None
    error: str | None = None
    llm_provider: str | None = None


class VitalsAnalysisRequest(BaseModel):
    patient_id: str
    readings: dict[str, Any]


class LLMStatusResponse(BaseModel):
    status: str
    primary_provider: str | None = None
    available_providers: list[str] = []
    config: dict[str, Any] = {}
    error: str | None = None


class MCPStatusResponse(BaseModel):
    mcp_servers: dict[str, Any] = {}


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/assess", response_model=ClinicalAssessmentResponse)
async def run_clinical_assessment(
    request: ClinicalAssessmentRequest,
    ctx: TenantContext = Depends(get_current_user),
):
    """Run comprehensive AI clinical assessment via the orchestrator."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    try:
        async with httpx.AsyncClient(timeout=ORCHESTRATOR_TIMEOUT) as client:
            r = await client.post(
                f"{ORCHESTRATOR_URL}/api/v1/assess",
                json=request.model_dump(),
            )
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Clinical orchestrator timed out")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Clinical orchestrator unavailable")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@router.get("/assess/{patient_id}", response_model=ClinicalAssessmentResponse)
async def get_clinical_assessment(
    patient_id: str,
    fhir_id: str | None = None,
    ctx: TenantContext = Depends(get_current_user),
):
    """Quick clinical assessment via GET."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    try:
        async with httpx.AsyncClient(timeout=ORCHESTRATOR_TIMEOUT) as client:
            params = {"fhir_id": fhir_id} if fhir_id else {}
            r = await client.get(
                f"{ORCHESTRATOR_URL}/api/v1/assess/{patient_id}",
                params=params,
            )
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Clinical orchestrator timed out")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Clinical orchestrator unavailable")


@router.post("/analyze-vitals")
async def analyze_vitals(
    request: VitalsAnalysisRequest,
    ctx: TenantContext = Depends(get_current_user),
):
    """Analyze vitals and generate AI recommendations."""
    ctx.require_permission(Permission.VITALS_READ)

    try:
        async with httpx.AsyncClient(timeout=ORCHESTRATOR_TIMEOUT) as client:
            r = await client.post(
                f"{ORCHESTRATOR_URL}/analyze-vitals",
                json=request.model_dump(),
            )
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Clinical orchestrator timed out")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Clinical orchestrator unavailable")


@router.get("/llm/status", response_model=LLMStatusResponse)
async def get_llm_status(
    ctx: TenantContext = Depends(get_current_user),
):
    """Get LLM provider status from the clinical orchestrator."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/api/v1/llm/status")
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.warning("llm_status.orchestrator_unreachable", url=ORCHESTRATOR_URL, error=str(exc))
        return LLMStatusResponse(status="unavailable", error=f"Orchestrator not reachable at {ORCHESTRATOR_URL}")


@router.post("/llm/switch")
async def switch_llm_provider(
    provider: str,
    ctx: TenantContext = Depends(get_current_user),
):
    """Switch the LLM provider used by the clinical orchestrator."""
    ctx.require_permission(Permission.AGENTS_MANAGE)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{ORCHESTRATOR_URL}/api/v1/llm/switch",
                params={"provider": provider},
            )
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Clinical orchestrator unavailable")


@router.get("/agents")
async def list_clinical_agents(
    ctx: TenantContext = Depends(get_current_user),
):
    """List specialty clinical agents from the orchestrator."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/api/v1/agents")
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        return {"agents": [], "error": "Orchestrator not reachable"}


@router.get("/mcp/status", response_model=MCPStatusResponse)
async def get_mcp_status(
    ctx: TenantContext = Depends(get_current_user),
):
    """Get MCP server connectivity status from the orchestrator."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/api/v1/mcp/status")
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        logger.warning("mcp_status.orchestrator_unreachable", url=ORCHESTRATOR_URL)
        return MCPStatusResponse(mcp_servers={
            "mcp-fhir-server": {"url": "http://mcp-fhir-server:8005", "status": "unreachable", "error": "Orchestrator not reachable"},
            "mcp-labs-server": {"url": "http://mcp-labs-server:8006", "status": "unreachable", "error": "Orchestrator not reachable"},
            "mcp-rag-server": {"url": "http://mcp-rag-server:8007", "status": "unreachable", "error": "Orchestrator not reachable"},
            "mcp-fhir-adapter": {"url": "http://mcp-fhir-adapter:8002", "status": "unreachable", "error": "Orchestrator not reachable"},
        })


@router.get("/simulator/status")
async def get_simulator_status(
    ctx: TenantContext = Depends(get_current_user),
):
    """Get IoT simulator status."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{IOT_SIMULATOR_URL}/status")
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        logger.warning("simulator_status.unreachable", url=IOT_SIMULATOR_URL)
        return {"running": False, "error": f"Simulator not reachable at {IOT_SIMULATOR_URL}"}


@router.post("/simulator/{action}")
async def control_simulator(
    action: str,
    ctx: TenantContext = Depends(get_current_user),
):
    """Control IoT simulator (start/stop/trigger)."""
    ctx.require_permission(Permission.AGENTS_MANAGE)

    if action not in ("start", "stop", "trigger", "reset-stats"):
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{IOT_SIMULATOR_URL}/{action}")
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Simulator not reachable")
