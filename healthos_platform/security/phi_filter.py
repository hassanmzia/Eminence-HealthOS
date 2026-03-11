"""
Eminence HealthOS — PHI/PII Detection and Masking
Identifies and redacts Protected Health Information before it reaches LLMs or logs.
"""

from __future__ import annotations

import re
from typing import Any


# PHI patterns (conservative — better to over-match than miss)
PHI_PATTERNS: dict[str, re.Pattern[str]] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "mrn": re.compile(r"\bMRN[:\s#]*\d{6,10}\b", re.IGNORECASE),
    "dob": re.compile(
        r"\b(?:DOB|date of birth|born)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE
    ),
    "address": re.compile(r"\b\d{1,5}\s\w+\s(?:St|Street|Ave|Avenue|Blvd|Dr|Drive|Ln|Lane|Rd|Road|Way|Ct|Court)\b", re.IGNORECASE),
    "zip": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}

REDACTION_MARKER = "[REDACTED-{type}]"


class PHIFilter:
    """Detects and redacts PHI from text and structured data."""

    def __init__(self, patterns: dict[str, re.Pattern[str]] | None = None) -> None:
        self.patterns = patterns or PHI_PATTERNS

    def scan_text(self, text: str) -> list[dict[str, Any]]:
        """Scan text for PHI matches. Returns list of detections."""
        detections: list[dict[str, Any]] = []
        for phi_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                detections.append({
                    "type": phi_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })
        return detections

    def redact_text(self, text: str) -> str:
        """Redact all PHI from text, replacing with type-tagged markers."""
        result = text
        # Process patterns from longest match to shortest to avoid overlap issues
        all_matches: list[tuple[int, int, str]] = []
        for phi_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                all_matches.append((match.start(), match.end(), phi_type))

        # Sort by position descending so we replace from end to start
        all_matches.sort(key=lambda x: x[0], reverse=True)

        for start, end, phi_type in all_matches:
            marker = REDACTION_MARKER.format(type=phi_type.upper())
            result = result[:start] + marker + result[end:]

        return result

    def redact_dict(self, data: dict[str, Any], sensitive_keys: set[str] | None = None) -> dict[str, Any]:
        """Redact PHI from dictionary values. Optionally redact specific keys entirely."""
        sensitive = sensitive_keys or {"ssn", "social_security", "password", "secret"}
        result: dict[str, Any] = {}

        for key, value in data.items():
            if key.lower() in sensitive:
                result[key] = "[REDACTED]"
            elif isinstance(value, str):
                result[key] = self.redact_text(value)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value, sensitive_keys)
            elif isinstance(value, list):
                result[key] = [
                    self.redact_dict(item, sensitive_keys) if isinstance(item, dict)
                    else self.redact_text(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    def has_phi(self, text: str) -> bool:
        """Quick check if text contains any PHI."""
        return any(pattern.search(text) for pattern in self.patterns.values())


# Module-level instance
phi_filter = PHIFilter()
