"""
PHI Detector

Detects Protected Health Information in SQL queries, column names, and free text.
Identifies blocked columns, HITL-required columns, and risk scoring.
"""

import re
from typing import Dict, List, Set, Tuple, Any
from .config import (
    SENSITIVE_COLUMNS,
    BLOCKED_COLUMNS,
    HITL_REQUIRED_COLUMNS,
    PHI_PATTERNS,
    MaskingLevel,
)


class PHIDetector:
    """Detects Protected Health Information in queries and data."""

    def __init__(self):
        self.sensitive_columns = SENSITIVE_COLUMNS
        self.blocked_columns = BLOCKED_COLUMNS
        self.hitl_required_columns = HITL_REQUIRED_COLUMNS
        self.phi_patterns = PHI_PATTERNS

    def detect_columns_in_sql(self, sql: str) -> Dict[str, Any]:
        """
        Detect sensitive columns referenced in a SQL query.

        Returns dict with:
            sensitive_columns, blocked_columns, hitl_required_columns,
            has_select_all, violations, risk_increase
        """
        sql_upper = sql.upper()
        result = {
            "sensitive_columns": [],
            "blocked_columns": [],
            "hitl_required_columns": [],
            "has_select_all": False,
            "violations": [],
            "risk_increase": 0.0,
        }

        # Check for SELECT *
        if re.search(r"SELECT\s+\*", sql_upper):
            result["has_select_all"] = True
            result["violations"].append(
                "SELECT * returns all columns including sensitive PHI data. "
                "Please specify only the columns you need."
            )
            result["risk_increase"] += 0.3

        # Check each sensitive column
        for column, masking_level in self.sensitive_columns.items():
            patterns = [
                rf"\b{column}\b",
                rf'"{column}"',
                rf"'{column}'",
            ]

            for pattern in patterns:
                if re.search(pattern, sql_upper):
                    result["sensitive_columns"].append(column)

                    if column in self.blocked_columns:
                        result["blocked_columns"].append(column)
                        result["violations"].append(
                            f"Access to {column} is prohibited. "
                            "This column contains highly sensitive PHI."
                        )
                        result["risk_increase"] += 0.5
                    elif column in self.hitl_required_columns:
                        result["hitl_required_columns"].append(column)
                        result["risk_increase"] += 0.2
                    elif masking_level != MaskingLevel.NONE:
                        result["risk_increase"] += 0.1

                    break

        # Deduplicate
        result["sensitive_columns"] = list(set(result["sensitive_columns"]))
        result["blocked_columns"] = list(set(result["blocked_columns"]))
        result["hitl_required_columns"] = list(set(result["hitl_required_columns"]))

        return result

    def detect_phi_in_text(self, text: str) -> Dict[str, List[Tuple[str, int, int]]]:
        """
        Detect PHI patterns in free text.

        Returns dict mapping pattern name to list of (match, start, end) tuples.
        """
        found = {}
        for pattern_name, pattern in self.phi_patterns.items():
            matches = list(pattern.finditer(text))
            if matches:
                found[pattern_name] = [
                    (match.group(), match.start(), match.end())
                    for match in matches
                ]
        return found

    def has_phi(self, text: str) -> bool:
        """Quick check if text contains any PHI."""
        for pattern in self.phi_patterns.values():
            if pattern.search(text):
                return True
        return False

    def get_column_masking_level(self, column_name: str) -> MaskingLevel:
        """Get the masking level for a column."""
        return self.sensitive_columns.get(column_name.upper(), MaskingLevel.NONE)

    def is_blocked_column(self, column_name: str) -> bool:
        """Check if column access should be blocked."""
        return column_name.upper() in self.blocked_columns

    def requires_hitl(self, column_name: str) -> bool:
        """Check if column access requires HITL approval."""
        return column_name.upper() in self.hitl_required_columns


# Module-level convenience functions
_detector = PHIDetector()


def detect_phi_columns(sql: str) -> Dict[str, Any]:
    """Detect PHI columns in SQL query."""
    return _detector.detect_columns_in_sql(sql)


def detect_phi_in_text(text: str) -> Dict[str, List[Tuple[str, int, int]]]:
    """Detect PHI patterns in text."""
    return _detector.detect_phi_in_text(text)


def has_phi(text: str) -> bool:
    """Quick PHI check."""
    return _detector.has_phi(text)
