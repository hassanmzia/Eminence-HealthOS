"""Operations module API routes — prior auth, insurance, referrals, tasks, scheduling, compliance."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

logger = logging.getLogger("healthos.routes.operations")
router = APIRouter(prefix="/operations", tags=["operations"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Prior Authorization ──────────────────────────────────────────────────────


@router.post("/prior-auth/evaluate")
async def evaluate_prior_auth(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Evaluate whether a procedure requires prior authorization."""
    from modules.operations.agents.prior_authorization import PriorAuthorizationAgent

    agent = PriorAuthorizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.prior_auth.evaluate",
        context={"action": "evaluate", **body},
    ))
    return output.result


@router.post("/prior-auth/submit")
async def submit_prior_auth(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Submit a prior authorization request."""
    from modules.operations.agents.prior_authorization import PriorAuthorizationAgent

    agent = PriorAuthorizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.prior_auth.submit",
        context={"action": "submit", **body},
    ))
    return output.result


@router.post("/prior-auth/status")
async def check_prior_auth_status(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check status of a prior authorization."""
    from modules.operations.agents.prior_authorization import PriorAuthorizationAgent

    agent = PriorAuthorizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.prior_auth.status",
        context={"action": "check_status", **body},
    ))
    return output.result


# ── Insurance Verification ───────────────────────────────────────────────────


@router.post("/insurance/verify")
async def verify_insurance(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Verify patient insurance eligibility."""
    from modules.operations.agents.insurance_verification import InsuranceVerificationAgent

    agent = InsuranceVerificationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.insurance.verify",
        context={"action": "verify_eligibility", **body},
    ))
    return output.result


@router.post("/insurance/benefits")
async def check_benefits(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check insurance benefits for a service type."""
    from modules.operations.agents.insurance_verification import InsuranceVerificationAgent

    agent = InsuranceVerificationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.insurance.benefits",
        context={"action": "check_benefits", **body},
    ))
    return output.result


@router.post("/insurance/estimate")
async def estimate_patient_cost(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Estimate patient out-of-pocket costs."""
    from modules.operations.agents.insurance_verification import InsuranceVerificationAgent

    agent = InsuranceVerificationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.insurance.estimate",
        context={"action": "estimate_cost", **body},
    ))
    return output.result


# ── Referral Coordination ────────────────────────────────────────────────────


@router.post("/referrals/create")
async def create_referral(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a new referral."""
    from modules.operations.agents.referral_coordination import ReferralCoordinationAgent

    agent = ReferralCoordinationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.referral.create",
        context={"action": "create", **body},
    ))
    return output.result


@router.post("/referrals/match-specialist")
async def match_specialist(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Find matching specialists for a referral."""
    from modules.operations.agents.referral_coordination import ReferralCoordinationAgent

    agent = ReferralCoordinationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.referral.match",
        context={"action": "match_specialist", **body},
    ))
    return output.result


@router.post("/referrals/track")
async def track_referral(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Track status of a referral."""
    from modules.operations.agents.referral_coordination import ReferralCoordinationAgent

    agent = ReferralCoordinationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.referral.track",
        context={"action": "track", **body},
    ))
    return output.result


# ── Task Orchestration ───────────────────────────────────────────────────────


@router.post("/tasks/create")
async def create_task(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a new operational task."""
    from modules.operations.agents.task_orchestration import TaskOrchestrationAgent

    agent = TaskOrchestrationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.task.create",
        context={"action": "create_task", **body},
    ))
    return output.result


@router.post("/tasks/workflow")
async def create_workflow(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a multi-step workflow."""
    from modules.operations.agents.task_orchestration import TaskOrchestrationAgent

    agent = TaskOrchestrationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.workflow.create",
        context={"action": "create_workflow", **body},
    ))
    return output.result


@router.post("/tasks/sla")
async def check_sla_compliance(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Check SLA compliance across operational tasks."""
    from modules.operations.agents.task_orchestration import TaskOrchestrationAgent

    agent = TaskOrchestrationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.sla.check",
        context={"action": "check_sla", **body},
    ))
    return output.result


@router.post("/tasks/queue")
async def get_task_queue(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get current task queue."""
    from modules.operations.agents.task_orchestration import TaskOrchestrationAgent

    agent = TaskOrchestrationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.task.queue",
        context={"action": "get_queue", **body},
    ))
    return output.result


# ── Billing ───────────────────────────────────────────────────────────────────


@router.post("/billing/validate")
async def validate_billing(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Validate encounter for billing readiness."""
    from modules.operations.agents.billing_readiness import BillingReadinessAgent

    agent = BillingReadinessAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="billing.encounter.validate",
        context={"action": "validate", **body},
    ))
    return output.result


@router.post("/billing/check-coding")
async def check_coding(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check CPT/ICD-10 coding accuracy."""
    from modules.operations.agents.billing_readiness import BillingReadinessAgent

    agent = BillingReadinessAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="billing.coding.check",
        context={"action": "check_coding", **body},
    ))
    return output.result


@router.post("/billing/prepare-claim")
async def prepare_claim(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Prepare a claim for submission."""
    from modules.operations.agents.billing_readiness import BillingReadinessAgent

    agent = BillingReadinessAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="billing.claim.prepare",
        context={"action": "prepare_claim", **body},
    ))
    return output.result


@router.post("/billing/audit")
async def run_billing_audit(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Run billing audit across recent encounters."""
    from modules.operations.agents.billing_readiness import BillingReadinessAgent

    agent = BillingReadinessAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="billing.audit",
        context={"action": "audit", **body},
    ))
    return output.result


# ── Workflow Engine ──────────────────────────────────────────────────────────


@router.post("/workflows/create")
async def create_workflow(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a new multi-step workflow from a template."""
    from modules.operations.workflow_engine import workflow_engine

    workflow = workflow_engine.create_workflow(
        workflow_type=body.get("workflow_type", ""),
        org_id=tenant_id,
        patient_id=body.get("patient_id"),
        priority=body.get("priority", "normal"),
        context=body.get("context", {}),
        custom_steps=body.get("steps"),
    )
    return workflow_engine.get_workflow_summary(workflow.workflow_id)


@router.get("/workflows/templates")
async def list_workflow_templates(
    user: CurrentUser = Depends(require_auth),
):
    """List available workflow templates."""
    from modules.operations.workflow_engine import workflow_engine
    return {"templates": workflow_engine.available_templates}


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    user: CurrentUser = Depends(require_auth),
):
    """Get workflow status and progress."""
    from modules.operations.workflow_engine import workflow_engine

    summary = workflow_engine.get_workflow_summary(workflow_id)
    if not summary:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Workflow not found")
    return summary


@router.get("/workflows")
async def list_workflows(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """List all workflows for the organization."""
    from modules.operations.workflow_engine import workflow_engine
    return {"workflows": workflow_engine.list_workflows(tenant_id)}


@router.post("/workflows/{workflow_id}/steps/{step_id}/complete")
async def complete_workflow_step(
    workflow_id: str,
    step_id: str,
    body: dict[str, Any],
    user: CurrentUser = Depends(require_auth),
):
    """Mark a workflow step as completed."""
    from modules.operations.workflow_engine import workflow_engine

    step = workflow_engine.complete_step(workflow_id, step_id, body.get("output", {}))
    if not step:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Step not found or not in progress")
    return workflow_engine.get_workflow_summary(workflow_id)


@router.post("/workflows/sla-violations")
async def check_sla_violations(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Check for SLA violations across active workflows."""
    from modules.operations.workflow_engine import workflow_engine
    return {"violations": workflow_engine.check_sla_violations(tenant_id)}


# ── Payer Integration ────────────────────────────────────────────────────────


@router.get("/payers")
async def list_payers(
    user: CurrentUser = Depends(require_auth),
):
    """List registered payer connectors."""
    from modules.operations.payer_connector import payer_registry
    return {"payers": payer_registry.list_payers()}


@router.post("/payers/{payer_id}/eligibility")
async def payer_eligibility_check(
    payer_id: str,
    body: dict[str, Any],
    user: CurrentUser = Depends(require_auth),
):
    """Check eligibility directly via payer connector."""
    from modules.operations.payer_connector import payer_registry, EligibilityRequest

    connector = payer_registry.get(payer_id)
    if not connector:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Payer '{payer_id}' not found")

    request = EligibilityRequest(**body)
    response = await connector.check_eligibility(request)
    return response.model_dump()


@router.post("/payers/{payer_id}/submit-claim")
async def payer_submit_claim(
    payer_id: str,
    body: dict[str, Any],
    user: CurrentUser = Depends(require_auth),
):
    """Submit a claim directly via payer connector."""
    from modules.operations.payer_connector import payer_registry, ClaimSubmission

    connector = payer_registry.get(payer_id)
    if not connector:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Payer '{payer_id}' not found")

    claim = ClaimSubmission(**body)
    response = await connector.submit_claim(claim)
    return response.model_dump()


@router.post("/payers/{payer_id}/claim-status")
async def payer_claim_status(
    payer_id: str,
    body: dict[str, Any],
    user: CurrentUser = Depends(require_auth),
):
    """Check claim status via payer connector."""
    from modules.operations.payer_connector import payer_registry

    connector = payer_registry.get(payer_id)
    if not connector:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Payer '{payer_id}' not found")

    return await connector.check_claim_status(body.get("claim_id", ""))


# ── Workflow Analytics ───────────────────────────────────────────────────────


@router.post("/analytics/summary")
async def operations_summary(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Generate operations summary report."""
    from modules.operations.agents.workflow_analytics import WorkflowAnalyticsAgent

    agent = WorkflowAnalyticsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.analytics.summary",
        context={"action": "summary", **body},
    ))
    return output.result


@router.post("/analytics/bottlenecks")
async def analyze_bottlenecks(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Identify operational bottlenecks."""
    from modules.operations.agents.workflow_analytics import WorkflowAnalyticsAgent

    agent = WorkflowAnalyticsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.analytics.bottlenecks",
        context={"action": "bottleneck_analysis", **body},
    ))
    return output.result


@router.post("/analytics/kpis")
async def kpi_report(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Generate KPI report."""
    from modules.operations.agents.workflow_analytics import WorkflowAnalyticsAgent

    agent = WorkflowAnalyticsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.analytics.kpis",
        context={"action": "kpi_report", **body},
    ))
    return output.result


@router.post("/analytics/trends")
async def analyze_trends(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Analyze operational trends."""
    from modules.operations.agents.workflow_analytics import WorkflowAnalyticsAgent

    agent = WorkflowAnalyticsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.analytics.trends",
        context={"action": "trend_analysis", **body},
    ))
    return output.result


# ── Legacy Routes (existing) ─────────────────────────────────────────────────


@router.post("/schedule/suggest")
async def suggest_schedule_slots(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get AI-suggested appointment slots."""
    from modules.operations.agents.scheduler import SchedulerAgent

    agent = SchedulerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="operations.schedule.suggest",
        context={"action": "suggest_slots", **body},
    ))
    return output.result


@router.post("/compliance/check")
async def run_compliance_check(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Run compliance audit check."""
    from modules.operations.agents.compliance_monitor import ComplianceMonitorAgent

    agent = ComplianceMonitorAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.compliance.check",
        context=body,
    ))
    return output.result


@router.post("/resources/optimize")
async def optimize_resources(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_role("admin")),
):
    """Run resource optimization analysis."""
    from modules.operations.agents.resource_optimizer import ResourceOptimizerAgent

    agent = ResourceOptimizerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="operations.resources.optimize",
        context=body,
    ))
    return output.result
