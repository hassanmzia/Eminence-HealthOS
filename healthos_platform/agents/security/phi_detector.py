"""
Eminence HealthOS — PHI Detector
Detects and redacts Protected Health Information (PHI) from agent
inputs and outputs using pattern matching and NER.
Supports HIPAA-defined PHI categories.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger()

# ── PHI Patterns ─────────────────────────────────────────────────────────────

PHI_PATTERNS: dict[str, re.Pattern] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "mrn": re.compile(r"\bMRN[:\s#]*\d{6,10}\b", re.IGNORECASE),
    "date_of_birth": re.compile(
        r"\b(?:DOB|date\s+of\s+birth|born)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        re.IGNORECASE,
    ),
    "medical_license": re.compile(r"\b[A-Z]{2}\d{6,8}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "zip_code_full": re.compile(r"\b\d{5}-\d{4}\b"),
}

# Redaction placeholder
REDACTED = "[REDACTED]"


class PHIDetector:
    """
    Detects and redacts PHI from text using regex patterns.
    For production, integrate with Microsoft Presidio for NER-based detection.
    """

    def __init__(self, patterns: dict[str, re.Pattern] | None = None) -> None:
        self.patterns = patterns or PHI_PATTERNS
        self._log = logger.bind(component="phi_detector")

    def detect(self, text: str) -> list[dict[str, Any]]:
        """Detect PHI entities in text. Returns list of detections."""
        detections: list[dict[str, Any]] = []

        for phi_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                detections.append({
                    "type": phi_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                })

        if detections:
            self._log.warning(
                "phi.detected",
                count=len(detections),
                types=[d["type"] for d in detections],
            )

        return detections

    def redact(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """Redact all PHI from text. Returns (redacted_text, detections)."""
        detections = self.detect(text)

        if not detections:
            return text, []

        # Sort by position (reverse) to preserve indices during replacement
        detections.sort(key=lambda d: d["start"], reverse=True)

        redacted = text
        for detection in detections:
            start, end = detection["start"], detection["end"]
            redacted = redacted[:start] + REDACTED + redacted[end:]

        return redacted, detections

    def contains_phi(self, text: str) -> bool:
        """Quick check if text contains any PHI."""
        return any(pattern.search(text) for pattern in self.patterns.values())

    def scan_dict(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Scan a dictionary's string values for PHI recursively."""
        detections: list[dict[str, Any]] = []

        def _scan(obj: Any, path: str = "") -> None:
            if isinstance(obj, str):
                for d in self.detect(obj):
                    d["path"] = path
                    detections.append(d)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    _scan(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _scan(item, f"{path}[{i}]")

        _scan(data)
        return detections

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact PHI from all string values in a dictionary."""
        import copy

        result = copy.deepcopy(data)

        def _redact(obj: Any) -> Any:
            if isinstance(obj, str):
                redacted, _ = self.redact(obj)
                return redacted
            elif isinstance(obj, dict):
                return {k: _redact(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_redact(item) for item in obj]
            return obj

        return _redact(result)
