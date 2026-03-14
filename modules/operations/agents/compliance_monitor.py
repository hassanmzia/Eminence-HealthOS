"""
Compliance Monitor Agent — HIPAA and regulatory compliance checking.

Monitors platform operations for compliance with HIPAA, HITRUST,
and other healthcare regulations. Tracks PHI access, consent status,
and audit completeness.
"""

import logging
from datetime import datetime, timedelta, timezone

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger("healthos.agent.compliance_monitor")


class ComplianceMonitorAgent(HealthOSAgent):
    """Monitors HIPAA and regulatory compliance."""

    def __init__(self):
        super().__init__(
            name="compliance_monitor",
            tier=AgentTier.MONITORING,
            description="Monitors HIPAA compliance, PHI access, and audit integrity",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        check_type = data.get("check_type", "comprehensive")

        findings = []

        if check_type in ("comprehensive", "phi_access"):
            findings.extend(self._check_phi_access(data.get("phi_access_log", [])))

        if check_type in ("comprehensive", "consent"):
            findings.extend(self._check_consent_status(data.get("patients", [])))

        if check_type in ("comprehensive", "audit"):
            findings.extend(self._check_audit_integrity(data.get("audit_entries", [])))

        if check_type in ("comprehensive", "encryption"):
            findings.extend(self._check_encryption_status(data))

        # Categorize findings
        critical = [f for f in findings if f["severity"] == "CRITICAL"]
        warnings = [f for f in findings if f["severity"] == "WARNING"]

        if critical:
            decision = "compliance_violation"
            severity = "CRITICAL"
        elif warnings:
            decision = "compliance_warning"
            severity = "MEDIUM"
        else:
            decision = "compliant"
            severity = "LOW"

        # --- LLM: generate compliance narrative with risk assessment ---
        compliance_narrative: str | None = None
        if findings:
            try:
                findings_text = "\n".join(
                    f"- [{f['severity']}] {f['category']}: {f['description']}"
                    for f in findings
                )
                resp = await llm_router.complete(LLMRequest(
                    messages=[{"role": "user", "content": (
                        f"Provide a compliance risk assessment narrative for the "
                        f"following findings from a {check_type} compliance check.\n\n"
                        f"Findings:\n{findings_text}\n\n"
                        f"Summary: {len(critical)} critical, {len(warnings)} warnings\n\n"
                        f"Include overall risk level, regulatory implications, "
                        f"and prioritized remediation steps."
                    )}],
                    system=(
                        "You are a healthcare compliance officer for Eminence HealthOS. "
                        "Provide clear, actionable compliance risk assessments referencing "
                        "HIPAA, HITRUST, and relevant regulations. Prioritize patient "
                        "safety and data protection."
                    ),
                    temperature=0.3,
                    max_tokens=1024,
                ))
                compliance_narrative = resp.content
            except Exception:
                logger.warning("LLM compliance_narrative generation failed; continuing without it")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=decision,
            rationale=f"Compliance check ({check_type}): {len(findings)} finding(s) — "
                      f"{len(critical)} critical, {len(warnings)} warnings",
            confidence=0.90,
            data={
                "check_type": check_type,
                "findings": findings,
                "summary": {
                    "total_findings": len(findings),
                    "critical": len(critical),
                    "warnings": len(warnings),
                    "compliant": len(findings) == 0,
                },
                "compliance_narrative": compliance_narrative,
            },
            feature_contributions=[
                {"feature": "phi_access", "contribution": 0.3, "value": "checked"},
                {"feature": "consent", "contribution": 0.25, "value": "checked"},
                {"feature": "audit_integrity", "contribution": 0.25, "value": "checked"},
                {"feature": "encryption", "contribution": 0.2, "value": "checked"},
            ],
            requires_hitl=bool(critical),
            safety_flags=[f"compliance_{f['category']}" for f in critical],
            risk_level=severity.lower(),
        )

    def _check_phi_access(self, access_log: list) -> list:
        findings = []
        for entry in access_log:
            # Check for unusual access patterns
            if entry.get("access_count", 0) > 100:
                findings.append({
                    "category": "phi_access",
                    "severity": "WARNING",
                    "description": f"High PHI access volume: {entry.get('user_id')} accessed {entry.get('access_count')} records",
                    "recommendation": "Review access patterns for potential breach",
                })
            if entry.get("after_hours", False):
                findings.append({
                    "category": "phi_access",
                    "severity": "WARNING",
                    "description": f"After-hours PHI access by {entry.get('user_id')}",
                    "recommendation": "Verify authorized access",
                })
        return findings

    def _check_consent_status(self, patients: list) -> list:
        findings = []
        for p in patients:
            if not p.get("has_consent", True):
                findings.append({
                    "category": "consent",
                    "severity": "CRITICAL",
                    "description": f"Missing data processing consent for patient {p.get('patient_id')}",
                    "recommendation": "Obtain consent before processing PHI",
                })
        return findings

    def _check_audit_integrity(self, entries: list) -> list:
        findings = []
        for i, entry in enumerate(entries):
            if not entry.get("hash"):
                findings.append({
                    "category": "audit",
                    "severity": "CRITICAL",
                    "description": f"Missing hash in audit entry {entry.get('id', i)}",
                    "recommendation": "Investigate audit log tampering",
                })
        return findings

    def _check_encryption_status(self, data: dict) -> list:
        findings = []
        if not data.get("phi_encrypted", True):
            findings.append({
                "category": "encryption",
                "severity": "CRITICAL",
                "description": "PHI data found without encryption",
                "recommendation": "Immediately encrypt all PHI at rest",
            })
        return findings
