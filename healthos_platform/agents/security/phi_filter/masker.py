"""
PHI Masker

Masks/redacts Protected Health Information in query results and text.
Supports four masking levels: NONE, PARTIAL, FULL, REDACT.
Column-aware masking for 60+ HIPAA-sensitive column types.
"""

import re
from typing import Dict, List, Any
from .config import (
    SENSITIVE_COLUMNS,
    PHI_PATTERNS,
    MaskingLevel,
)


class PHIMasker:
    """Masks Protected Health Information in data."""

    def __init__(self, default_level: MaskingLevel = MaskingLevel.PARTIAL):
        self.default_level = default_level
        self.sensitive_columns = SENSITIVE_COLUMNS
        self.phi_patterns = PHI_PATTERNS

    def mask_value(
        self,
        value: Any,
        column_name: str = None,
        masking_level: MaskingLevel = None,
    ) -> Any:
        """Mask a single value based on column name or explicit level."""
        if value is None:
            return None

        if masking_level is None:
            if column_name:
                masking_level = self.sensitive_columns.get(
                    column_name.upper(), MaskingLevel.NONE
                )
            else:
                masking_level = self.default_level

        if masking_level == MaskingLevel.NONE:
            return value

        str_value = str(value)

        if masking_level == MaskingLevel.REDACT:
            return "[REDACTED]"
        if masking_level == MaskingLevel.FULL:
            return self._full_mask(str_value, column_name)
        if masking_level == MaskingLevel.PARTIAL:
            return self._partial_mask(str_value, column_name)

        return value

    def _full_mask(self, value: str, column_name: str = None) -> str:
        """Apply full masking — hide everything."""
        col_upper = (column_name or "").upper()

        if col_upper in ("SSN", "SOCIAL_SECURITY"):
            return "***-**-****"
        if col_upper in ("PHONE", "TELEPHONE", "MOBILE", "FAX"):
            return "(***) ***-****"
        if col_upper == "EMAIL":
            return "***@***.***"
        if col_upper in ("ADDRESS", "STREET"):
            return "[ADDRESS REDACTED]"
        if col_upper in ("LAT", "LON", "LATITUDE", "LONGITUDE"):
            return "**.****"

        return "*" * min(len(value), 20)

    def _partial_mask(self, value: str, column_name: str = None) -> str:
        """Apply partial masking — show some characters."""
        col_upper = (column_name or "").upper()

        # Name: Show first initial
        if col_upper in (
            "FIRST", "LAST", "NAME", "FIRST_NAME", "LAST_NAME",
            "MAIDEN", "MAIDEN_NAME",
        ):
            if len(value) > 0:
                return f"{value[0]}***"
            return "***"

        # SSN: Show last 4
        if col_upper in ("SSN", "SOCIAL_SECURITY"):
            if len(value) >= 4:
                return f"***-**-{value[-4:]}"
            return "***-**-****"

        # Phone: Show last 4
        if col_upper in ("PHONE", "TELEPHONE", "MOBILE"):
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return f"(***) ***-{digits[-4:]}"
            return "(***) ***-****"

        # Date: Show year only
        if col_upper in (
            "BIRTHDATE", "BIRTH_DATE", "DOB", "DATE_OF_BIRTH",
            "DEATHDATE", "DEATH_DATE",
        ):
            if re.match(r"^\d{4}-\d{2}-\d{2}", value):
                return f"{value[:4]}-**-**"
            return "****-**-**"

        # ZIP: Show first 3
        if col_upper in ("ZIP", "ZIPCODE"):
            if len(value) >= 3:
                return f"{value[:3]}**"
            return "*****"

        # City: Show first 3
        if col_upper == "CITY":
            if len(value) >= 3:
                return f"{value[:3]}***"
            return "***"

        # UUID/ID: Show first 8 chars
        if col_upper in ("ID", "PATIENT_ID"):
            if len(value) >= 8:
                return f"{value[:8]}..."
            return value

        # Email: Show first char and mask domain
        if col_upper == "EMAIL":
            if "@" in value:
                parts = value.split("@")
                return f"{parts[0][0]}***@***.***"
            return "***@***.***"

        # Default: show first and last char
        if len(value) > 2:
            return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"
        return "*" * len(value)

    def mask_dict(
        self,
        data: Dict[str, Any],
        masking_level: MaskingLevel = None,
    ) -> Dict[str, Any]:
        """Mask PHI in a dictionary (single row)."""
        masked = {}
        for key, value in data.items():
            level = masking_level or self.sensitive_columns.get(
                key.upper(), MaskingLevel.NONE
            )
            masked[key] = self.mask_value(value, key, level)
        return masked

    def mask_rows(
        self,
        rows: List[Dict[str, Any]],
        masking_level: MaskingLevel = None,
    ) -> List[Dict[str, Any]]:
        """Mask PHI in a list of dictionaries (multiple rows)."""
        return [self.mask_dict(row, masking_level) for row in rows]

    def mask_text(
        self,
        text: str,
        masking_level: MaskingLevel = None,
    ) -> str:
        """Mask PHI patterns found in free text."""
        if not text:
            return text

        level = masking_level or self.default_level
        masked_text = text

        for pattern_name, pattern in self.phi_patterns.items():
            if level == MaskingLevel.FULL or level == MaskingLevel.REDACT:
                masked_text = pattern.sub(
                    "[REDACTED]" if level == MaskingLevel.REDACT
                    else self._get_pattern_mask(pattern_name),
                    masked_text,
                )
            elif level == MaskingLevel.PARTIAL:
                masked_text = pattern.sub(
                    lambda m: self._partial_mask_pattern(m.group(), pattern_name),
                    masked_text,
                )

        return masked_text

    def _get_pattern_mask(self, pattern_name: str) -> str:
        """Get full mask for a pattern type."""
        masks = {
            "ssn": "***-**-****",
            "phone": "(***) ***-****",
            "email": "***@***.***",
            "dob": "****-**-**",
            "zip": "*****",
            "mrn": "MRN-******",
            "uuid": "********-****-****-****-************",
            "credit_card": "****-****-****-****",
        }
        return masks.get(pattern_name, "[REDACTED]")

    def _partial_mask_pattern(self, value: str, pattern_name: str) -> str:
        """Partial mask for detected patterns."""
        if pattern_name == "ssn":
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return f"***-**-{digits[-4:]}"

        if pattern_name == "phone":
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return f"(***) ***-{digits[-4:]}"

        if pattern_name == "email":
            if "@" in value:
                parts = value.split("@")
                return f"{parts[0][0]}***@***.***"

        if pattern_name == "uuid":
            if len(value) >= 8:
                return f"{value[:8]}..."

        return "[REDACTED]"


# Module-level convenience functions
_masker = PHIMasker()


def mask_phi_in_dict(data: Dict[str, Any], level: MaskingLevel = None) -> Dict[str, Any]:
    """Mask PHI in a dictionary."""
    return _masker.mask_dict(data, level)


def mask_phi_in_text(text: str, level: MaskingLevel = None) -> str:
    """Mask PHI in free text."""
    return _masker.mask_text(text, level)


def mask_phi_in_rows(
    rows: List[Dict[str, Any]], level: MaskingLevel = None
) -> List[Dict[str, Any]]:
    """Mask PHI in multiple rows."""
    return _masker.mask_rows(rows, level)
