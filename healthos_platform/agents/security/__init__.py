"""
Eminence HealthOS — Agent Security Module

PHI detection (Presidio + regex), clinical guardrails with prompt injection
detection, rate limiting, topic restriction, dosage validation, and
blockchain-style tamper-evident audit logging for HIPAA compliance.
"""

from healthos_platform.agents.security.audit_logger import (
    AgentAuditLogger,
    AuditRecord,
    ChainVerificationReport,
    audit_logger,
)
from healthos_platform.agents.security.guardrails import (
    ClinicalGuardrails,
    DosageCheckResult,
    GuardrailsEngine,
    GuardrailViolation,
    InputCheckResult,
    OutputCheckResult,
    guardrails,
)
from healthos_platform.agents.security.phi_detector import (
    PHIDetectionResult,
    PHIDetector,
    PHIDictScanResult,
    PHIRedactionReport,
    phi_detector,
)

__all__ = [
    # PHI Detection
    "PHIDetector",
    "PHIDetectionResult",
    "PHIRedactionReport",
    "PHIDictScanResult",
    "phi_detector",
    # Guardrails
    "GuardrailsEngine",
    "ClinicalGuardrails",
    "GuardrailViolation",
    "InputCheckResult",
    "OutputCheckResult",
    "DosageCheckResult",
    "guardrails",
    # Audit Logging
    "AgentAuditLogger",
    "AuditRecord",
    "ChainVerificationReport",
    "audit_logger",
]
