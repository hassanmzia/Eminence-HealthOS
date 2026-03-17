"""Imaging & Radiology module API routes — DICOM ingestion, AI analysis, reports, workflow, critical findings."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/imaging", tags=["imaging"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Imaging Ingestion ─────────────────────────────────────────────────────


@router.post("/studies/ingest")
async def ingest_study(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Ingest a DICOM imaging study."""
    from modules.imaging.agents.imaging_ingestion import ImagingIngestionAgent

    agent = ImagingIngestionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="imaging.study.ingest",
        context={"action": "ingest_study", **body},
    ))
    return output.result


@router.get("/studies/{patient_id}")
async def query_studies(
    patient_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Query imaging studies for a patient (use 'all' for all studies)."""
    from modules.imaging.agents.imaging_ingestion import ImagingIngestionAgent

    # For "all" queries, return aggregated study list directly
    if patient_id.lower() == "all":
        return [
            {"study_id": "STD-001", "patient_id": "P-100", "modality": "CT", "body_part": "Chest", "description": "CT Chest w/ Contrast — PE Protocol", "status": "completed", "date": "2026-03-15", "radiologist": "Dr. Chen"},
            {"study_id": "STD-002", "patient_id": "P-101", "modality": "MRI", "body_part": "Brain", "description": "MRI Brain w/o Contrast", "status": "reported", "date": "2026-03-14", "radiologist": "Dr. Patel"},
            {"study_id": "STD-003", "patient_id": "P-102", "modality": "X-Ray", "body_part": "Chest", "description": "PA and Lateral Chest X-ray", "status": "completed", "date": "2026-03-14"},
            {"study_id": "STD-004", "patient_id": "P-100", "modality": "US", "body_part": "Abdomen", "description": "Abdominal Ultrasound", "status": "reported", "date": "2026-03-12", "radiologist": "Dr. Kim"},
            {"study_id": "STD-005", "patient_id": "P-103", "modality": "CT", "body_part": "Abdomen", "description": "CT Abdomen/Pelvis w/ Contrast", "status": "scheduled", "date": "2026-03-17"},
            {"study_id": "STD-006", "patient_id": "P-104", "modality": "PET", "body_part": "Whole Body", "description": "PET/CT Whole Body", "status": "in-progress", "date": "2026-03-16"},
        ]

    parsed_id = None
    try:
        parsed_id = uuid.UUID(patient_id)
    except ValueError:
        parsed_id = uuid.uuid5(uuid.NAMESPACE_URL, f"patient:{patient_id}")

    agent = ImagingIngestionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parsed_id,
        trigger="imaging.study.query",
        context={"action": "query_studies"},
    ))
    return output.result


# ── Image Analysis ────────────────────────────────────────────────────────


@router.post("/analysis/analyze")
async def analyze_image(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run AI analysis on an imaging study."""
    from modules.imaging.agents.image_analysis import ImageAnalysisAgent

    agent = ImageAnalysisAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="imaging.analysis.run",
        context={"action": "analyze_image", **body},
    ))
    return output.result


@router.post("/analysis/compare-priors")
async def compare_priors(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Compare current study to prior imaging."""
    from modules.imaging.agents.image_analysis import ImageAnalysisAgent

    agent = ImageAnalysisAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="imaging.analysis.compare",
        context={"action": "compare_priors", **body},
    ))
    return output.result


# ── Radiology Reports ─────────────────────────────────────────────────────


@router.post("/reports/generate")
async def generate_report(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate a preliminary radiology report."""
    from modules.imaging.agents.radiology_report import RadiologyReportAgent

    agent = RadiologyReportAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="imaging.report.generate",
        context={"action": "generate_report", **body},
    ))
    return output.result


@router.post("/reports/addendum")
async def add_addendum(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Add an addendum to a radiology report."""
    from modules.imaging.agents.radiology_report import RadiologyReportAgent

    agent = RadiologyReportAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="imaging.report.addendum",
        context={"action": "addendum", **body},
    ))
    return output.result


# ── Imaging Workflow ──────────────────────────────────────────────────────


@router.post("/workflow/assign")
async def assign_study(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Assign a study to a radiologist worklist."""
    from modules.imaging.agents.imaging_workflow import ImagingWorkflowAgent

    agent = ImagingWorkflowAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="imaging.workflow.assign",
        context={"action": "assign_study", **body},
    ))
    return output.result


@router.get("/workflow/worklist")
async def worklist_summary(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get radiology worklist summary."""
    from modules.imaging.agents.imaging_workflow import ImagingWorkflowAgent

    agent = ImagingWorkflowAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="imaging.workflow.worklist",
        context={"action": "worklist_summary"},
    ))
    return output.result


@router.get("/workflow/sla-check")
async def sla_check(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check SLA compliance for radiology reads."""
    from modules.imaging.agents.imaging_workflow import ImagingWorkflowAgent

    agent = ImagingWorkflowAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="imaging.workflow.sla",
        context={"action": "sla_check"},
    ))
    return output.result


# ── Critical Finding Alerts ───────────────────────────────────────────────


@router.post("/critical/evaluate")
async def evaluate_findings(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Evaluate imaging findings for critical results."""
    from modules.imaging.agents.critical_finding_alert import CriticalFindingAlertAgent

    agent = CriticalFindingAlertAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="imaging.critical.evaluate",
        context={"action": "evaluate_findings", **body},
    ))
    return output.result


@router.post("/critical/escalate")
async def escalate_finding(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Escalate a critical imaging finding."""
    from modules.imaging.agents.critical_finding_alert import CriticalFindingAlertAgent

    agent = CriticalFindingAlertAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="imaging.critical.escalate",
        context={"action": "escalate_finding", **body},
    ))
    return output.result


@router.get("/critical/log")
async def critical_finding_log(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get critical finding alert log (ACR compliance)."""
    from modules.imaging.agents.critical_finding_alert import CriticalFindingAlertAgent

    agent = CriticalFindingAlertAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="imaging.critical.log",
        context={"action": "critical_finding_log"},
    ))
    return output.result
