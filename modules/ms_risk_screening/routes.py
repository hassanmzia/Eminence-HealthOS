"""MS Risk Screening proxy routes.

Proxies requests from the main HealthOS API to the ms-risk-backend
Django service, keeping a single unified API surface for the frontend.

Auth is NOT enforced at the gateway level — the ms-risk-backend Django
service validates tokens itself.  This mirrors the Next.js rewrite
proxy which also passes requests through without gateway auth.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger("healthos.modules.ms_risk_screening")

router = APIRouter(prefix="/ms-risk-screening", tags=["MS Risk Screening"])

MS_RISK_BACKEND = "http://ms-risk-backend:8000"


async def _proxy(method: str, path: str, body: Any = None, params: dict | None = None) -> Any:
    """Forward a request to the ms-risk-backend Django service."""
    url = f"{MS_RISK_BACKEND}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, json=body, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="MS Risk Screening service unavailable")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


# ── Dashboard / Summary ──────────────────────────────────────────────────────

@router.get("/dashboard")
async def ms_risk_dashboard():
    """Aggregated MS Risk Screening dashboard data."""
    return await _proxy("GET", "/api/dashboard/")


@router.get("/health")
async def ms_risk_health():
    """Health check for the MS Risk Screening backend."""
    return await _proxy("GET", "/api/health/")


# ── Patients ─────────────────────────────────────────────────────────────────

@router.get("/patients")
async def list_ms_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    """List MS risk screening patients."""
    return await _proxy("GET", "/api/patients/", params={"page": page, "page_size": page_size})


@router.get("/patients/summary")
async def patient_summary():
    """Population-level patient summary statistics."""
    return await _proxy("GET", "/api/patients/summary/")


@router.get("/patients/{patient_id}")
async def get_ms_patient(patient_id: str):
    """Get a specific MS screening patient."""
    return await _proxy("GET", f"/api/patients/{patient_id}/")


@router.get("/patients/{patient_id}/risk_history")
async def patient_risk_history(patient_id: str):
    """Get risk assessment history for a specific patient."""
    return await _proxy("GET", f"/api/patients/{patient_id}/risk_history/")


# ── Risk Assessments ─────────────────────────────────────────────────────────

@router.get("/assessments")
async def list_assessments(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    """List risk assessments."""
    return await _proxy("GET", "/api/assessments/", params={"page": page, "page_size": page_size})


@router.get("/assessments/high_risk")
async def high_risk_assessments(
    threshold: float = Query(0.65, ge=0.0, le=1.0),
    run_id: str | None = Query(None),
):
    """Get high-risk assessments filtered by threshold."""
    params: dict[str, Any] = {"threshold": threshold}
    if run_id:
        params["run_id"] = run_id
    return await _proxy("GET", "/api/assessments/high_risk/", params=params)


@router.get("/assessments/pending_review")
async def pending_review_assessments():
    """Get assessments awaiting clinician review."""
    return await _proxy("GET", "/api/assessments/pending_review/")


@router.get("/assessments/{assessment_id}")
async def get_assessment(assessment_id: str):
    """Get a specific risk assessment."""
    return await _proxy("GET", f"/api/assessments/{assessment_id}/")


@router.post("/assessments/{assessment_id}/review")
async def review_assessment(assessment_id: str, body: dict[str, Any]):
    """Submit a clinician review for an assessment."""
    return await _proxy("POST", f"/api/assessments/{assessment_id}/review/", body=body)


# ── Workflow Runs ─────────────────────────────────────────────────────────────

@router.get("/workflows")
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """List workflow runs."""
    return await _proxy("GET", "/api/workflows/", params={"page": page, "page_size": page_size})


@router.post("/workflows/trigger")
async def trigger_workflow(body: dict[str, Any]):
    """Trigger a new multi-agent screening workflow."""
    return await _proxy("POST", "/api/workflows/trigger/", body=body)


@router.get("/workflows/{run_id}")
async def get_workflow(run_id: str):
    """Get workflow run details."""
    return await _proxy("GET", f"/api/workflows/{run_id}/")


@router.get("/workflows/{run_id}/metrics")
async def workflow_metrics(run_id: str):
    """Get comprehensive metrics (confusion matrix, F1, etc.) for a workflow run."""
    return await _proxy("GET", f"/api/workflows/{run_id}/metrics/")


@router.get("/workflows/{run_id}/risk_distribution")
async def workflow_risk_distribution(run_id: str):
    """Get risk score histogram for a workflow run."""
    return await _proxy("GET", f"/api/workflows/{run_id}/risk_distribution/")


@router.get("/workflows/{run_id}/action_distribution")
async def workflow_action_distribution(run_id: str):
    """Get action breakdown for a workflow run."""
    return await _proxy("GET", f"/api/workflows/{run_id}/action_distribution/")


@router.get("/workflows/{run_id}/autonomy_distribution")
async def workflow_autonomy_distribution(run_id: str):
    """Get autonomy level distribution for a workflow run."""
    return await _proxy("GET", f"/api/workflows/{run_id}/autonomy_distribution/")


@router.get("/workflows/{run_id}/calibration")
async def workflow_calibration(run_id: str):
    """Get calibration curve data for a workflow run."""
    return await _proxy("GET", f"/api/workflows/{run_id}/calibration/")


@router.get("/workflows/{run_id}/fairness")
async def workflow_fairness(
    run_id: str,
    group_by: str = Query("sex", pattern="^(sex|age_band|lookalike_dx)$"),
):
    """Get subgroup fairness analysis for a workflow run."""
    return await _proxy("GET", f"/api/workflows/{run_id}/fairness/", params={"group_by": group_by})


# ── Policy Configuration ─────────────────────────────────────────────────────

@router.get("/policies")
async def list_policies():
    """List policy configurations."""
    return await _proxy("GET", "/api/policies/")


@router.post("/policies")
async def create_policy(body: dict[str, Any]):
    """Create a new policy configuration."""
    return await _proxy("POST", "/api/policies/", body=body)


@router.post("/policies/{policy_id}/activate")
async def activate_policy(policy_id: str):
    """Set a policy as the active configuration."""
    return await _proxy("POST", f"/api/policies/{policy_id}/activate/")


# ── What-If Analysis ─────────────────────────────────────────────────────────

@router.post("/what-if")
async def what_if_analysis(body: dict[str, Any]):
    """Run what-if policy simulation."""
    return await _proxy("POST", "/api/what-if/", body=body)


# ── Governance ────────────────────────────────────────────────────────────────

@router.get("/governance-rules")
async def list_governance_rules():
    """List governance rules."""
    return await _proxy("GET", "/api/governance-rules/")


@router.post("/governance-rules")
async def create_governance_rule(body: dict[str, Any]):
    """Create a governance rule."""
    return await _proxy("POST", "/api/governance-rules/", body=body)


@router.get("/compliance-reports")
async def list_compliance_reports():
    """List compliance reports."""
    return await _proxy("GET", "/api/compliance-reports/")


@router.post("/compliance-reports/generate")
async def generate_compliance_report(body: dict[str, Any]):
    """Generate a new compliance report for a workflow run."""
    return await _proxy("POST", "/api/compliance-reports/generate/", body=body)


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action_type: str | None = Query(None),
    actor: str | None = Query(None),
):
    """List audit logs with optional filters."""
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if action_type:
        params["action_type"] = action_type
    if actor:
        params["actor"] = actor
    return await _proxy("GET", "/api/audit-logs/", params=params)


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    """List notifications."""
    return await _proxy("GET", "/api/notifications/", params={"page": page, "page_size": page_size})


@router.get("/notifications/unread_count")
async def notification_unread_count():
    """Get count of unread notifications."""
    return await _proxy("GET", "/api/notifications/unread_count/")


@router.post("/notifications/{notification_id}/mark_read")
async def mark_notification_read(notification_id: str):
    """Mark a single notification as read."""
    return await _proxy("POST", f"/api/notifications/{notification_id}/mark_read/")


@router.post("/notifications/mark_all_read")
async def mark_all_notifications_read():
    """Mark all notifications as read."""
    return await _proxy("POST", "/api/notifications/mark_all_read/")


# ── MCP Proxy (expose ms_risk_screening MCP server) ──────────────────────────

@router.get("/mcp/tools")
async def ms_risk_mcp_tools():
    """List MCP tools available in the MS Risk Screening module."""
    return await _proxy("GET", "/mcp/tools/")


@router.post("/mcp/invoke")
async def ms_risk_mcp_invoke(body: dict[str, Any]):
    """Invoke an MCP tool on the MS Risk Screening backend."""
    return await _proxy("POST", "/mcp/invoke/", body=body)


# ── A2A Proxy (expose ms_risk_screening A2A agents) ──────────────────────────

@router.get("/a2a/agents")
async def ms_risk_a2a_agents():
    """List A2A agents in the MS Risk Screening module."""
    return await _proxy("GET", "/a2a/agents/")


@router.post("/a2a/tasks/create")
async def ms_risk_a2a_create_task(body: dict[str, Any]):
    """Create a task via MS Risk Screening A2A."""
    return await _proxy("POST", "/a2a/tasks/create/", body=body)


@router.post("/a2a/orchestrate")
async def ms_risk_a2a_orchestrate(body: dict[str, Any]):
    """Orchestrate a full screening via A2A."""
    return await _proxy("POST", "/a2a/orchestrate/", body=body)
