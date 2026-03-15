"""Compliance & Governance module API routes — HIPAA monitoring, AI governance, consent management, regulatory reporting."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/compliance")

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── HIPAA Compliance ──────────────────────────────────────────────────────────


@router.post("/hipaa/scan")
async def run_hipaa_scan(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run a HIPAA compliance scan across platform operations."""
    from modules.compliance.agents.hipaa_compliance_monitor import HIPAAComplianceMonitorAgent

    agent = HIPAAComplianceMonitorAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.hipaa.scan",
        context={"action": "full_scan", **body},
    ))
    return output.result


@router.get("/hipaa/status")
async def get_hipaa_status(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get current HIPAA compliance status and scores."""
    from modules.compliance.agents.hipaa_compliance_monitor import HIPAAComplianceMonitorAgent

    agent = HIPAAComplianceMonitorAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.hipaa.status",
        context={"action": "compliance_status"},
    ))
    return output.result


@router.post("/hipaa/audit-log")
async def query_hipaa_audit_log(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Query the HIPAA audit log for PHI access events."""
    from modules.compliance.agents.hipaa_compliance_monitor import HIPAAComplianceMonitorAgent

    agent = HIPAAComplianceMonitorAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.hipaa.audit_log",
        context={"action": "audit_log_query", **body},
    ))
    return output.result


# ── AI Governance ─────────────────────────────────────────────────────────────


@router.get("/ai-governance/models")
async def list_ai_models(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """List all registered AI models with governance status."""
    from modules.compliance.agents.ai_governance import AIGovernanceAgent

    agent = AIGovernanceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.ai_governance.list_models",
        context={"action": "list_models"},
    ))
    return output.result


@router.post("/ai-governance/audit")
async def audit_ai_model(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Audit a specific AI model for drift, bias, and performance."""
    from modules.compliance.agents.ai_governance import AIGovernanceAgent

    agent = AIGovernanceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.ai_governance.audit",
        context={"action": "audit_model", **body},
    ))
    return output.result


@router.post("/ai-governance/drift-check")
async def check_model_drift(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check a model for data drift using PSI (Population Stability Index)."""
    from modules.compliance.agents.ai_governance import AIGovernanceAgent

    agent = AIGovernanceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.ai_governance.drift_check",
        context={"action": "drift_check", **body},
    ))
    return output.result


# ── Consent Management ────────────────────────────────────────────────────────


@router.post("/consent/capture")
async def capture_consent(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Capture patient consent for a specific purpose."""
    from modules.compliance.agents.consent_management import ConsentManagementAgent

    agent = ConsentManagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="compliance.consent.capture",
        context={"action": "capture_consent", **body},
    ))
    return output.result


@router.post("/consent/revoke")
async def revoke_consent(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Revoke patient consent for a specific purpose."""
    from modules.compliance.agents.consent_management import ConsentManagementAgent

    agent = ConsentManagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="compliance.consent.revoke",
        context={"action": "revoke_consent", **body},
    ))
    return output.result


@router.post("/consent/status")
async def get_consent_status(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get consent status for a patient across all purposes."""
    from modules.compliance.agents.consent_management import ConsentManagementAgent

    agent = ConsentManagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="compliance.consent.status",
        context={"action": "consent_status", **body},
    ))
    return output.result


@router.get("/consent/audit-trail")
async def get_consent_audit_trail(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get the consent audit trail for compliance reporting."""
    from modules.compliance.agents.consent_management import ConsentManagementAgent

    agent = ConsentManagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.consent.audit_trail",
        context={"action": "audit_trail"},
    ))
    return output.result


# ── Regulatory Reporting ──────────────────────────────────────────────────────


@router.post("/reports/generate")
async def generate_compliance_report(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate a compliance report for a specified framework (HIPAA, SOC2, HITRUST, etc.)."""
    from modules.compliance.agents.regulatory_reporting import RegulatoryReportingAgent

    agent = RegulatoryReportingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.reports.generate",
        context={"action": "generate_report", **body},
    ))
    return output.result


@router.post("/reports/gap-analysis")
async def run_gap_analysis(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run a gap analysis for a specific compliance framework."""
    from modules.compliance.agents.regulatory_reporting import RegulatoryReportingAgent

    agent = RegulatoryReportingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.reports.gap_analysis",
        context={"action": "gap_analysis", **body},
    ))
    return output.result


@router.get("/frameworks")
async def list_frameworks(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """List all compliance frameworks and their current status."""
    from modules.compliance.agents.regulatory_reporting import RegulatoryReportingAgent

    agent = RegulatoryReportingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="compliance.frameworks.list",
        context={"action": "list_frameworks"},
    ))
    return output.result
