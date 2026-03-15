"""
Eminence HealthOS — Agent Audit Logger
Structured audit logging for all agent actions, decisions, and data access.
Supports HIPAA compliance requirements for audit trails.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


class AuditEntry:
    """A single audit log entry."""

    def __init__(
        self,
        trace_id: str,
        agent_name: str,
        action: str,
        resource_type: str,
        resource_id: str = "",
        patient_id: str = "",
        org_id: str = "",
        user_id: str = "",
        details: dict[str, Any] | None = None,
        outcome: str = "success",
        phi_accessed: bool = False,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.patient_id = patient_id
        self.org_id = org_id
        self.user_id = user_id
        self.details = details or {}
        self.outcome = outcome
        self.phi_accessed = phi_accessed

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "patient_id": self.patient_id,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "details": self.details,
            "outcome": self.outcome,
            "phi_accessed": self.phi_accessed,
        }


class AgentAuditLogger:
    """
    Centralized audit logger for agent actions.
    Logs to structured log output and optionally persists to database.
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="audit_logger")
        self._entries: list[AuditEntry] = []

    def log_action(
        self,
        trace_id: str,
        agent_name: str,
        action: str,
        resource_type: str,
        resource_id: str = "",
        patient_id: str = "",
        org_id: str = "",
        user_id: str = "",
        details: dict[str, Any] | None = None,
        outcome: str = "success",
        phi_accessed: bool = False,
    ) -> AuditEntry:
        """Log an agent action to the audit trail."""
        entry = AuditEntry(
            trace_id=trace_id,
            agent_name=agent_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            org_id=org_id,
            user_id=user_id,
            details=details,
            outcome=outcome,
            phi_accessed=phi_accessed,
        )

        self._entries.append(entry)

        self._log.info(
            "audit.action",
            audit_id=entry.id,
            trace_id=trace_id,
            agent=agent_name,
            action=action,
            resource=f"{resource_type}/{resource_id}",
            outcome=outcome,
            phi_accessed=phi_accessed,
        )

        return entry

    def log_data_access(
        self,
        trace_id: str,
        agent_name: str,
        resource_type: str,
        resource_id: str,
        patient_id: str,
        org_id: str = "",
        access_type: str = "read",
    ) -> AuditEntry:
        """Log a data access event (HIPAA requirement)."""
        return self.log_action(
            trace_id=trace_id,
            agent_name=agent_name,
            action=f"data_{access_type}",
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            org_id=org_id,
            details={"access_type": access_type},
            phi_accessed=True,
        )

    def log_decision(
        self,
        trace_id: str,
        agent_name: str,
        decision: str,
        confidence: float,
        rationale: str,
        patient_id: str = "",
        requires_hitl: bool = False,
    ) -> AuditEntry:
        """Log an agent clinical decision."""
        return self.log_action(
            trace_id=trace_id,
            agent_name=agent_name,
            action="clinical_decision",
            resource_type="decision",
            details={
                "decision": decision,
                "confidence": confidence,
                "rationale": rationale,
                "requires_hitl": requires_hitl,
            },
            patient_id=patient_id,
        )

    def log_error(
        self,
        trace_id: str,
        agent_name: str,
        error: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Log an agent error."""
        return self.log_action(
            trace_id=trace_id,
            agent_name=agent_name,
            action="error",
            resource_type="agent",
            details={"error": error, **(details or {})},
            outcome="failure",
        )

    def get_entries(
        self,
        trace_id: str | None = None,
        agent_name: str | None = None,
        patient_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query audit entries with optional filters."""
        filtered = self._entries

        if trace_id:
            filtered = [e for e in filtered if e.trace_id == trace_id]
        if agent_name:
            filtered = [e for e in filtered if e.agent_name == agent_name]
        if patient_id:
            filtered = [e for e in filtered if e.patient_id == patient_id]

        return [e.to_dict() for e in filtered[-limit:]]


# Module-level singleton
audit_logger = AgentAuditLogger()
