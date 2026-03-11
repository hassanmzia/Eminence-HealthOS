"""
Eminence HealthOS — Policy / Rules Agent
Layer 3 (Decisioning): Validates agent decisions against configurable
clinical policies, organizational guardrails, and regulatory rules.
Flags violations and can halt pipelines when safety thresholds are breached.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    AlertType,
    PipelineState,
    Severity,
)

logger = structlog.get_logger()


# ── Default Clinical Policy Thresholds ────────────────────────────────────────

DEFAULT_POLICIES: dict[str, Any] = {
    # Risk score thresholds for escalation
    "risk_escalation": {
        "critical_threshold": 0.75,
        "high_threshold": 0.50,
        "auto_escalate_critical": True,
        "require_hitl_above": 0.80,
    },
    # Anomaly policies
    "anomaly_rules": {
        "max_unresolved_critical": 2,  # Flag if > N unresolved critical anomalies
        "multi_vital_escalation": True,  # Escalate if multiple vital types affected
        "escalation_vital_count": 3,
    },
    # Alert policies
    "alert_rules": {
        "max_pending_critical_alerts": 3,
        "auto_assign_critical": True,
        "escalation_timeout_minutes": 30,
    },
    # Agent governance
    "agent_governance": {
        "require_hitl_for_medication_changes": True,
        "require_hitl_for_care_plan_changes": True,
        "min_confidence_for_auto_action": 0.85,
        "max_pipeline_duration_seconds": 60,
    },
    # Regulatory compliance
    "compliance": {
        "phi_audit_required": True,
        "consent_check_required": True,
        "data_retention_days": 2555,  # 7 years for HIPAA
    },
}


class PolicyRulesAgent(BaseAgent):
    """
    Validates pipeline state and agent outputs against configurable policies.

    Checks:
    1. Risk score escalation rules
    2. Anomaly severity limits
    3. Alert management policies
    4. Agent governance guardrails
    5. Regulatory compliance requirements

    Can halt the pipeline (HITL) if critical policy violations occur.
    """

    name = "policy_rules"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Validates agent decisions against clinical policies and organizational guardrails"
    min_confidence = 0.9  # High confidence for policy enforcement

    def __init__(self, policies: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.policies = policies or DEFAULT_POLICIES

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Validate context against policies (standalone mode)."""
        context = input_data.context or {}
        violations = self._check_policies_from_dict(context)

        requires_hitl = any(v["severity"] == "critical" for v in violations)

        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            status=AgentStatus.WAITING_HITL if requires_hitl else AgentStatus.COMPLETED,
            confidence=0.95 if not violations else 0.85,
            result={
                "violations": violations,
                "violation_count": len(violations),
                "policies_checked": list(self.policies.keys()),
                "compliant": len(violations) == 0,
            },
            rationale=self._build_rationale(violations),
            requires_hitl=requires_hitl,
            hitl_reason="Critical policy violation requires human review" if requires_hitl else None,
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Check pipeline state against all configured policies."""
        violations: list[dict[str, Any]] = []

        # 1. Risk escalation checks
        violations.extend(self._check_risk_policies(state))

        # 2. Anomaly rules
        violations.extend(self._check_anomaly_policies(state))

        # 3. Agent governance
        violations.extend(self._check_governance_policies(state))

        # 4. Record violations in state
        state.policy_violations = [v["description"] for v in violations]

        # 5. Determine if HITL is required
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        if critical_violations:
            state.requires_hitl = True
            state.hitl_reason = (
                f"{len(critical_violations)} critical policy violation(s): "
                + "; ".join(v["rule"] for v in critical_violations)
            )

        # 6. Generate escalation alert requests if needed
        for v in violations:
            if v.get("auto_escalate"):
                from healthos_platform.agents.types import AlertRequest

                state.alert_requests.append(
                    AlertRequest(
                        patient_id=state.patient_id,
                        org_id=state.org_id,
                        alert_type=AlertType.PHYSICIAN_REVIEW
                        if v["severity"] == "critical"
                        else AlertType.NURSE_REVIEW,
                        priority=Severity.CRITICAL
                        if v["severity"] == "critical"
                        else Severity.HIGH,
                        message=v["description"],
                    )
                )

        # Track execution
        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result={
                "violations": violations,
                "violation_count": len(violations),
                "compliant": len(violations) == 0,
            },
            confidence=0.95 if not violations else 0.85,
            rationale=self._build_rationale(violations),
        )

        return state

    # ── Policy Check Methods ──────────────────────────────────────────────────

    def _check_risk_policies(self, state: PipelineState) -> list[dict[str, Any]]:
        """Check risk score escalation policies."""
        violations: list[dict[str, Any]] = []
        policy = self.policies.get("risk_escalation", {})

        for assessment in state.risk_assessments:
            score = assessment.score

            # Critical risk requires immediate escalation
            if score >= policy.get("critical_threshold", 0.75):
                violations.append({
                    "rule": "risk_critical_threshold",
                    "severity": "critical",
                    "description": (
                        f"Patient risk score {score:.2f} exceeds critical threshold "
                        f"{policy.get('critical_threshold', 0.75)}"
                    ),
                    "auto_escalate": policy.get("auto_escalate_critical", True),
                    "data": {"score": score, "score_type": assessment.score_type},
                })

            # HITL required above safety threshold
            if score >= policy.get("require_hitl_above", 0.80):
                violations.append({
                    "rule": "risk_hitl_required",
                    "severity": "critical",
                    "description": (
                        f"Risk score {score:.2f} requires human-in-the-loop review "
                        f"(threshold: {policy.get('require_hitl_above', 0.80)})"
                    ),
                    "auto_escalate": False,
                    "data": {"score": score},
                })

        return violations

    def _check_anomaly_policies(self, state: PipelineState) -> list[dict[str, Any]]:
        """Check anomaly-related policies."""
        violations: list[dict[str, Any]] = []
        policy = self.policies.get("anomaly_rules", {})

        # Count critical anomalies
        critical_count = sum(
            1 for a in state.anomalies if a.severity == Severity.CRITICAL
        )
        max_critical = policy.get("max_unresolved_critical", 2)

        if critical_count > max_critical:
            violations.append({
                "rule": "anomaly_critical_limit",
                "severity": "critical",
                "description": (
                    f"{critical_count} critical anomalies exceed limit of {max_critical}"
                ),
                "auto_escalate": True,
                "data": {"critical_count": critical_count, "limit": max_critical},
            })

        # Multi-vital type escalation
        if policy.get("multi_vital_escalation", True):
            affected_types = set(
                a.vital_type.value if hasattr(a.vital_type, "value") else str(a.vital_type)
                for a in state.anomalies
                if a.severity in (Severity.HIGH, Severity.CRITICAL)
            )
            threshold = policy.get("escalation_vital_count", 3)

            if len(affected_types) >= threshold:
                violations.append({
                    "rule": "anomaly_multi_vital_escalation",
                    "severity": "high",
                    "description": (
                        f"{len(affected_types)} vital types affected by high/critical anomalies "
                        f"(threshold: {threshold})"
                    ),
                    "auto_escalate": True,
                    "data": {"affected_types": list(affected_types)},
                })

        return violations

    def _check_governance_policies(self, state: PipelineState) -> list[dict[str, Any]]:
        """Check agent governance rules."""
        violations: list[dict[str, Any]] = []
        policy = self.policies.get("agent_governance", {})

        min_conf = policy.get("min_confidence_for_auto_action", 0.85)

        # Check all agent outputs for low-confidence auto-actions
        for agent_name, output in state.agent_outputs.items():
            if output.confidence < min_conf and output.status == AgentStatus.COMPLETED:
                violations.append({
                    "rule": "governance_low_confidence",
                    "severity": "moderate",
                    "description": (
                        f"Agent '{agent_name}' confidence {output.confidence:.2f} "
                        f"below auto-action threshold {min_conf}"
                    ),
                    "auto_escalate": False,
                    "data": {
                        "agent": agent_name,
                        "confidence": output.confidence,
                        "threshold": min_conf,
                    },
                })

        return violations

    def _check_policies_from_dict(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Check policies from raw dict context (standalone mode)."""
        violations: list[dict[str, Any]] = []
        policy = self.policies.get("risk_escalation", {})

        # Check risk scores in context
        risk_assessments = context.get("risk_assessments", [])
        for r in risk_assessments:
            score = r.get("score", 0.0) if isinstance(r, dict) else 0.0
            if score >= policy.get("critical_threshold", 0.75):
                violations.append({
                    "rule": "risk_critical_threshold",
                    "severity": "critical",
                    "description": f"Risk score {score:.2f} exceeds critical threshold",
                    "auto_escalate": True,
                    "data": {"score": score},
                })

        # Check anomaly counts
        anomalies = context.get("anomalies", [])
        anomaly_policy = self.policies.get("anomaly_rules", {})
        critical_count = sum(
            1 for a in anomalies
            if (a.get("severity", "") if isinstance(a, dict) else "") == "critical"
        )
        if critical_count > anomaly_policy.get("max_unresolved_critical", 2):
            violations.append({
                "rule": "anomaly_critical_limit",
                "severity": "critical",
                "description": f"{critical_count} critical anomalies exceed limit",
                "auto_escalate": True,
                "data": {"critical_count": critical_count},
            })

        return violations

    def _build_rationale(self, violations: list[dict[str, Any]]) -> str:
        """Build human-readable rationale."""
        if not violations:
            return "All policy checks passed — no violations detected"

        severity_counts: dict[str, int] = {}
        for v in violations:
            sev = v.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        parts = [f"{count} {sev}" for sev, count in severity_counts.items()]
        return f"Policy violations: {', '.join(parts)} — rules: {', '.join(v['rule'] for v in violations)}"
