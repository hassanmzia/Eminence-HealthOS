"""
Eminence HealthOS — Workflow Engine
Manages complex multi-step workflows with dependency tracking, state
transitions, retries, and SLA enforcement. Provides a lightweight
alternative to Temporal for internal operational workflows.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("healthos.workflow.engine")


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class WorkflowStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    step_id: str = Field(default_factory=lambda: f"STEP-{uuid.uuid4().hex[:8]}")
    name: str
    agent_name: str
    action: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)  # step_ids
    retry_count: int = 0
    max_retries: int = 2
    timeout_minutes: int = 60
    sla_hours: float = 24
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkflowDefinition(BaseModel):
    """A complete workflow with steps and metadata."""

    workflow_id: str = Field(default_factory=lambda: f"WF-{uuid.uuid4().hex[:12]}")
    name: str
    workflow_type: str
    org_id: str
    patient_id: str | None = None
    priority: str = "normal"
    status: WorkflowStatus = WorkflowStatus.CREATED
    steps: list[WorkflowStep] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

WORKFLOW_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "new_patient_intake": [
        {"name": "Verify Insurance", "agent_name": "insurance_verification", "action": "verify_eligibility", "sla_hours": 2},
        {"name": "Check Benefits", "agent_name": "insurance_verification", "action": "check_benefits", "depends_on_index": [0], "sla_hours": 4},
        {"name": "Collect Demographics", "agent_name": "task_orchestration", "action": "create_task", "sla_hours": 8},
        {"name": "Schedule Initial Visit", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [0, 2], "sla_hours": 24},
        {"name": "Assign Care Team", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [3], "sla_hours": 24},
    ],
    "surgical_prep": [
        {"name": "Verify Surgical Coverage", "agent_name": "insurance_verification", "action": "verify_eligibility", "sla_hours": 4},
        {"name": "Submit Prior Authorization", "agent_name": "prior_authorization", "action": "submit", "depends_on_index": [0], "sla_hours": 48},
        {"name": "Estimate Patient Cost", "agent_name": "insurance_verification", "action": "estimate_cost", "depends_on_index": [0], "sla_hours": 8},
        {"name": "Schedule Pre-Op", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [1], "sla_hours": 72},
        {"name": "Prepare Consent Forms", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [3], "sla_hours": 24},
        {"name": "Coordinate Surgical Team", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [1, 3], "sla_hours": 48},
    ],
    "specialist_referral": [
        {"name": "Verify Specialist Coverage", "agent_name": "insurance_verification", "action": "verify_eligibility", "sla_hours": 4},
        {"name": "Create Referral", "agent_name": "referral_coordination", "action": "create", "depends_on_index": [0], "sla_hours": 8},
        {"name": "Match Specialist", "agent_name": "referral_coordination", "action": "match_specialist", "depends_on_index": [1], "sla_hours": 24},
        {"name": "Schedule Specialist Visit", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [2], "sla_hours": 48},
        {"name": "Send Clinical Summary", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [1], "sla_hours": 24},
    ],
    "discharge_follow_up": [
        {"name": "Prepare Discharge Summary", "agent_name": "task_orchestration", "action": "create_task", "sla_hours": 4},
        {"name": "Review Billing", "agent_name": "billing_readiness", "action": "validate", "sla_hours": 24},
        {"name": "Schedule Follow-Up", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [0], "sla_hours": 48},
        {"name": "Notify PCP", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [0], "sla_hours": 24},
        {"name": "Patient Education", "agent_name": "task_orchestration", "action": "create_task", "depends_on_index": [0], "sla_hours": 8},
    ],
    "claim_submission": [
        {"name": "Validate Encounter", "agent_name": "billing_readiness", "action": "validate", "sla_hours": 4},
        {"name": "Check Coding", "agent_name": "billing_readiness", "action": "check_coding", "depends_on_index": [0], "sla_hours": 4},
        {"name": "Verify Insurance", "agent_name": "insurance_verification", "action": "verify_eligibility", "sla_hours": 4},
        {"name": "Check Prior Auth", "agent_name": "prior_authorization", "action": "check_status", "depends_on_index": [2], "sla_hours": 8},
        {"name": "Prepare Claim", "agent_name": "billing_readiness", "action": "prepare_claim", "depends_on_index": [0, 1, 2], "sla_hours": 8},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class WorkflowEngine:
    """
    Manages workflow lifecycle: creation, step execution, dependency resolution,
    and state transitions.
    """

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def create_workflow(
        self,
        workflow_type: str,
        org_id: str,
        patient_id: str | None = None,
        priority: str = "normal",
        context: dict[str, Any] | None = None,
        custom_steps: list[dict[str, Any]] | None = None,
    ) -> WorkflowDefinition:
        """Create a new workflow from a template or custom steps."""
        template_steps = custom_steps or WORKFLOW_TEMPLATES.get(workflow_type, [])
        if not template_steps:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # Build workflow steps with dependency resolution
        steps: list[WorkflowStep] = []
        for i, tpl in enumerate(template_steps):
            dep_indices = tpl.get("depends_on_index", [])
            depends_on = [steps[idx].step_id for idx in dep_indices if idx < len(steps)]

            step = WorkflowStep(
                name=tpl["name"],
                agent_name=tpl["agent_name"],
                action=tpl["action"],
                input_data=tpl.get("input_data", {}),
                depends_on=depends_on,
                sla_hours=tpl.get("sla_hours", 24),
                max_retries=tpl.get("max_retries", 2),
                timeout_minutes=tpl.get("timeout_minutes", 60),
                status=StepStatus.READY if not depends_on else StepStatus.PENDING,
            )
            steps.append(step)

        workflow = WorkflowDefinition(
            name=f"{workflow_type.replace('_', ' ').title()} Workflow",
            workflow_type=workflow_type,
            org_id=org_id,
            patient_id=patient_id,
            priority=priority,
            status=WorkflowStatus.ACTIVE,
            steps=steps,
            context=context or {},
        )

        self._workflows[workflow.workflow_id] = workflow
        logger.info(
            "workflow.created",
            extra={
                "workflow_id": workflow.workflow_id,
                "type": workflow_type,
                "steps": len(steps),
            },
        )

        return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)

    def get_ready_steps(self, workflow_id: str) -> list[WorkflowStep]:
        """Get all steps that are ready to execute (dependencies met)."""
        workflow = self._workflows.get(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.ACTIVE:
            return []

        completed_ids = {
            s.step_id for s in workflow.steps if s.status == StepStatus.COMPLETED
        }

        ready = []
        for step in workflow.steps:
            if step.status == StepStatus.PENDING:
                if all(dep in completed_ids for dep in step.depends_on):
                    step.status = StepStatus.READY
                    ready.append(step)
            elif step.status == StepStatus.READY:
                ready.append(step)

        return ready

    def start_step(self, workflow_id: str, step_id: str) -> WorkflowStep | None:
        """Mark a step as in-progress."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        for step in workflow.steps:
            if step.step_id == step_id and step.status == StepStatus.READY:
                step.status = StepStatus.IN_PROGRESS
                step.started_at = datetime.now(timezone.utc)
                workflow.updated_at = datetime.now(timezone.utc)
                return step

        return None

    def complete_step(
        self, workflow_id: str, step_id: str, output: dict[str, Any]
    ) -> WorkflowStep | None:
        """Mark a step as completed with output data."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        for step in workflow.steps:
            if step.step_id == step_id and step.status == StepStatus.IN_PROGRESS:
                step.status = StepStatus.COMPLETED
                step.output = output
                step.completed_at = datetime.now(timezone.utc)
                workflow.updated_at = datetime.now(timezone.utc)

                # Check if workflow is complete
                if all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in workflow.steps):
                    workflow.status = WorkflowStatus.COMPLETED
                    workflow.completed_at = datetime.now(timezone.utc)

                return step

        return None

    def fail_step(
        self, workflow_id: str, step_id: str, error: str
    ) -> WorkflowStep | None:
        """Mark a step as failed with retry logic."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        for step in workflow.steps:
            if step.step_id == step_id:
                step.retry_count += 1
                if step.retry_count <= step.max_retries:
                    step.status = StepStatus.READY  # retry
                    step.error = f"Retry {step.retry_count}/{step.max_retries}: {error}"
                else:
                    step.status = StepStatus.FAILED
                    step.error = error
                    workflow.status = WorkflowStatus.FAILED
                    workflow.updated_at = datetime.now(timezone.utc)
                return step

        return None

    def get_workflow_summary(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a summary of workflow status."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        step_counts = {}
        for step in workflow.steps:
            status = step.status.value
            step_counts[status] = step_counts.get(status, 0) + 1

        total = len(workflow.steps)
        completed = step_counts.get("completed", 0) + step_counts.get("skipped", 0)

        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "workflow_type": workflow.workflow_type,
            "status": workflow.status.value,
            "priority": workflow.priority,
            "patient_id": workflow.patient_id,
            "progress": round(completed / total, 2) if total else 0,
            "total_steps": total,
            "step_counts": step_counts,
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "agent": s.agent_name,
                    "status": s.status.value,
                    "depends_on": s.depends_on,
                    "error": s.error,
                    "retry_count": s.retry_count,
                }
                for s in workflow.steps
            ],
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        }

    def list_workflows(
        self, org_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        """List all workflows for an organization."""
        results = []
        for wf in self._workflows.values():
            if wf.org_id == org_id:
                if status and wf.status.value != status:
                    continue
                total = len(wf.steps)
                completed = sum(
                    1 for s in wf.steps
                    if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
                )
                results.append({
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "workflow_type": wf.workflow_type,
                    "status": wf.status.value,
                    "priority": wf.priority,
                    "patient_id": wf.patient_id,
                    "progress": round(completed / total, 2) if total else 0,
                    "total_steps": total,
                    "created_at": wf.created_at.isoformat(),
                })
        return results

    def check_sla_violations(self, org_id: str) -> list[dict[str, Any]]:
        """Check for SLA violations across active workflows."""
        violations = []
        now = datetime.now(timezone.utc)

        for wf in self._workflows.values():
            if wf.org_id != org_id or wf.status != WorkflowStatus.ACTIVE:
                continue
            for step in wf.steps:
                if step.status in (StepStatus.READY, StepStatus.IN_PROGRESS):
                    deadline = wf.created_at + timedelta(hours=step.sla_hours)
                    if now > deadline:
                        violations.append({
                            "workflow_id": wf.workflow_id,
                            "workflow_name": wf.name,
                            "step_id": step.step_id,
                            "step_name": step.name,
                            "sla_hours": step.sla_hours,
                            "hours_overdue": round((now - deadline).total_seconds() / 3600, 1),
                            "priority": wf.priority,
                        })

        return violations

    @property
    def available_templates(self) -> list[dict[str, Any]]:
        """List all available workflow templates."""
        return [
            {
                "type": wf_type,
                "name": wf_type.replace("_", " ").title(),
                "steps": len(steps),
            }
            for wf_type, steps in WORKFLOW_TEMPLATES.items()
        ]


# Module-level singleton
workflow_engine = WorkflowEngine()
