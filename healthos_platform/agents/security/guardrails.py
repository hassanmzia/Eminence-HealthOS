"""
Eminence HealthOS — Guardrails Module

Multi-layer safety guardrails protecting the HealthOS agent system against:
  1. Prompt injection attacks
  2. Jailbreak attempts
  3. Topic restriction (clinical scope only)
  4. Output validation and sanitization
  5. Rate limiting per tenant
  6. Patient scope / multi-tenant isolation
  7. Clinical safety checks (blocked actions, dosage limits)
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Any, Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# ── Prompt Injection Detection Patterns ──────────────────────────────────────

INJECTION_PATTERNS = [
    # Classic prompt injection
    r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+instructions",
    r"disregard\s+(?:all\s+)?(?:previous|above|prior)\s+instructions",
    r"forget\s+(?:all\s+)?(?:previous|above|prior)\s+instructions",
    r"new\s+instruction[s]?:",
    r"system\s*:\s*you\s+are\s+now",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)|a|an)\s+(?:different|new|evil|uncensored)",
    # Jailbreak patterns
    r"do\s+anything\s+now",
    r"dan\s+mode",
    r"developer\s+mode",
    r"jailbreak",
    r"bypass\s+(?:safety|restriction|filter|guardrail|check|validation)",
    r"ignore\s+(?:safety|ethical)\s+(?:guidelines|constraints)",
    # Role manipulation
    r"you\s+(?:are|were|will be)\s+(?:now\s+)?(?:a\s+)?(?:hacker|criminal|malicious)",
    r"pretend\s+(?:that\s+)?you\s+(?:have\s+no\s+)?(?:restrictions|limits|constraints)",
    # Data extraction
    r"reveal\s+(?:your\s+)?(?:system\s+)?prompt",
    r"show\s+(?:me\s+)?(?:your\s+)?(?:system\s+)?(?:instructions|prompt|training)",
    r"print\s+(?:your\s+)?(?:full\s+)?(?:system\s+)?prompt",
    r"what\s+(?:are\s+)?(?:your\s+)?(?:exact\s+)?instructions",
    # Override attempts
    r"override\s+(?:safety|clinical|protocol)",
    r"act\s+as\s+(?:if|though)\s+you\s+(?:are|were)",
    r"<\s*(?:system|admin|root)\s*>",
]

# ── Restricted Topics (off-topic for a clinical platform) ────────────────────

RESTRICTED_TOPICS = [
    "cryptocurrency",
    "investment advice",
    "stock market",
    "bitcoin",
    "political opinion",
    "election",
    "weapons manufacturing",
    "drug synthesis",  # Note: different from pharmacology
    "illegal activity",
    "hacking tutorial",
    "sex",
    "adult content",
    "gambling",
]

# ── Clinical Scope Keywords ──────────────────────────────────────────────────

CLINICAL_KEYWORDS = [
    "patient", "diagnosis", "treatment", "medication", "symptom", "disease",
    "health", "medical", "clinical", "therapy", "lab", "glucose", "blood",
    "heart", "kidney", "lung", "cancer", "diabetes", "hypertension", "chronic",
    "doctor", "physician", "nurse", "hospital", "prescription", "risk", "vitals",
    "pharmacology", "dosage", "adverse", "contraindication",
]

# ── Blocked Clinical Actions ─────────────────────────────────────────────────

BLOCKED_ACTIONS = {
    "prescribe_controlled_without_dea",
    "override_allergy_alert",
    "discharge_critical_patient",
    "modify_dosage_beyond_max",
    "skip_drug_interaction_check",
}

# ── Dosage Limits (simplified — production uses drug database) ───────────────

MAX_DOSAGES: dict[str, dict[str, Any]] = {
    "metformin": {"max_daily_mg": 2550, "unit": "mg"},
    "lisinopril": {"max_daily_mg": 80, "unit": "mg"},
    "atorvastatin": {"max_daily_mg": 80, "unit": "mg"},
    "metoprolol": {"max_daily_mg": 400, "unit": "mg"},
    "amlodipine": {"max_daily_mg": 10, "unit": "mg"},
    "insulin_glargine": {"max_daily_units": 80, "unit": "units"},
    "warfarin": {"max_daily_mg": 15, "unit": "mg"},
    "apixaban": {"max_daily_mg": 10, "unit": "mg"},
}

# ── Rate Limiting Config ─────────────────────────────────────────────────────

_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_REQUESTS = int(os.getenv("GUARDRAIL_RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("GUARDRAIL_RATE_LIMIT_WINDOW", "60"))


# ── Pydantic Models ─────────────────────────────────────────────────────────


class GuardrailViolation(BaseModel):
    """A single guardrail violation."""

    type: str
    severity: str = "critical"
    detail: str = ""
    matched_text: str = ""
    pattern: str = ""
    position: int | None = None


class InputCheckResult(BaseModel):
    """Result of input guardrail checks."""

    is_safe: bool = True
    reason: str | None = None
    violations: list[GuardrailViolation] = Field(default_factory=list)


class OutputCheckResult(BaseModel):
    """Result of output validation."""

    is_safe: bool = True
    sanitized_output: str = ""
    modifications: list[str] = Field(default_factory=list)


class DosageCheckResult(BaseModel):
    """Result of a dosage safety check."""

    type: str = "dosage_exceeded"
    severity: str = "high"
    drug: str = ""
    prescribed_dose: float = 0.0
    max_dose: float = 0.0
    unit: str = "mg"
    recommendation: str = ""


# ── Guardrails Engine ────────────────────────────────────────────────────────


class GuardrailsEngine:
    """
    Multi-layer safety guardrail engine for HealthOS agents.

    Combines prompt injection detection, topic restriction, rate limiting,
    clinical safety checks, and output sanitization.
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="guardrails")
        self._injection_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in INJECTION_PATTERNS
        ]

    # ── Input Guardrails ─────────────────────────────────────────────────────

    def check_input(
        self,
        text: str,
        tenant_id: str,
        context: dict[str, Any] | None = None,
    ) -> InputCheckResult:
        """
        Run all input guardrails. Returns structured result with safety status.
        """
        # 1. Rate limiting
        safe, reason = self._check_rate_limit(tenant_id)
        if not safe:
            return InputCheckResult(is_safe=False, reason=reason)

        # 2. Prompt injection detection
        safe, reason = self._detect_prompt_injection(text)
        if not safe:
            return InputCheckResult(is_safe=False, reason=reason)

        # 3. Restricted topic check
        safe, reason = self._check_restricted_topics(text)
        if not safe:
            return InputCheckResult(is_safe=False, reason=reason)

        # 4. Input length validation
        if len(text) > 50_000:
            return InputCheckResult(
                is_safe=False,
                reason="Input exceeds maximum allowed length (50,000 characters)",
            )

        return InputCheckResult(is_safe=True)

    # ── Output Guardrails ────────────────────────────────────────────────────

    def check_output(
        self,
        output: str,
        original_input: str = "",
    ) -> OutputCheckResult:
        """
        Validate and sanitize agent output.
        """
        sanitized = output
        modifications: list[str] = []

        # Remove any leaked system prompt artifacts
        leaked_pattern = re.compile(
            r"(?:SYSTEM|INSTRUCTIONS|PROMPT)[:\s]*\[.*?\]",
            re.IGNORECASE | re.DOTALL,
        )
        if leaked_pattern.search(sanitized):
            sanitized = leaked_pattern.sub("[REDACTED]", sanitized)
            modifications.append("removed_leaked_system_prompt")

        # Remove potential SQL injection in output
        dangerous_sql = re.compile(
            r"(?:DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE)\s+(?:TABLE|DATABASE|FROM|INTO)\s+\w+",
            re.IGNORECASE,
        )
        if dangerous_sql.search(sanitized):
            sanitized = dangerous_sql.sub("[BLOCKED SQL OPERATION]", sanitized)
            modifications.append("blocked_sql_operation")
            self._log.warning("guardrails.sql_in_output")

        return OutputCheckResult(
            is_safe=True,
            sanitized_output=sanitized,
            modifications=modifications,
        )

    # ── Prompt Injection Detection ───────────────────────────────────────────

    def check_prompt_injection(self, text: str) -> list[GuardrailViolation]:
        """
        Detect potential prompt injection attempts.
        Returns list of violations (empty if clean).
        """
        violations: list[GuardrailViolation] = []
        for pattern in self._injection_patterns:
            match = pattern.search(text)
            if match:
                violations.append(
                    GuardrailViolation(
                        type="prompt_injection",
                        severity="critical",
                        detail=f"Injection pattern matched: {match.group(0)[:50]}",
                        matched_text=match.group(),
                        pattern=pattern.pattern,
                        position=match.start(),
                    )
                )

        if violations:
            self._log.critical(
                "guardrails.prompt_injection_detected",
                count=len(violations),
            )

        return violations

    # ── Clinical Safety Checks ───────────────────────────────────────────────

    def check_blocked_actions(self, action: str) -> GuardrailViolation | None:
        """Check if an action is blocked by clinical safety rules."""
        if action in BLOCKED_ACTIONS:
            self._log.warning("guardrails.blocked_action", action=action)
            return GuardrailViolation(
                type="blocked_action",
                severity="critical",
                detail=f"Action '{action}' is blocked by clinical safety rules",
            )
        return None

    def check_dosage(
        self, drug_name: str, daily_dose: float, unit: str = "mg"
    ) -> DosageCheckResult | None:
        """Validate medication dosage against maximum safe limits."""
        drug_key = drug_name.lower().replace(" ", "_")
        limits = MAX_DOSAGES.get(drug_key)

        if not limits:
            return None  # Drug not in our safety database

        max_key = f"max_daily_{unit}"
        max_dose = limits.get(max_key, limits.get("max_daily_mg"))

        if max_dose and daily_dose > max_dose:
            self._log.warning(
                "guardrails.dosage_exceeded",
                drug=drug_name,
                dose=daily_dose,
                max_dose=max_dose,
                unit=unit,
            )
            return DosageCheckResult(
                drug=drug_name,
                prescribed_dose=daily_dose,
                max_dose=max_dose,
                unit=unit,
                recommendation=f"Maximum daily dose of {drug_name} is {max_dose}{unit}",
            )
        return None

    def validate_agent_output(
        self, agent_name: str, output: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Run all guardrail checks on an agent's output dictionary."""
        violations: list[dict[str, Any]] = []

        # Check for prompt injection in text fields
        for key in ("rationale", "recommendation", "response", "text"):
            if key in output and isinstance(output[key], str):
                for v in self.check_prompt_injection(output[key]):
                    violations.append(v.model_dump())

        # Check blocked actions
        action = output.get("action", output.get("decision", ""))
        if action:
            blocked = self.check_blocked_actions(str(action))
            if blocked:
                violations.append(blocked.model_dump())

        # Check medication dosages
        medications = output.get("medications", output.get("prescriptions", []))
        if isinstance(medications, list):
            for med in medications:
                if isinstance(med, dict):
                    drug = med.get("name", med.get("drug", ""))
                    dose = med.get("dose", med.get("daily_dose", 0))
                    unit = med.get("unit", "mg")
                    if drug and dose:
                        dosage_result = self.check_dosage(drug, float(dose), unit)
                        if dosage_result:
                            violations.append(dosage_result.model_dump())

        if violations:
            self._log.warning(
                "guardrails.violations_found",
                agent=agent_name,
                count=len(violations),
                types=[v["type"] for v in violations],
            )

        return violations

    # ── Patient Scope / Multi-Tenant Isolation ───────────────────────────────

    def validate_patient_scope(
        self,
        query_patient_id: str,
        authenticated_patient_ids: list[str],
        tenant_id: str,
    ) -> bool:
        """
        Ensure the agent only accesses data for authorized patients.
        Multi-tenant isolation check.
        """
        if query_patient_id not in authenticated_patient_ids:
            self._log.critical(
                "guardrails.cross_patient_access",
                query_patient=query_patient_id,
                tenant=tenant_id,
            )
            return False
        return True

    # ── Input Sanitization ───────────────────────────────────────────────────

    def sanitize_for_llm(self, text: str) -> str:
        """
        Sanitize user input before passing to LLM.
        Removes special characters that could confuse prompt parsing.
        """
        # Remove null bytes
        text = text.replace("\x00", "")
        # Limit consecutive special characters
        text = re.sub(r"[<>]{3,}", "...", text)
        # Remove HTML tags (potential XSS in prompts)
        text = re.sub(r"<[^>]{1,200}>", "", text)
        return text.strip()

    def hash_for_audit(self, text: str) -> str:
        """Return a SHA-256 hash of text for audit logging without storing raw content."""
        return hashlib.sha256(text.encode()).hexdigest()

    # ── Internal Methods ─────────────────────────────────────────────────────

    def _check_rate_limit(self, tenant_id: str) -> tuple[bool, str | None]:
        """Sliding window rate limiter per tenant."""
        now = time.monotonic()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        if tenant_id not in _rate_limit_store:
            _rate_limit_store[tenant_id] = []

        # Clean old timestamps
        _rate_limit_store[tenant_id] = [
            ts for ts in _rate_limit_store[tenant_id] if ts > window_start
        ]

        if len(_rate_limit_store[tenant_id]) >= RATE_LIMIT_REQUESTS:
            return (
                False,
                f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS}s",
            )

        _rate_limit_store[tenant_id].append(now)
        return True, None

    def _detect_prompt_injection(self, text: str) -> tuple[bool, str | None]:
        """Detect prompt injection attempts."""
        for pattern in self._injection_patterns:
            match = pattern.search(text)
            if match:
                self._log.warning(
                    "guardrails.prompt_injection",
                    pattern=pattern.pattern[:50],
                    match=match.group(0)[:50],
                )
                return False, f"Prompt injection attempt detected: {match.group(0)[:50]}"
        return True, None

    def _check_restricted_topics(self, text: str) -> tuple[bool, str | None]:
        """Check if input is about a restricted (off-topic) subject."""
        text_lower = text.lower()

        for topic in RESTRICTED_TOPICS:
            if topic in text_lower:
                # Verify it's not clinically relevant
                clinical_context = any(kw in text_lower for kw in CLINICAL_KEYWORDS)
                if not clinical_context:
                    return (
                        False,
                        f"Off-topic query detected: '{topic}'. HealthOS supports clinical queries only.",
                    )

        return True, None


# Backward-compatible alias
ClinicalGuardrails = GuardrailsEngine

# ── Module-level singleton ───────────────────────────────────────────────────

guardrails = GuardrailsEngine()
