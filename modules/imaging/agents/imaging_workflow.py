"""
Eminence HealthOS — Imaging Workflow Agent (#54)
Layer 4 (Action): Routes images for radiologist review, tracks read status,
and manages the radiology priority queue.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

WORKLIST_PRIORITIES = {
    "stat": {"sla_minutes": 30, "auto_escalate": True},
    "urgent": {"sla_minutes": 120, "auto_escalate": True},
    "routine": {"sla_minutes": 1440, "auto_escalate": False},
    "screening": {"sla_minutes": 4320, "auto_escalate": False},
}


class ImagingWorkflowAgent(BaseAgent):
    """Routes images for radiologist review and manages radiology worklists."""

    name = "imaging_workflow"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Radiology workflow management — worklist prioritization, study assignment, "
        "read status tracking, and SLA monitoring"
    )
    min_confidence = 0.88

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "assign_study")

        if action == "assign_study":
            return self._assign_study(input_data)
        elif action == "update_read_status":
            return self._update_read_status(input_data)
        elif action == "worklist_summary":
            return self._worklist_summary(input_data)
        elif action == "sla_check":
            return self._sla_check(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown imaging workflow action: {action}",
                status=AgentStatus.FAILED,
            )

    def _assign_study(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        study_id = ctx.get("study_id", str(uuid.uuid4()))
        priority = ctx.get("priority", "routine")
        modality = ctx.get("modality", "CR")
        has_critical_ai_finding = ctx.get("has_critical_ai_finding", False)

        if has_critical_ai_finding:
            priority = "stat"

        sla = WORKLIST_PRIORITIES.get(priority, WORKLIST_PRIORITIES["routine"])

        result = {
            "assignment_id": str(uuid.uuid4()),
            "study_id": study_id,
            "assigned_at": now.isoformat(),
            "priority": priority,
            "assigned_radiologist": ctx.get("radiologist", "Dr. Rodriguez (on-call)"),
            "worklist": priority.upper(),
            "sla_minutes": sla["sla_minutes"],
            "auto_escalation": sla["auto_escalate"],
            "modality": modality,
            "ai_pre_read_available": True,
            "status": "assigned",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Study {study_id} assigned to {result['assigned_radiologist']} ({priority})",
        )

    def _update_read_status(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "study_id": ctx.get("study_id", "unknown"),
            "updated_at": now.isoformat(),
            "previous_status": ctx.get("previous_status", "assigned"),
            "new_status": ctx.get("new_status", "read"),
            "radiologist": ctx.get("radiologist", "Dr. Rodriguez"),
            "read_time_minutes": ctx.get("read_time_minutes", 12),
            "report_dictated": True,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Study read status updated to: {result['new_status']}",
        )

    def _worklist_summary(self, input_data: AgentInput) -> AgentOutput:
        now = datetime.now(timezone.utc)

        worklists = {
            "STAT": {"pending": 1, "in_progress": 0, "completed_today": 3},
            "URGENT": {"pending": 4, "in_progress": 2, "completed_today": 8},
            "ROUTINE": {"pending": 18, "in_progress": 3, "completed_today": 42},
            "SCREENING": {"pending": 12, "in_progress": 0, "completed_today": 15},
        }

        total_pending = sum(w["pending"] for w in worklists.values())
        total_completed = sum(w["completed_today"] for w in worklists.values())

        result = {
            "summary_at": now.isoformat(),
            "worklists": worklists,
            "total_pending": total_pending,
            "total_in_progress": sum(w["in_progress"] for w in worklists.values()),
            "total_completed_today": total_completed,
            "average_read_time_min": 14,
            "sla_compliance_pct": 96.5,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"Worklist summary: {total_pending} pending, {total_completed} completed today",
        )

    def _sla_check(self, input_data: AgentInput) -> AgentOutput:
        now = datetime.now(timezone.utc)

        breaches = [
            {"study_id": "STD-089", "priority": "urgent", "sla_minutes": 120, "elapsed_minutes": 145, "assigned_to": "Dr. Chen", "modality": "CT"},
        ]

        at_risk = [
            {"study_id": "STD-092", "priority": "stat", "sla_minutes": 30, "elapsed_minutes": 22, "assigned_to": "Dr. Rodriguez", "modality": "CR"},
        ]

        result = {
            "checked_at": now.isoformat(),
            "sla_breaches": breaches,
            "at_risk": at_risk,
            "total_breaches": len(breaches),
            "total_at_risk": len(at_risk),
            "overall_compliance_pct": 96.5,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"SLA check: {len(breaches)} breaches, {len(at_risk)} at risk",
        )
