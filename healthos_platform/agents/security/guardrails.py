"""
Eminence HealthOS — Clinical Guardrails
Safety checks for agent outputs to prevent harmful clinical decisions.
Includes prompt injection detection, dosage validation, and
clinical safety boundaries.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger()

# ── Prompt Injection Patterns ────────────────────────────────────────────────

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*(?:system|admin|root)\s*>", re.IGNORECASE),
    re.compile(r"override\s+(?:safety|clinical|protocol)", re.IGNORECASE),
    re.compile(r"bypass\s+(?:guardrail|safety|check|validation)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:if|though)\s+you\s+(?:are|were)", re.IGNORECASE),
]

# ── Dangerous Clinical Actions ───────────────────────────────────────────────

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


class ClinicalGuardrails:
    """
    Clinical safety guardrails for agent outputs.
    Validates that agent decisions stay within safe clinical boundaries.
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="guardrails")

    def check_prompt_injection(self, text: str) -> list[dict[str, Any]]:
        """Detect potential prompt injection attempts."""
        violations = []
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append({
                    "type": "prompt_injection",
                    "severity": "critical",
                    "pattern": pattern.pattern,
                    "matched_text": match.group(),
                    "position": match.start(),
                })

        if violations:
            self._log.critical(
                "guardrails.prompt_injection_detected",
                count=len(violations),
            )

        return violations

    def check_blocked_actions(self, action: str) -> dict[str, Any] | None:
        """Check if an action is blocked by safety rules."""
        if action in BLOCKED_ACTIONS:
            self._log.warning("guardrails.blocked_action", action=action)
            return {
                "type": "blocked_action",
                "severity": "critical",
                "action": action,
                "reason": f"Action '{action}' is blocked by clinical safety rules",
            }
        return None

    def check_dosage(
        self, drug_name: str, daily_dose: float, unit: str = "mg"
    ) -> dict[str, Any] | None:
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
            return {
                "type": "dosage_exceeded",
                "severity": "high",
                "drug": drug_name,
                "prescribed_dose": daily_dose,
                "max_dose": max_dose,
                "unit": unit,
                "recommendation": f"Maximum daily dose of {drug_name} is {max_dose}{unit}",
            }
        return None

    def validate_agent_output(
        self, agent_name: str, output: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Run all guardrail checks on an agent's output."""
        violations: list[dict[str, Any]] = []

        # Check for prompt injection in text fields
        for key in ("rationale", "recommendation", "response", "text"):
            if key in output and isinstance(output[key], str):
                violations.extend(self.check_prompt_injection(output[key]))

        # Check blocked actions
        action = output.get("action", output.get("decision", ""))
        if action:
            blocked = self.check_blocked_actions(str(action))
            if blocked:
                violations.append(blocked)

        # Check medication dosages
        medications = output.get("medications", output.get("prescriptions", []))
        if isinstance(medications, list):
            for med in medications:
                if isinstance(med, dict):
                    drug = med.get("name", med.get("drug", ""))
                    dose = med.get("dose", med.get("daily_dose", 0))
                    unit = med.get("unit", "mg")
                    if drug and dose:
                        dosage_violation = self.check_dosage(drug, float(dose), unit)
                        if dosage_violation:
                            violations.append(dosage_violation)

        if violations:
            self._log.warning(
                "guardrails.violations_found",
                agent=agent_name,
                count=len(violations),
                types=[v["type"] for v in violations],
            )

        return violations
