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
router = APIRouter()

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
