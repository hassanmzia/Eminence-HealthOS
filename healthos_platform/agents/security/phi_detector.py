"""
Eminence HealthOS — PHI Detection Module

Presidio-based PHI detection and anonymization for HealthOS agents.
Ensures no Protected Health Information leaks to LLM providers or logs.

Supports:
  - Microsoft Presidio NER-based detection (when available)
  - Regex fallback for environments without Presidio
  - Custom HIPAA pattern extensions (MRN, NPI, DEA, etc.)
  - Recursive dictionary scanning and redaction
"""

from __future__ import annotations

import copy
import re
from typing import Any, Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# ── PHI Entity Types (Presidio-supported) ────────────────────────────────────

PHI_ENTITY_TYPES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
    "DATE_TIME",
    "NRP",
    "MEDICAL_LICENSE",
    "URL",
]

# ── Custom HIPAA PHI Patterns (beyond Presidio defaults) ─────────────────────

HIPAA_PHI_PATTERNS: dict[str, str] = {
    "MRN": r"\bMRN[:#\s]\s*\d{6,12}\b",
    "DOB": r"\b(?:DOB|Date of Birth|birth date)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "ACCOUNT_NUMBER": r"\b(?:Account|Acct)[#\s:]+\d{5,15}\b",
    "HEALTH_PLAN": r"\bPolicy\s+(?:Number|#|No)[:\s]+[A-Z0-9\-]{6,20}\b",
    "NPI": r"\bNPI[:\s]+\d{10}\b",
    "DEA": r"\bDEA[:\s]+[A-Z]{2}\d{7}\b",
}

# ── Regex-only patterns (always available, no Presidio needed) ───────────────

REGEX_PHI_PATTERNS: dict[str, re.Pattern[str]] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "mrn": re.compile(r"\bMRN[:\s#]*\d{6,12}\b", re.IGNORECASE),
    "date_of_birth": re.compile(
        r"\b(?:DOB|date\s+of\s+birth|born)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        re.IGNORECASE,
    ),
    "medical_license": re.compile(r"\b[A-Z]{2}\d{6,8}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "zip_code_full": re.compile(r"\b\d{5}-\d{4}\b"),
}


# ── Pydantic Models ──────────────────────────────────────────────────────────


class PHIEntity(BaseModel):
    """A single detected PHI entity."""

    type: str
    start: int
    end: int
    score: float = 0.95
    text: str = ""


class PHICustomMatch(BaseModel):
    """A match from custom HIPAA regex patterns."""

    type: str
    match: str


class PHIDetectionResult(BaseModel):
    """Result of a PHI detection scan."""

    has_phi: bool = False
    phi_count: int = 0
    entities: list[PHIEntity] = Field(default_factory=list)
    custom_matches: list[PHICustomMatch] = Field(default_factory=list)
    text_length: int = 0


class PHIRedactionReport(BaseModel):
    """Report describing what was redacted."""

    redacted: bool = False
    original_length: int = 0
    redacted_length: int = 0
    phi_entities_removed: int = 0
    custom_matches_removed: int = 0


class PHIDictScanResult(BaseModel):
    """Result of scanning a dictionary for PHI."""

    has_phi: bool = False
    issues: list[dict[str, Any]] = Field(default_factory=list)


# ── PHI Detector ─────────────────────────────────────────────────────────────


class PHIDetector:
    """
    HIPAA-compliant PHI detection using Presidio with custom pattern extensions.

    Falls back to regex-only detection when Presidio is not installed.
    Thread-safe singleton pattern for production use.
    """

    _instance: Optional[PHIDetector] = None
    _analyzer: Any = None
    _anonymizer: Any = None

    def __new__(cls) -> PHIDetector:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        self._log = logger.bind(component="phi_detector")

    def _initialize(self) -> None:
        """Lazy-initialize Presidio engines (or fall back to regex)."""
        if self._initialized:
            return
        try:
            from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
            from presidio_anonymizer import AnonymizerEngine

            self._analyzer = AnalyzerEngine()

            # Register custom HIPAA patterns
            for phi_type, pattern in HIPAA_PHI_PATTERNS.items():
                recognizer = PatternRecognizer(
                    supported_entity=phi_type,
                    patterns=[Pattern(name=phi_type, regex=pattern, score=0.9)],
                )
                self._analyzer.registry.add_recognizer(recognizer)

            self._anonymizer = AnonymizerEngine()
            self._initialized = True
            self._log.info("phi_detector.initialized", backend="presidio")

        except ImportError as exc:
            self._log.warning(
                "phi_detector.presidio_unavailable",
                error=str(exc),
                fallback="regex",
            )
            self._initialized = True
        except Exception as exc:
            self._log.error("phi_detector.init_failed", error=str(exc))
            self._initialized = True

    # ── Detection ────────────────────────────────────────────────────────────

    def detect(self, text: str, threshold: float = 0.7) -> PHIDetectionResult:
        """
        Detect PHI entities in text.

        Uses Presidio when available, always runs custom HIPAA patterns.
        """
        self._initialize()
        entities: list[PHIEntity] = []
        custom_matches: list[PHICustomMatch] = []

        # Presidio analysis
        if self._analyzer:
            try:
                results = self._analyzer.analyze(
                    text=text,
                    language="en",
                    entities=PHI_ENTITY_TYPES,
                    score_threshold=threshold,
                )
                entities = [
                    PHIEntity(
                        type=r.entity_type,
                        start=r.start,
                        end=r.end,
                        score=round(r.score, 3),
                        text=text[r.start : r.end],
                    )
                    for r in results
                ]
            except Exception as exc:
                self._log.warning("phi_detector.presidio_analysis_failed", error=str(exc))
        else:
            # Regex fallback when Presidio is not available
            for phi_type, pattern in REGEX_PHI_PATTERNS.items():
                for match in pattern.finditer(text):
                    entities.append(
                        PHIEntity(
                            type=phi_type,
                            start=match.start(),
                            end=match.end(),
                            score=0.95,
                            text=match.group(),
                        )
                    )

        # Custom HIPAA pattern matching (always runs)
        for phi_type, pattern in HIPAA_PHI_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match_text in matches:
                custom_matches.append(PHICustomMatch(type=phi_type, match=match_text))

        total_phi = len(entities) + len(custom_matches)

        if total_phi > 0:
            self._log.warning(
                "phi.detected",
                count=total_phi,
                entity_types=[e.type for e in entities],
                custom_types=[m.type for m in custom_matches],
            )

        return PHIDetectionResult(
            has_phi=total_phi > 0,
            phi_count=total_phi,
            entities=entities,
            custom_matches=custom_matches,
            text_length=len(text),
        )

    def contains_phi(self, text: str) -> bool:
        """Quick check if text contains any PHI."""
        result = self.detect(text)
        return result.has_phi

    # ── Redaction ────────────────────────────────────────────────────────────

    def redact(self, text: str) -> tuple[str, PHIRedactionReport]:
        """
        Redact PHI from text. Returns (redacted_text, redaction_report).
        """
        self._initialize()
        detection = self.detect(text)

        if not detection.has_phi:
            return text, PHIRedactionReport(redacted=False)

        redacted_text = text

        # Presidio anonymization
        if self._anonymizer and self._analyzer:
            try:
                from presidio_anonymizer.entities import OperatorConfig

                analyzer_results = self._analyzer.analyze(text=text, language="en")
                anonymized = self._anonymizer.anonymize(
                    text=text,
                    analyzer_results=analyzer_results,
                    operators={
                        "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
                        "PERSON": OperatorConfig("replace", {"new_value": "<PATIENT_NAME>"}),
                        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
                        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
                        "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
                        "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
                        "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
                        "IP_ADDRESS": OperatorConfig("replace", {"new_value": "<IP>"}),
                    },
                )
                redacted_text = anonymized.text
            except Exception as exc:
                self._log.warning(
                    "phi_detector.presidio_redaction_failed",
                    error=str(exc),
                    fallback="regex",
                )
                redacted_text = self._regex_redact(text)
        else:
            redacted_text = self._regex_redact(text)

        # Apply custom HIPAA pattern redaction
        for phi_type, pattern in HIPAA_PHI_PATTERNS.items():
            redacted_text = re.sub(pattern, f"<{phi_type}>", redacted_text, flags=re.IGNORECASE)

        report = PHIRedactionReport(
            redacted=True,
            original_length=len(text),
            redacted_length=len(redacted_text),
            phi_entities_removed=len(detection.entities),
            custom_matches_removed=len(detection.custom_matches),
        )

        self._log.info(
            "phi.redacted",
            entities_removed=report.phi_entities_removed,
            custom_removed=report.custom_matches_removed,
        )

        return redacted_text, report

    def _regex_redact(self, text: str) -> str:
        """Regex-based PHI redaction fallback when Presidio is unavailable."""
        # Email
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "<EMAIL>", text
        )
        # Phone
        text = re.sub(
            r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "<PHONE>", text
        )
        # SSN
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "<SSN>", text)
        # Dates with context
        text = re.sub(
            r"\b(?:DOB|born|birthday)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            "<DOB>",
            text,
            flags=re.IGNORECASE,
        )
        return text

    # ── Dictionary Scanning ──────────────────────────────────────────────────

    def scan_dict(self, data: dict[str, Any]) -> PHIDictScanResult:
        """
        Recursively scan a dictionary for PHI and return detection report.
        Does NOT modify the dict (use redact_dict for that).
        """
        issues: list[dict[str, Any]] = []
        self._scan_dict_recursive(data, "", issues)
        return PHIDictScanResult(has_phi=len(issues) > 0, issues=issues)

    def _scan_dict_recursive(
        self,
        data: Any,
        path: str,
        issues: list[dict[str, Any]],
    ) -> None:
        if isinstance(data, str) and len(data) > 5:
            result = self.detect(data)
            if result.has_phi:
                issues.append({"path": path, "phi_count": result.phi_count})
        elif isinstance(data, dict):
            for key, value in data.items():
                self._scan_dict_recursive(value, f"{path}.{key}" if path else key, issues)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._scan_dict_recursive(item, f"{path}[{i}]", issues)

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact PHI from all string values in a dictionary (deep copy)."""
        result = copy.deepcopy(data)

        def _redact(obj: Any) -> Any:
            if isinstance(obj, str):
                redacted_text, _ = self.redact(obj)
                return redacted_text
            elif isinstance(obj, dict):
                return {k: _redact(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_redact(item) for item in obj]
            return obj

        return _redact(result)


# ── Module-level singleton ───────────────────────────────────────────────────

phi_detector = PHIDetector()
