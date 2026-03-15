"""
Eminence HealthOS — Marketplace Security Scanner Agent
Layer 5 (Measurement): Scans third-party agent code for security vulnerabilities,
PHI compliance issues, and unsafe patterns before allowing marketplace publication.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

logger = logging.getLogger(__name__)

# ── Security rule definitions ─────────────────────────────────────────────────

UNSAFE_IMPORTS = {
    "subprocess", "os.system", "shutil.rmtree", "ctypes", "pickle",
    "shelve", "marshal", "importlib", "eval", "exec", "compile",
}

UNSAFE_PATTERNS: list[dict[str, Any]] = [
    {
        "id": "PHI_UNSCOPED_ACCESS",
        "pattern": r"(SELECT|INSERT|UPDATE|DELETE)\s+.*\bFROM\b.*\bpatient",
        "severity": "critical",
        "message": "Direct SQL query against patient table without tenant scoping detected.",
        "category": "phi_access",
    },
    {
        "id": "UNSCOPED_DB_QUERY",
        "pattern": r"(db|session|engine)\.(execute|query|raw)\s*\(",
        "severity": "high",
        "message": "Unscoped database query — all queries must go through the tenant-scoped data layer.",
        "category": "data_access",
    },
    {
        "id": "DIRECT_NETWORK_CALL",
        "pattern": r"(requests|httpx|urllib|aiohttp)\.(get|post|put|delete|patch|head)\s*\(",
        "severity": "high",
        "message": "Direct network call detected — agents must use the HealthOS HTTP gateway.",
        "category": "network",
    },
    {
        "id": "CREDENTIAL_ACCESS",
        "pattern": r"(os\.environ|getenv|\.env|SECRET|PASSWORD|API_KEY|PRIVATE_KEY)",
        "severity": "critical",
        "message": "Credential or secret access detected — agents must use the HealthOS secrets manager.",
        "category": "credentials",
    },
    {
        "id": "FILE_SYSTEM_ACCESS",
        "pattern": r"(open\s*\(|pathlib\.Path|os\.path|shutil\.(copy|move))",
        "severity": "medium",
        "message": "Direct file system access — agents should use the HealthOS storage abstraction.",
        "category": "filesystem",
    },
    {
        "id": "PHI_LOGGING",
        "pattern": r"(logger|logging|print)\s*\(.*\b(patient_name|ssn|mrn|dob|address)\b",
        "severity": "critical",
        "message": "Potential PHI being written to logs — all PHI must be redacted before logging.",
        "category": "phi_access",
    },
]

# ── Permission definitions ────────────────────────────────────────────────────

VALID_PERMISSIONS = {
    "patient:read", "patient:write", "patient:phi",
    "vitals:read", "vitals:write",
    "alerts:read", "alerts:write",
    "orders:read", "orders:write",
    "analytics:read", "analytics:write",
    "network:outbound", "storage:read", "storage:write",
}

ELEVATED_PERMISSIONS = {"patient:phi", "orders:write", "network:outbound"}


class SecurityScannerAgent(BaseAgent):
    """Scans third-party agent code for security issues before marketplace publication."""

    name = "marketplace_security_scanner"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Scans agent code for security vulnerabilities, PHI compliance, and unsafe patterns."

    async def process(self, input_data: AgentInput) -> AgentOutput:
        action = input_data.context.get("action", "scan_agent")
        ctx = input_data.context

        handler = {
            "scan_agent": self._scan_agent,
            "audit_permissions": self._audit_permissions,
            "check_phi_compliance": self._check_phi_compliance,
        }.get(action)

        if handler is None:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Action '{action}' is not supported by the security scanner.",
                status=AgentStatus.FAILED,
            )

        return await handler(input_data, ctx)

    # ── Action Handlers ───────────────────────────────────────────────────────

    async def _scan_agent(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Perform a full security scan on agent source code."""
        source_code = ctx.get("source_code", "")
        agent_id = ctx.get("agent_id", "unknown")

        findings: list[dict[str, Any]] = []

        # Check for unsafe imports
        for unsafe in UNSAFE_IMPORTS:
            if unsafe in source_code:
                findings.append({
                    "rule_id": "UNSAFE_IMPORT",
                    "severity": "critical",
                    "message": f"Unsafe import detected: '{unsafe}'",
                    "category": "imports",
                })

        # Check for unsafe patterns
        for rule in UNSAFE_PATTERNS:
            matches = re.findall(rule["pattern"], source_code, re.IGNORECASE)
            if matches:
                findings.append({
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "message": rule["message"],
                    "category": rule["category"],
                    "match_count": len(matches),
                })

        # Calculate security score
        score = self._calculate_score(findings)
        passed = score >= 70 and not any(f["severity"] == "critical" for f in findings)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "agent_id": agent_id,
                "security_score": score,
                "passed": passed,
                "findings": findings,
                "total_findings": len(findings),
                "critical_count": sum(1 for f in findings if f["severity"] == "critical"),
                "high_count": sum(1 for f in findings if f["severity"] == "high"),
                "medium_count": sum(1 for f in findings if f["severity"] == "medium"),
                "scanned_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.9,
            rationale=(
                f"Security scan {'passed' if passed else 'failed'} with score {score}/100. "
                f"Found {len(findings)} issue(s)."
            ),
        )

    async def _audit_permissions(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Audit the permissions requested by a third-party agent."""
        requested = set(ctx.get("requested_permissions", []))
        agent_id = ctx.get("agent_id", "unknown")

        unknown = requested - VALID_PERMISSIONS
        elevated = requested & ELEVATED_PERMISSIONS
        standard = requested - ELEVATED_PERMISSIONS - unknown

        issues: list[dict[str, Any]] = []

        if unknown:
            issues.append({
                "type": "unknown_permission",
                "severity": "high",
                "permissions": sorted(unknown),
                "message": f"Unknown permissions requested: {', '.join(sorted(unknown))}",
            })

        if elevated:
            issues.append({
                "type": "elevated_permission",
                "severity": "medium",
                "permissions": sorted(elevated),
                "message": (
                    f"Elevated permissions requested: {', '.join(sorted(elevated))}. "
                    "These require additional review."
                ),
            })

        approved = len(unknown) == 0

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "agent_id": agent_id,
                "approved": approved,
                "standard_permissions": sorted(standard),
                "elevated_permissions": sorted(elevated),
                "unknown_permissions": sorted(unknown),
                "issues": issues,
                "requires_manual_review": len(elevated) > 0,
            },
            confidence=0.95,
            rationale=(
                f"Permission audit for '{agent_id}': {len(standard)} standard, "
                f"{len(elevated)} elevated, {len(unknown)} unknown."
            ),
        )

    async def _check_phi_compliance(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Check agent code for PHI compliance issues specifically."""
        source_code = ctx.get("source_code", "")
        agent_id = ctx.get("agent_id", "unknown")

        phi_findings: list[dict[str, Any]] = []

        # Check for PHI-related patterns
        phi_rules = [r for r in UNSAFE_PATTERNS if r["category"] == "phi_access"]
        for rule in phi_rules:
            matches = re.findall(rule["pattern"], source_code, re.IGNORECASE)
            if matches:
                phi_findings.append({
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "message": rule["message"],
                    "match_count": len(matches),
                })

        # Check for PHI field references without proper access patterns
        phi_fields = ["patient_name", "ssn", "date_of_birth", "dob", "address", "phone", "email", "mrn"]
        for field in phi_fields:
            if field in source_code.lower():
                phi_findings.append({
                    "rule_id": "PHI_FIELD_REFERENCE",
                    "severity": "medium",
                    "message": f"Reference to PHI field '{field}' detected — ensure proper access controls.",
                    "field": field,
                })

        compliant = not any(f["severity"] == "critical" for f in phi_findings)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "agent_id": agent_id,
                "phi_compliant": compliant,
                "findings": phi_findings,
                "total_findings": len(phi_findings),
                "recommendation": (
                    "Agent meets PHI handling requirements."
                    if compliant
                    else "Agent has critical PHI compliance issues that must be resolved."
                ),
            },
            confidence=0.9,
            rationale=(
                f"PHI compliance check {'passed' if compliant else 'failed'} "
                f"with {len(phi_findings)} finding(s)."
            ),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_score(findings: list[dict[str, Any]]) -> int:
        """Calculate a security score from 0-100 based on findings."""
        score = 100
        for f in findings:
            severity = f.get("severity", "low")
            if severity == "critical":
                score -= 25
            elif severity == "high":
                score -= 15
            elif severity == "medium":
                score -= 5
            else:
                score -= 2
        return max(0, score)
