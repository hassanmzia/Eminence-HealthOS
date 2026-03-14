"""
Eminence HealthOS — Task Orchestration Agent
Layer 4 (Action): Manages and coordinates operational tasks across the
operations module. Handles workflow creation, task assignment, priority
management, dependency tracking, and SLA monitoring.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger("healthos.agent.task_orchestration")


# Task type definitions with default SLAs (hours)
TASK_SLAS = {
    "prior_auth": {"urgent": 4, "normal": 24, "low": 72},
    "insurance_verification": {"urgent": 2, "normal": 8, "low": 24},
    "referral": {"urgent": 4, "normal": 24, "low": 48},
    "scheduling": {"urgent": 1, "normal": 8, "low": 24},
    "documentation": {"urgent": 4, "normal": 24, "low": 72},
    "billing_review": {"urgent": 8, "normal": 48, "low": 120},
    "care_coordination": {"urgent": 2, "normal": 12, "low": 48},
    "default": {"urgent": 4, "normal": 24, "low": 72},
}

# Auto-assignment rules by task type
ASSIGNMENT_RULES = {
    "prior_auth": "auth_specialist",
    "insurance_verification": "billing_team",
    "referral": "care_coordinator",
    "scheduling": "front_desk",
    "documentation": "medical_records",
    "billing_review": "billing_team",
    "care_coordination": "care_coordinator",
}


class TaskOrchestrationAgent(BaseAgent):
    """Orchestrates operational tasks, workflows, and SLA tracking."""

    name = "task_orchestration"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Manages operational workflows, task assignment, and SLA monitoring"
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "create_task")

        if action == "create_task":
            return await self._create_task(input_data)
        elif action == "create_workflow":
            return self._create_workflow(input_data)
        elif action == "assign":
            return self._assign_task(input_data)
        elif action == "update_status":
            return self._update_task_status(input_data)
        elif action == "check_sla":
            return self._check_sla_compliance(input_data)
        elif action == "get_queue":
            return self._get_task_queue(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown task orchestration action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _create_task(self, input_data: AgentInput) -> AgentOutput:
        """Create a new operational task."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "")
        task_type = ctx.get("task_type", "default")
        priority = ctx.get("priority", "normal")
        title = ctx.get("title", "")
        description = ctx.get("description", "")
        dependencies = ctx.get("dependencies", [])
        metadata = ctx.get("metadata", {})

        if not title:
            title = f"{task_type.replace('_', ' ').title()} Task"

        # Calculate SLA deadline
        sla_hours = TASK_SLAS.get(task_type, TASK_SLAS["default"]).get(priority, 24)
        sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

        # Auto-assign based on task type
        suggested_assignee = ASSIGNMENT_RULES.get(task_type, "operations_team")

        task_id = f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # --- LLM: generate task narrative ---
        task_narrative: str | None = None
        try:
            deps_text = ", ".join(dependencies) if dependencies else "None"
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Explain the prioritization and assignment rationale for this "
                    f"operational task.\n\n"
                    f"Task: {title}\n"
                    f"Type: {task_type}\n"
                    f"Description: {description}\n"
                    f"Priority: {priority}\n"
                    f"SLA: {sla_hours} hours\n"
                    f"Suggested assignee: {suggested_assignee}\n"
                    f"Dependencies: {deps_text}\n\n"
                    f"Provide a brief rationale for the priority level, assignment, "
                    f"and any sequencing considerations."
                )}],
                system=(
                    "You are an operations workflow advisor for Eminence HealthOS. "
                    "Explain task prioritization and assignment decisions clearly "
                    "and concisely for the operations team."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            task_narrative = resp.content
        except Exception:
            logger.warning("LLM task_narrative generation failed; continuing without it")

        result = {
            "task_id": task_id,
            "task_type": task_type,
            "title": title,
            "description": description,
            "patient_id": patient_id,
            "priority": priority,
            "status": "pending",
            "suggested_assignee": suggested_assignee,
            "sla_deadline": sla_deadline.isoformat(),
            "sla_hours": sla_hours,
            "dependencies": dependencies,
            "dependencies_met": len(dependencies) == 0,
            "metadata": metadata,
            "task_narrative": task_narrative,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=(
                f"Task {task_id} created: {title} — {priority} priority, "
                f"SLA: {sla_hours}h, suggested assignee: {suggested_assignee}"
            ),
        )

    def _create_workflow(self, input_data: AgentInput) -> AgentOutput:
        """Create a multi-step workflow with ordered tasks."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "")
        workflow_type = ctx.get("workflow_type", "")
        priority = ctx.get("priority", "normal")

        # Pre-built workflow templates
        templates = {
            "new_patient_intake": [
                {"task_type": "insurance_verification", "title": "Verify insurance coverage"},
                {"task_type": "documentation", "title": "Collect patient demographics"},
                {"task_type": "scheduling", "title": "Schedule initial appointment"},
                {"task_type": "care_coordination", "title": "Assign care team"},
            ],
            "surgical_prep": [
                {"task_type": "insurance_verification", "title": "Verify surgical coverage"},
                {"task_type": "prior_auth", "title": "Submit prior authorization"},
                {"task_type": "scheduling", "title": "Schedule pre-op appointment"},
                {"task_type": "documentation", "title": "Prepare surgical consent forms"},
                {"task_type": "care_coordination", "title": "Coordinate with surgical team"},
            ],
            "specialist_referral": [
                {"task_type": "insurance_verification", "title": "Verify specialist coverage"},
                {"task_type": "referral", "title": "Create and send referral"},
                {"task_type": "scheduling", "title": "Schedule specialist appointment"},
                {"task_type": "care_coordination", "title": "Send clinical summary to specialist"},
            ],
            "discharge_follow_up": [
                {"task_type": "scheduling", "title": "Schedule follow-up appointment"},
                {"task_type": "documentation", "title": "Prepare discharge summary"},
                {"task_type": "care_coordination", "title": "Notify primary care provider"},
                {"task_type": "billing_review", "title": "Review billing for stay"},
            ],
        }

        steps = ctx.get("steps") or templates.get(workflow_type, [])
        if not steps:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown workflow type: {workflow_type}"},
                confidence=0.0,
                rationale=f"No template found for workflow type: {workflow_type}",
                status=AgentStatus.FAILED,
            )

        workflow_id = f"WF-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Build tasks with sequential dependencies
        tasks = []
        for i, step in enumerate(steps):
            task_type = step.get("task_type", "default")
            sla_hours = TASK_SLAS.get(task_type, TASK_SLAS["default"]).get(priority, 24)
            tasks.append({
                "task_id": f"{workflow_id}-T{i+1:02d}",
                "sequence": i + 1,
                "task_type": task_type,
                "title": step.get("title", f"Step {i+1}"),
                "priority": priority,
                "status": "pending" if i > 0 else "ready",
                "depends_on": f"{workflow_id}-T{i:02d}" if i > 0 else None,
                "sla_hours": sla_hours,
                "suggested_assignee": ASSIGNMENT_RULES.get(task_type, "operations_team"),
            })

        total_sla = sum(t["sla_hours"] for t in tasks)

        result = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type or "custom",
            "patient_id": patient_id,
            "priority": priority,
            "status": "active",
            "total_steps": len(tasks),
            "completed_steps": 0,
            "tasks": tasks,
            "total_sla_hours": total_sla,
            "estimated_completion": (
                datetime.now(timezone.utc) + timedelta(hours=total_sla)
            ).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=(
                f"Workflow {workflow_id} created: {len(tasks)} steps, "
                f"total SLA {total_sla}h, type: {workflow_type or 'custom'}"
            ),
        )

    def _assign_task(self, input_data: AgentInput) -> AgentOutput:
        """Assign or reassign a task to a team member."""
        ctx = input_data.context
        task_id = ctx.get("task_id", "")
        assignee = ctx.get("assignee", "")

        result = {
            "task_id": task_id,
            "assignee": assignee,
            "status": "assigned",
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Task {task_id} assigned to {assignee}",
        )

    def _update_task_status(self, input_data: AgentInput) -> AgentOutput:
        """Update task status and handle workflow progression."""
        ctx = input_data.context
        task_id = ctx.get("task_id", "")
        new_status = ctx.get("status", "")
        notes = ctx.get("notes", "")

        # Determine downstream effects
        triggers = []
        if new_status == "completed":
            triggers.append("Check dependent tasks for readiness")
            triggers.append("Update workflow progress")
        elif new_status == "blocked":
            triggers.append("Escalate to supervisor")
            triggers.append("Notify workflow owner")

        result = {
            "task_id": task_id,
            "previous_status": "in_progress",
            "new_status": new_status,
            "notes": notes,
            "triggered_actions": triggers,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Task {task_id} status updated to {new_status}",
        )

    def _check_sla_compliance(self, input_data: AgentInput) -> AgentOutput:
        """Check SLA compliance across operational tasks."""
        ctx = input_data.context
        scope = ctx.get("scope", "all")  # all, overdue, at_risk

        # In production, queries task database
        now = datetime.now(timezone.utc)
        summary = {
            "total_open_tasks": 24,
            "on_track": 18,
            "at_risk": 4,
            "overdue": 2,
            "sla_compliance_rate": 0.917,
            "overdue_tasks": [
                {
                    "task_id": "TASK-20260310-001",
                    "title": "Prior auth for MRI",
                    "sla_deadline": (now - timedelta(hours=6)).isoformat(),
                    "hours_overdue": 6,
                    "assignee": "auth_specialist",
                },
                {
                    "task_id": "TASK-20260311-003",
                    "title": "Insurance verification — Johnson",
                    "sla_deadline": (now - timedelta(hours=2)).isoformat(),
                    "hours_overdue": 2,
                    "assignee": "billing_team",
                },
            ],
            "at_risk_tasks": [
                {
                    "task_id": "TASK-20260312-001",
                    "title": "Referral to cardiology",
                    "sla_deadline": (now + timedelta(hours=2)).isoformat(),
                    "hours_remaining": 2,
                    "assignee": "care_coordinator",
                },
            ],
            "checked_at": now.isoformat(),
        }

        compliance = summary["sla_compliance_rate"]
        status = AgentStatus.COMPLETED
        if summary["overdue"] > 0:
            status = AgentStatus.COMPLETED  # still completed but flagged

        return self.build_output(
            trace_id=input_data.trace_id,
            result=summary,
            confidence=0.90,
            rationale=(
                f"SLA compliance: {compliance:.1%} — "
                f"{summary['overdue']} overdue, {summary['at_risk']} at risk"
            ),
            status=status,
        )

    def _get_task_queue(self, input_data: AgentInput) -> AgentOutput:
        """Get the current task queue for an assignee or team."""
        ctx = input_data.context
        assignee = ctx.get("assignee", "")
        status_filter = ctx.get("status", "pending,in_progress")
        limit = ctx.get("limit", 20)

        now = datetime.now(timezone.utc)

        # In production, queries task database
        queue = [
            {
                "task_id": "TASK-20260312-001",
                "title": "Verify insurance — Smith",
                "task_type": "insurance_verification",
                "priority": "urgent",
                "status": "pending",
                "sla_deadline": (now + timedelta(hours=2)).isoformat(),
                "patient_id": "PT-001",
            },
            {
                "task_id": "TASK-20260312-002",
                "title": "Prior auth — CT scan",
                "task_type": "prior_auth",
                "priority": "normal",
                "status": "in_progress",
                "sla_deadline": (now + timedelta(hours=18)).isoformat(),
                "patient_id": "PT-002",
            },
            {
                "task_id": "TASK-20260312-003",
                "title": "Referral follow-up — cardiology",
                "task_type": "referral",
                "priority": "normal",
                "status": "pending",
                "sla_deadline": (now + timedelta(hours=20)).isoformat(),
                "patient_id": "PT-003",
            },
        ]

        result = {
            "assignee": assignee or "all",
            "total_tasks": len(queue),
            "tasks": queue[:limit],
            "retrieved_at": now.isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"Task queue: {len(queue)} task(s) for {assignee or 'all'}",
        )
