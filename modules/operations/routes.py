"""Operations module API routes — prior auth, insurance, referrals, tasks, scheduling, compliance."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.agents.types import AgentInput, parse_patient_id
from healthos_platform.database import get_db
from healthos_platform.models import (
    InsuranceVerification,
    OperationalWorkflow,
    PriorAuthorization,
    Referral,
)
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

logger = logging.getLogger("healthos.routes.operations")
router = APIRouter(prefix="/operations", tags=["operations"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── List Endpoints (DB-backed) ──────────────────────────────────────────────


@router.get("/prior-auth/list")
async def list_prior_authorizations(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """List prior authorization requests for the organization."""
    q = select(PriorAuthorization).where(PriorAuthorization.org_id == DEFAULT_ORG)
    if status:
        q = q.where(PriorAuthorization.status == status)
    q = q.order_by(PriorAuthorization.created_at.desc()).limit(limit)
    result = await db.execute(q)
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "auth_reference": r.auth_reference,
                "patient_id": str(r.patient_id),
                "payer": r.payer,
                "status": r.status,
                "cpt_codes": r.cpt_codes or [],
                "diagnosis_codes": r.diagnosis_codes or [],
                "clinical_summary": r.clinical_summary,
                "estimated_cost": r.estimated_cost,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "decided_at": r.decided_at.isoformat() if r.decided_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/insurance/list")
async def list_insurance_verifications(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """List recent insurance verifications for the organization."""
    q = (
        select(InsuranceVerification)
        .where(InsuranceVerification.org_id == DEFAULT_ORG)
        .order_by(InsuranceVerification.verified_at.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "patient_id": str(r.patient_id),
                "payer": r.payer,
                "member_id": r.member_id,
                "group_number": r.group_number,
                "plan_name": r.plan_name,
                "plan_type": r.plan_type,
                "eligible": r.eligible,
                "coverage_status": r.coverage_status,
                "effective_date": r.effective_date.isoformat() if r.effective_date else None,
                "termination_date": r.termination_date.isoformat() if r.termination_date else None,
                "benefits": r.benefits or {},
                "verified_at": r.verified_at.isoformat() if r.verified_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/referrals/list")
async def list_referrals(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """List referrals for the organization."""
    q = select(Referral).where(Referral.org_id == DEFAULT_ORG)
    if status:
        q = q.where(Referral.status == status)
    q = q.order_by(Referral.created_at.desc()).limit(limit)
    result = await db.execute(q)
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "referral_id": r.referral_id,
                "patient_id": str(r.patient_id),
                "specialty": r.specialty,
                "urgency": r.urgency,
                "reason": r.reason,
                "status": r.status,
                "clinical_notes": r.clinical_notes,
                "specialist_notes": r.specialist_notes,
                "outcome": r.outcome,
                "target_date": r.target_date.isoformat() if r.target_date else None,
                "scheduled_date": r.scheduled_date.isoformat() if r.scheduled_date else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/workflows/list")
async def list_operational_workflows(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """List operational workflows from the database."""
    q = select(OperationalWorkflow).where(OperationalWorkflow.org_id == DEFAULT_ORG)
    if status:
        q = q.where(OperationalWorkflow.status == status)
    q = q.order_by(OperationalWorkflow.created_at.desc()).limit(limit)
    result = await db.execute(q)
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "workflow_id": r.workflow_id,
                "workflow_type": r.workflow_type,
                "name": r.name,
                "status": r.status,
                "priority": r.priority,
                "steps": r.steps or [],
                "total_steps": r.total_steps,
                "completed_steps": r.completed_steps,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
        patient_id=parse_patient_id(body.get("patient_id")),
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
