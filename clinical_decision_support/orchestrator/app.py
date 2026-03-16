from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import logging

from graph.graph import run_graph, analyze_vitals
from agents import (
    SupervisorAgent, PatientContext, ComprehensiveRecommendation,
    DiagnosticianAgent, TreatmentAgent, SafetyAgent, CodingAgent, CardiologyAgent
)
from llm import get_clinical_llm, LLMConfig, configure_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Health AI Orchestrator",
    description="Multi-agent clinical decision support system",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_INTERNAL = "http://backend:8000"

# Initialize agents
supervisor = SupervisorAgent()


class VitalsAnalysisRequest(BaseModel):
    patient_id: str
    readings: dict  # e.g., {"HR": 85, "SpO2": 97, "TempC": 37.2, "BP_SYS": 130, "BP_DIA": 85}


@app.post("/run")
async def run(data: dict):
    result = await run_graph(data["vitals_event_id"])
    return result


@app.post("/analyze-vitals")
async def analyze_vitals_endpoint(request: VitalsAnalysisRequest):
    """Analyze vitals directly and generate/persist recommendations."""
    # Analyze the vitals
    recommendation = analyze_vitals(request.readings)

    # Persist to backend
    recommendation_data = {
        "patient_id": request.patient_id,
        "severity": recommendation.get("severity", "info"),
        "title": recommendation.get("title", "Vitals Assessment"),
        "summary": recommendation.get("summary", ""),
        "actions": recommendation.get("actions", []),
        "rationale": recommendation.get("rationale", ""),
        "evidence": recommendation.get("evidence", []),
        "confidence": recommendation.get("confidence", 0.0),
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{BACKEND_INTERNAL}/api/v1/recommendations/",
                json=recommendation_data
            )
            r.raise_for_status()
            recommendation["persisted"] = r.json()
    except Exception as e:
        recommendation["persist_error"] = str(e)

    return recommendation


@app.get("/health")
async def health():
    return {"status": "healthy"}


# =============================================================================
# Comprehensive Clinical Assessment Endpoint
# =============================================================================

class ClinicalAssessmentRequest(BaseModel):
    """Request for comprehensive clinical assessment"""
    patient_id: str
    fhir_id: Optional[str] = None
    include_diagnoses: bool = True
    include_treatments: bool = True
    include_codes: bool = True


class ClinicalAssessmentResponse(BaseModel):
    """Response from comprehensive clinical assessment"""
    success: bool
    patient_id: str
    assessment: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    llm_provider: Optional[str] = None


@app.post("/api/v1/assess", response_model=ClinicalAssessmentResponse)
async def comprehensive_assessment(request: ClinicalAssessmentRequest):
    """
    Run comprehensive clinical assessment using multi-agent system.

    This endpoint:
    1. Gathers patient context from MCP-FHIR server
    2. Runs triage assessment
    3. Generates differential diagnoses with ICD-10 codes
    4. Creates treatment recommendations with CPT codes
    5. Validates against clinical guidelines
    6. Returns comprehensive recommendation
    """
    try:
        logger.info(f"Starting comprehensive assessment for patient: {request.patient_id}")

        # Get patient context from MCP
        fhir_id = request.fhir_id or request.patient_id
        context = await supervisor.mcp.get_patient_context(fhir_id)

        # Run multi-agent workflow
        output = await supervisor.process(context)

        if not output.success:
            return ClinicalAssessmentResponse(
                success=False,
                patient_id=request.patient_id,
                error="; ".join(output.errors) if output.errors else "Assessment failed"
            )

        # Build assessment response
        assessment = {
            "patient_summary": {
                "patient_id": context.patient_id,
                "name": context.name,
                "age": context.age,
                "sex": context.sex,
            },
            "findings": [f.dict() for f in output.findings],
            "critical_findings": [f.dict() for f in output.findings if f.status == "critical"],
            "diagnoses": [d.dict() for d in output.diagnoses] if request.include_diagnoses else [],
            "treatments": [t.dict() for t in output.treatments] if request.include_treatments else [],
            "icd10_codes": output.icd10_codes if request.include_codes else [],
            "cpt_codes": output.cpt_codes if request.include_codes else [],
            "confidence": output.confidence,
            "reasoning": output.reasoning_steps,
            "warnings": output.warnings,
            "requires_human_review": output.requires_human_review,
            "review_reason": output.review_reason,
        }

        # Try to get LLM provider info
        llm_provider = None
        try:
            llm = get_clinical_llm()
            available = llm.get_available_providers()
            llm_provider = llm.primary_provider.value if available else None
        except Exception:
            pass

        # Persist assessment to backend for physician review workflow
        if output.success:
            try:
                # Build assessment data for the clinical assessment model
                assessment_data = {
                    "patient": int(request.patient_id) if request.patient_id.isdigit() else 1,
                    "patient_summary": assessment["patient_summary"],
                    "chief_complaint": context.chief_complaint or "",
                    "history_present_illness": context.history_present_illness or "",
                    "physician_notes": context.physician_notes or "",
                    "findings": assessment["findings"],
                    "critical_findings": assessment["critical_findings"],
                    "diagnoses": assessment["diagnoses"],
                    "primary_diagnosis_code": output.diagnoses[0].icd10_code if output.diagnoses else "",
                    "primary_diagnosis_description": output.diagnoses[0].diagnosis if output.diagnoses else "",
                    "treatments": assessment["treatments"],
                    "immediate_actions": [t.dict() for t in output.treatments if t.priority in ["immediate", "urgent"]],
                    "icd10_codes": assessment["icd10_codes"],
                    "cpt_codes": assessment["cpt_codes"],
                    "confidence_score": output.confidence,
                    "reasoning_chain": output.reasoning_steps,
                    "warnings": output.warnings,
                    "agents_used": list(assessment.get("agent_outputs", {}).keys()) if "agent_outputs" in assessment else [],
                    "requires_human_review": output.requires_human_review,
                    "review_reasons": [output.review_reason] if output.review_reason else [],
                    "llm_provider": llm_provider or ""
                }

                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(
                        f"{BACKEND_INTERNAL}/api/v1/clinical/assessments/",
                        json=assessment_data
                    )
                    if r.status_code < 400:
                        persisted = r.json()
                        assessment["assessment_id"] = persisted.get("id")
                        assessment["persisted"] = True
                        logger.info(f"Assessment persisted with ID: {persisted.get('id')}")
                    else:
                        logger.warning(f"Failed to persist assessment: {r.status_code} - {r.text}")
                        assessment["persist_warning"] = f"Status {r.status_code}"
            except Exception as e:
                logger.warning(f"Failed to persist assessment: {e}")
                assessment["persist_warning"] = str(e)

            # Also create legacy recommendation for backwards compatibility
            try:
                recommendation_data = {
                    "patient_id": request.patient_id,
                    "severity": "critical" if output.warnings else ("warning" if output.requires_human_review else "info"),
                    "title": f"Clinical Assessment: {output.diagnoses[0].diagnosis if output.diagnoses else 'General'}",
                    "summary": output.diagnoses[0].rationale if output.diagnoses else "Comprehensive clinical assessment completed",
                    "actions": [t.description for t in output.treatments[:5]],
                    "rationale": "; ".join(output.reasoning_steps[-3:]),
                    "evidence": [f.interpretation for f in output.findings if f.status != "normal"],
                    "confidence": output.confidence,
                }

                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(
                        f"{BACKEND_INTERNAL}/api/v1/recommendations/",
                        json=recommendation_data
                    )
                    if r.status_code < 400:
                        assessment["persisted_recommendation_id"] = r.json().get("id")
            except Exception as e:
                logger.warning(f"Failed to persist legacy recommendation: {e}")

        return ClinicalAssessmentResponse(
            success=True,
            patient_id=request.patient_id,
            assessment=assessment,
            llm_provider=llm_provider
        )

    except Exception as e:
        logger.error(f"Assessment failed for patient {request.patient_id}: {e}")
        return ClinicalAssessmentResponse(
            success=False,
            patient_id=request.patient_id,
            error=str(e)
        )


@app.get("/api/v1/assess/{patient_id}")
async def get_assessment(patient_id: str, fhir_id: Optional[str] = None):
    """Quick assessment endpoint using GET"""
    request = ClinicalAssessmentRequest(
        patient_id=patient_id,
        fhir_id=fhir_id
    )
    return await comprehensive_assessment(request)


# =============================================================================
# LLM Status and Configuration
# =============================================================================

@app.get("/api/v1/llm/status")
async def llm_status():
    """Get LLM provider status and configuration"""
    try:
        llm = get_clinical_llm()
        return {
            "status": "available",
            "primary_provider": llm.primary_provider.value,
            "available_providers": llm.get_available_providers(),
            "config": {
                "claude_model": llm.config.claude_model,
                "ollama_model": llm.config.ollama_model,
                "ollama_base_url": llm.config.ollama_base_url,
                "temperature": llm.config.temperature,
                "max_tokens": llm.config.max_tokens,
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.post("/api/v1/llm/switch")
async def switch_llm_provider(provider: str):
    """Switch the primary LLM provider (claude, ollama)"""
    try:
        llm = get_clinical_llm()
        llm.set_provider(provider)
        return {
            "success": True,
            "new_provider": provider,
            "available_providers": llm.get_available_providers()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/llm/traces")
async def get_llm_traces(limit: int = 50):
    """Get recent LLM call traces for debugging"""
    try:
        llm = get_clinical_llm()
        return {
            "traces": llm.get_traces(limit)
        }
    except Exception as e:
        return {"error": str(e), "traces": []}


# =============================================================================
# Agent Status
# =============================================================================

@app.get("/api/v1/agents")
async def list_agents():
    """List available agents and their capabilities"""
    return {
        "agents": [
            supervisor.get_agent_card().dict(),
            supervisor.diagnostician.get_agent_card().dict(),
            supervisor.treatment.get_agent_card().dict(),
            supervisor.safety.get_agent_card().dict(),
            supervisor.coding.get_agent_card().dict(),
            supervisor.cardiology.get_agent_card().dict(),
        ]
    }


@app.get("/api/v1/mcp/status")
async def mcp_status():
    """Get MCP server connectivity status"""
    status = {}
    for server_name, url in supervisor.mcp.base_urls.items():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{url}/health")
                status[server_name] = {
                    "url": url,
                    "status": "healthy" if r.status_code == 200 else "unhealthy",
                    "response_code": r.status_code
                }
        except Exception as e:
            status[server_name] = {
                "url": url,
                "status": "unreachable",
                "error": str(e)
            }
    return {"mcp_servers": status}
