"""
PHI Filter Configuration

Defines sensitive columns, patterns, and masking rules for HIPAA compliance.
Maps 60+ column types to masking levels, defines blocked/HITL-required columns,
and provides regex patterns for PHI and toxicity detection.
"""

from enum import Enum
from typing import Dict, Set
import re


class MaskingLevel(str, Enum):
    """Level of PHI masking to apply"""
    NONE = "none"       # No masking (development only)
    PARTIAL = "partial" # Partial masking (show last 4 digits, first initial, etc.)
    FULL = "full"       # Complete masking
    REDACT = "redact"   # Replace with [REDACTED]


# ============================================================================
# SENSITIVE COLUMNS - Columns that contain PHI (18 HIPAA identifiers)
# ============================================================================

SENSITIVE_COLUMNS: Dict[str, MaskingLevel] = {
    # Direct Identifiers
    "SSN": MaskingLevel.FULL,
    "SOCIAL_SECURITY": MaskingLevel.FULL,
    "PASSPORT": MaskingLevel.FULL,
    "DRIVERS": MaskingLevel.FULL,
    "DRIVERS_LICENSE": MaskingLevel.FULL,
    "LICENSE": MaskingLevel.FULL,

    # Names
    "FIRST": MaskingLevel.PARTIAL,
    "LAST": MaskingLevel.PARTIAL,
    "MAIDEN": MaskingLevel.PARTIAL,
    "FIRST_NAME": MaskingLevel.PARTIAL,
    "LAST_NAME": MaskingLevel.PARTIAL,
    "MAIDEN_NAME": MaskingLevel.PARTIAL,
    "NAME": MaskingLevel.PARTIAL,
    "PATIENT_NAME": MaskingLevel.PARTIAL,

    # Dates
    "BIRTHDATE": MaskingLevel.PARTIAL,
    "BIRTH_DATE": MaskingLevel.PARTIAL,
    "DOB": MaskingLevel.PARTIAL,
    "DATE_OF_BIRTH": MaskingLevel.PARTIAL,
    "DEATHDATE": MaskingLevel.PARTIAL,
    "DEATH_DATE": MaskingLevel.PARTIAL,

    # Geographic
    "ADDRESS": MaskingLevel.FULL,
    "STREET": MaskingLevel.FULL,
    "CITY": MaskingLevel.PARTIAL,
    "STATE": MaskingLevel.NONE,
    "ZIP": MaskingLevel.PARTIAL,
    "ZIPCODE": MaskingLevel.PARTIAL,
    "COUNTY": MaskingLevel.PARTIAL,
    "LAT": MaskingLevel.FULL,
    "LON": MaskingLevel.FULL,
    "LATITUDE": MaskingLevel.FULL,
    "LONGITUDE": MaskingLevel.FULL,

    # Contact Information
    "PHONE": MaskingLevel.FULL,
    "TELEPHONE": MaskingLevel.FULL,
    "MOBILE": MaskingLevel.FULL,
    "EMAIL": MaskingLevel.FULL,
    "FAX": MaskingLevel.FULL,

    # Medical Record Numbers
    "MRN": MaskingLevel.FULL,
    "MEDICAL_RECORD_NUMBER": MaskingLevel.FULL,
    "PATIENT_ID": MaskingLevel.PARTIAL,

    # Financial
    "HEALTHCARE_EXPENSES": MaskingLevel.PARTIAL,
    "HEALTHCARE_COVERAGE": MaskingLevel.PARTIAL,
    "INCOME": MaskingLevel.FULL,

    # Other Identifiers
    "ID": MaskingLevel.PARTIAL,

    # FHIR-specific columns
    "IDENTIFIER_SSN": MaskingLevel.FULL,
    "IDENTIFIER_PASSPORT": MaskingLevel.FULL,
    "IDENTIFIER_DRIVERS_LICENSE": MaskingLevel.FULL,
    "IDENTIFIER_MRN": MaskingLevel.FULL,
    "NAME_GIVEN": MaskingLevel.PARTIAL,
    "NAME_FAMILY": MaskingLevel.PARTIAL,
    "NAME_MAIDEN": MaskingLevel.PARTIAL,
    "NAME_PREFIX": MaskingLevel.PARTIAL,
    "NAME_SUFFIX": MaskingLevel.PARTIAL,
    "DECEASED_DATE_TIME": MaskingLevel.PARTIAL,
    "ADDRESS_LINE": MaskingLevel.FULL,
    "ADDRESS_CITY": MaskingLevel.PARTIAL,
    "ADDRESS_POSTAL_CODE": MaskingLevel.PARTIAL,
    "ADDRESS_LATITUDE": MaskingLevel.FULL,
    "ADDRESS_LONGITUDE": MaskingLevel.FULL,
    "TELECOM_PHONE_HOME": MaskingLevel.FULL,
    "TELECOM_PHONE_MOBILE": MaskingLevel.FULL,
    "TELECOM_PHONE_WORK": MaskingLevel.FULL,
    "TELECOM_PHONE": MaskingLevel.FULL,
    "TELECOM_EMAIL": MaskingLevel.FULL,
    "IDENTIFIER_NPI": MaskingLevel.PARTIAL,
}

# Columns that should NEVER be returned (block query if selected)
BLOCKED_COLUMNS: Set[str] = {
    "SSN",
    "SOCIAL_SECURITY",
    "PASSPORT",
    "DRIVERS",
    "DRIVERS_LICENSE",
    "IDENTIFIER_SSN",
    "IDENTIFIER_PASSPORT",
    "IDENTIFIER_DRIVERS_LICENSE",
}

# Columns that require HITL approval to access
HITL_REQUIRED_COLUMNS: Set[str] = {
    "FIRST",
    "LAST",
    "BIRTHDATE",
    "ADDRESS",
    "PHONE",
    "EMAIL",
    "NAME_GIVEN",
    "NAME_FAMILY",
    "NAME_MAIDEN",
    "BIRTH_DATE",
    "TELECOM_EMAIL",
    "TELECOM_PHONE_HOME",
    "TELECOM_PHONE_MOBILE",
    "TELECOM_PHONE_WORK",
    "ADDRESS_LINE",
    "IDENTIFIER_MRN",
}


# ============================================================================
# PHI PATTERNS - Regex patterns to detect PHI in text
# ============================================================================

PHI_PATTERNS: Dict[str, re.Pattern] = {
    "ssn": re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),
    "phone": re.compile(r'\b(?:\+1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "dob": re.compile(r'\b(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b'),
    "zip": re.compile(r'\b\d{5}(?:[-]\d{4})?\b'),
    "mrn": re.compile(r'\bMRN[-:\s]?\d{6,10}\b', re.IGNORECASE),
    "uuid": re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE),
    "credit_card": re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'),
}


# ============================================================================
# TOXICITY PATTERNS - Harmful or inappropriate content
# ============================================================================

TOXIC_PATTERNS: Dict[str, re.Pattern] = {
    "hate_speech": re.compile(
        r'\b(hate|kill|attack|destroy|eliminate)\s+(patients?|people|users?)\b',
        re.IGNORECASE
    ),
    "discrimination": re.compile(
        r'\b(only|exclude|discriminate|filter\s+out)\s+(race|gender|religion|ethnicity|nationality)\b',
        re.IGNORECASE
    ),
    "exfiltration": re.compile(
        r'\b(dump|export|download|extract)\s+(all|every|entire)\s+(data|records?|patients?|database)\b',
        re.IGNORECASE
    ),
    "malicious": re.compile(
        r'\b(hack|exploit|bypass|circumvent|disable)\s+(security|audit|logging|access)\b',
        re.IGNORECASE
    ),
    "privacy_violation": re.compile(
        r'\b(stalk|track|monitor|spy\s+on)\s+(patient|person|individual)\b',
        re.IGNORECASE
    ),
    "unauthorized": re.compile(
        r'\b(without\s+consent|unauthorized|illegally|secretly)\s+(access|view|share)\b',
        re.IGNORECASE
    ),
    "bulk_request": re.compile(
        r'\b(list|show|get|select)\s+(all|every)\s+(ssn|social\s+security|passport|license)\b',
        re.IGNORECASE
    ),
    "profanity": re.compile(
        r'\b(fuck|shit|damn|ass|bitch|bastard)\b',
        re.IGNORECASE
    ),
}

# Toxicity severity levels (0-10 scale)
TOXICITY_SEVERITY: Dict[str, int] = {
    "hate_speech": 10,        # Immediate block
    "malicious": 10,          # Immediate block
    "privacy_violation": 9,   # Block
    "unauthorized": 9,        # Block
    "bulk_request": 8,        # Block
    "discrimination": 8,      # Block
    "exfiltration": 7,        # Require HITL
    "profanity": 3,           # Warning only
}


# ============================================================================
# MASKING FORMATS
# ============================================================================

MASK_FORMATS: Dict[str, str] = {
    "ssn": "***-**-{last4}",
    "phone": "(**) ***-{last4}",
    "email": "{first}***@***.***",
    "name": "{first}***",
    "date": "****-**-{day}",
    "address": "[ADDRESS REDACTED]",
    "uuid": "{first8}***-****-****-****-************",
    "default": "[REDACTED]",
}
