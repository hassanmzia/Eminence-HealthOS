"""Labs module API routes — lab orders, results, trends, critical value alerts."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput, parse_patient_id
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/labs", tags=["labs"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")




# ── Lab Orders ────────────────────────────────────────────────────────────


@router.post("/orders/create")
async def create_order(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a new lab order."""
    from modules.labs.agents.lab_order import LabOrderAgent

    agent = LabOrderAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="labs.order.create",
        context={"action": "create_order", **body},
    ))
    return output.result


@router.post("/orders/cancel")
async def cancel_order(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Cancel a lab order."""
    from modules.labs.agents.lab_order import LabOrderAgent

    agent = LabOrderAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.order.cancel",
        context={"action": "cancel_order", **body},
    ))
    return output.result


@router.get("/orders/{order_id}/status")
async def order_status(
    order_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get lab order status."""
    from modules.labs.agents.lab_order import LabOrderAgent

    agent = LabOrderAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.order.status",
        context={"action": "order_status", "lab_order_id": order_id},
    ))
    return output.result


@router.post("/orders/suggest-panels")
async def suggest_panels(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Suggest lab panels based on conditions and medications."""
    from modules.labs.agents.lab_order import LabOrderAgent

    agent = LabOrderAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="labs.order.suggest",
        context={"action": "suggest_panels", **body},
    ))
    return output.result


# ── Lab Results ───────────────────────────────────────────────────────────


@router.post("/results/ingest")
async def ingest_results(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Ingest lab results from external systems."""
    from modules.labs.agents.lab_results import LabResultsAgent

    agent = LabResultsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="labs.results.ingest",
        context={"action": "ingest_results", **body},
    ))
    return output.result


@router.post("/results/flag-abnormals")
async def flag_abnormals(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Flag abnormal lab values."""
    from modules.labs.agents.lab_results import LabResultsAgent

    agent = LabResultsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.results.flag",
        context={"action": "flag_abnormals", **body},
    ))
    return output.result


@router.post("/results/interpret")
async def interpret_results(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Interpret lab results with AI-generated clinical narrative."""
    from modules.labs.agents.lab_results import LabResultsAgent

    agent = LabResultsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.results.interpret",
        context={"action": "interpret_results", **body},
    ))
    return output.result


@router.get("/results/{patient_id}")
async def get_results(
    patient_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get latest lab results for a patient."""
    from modules.labs.agents.lab_results import LabResultsAgent

    agent = LabResultsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id),
        trigger="labs.results.get",
        context={"action": "get_results"},
    ))
    return output.result


@router.post("/results/compare")
async def compare_to_prior(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Compare current results to prior results."""
    from modules.labs.agents.lab_results import LabResultsAgent

    agent = LabResultsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="labs.results.compare",
        context={"action": "compare_to_prior", **body},
    ))
    return output.result


# ── Lab Trends ────────────────────────────────────────────────────────────


@router.post("/trends/analyze")
async def analyze_trends(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Analyze lab value trends over time."""
    from modules.labs.agents.lab_trend import LabTrendAgent

    agent = LabTrendAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="labs.trends.analyze",
        context={"action": "analyze_trends", **body},
    ))
    return output.result


@router.post("/trends/project")
async def project_trajectory(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Project lab value trajectory."""
    from modules.labs.agents.lab_trend import LabTrendAgent

    agent = LabTrendAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.trends.project",
        context={"action": "project_trajectory", **body},
    ))
    return output.result


@router.get("/trends/summary/{patient_id}")
async def trend_summary(
    patient_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get trend summary for a patient."""
    from modules.labs.agents.lab_trend import LabTrendAgent

    agent = LabTrendAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id),
        trigger="labs.trends.summary",
        context={"action": "trend_summary"},
    ))
    return output.result


# ── Critical Value Alerts ─────────────────────────────────────────────────


@router.post("/critical/evaluate")
async def evaluate_critical(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Evaluate lab results for critical values."""
    from modules.labs.agents.critical_value_alert import CriticalValueAlertAgent

    agent = CriticalValueAlertAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="labs.critical.evaluate",
        context={"action": "evaluate_critical", **body},
    ))
    return output.result


@router.post("/critical/escalate")
async def escalate_critical(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Escalate a critical value alert."""
    from modules.labs.agents.critical_value_alert import CriticalValueAlertAgent

    agent = CriticalValueAlertAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.critical.escalate",
        context={"action": "escalate", **body},
    ))
    return output.result


@router.post("/critical/acknowledge")
async def acknowledge_critical(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Acknowledge a critical value alert."""
    from modules.labs.agents.critical_value_alert import CriticalValueAlertAgent

    agent = CriticalValueAlertAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.critical.acknowledge",
        context={"action": "acknowledge", **body},
    ))
    return output.result


@router.get("/critical/log")
async def critical_log(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get critical value alert log (CLIA compliance)."""
    from modules.labs.agents.critical_value_alert import CriticalValueAlertAgent

    agent = CriticalValueAlertAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="labs.critical.log",
        context={"action": "critical_log"},
    ))
    return output.result
