"""
Eminence HealthOS — Human-in-the-Loop (HITL) Agent
Layer 3 (Decisioning): Evaluates pipeline state to determine when human review
is required.  Aggregates confidence scores, policy violations, and governance
rules to produce explicit HITL review requests with structured context for
the reviewing clinician or administrator.
"""

from __future__ import annotations

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
    Severity,
)

logger = structlog.get_logger()


# ── Default HITL Thresholds ───────────────────────────────────────────────────

DEFAULT_HITL_CONFIG: dict[str, Any] = {
    # Confidence below which an agent's output should trigger review
    "confidence_threshold": 0.70,
    # Number of low-confidence agents that triggers mandatory review
    "low_confidence_agent_limit": 2,
    # Always require HITL for these decision categories
    "mandatory_review_categories": [
        "medication_change",
        "care_plan_change",
        "discharge",
        "emergency_escalation",
    ],
    # Risk score above which HITL is always required
    "risk_hitl_threshold": 0.80,
    # Maximum policy violations before mandatory review
    "max_policy_violations": 3,
}


class HITLReviewRequest:
    """Structured HITL review request for the reviewing clinician."""

    def __init__(
        self,
        request_id: str,
        patient_id: str,
        urgency: str,
        reason: str,
        summary: str,
        review_items: list[dict[str, Any]],
        context_snapshot: dict[str, Any],
    ) -> None:
        self.request_id = request_id
        self.patient_id = patient_id
        self.urgency = urgency
        self.reason = reason
        self.summary = summary
        self.review_items = review_items
        self.context_snapshot = context_snapshot
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "patient_id": self.patient_id,
            "urgency": self.urgency,
            "reason": self.reason,
            "summary": self.summary,
            "review_items": self.review_items,
            "context_snapshot": self.context_snapshot,
            "created_at": self.created_at,
        }


class HumanInTheLoopAgent(BaseAgent):
    """
    Evaluates whether the current pipeline execution requires human review.

    Checks:
    1. Agent confidence scores below threshold
    2. Policy violations exceeding limits
    3. Mandatory review categories (medication changes, etc.)
    4. High-risk patient scores
    5. Explicit HITL flags set by upstream agents

    When review is required, produces a structured HITLReviewRequest with
    all relevant context for the reviewer.
    """

    name = "hitl"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Determines when human review is required and builds structured review requests"
    min_confidence = 0.90

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.config = config or DEFAULT_HITL_CONFIG

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Evaluate HITL need from standalone input context."""
        context = input_data.context or {}
        triggers = self._evaluate_from_dict(context)
        requires_review = len(triggers) > 0

        review_request = None
        if requires_review:
            review_request = HITLReviewRequest(
                request_id=str(uuid.uuid4()),
                patient_id=str(input_data.patient_id or ""),
                urgency=self._compute_urgency(triggers),
                reason=self._summarize_triggers(triggers),
                summary=self._build_review_summary(triggers, context),
                review_items=triggers,
                context_snapshot=context,
            ).to_dict()

        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            status=AgentStatus.WAITING_HITL if requires_review else AgentStatus.COMPLETED,
            confidence=0.95,
            result={
                "requires_review": requires_review,
                "trigger_count": len(triggers),
                "triggers": triggers,
                "review_request": review_request,
            },
            rationale=self._summarize_triggers(triggers) if triggers else "No HITL review required",
            requires_hitl=requires_review,
            hitl_reason=self._summarize_triggers(triggers) if requires_review else None,
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Evaluate the full pipeline state for HITL requirements."""
        triggers: list[dict[str, Any]] = []

        # 1. Check for low-confidence agent outputs
        triggers.extend(self._check_confidence(state))

        # 2. Check policy violations
        triggers.extend(self._check_policy_violations(state))

        # 3. Check high-risk patients
        triggers.extend(self._check_risk_scores(state))

        # 4. Check for mandatory review categories
        triggers.extend(self._check_mandatory_categories(state))

        # 5. Check explicit upstream HITL flags
        triggers.extend(self._check_upstream_flags(state))

        requires_review = len(triggers) > 0

        review_request = None
        if requires_review:
            review_request = HITLReviewRequest(
                request_id=str(uuid.uuid4()),
                patient_id=str(state.patient_id),
                urgency=self._compute_urgency(triggers),
                reason=self._summarize_triggers(triggers),
                summary=self._build_review_summary_from_state(triggers, state),
                review_items=triggers,
                context_snapshot={
                    "executed_agents": list(state.executed_agents),
                    "policy_violations": list(state.policy_violations),
                    "anomaly_count": len(state.anomalies),
                    "risk_count": len(state.risk_assessments),
                },
            ).to_dict()

            state.requires_hitl = True
            state.hitl_reason = self._summarize_triggers(triggers)

        # Store review request in patient context for downstream access
        state.patient_context["hitl_review"] = {
            "requires_review": requires_review,
            "triggers": triggers,
            "review_request": review_request,
        }

        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result={
                "requires_review": requires_review,
                "trigger_count": len(triggers),
                "triggers": triggers,
                "review_request": review_request,
            },
            confidence=0.95,
            rationale=self._summarize_triggers(triggers) if triggers else "No HITL review required",
            status=AgentStatus.WAITING_HITL if requires_review else AgentStatus.COMPLETED,
        )

        return state

    # ── Check Methods ─────────────────────────────────────────────────────────

    def _check_confidence(self, state: PipelineState) -> list[dict[str, Any]]:
        """Flag agents with confidence below threshold."""
        triggers: list[dict[str, Any]] = []
        threshold = self.config.get("confidence_threshold", 0.70)

        low_confidence_agents = []
        for agent_name, output in state.agent_outputs.items():
            if output.confidence < threshold:
                low_confidence_agents.append({
                    "agent": agent_name,
                    "confidence": output.confidence,
                })

        limit = self.config.get("low_confidence_agent_limit", 2)
        if len(low_confidence_agents) >= limit:
            triggers.append({
                "type": "low_confidence",
                "severity": "high",
                "description": (
                    f"{len(low_confidence_agents)} agents below confidence threshold "
                    f"{threshold}: {', '.join(a['agent'] for a in low_confidence_agents)}"
                ),
                "data": {"agents": low_confidence_agents, "threshold": threshold},
            })
        elif low_confidence_agents:
            triggers.append({
                "type": "low_confidence",
                "severity": "moderate",
                "description": (
                    f"Agent(s) below confidence threshold: "
                    f"{', '.join(a['agent'] for a in low_confidence_agents)}"
                ),
                "data": {"agents": low_confidence_agents, "threshold": threshold},
            })

        return triggers

    def _check_policy_violations(self, state: PipelineState) -> list[dict[str, Any]]:
        """Flag when policy violations exceed limits."""
        triggers: list[dict[str, Any]] = []
        max_violations = self.config.get("max_policy_violations", 3)

        if len(state.policy_violations) >= max_violations:
            triggers.append({
                "type": "policy_violations",
                "severity": "critical",
                "description": (
                    f"{len(state.policy_violations)} policy violations exceed "
                    f"limit of {max_violations}"
                ),
                "data": {"violations": list(state.policy_violations)},
            })

        return triggers

    def _check_risk_scores(self, state: PipelineState) -> list[dict[str, Any]]:
        """Flag high-risk patients requiring clinician review."""
        triggers: list[dict[str, Any]] = []
        threshold = self.config.get("risk_hitl_threshold", 0.80)

        for assessment in state.risk_assessments:
            if assessment.score >= threshold:
                triggers.append({
                    "type": "high_risk",
                    "severity": "critical",
                    "description": (
                        f"Patient risk score {assessment.score:.2f} "
                        f"({assessment.score_type}) exceeds HITL threshold {threshold}"
                    ),
                    "data": {
                        "score": assessment.score,
                        "score_type": assessment.score_type,
                        "risk_level": assessment.risk_level.value
                        if hasattr(assessment.risk_level, "value")
                        else str(assessment.risk_level),
                    },
                })

        return triggers

    def _check_mandatory_categories(self, state: PipelineState) -> list[dict[str, Any]]:
        """Check if the pipeline involves categories that always require review."""
        triggers: list[dict[str, Any]] = []
        mandatory = self.config.get("mandatory_review_categories", [])

        # Check trigger event against mandatory categories
        event = state.trigger_event.lower()
        for category in mandatory:
            if category.replace("_", ".") in event or category in event:
                triggers.append({
                    "type": "mandatory_category",
                    "severity": "high",
                    "description": f"Event '{state.trigger_event}' matches mandatory review category '{category}'",
                    "data": {"category": category, "event": state.trigger_event},
                })

        return triggers

    def _check_upstream_flags(self, state: PipelineState) -> list[dict[str, Any]]:
        """Collect any explicit HITL requests from upstream agent outputs."""
        triggers: list[dict[str, Any]] = []

        for agent_name, output in state.agent_outputs.items():
            if agent_name == self.name:
                continue
            if output.requires_hitl and output.hitl_reason:
                triggers.append({
                    "type": "upstream_flag",
                    "severity": "high",
                    "description": f"Agent '{agent_name}' requested HITL: {output.hitl_reason}",
                    "data": {"agent": agent_name, "reason": output.hitl_reason},
                })

        return triggers

    # ── Utility Methods ───────────────────────────────────────────────────────

    def _evaluate_from_dict(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Evaluate HITL need from raw dict context (standalone mode)."""
        triggers: list[dict[str, Any]] = []

        # Check risk scores
        threshold = self.config.get("risk_hitl_threshold", 0.80)
        for r in context.get("risk_assessments", []):
            score = r.get("score", 0.0) if isinstance(r, dict) else 0.0
            if score >= threshold:
                triggers.append({
                    "type": "high_risk",
                    "severity": "critical",
                    "description": f"Risk score {score:.2f} exceeds HITL threshold",
                    "data": {"score": score},
                })

        # Check policy violations
        violations = context.get("policy_violations", [])
        max_violations = self.config.get("max_policy_violations", 3)
        if len(violations) >= max_violations:
            triggers.append({
                "type": "policy_violations",
                "severity": "critical",
                "description": f"{len(violations)} policy violations",
                "data": {"violations": violations},
            })

        return triggers

    @staticmethod
    def _compute_urgency(triggers: list[dict[str, Any]]) -> str:
        """Compute overall urgency from trigger severities."""
        severities = [t.get("severity", "moderate") for t in triggers]
        if "critical" in severities:
            return "stat"  # Immediate clinician review
        if "high" in severities:
            return "urgent"
        return "routine"

    @staticmethod
    def _summarize_triggers(triggers: list[dict[str, Any]]) -> str:
        if not triggers:
            return "No HITL triggers"
        parts = [t["description"] for t in triggers[:5]]
        suffix = f" (+{len(triggers) - 5} more)" if len(triggers) > 5 else ""
        return "; ".join(parts) + suffix

    @staticmethod
    def _build_review_summary(
        triggers: list[dict[str, Any]], context: dict[str, Any]
    ) -> str:
        return (
            f"{len(triggers)} review trigger(s) identified. "
            f"Context keys: {', '.join(context.keys()) if context else 'none'}"
        )

    @staticmethod
    def _build_review_summary_from_state(
        triggers: list[dict[str, Any]], state: PipelineState
    ) -> str:
        return (
            f"{len(triggers)} review trigger(s) after {len(state.executed_agents)} "
            f"agents executed. {len(state.anomalies)} anomalies, "
            f"{len(state.risk_assessments)} risk assessments, "
            f"{len(state.policy_violations)} policy violations."
        )
