"""
Eminence HealthOS — Audit / Trace Agent
Layer 5 (Measurement): Records a complete decision-chain audit trail for every
pipeline execution.  Captures who did what, when, why, and based on what inputs
— providing full traceability for HIPAA compliance, clinical governance, and
post-hoc analysis.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    PipelineState,
)

logger = structlog.get_logger()


class AuditEntry:
    """A single entry in the decision-chain audit log."""

    def __init__(
        self,
        agent_name: str,
        action: str,
        inputs_summary: dict[str, Any],
        outputs_summary: dict[str, Any],
        confidence: float,
        status: str,
        rationale: str,
        timestamp: str | None = None,
        duration_ms: int = 0,
        requires_hitl: bool = False,
        hitl_reason: str | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.action = action
        self.inputs_summary = inputs_summary
        self.outputs_summary = outputs_summary
        self.confidence = confidence
        self.status = status
        self.rationale = rationale
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.duration_ms = duration_ms
        self.requires_hitl = requires_hitl
        self.hitl_reason = hitl_reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "action": self.action,
            "inputs_summary": self.inputs_summary,
            "outputs_summary": self.outputs_summary,
            "confidence": self.confidence,
            "status": self.status,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "requires_hitl": self.requires_hitl,
            "hitl_reason": self.hitl_reason,
        }


class AuditTraceAgent(BaseAgent):
    """
    Produces a comprehensive audit trail from the pipeline state.

    Records for every executed agent:
    - What agent ran (who)
    - What it decided / produced (what)
    - When it ran (when)
    - Why it made its decisions (rationale)
    - What inputs it used (based on what)
    - Confidence level and HITL status

    Also computes a tamper-evident integrity hash of the full audit log.
    """

    name = "audit_trace"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Records complete decision-chain audit trail for compliance and traceability"
    min_confidence = 0.95

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Build an audit trail from standalone input context."""
        context = input_data.context or {}
        entries = self._build_entries_from_dict(context)
        integrity_hash = self._compute_integrity_hash(entries)

        audit_log = {
            "trace_id": str(input_data.trace_id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entry_count": len(entries),
            "entries": entries,
            "integrity_hash": integrity_hash,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"audit_log": audit_log},
            confidence=0.99,
            rationale=f"Audit trail generated with {len(entries)} entries",
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Build a full audit trail from the completed pipeline state."""
        entries: list[dict[str, Any]] = []

        # Build an audit entry for every executed agent
        for agent_name in state.executed_agents:
            if agent_name == self.name:
                continue  # Don't audit ourselves
            output = state.agent_outputs.get(agent_name)
            if output is None:
                entries.append(self._missing_entry(agent_name))
                continue

            entry = AuditEntry(
                agent_name=agent_name,
                action=f"Executed in pipeline for event '{state.trigger_event}'",
                inputs_summary=self._summarize_inputs(agent_name, state),
                outputs_summary=self._summarize_outputs(output),
                confidence=output.confidence,
                status=output.status.value if hasattr(output.status, "value") else str(output.status),
                rationale=output.rationale,
                duration_ms=output.duration_ms,
                requires_hitl=output.requires_hitl,
                hitl_reason=output.hitl_reason,
            )
            entries.append(entry.to_dict())

        # Record policy violations
        policy_record = {
            "total_violations": len(state.policy_violations),
            "violations": list(state.policy_violations),
        }

        # Compute integrity hash
        integrity_hash = self._compute_integrity_hash(entries)

        audit_log = {
            "trace_id": str(state.trace_id),
            "org_id": str(state.org_id),
            "patient_id": str(state.patient_id),
            "trigger_event": state.trigger_event,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agents_executed": list(state.executed_agents),
            "entry_count": len(entries),
            "entries": entries,
            "policy_record": policy_record,
            "hitl_required": state.requires_hitl,
            "hitl_reason": state.hitl_reason,
            "integrity_hash": integrity_hash,
        }

        # Store on pipeline state
        state.patient_context["audit_log"] = audit_log

        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result={"audit_log": audit_log},
            confidence=0.99,
            rationale=self._build_rationale(entries, state),
        )

        logger.info(
            "audit.trail_generated",
            trace_id=str(state.trace_id),
            entry_count=len(entries),
            integrity_hash=integrity_hash,
        )

        return state

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _summarize_inputs(self, agent_name: str, state: PipelineState) -> dict[str, Any]:
        """Summarize what data was available to the agent at execution time."""
        return {
            "vitals_available": len(state.normalized_vitals),
            "anomalies_available": len(state.anomalies),
            "risk_assessments_available": len(state.risk_assessments),
            "prior_agents": [
                a for a in state.executed_agents if a != agent_name
            ],
            "patient_context_keys": list(state.patient_context.keys())
            if state.patient_context
            else [],
        }

    @staticmethod
    def _summarize_outputs(output: AgentOutput) -> dict[str, Any]:
        """Summarize an agent's outputs for the audit record."""
        result_keys = list(output.result.keys()) if output.result else []
        return {
            "result_keys": result_keys,
            "has_errors": len(output.errors) > 0,
            "error_count": len(output.errors),
            "message_count": len(output.messages),
        }

    @staticmethod
    def _missing_entry(agent_name: str) -> dict[str, Any]:
        """Create a placeholder entry for an agent with no output recorded."""
        return {
            "agent_name": agent_name,
            "action": "Executed but no output recorded",
            "inputs_summary": {},
            "outputs_summary": {},
            "confidence": 0.0,
            "status": "unknown",
            "rationale": "Agent output was not captured in pipeline state",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 0,
            "requires_hitl": False,
            "hitl_reason": None,
        }

    @staticmethod
    def _compute_integrity_hash(entries: list[dict[str, Any]]) -> str:
        """Compute a SHA-256 hash of the audit entries for tamper detection."""
        canonical = json.dumps(entries, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _build_entries_from_dict(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Build audit entries from raw dict context (standalone mode)."""
        entries: list[dict[str, Any]] = []
        agent_outputs = context.get("agent_outputs", {})

        for agent_name, output_data in agent_outputs.items():
            if isinstance(output_data, dict):
                entry = AuditEntry(
                    agent_name=agent_name,
                    action="Executed (reconstructed from context)",
                    inputs_summary={},
                    outputs_summary={"result_keys": list(output_data.get("result", {}).keys())},
                    confidence=output_data.get("confidence", 0.0),
                    status=output_data.get("status", "unknown"),
                    rationale=output_data.get("rationale", ""),
                    duration_ms=output_data.get("duration_ms", 0),
                )
                entries.append(entry.to_dict())

        return entries

    @staticmethod
    def _build_rationale(entries: list[dict[str, Any]], state: PipelineState) -> str:
        hitl_count = sum(1 for e in entries if e.get("requires_hitl"))
        error_count = sum(
            1 for e in entries if e.get("outputs_summary", {}).get("has_errors")
        )
        return (
            f"Audit trail: {len(entries)} agent(s) traced for event "
            f"'{state.trigger_event}', {hitl_count} HITL request(s), "
            f"{error_count} error(s), {len(state.policy_violations)} policy violation(s)"
        )
