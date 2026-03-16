"""
Toxicity Filter

Detects and blocks harmful, inappropriate, or malicious queries.
Checks both natural language input and generated SQL for threats.
"""

import re
from typing import Dict, List, Any
from .config import TOXIC_PATTERNS, TOXICITY_SEVERITY


class ToxicityFilter:
    """Filters toxic, harmful, or inappropriate content in queries."""

    BLOCK_THRESHOLD = 7
    HITL_THRESHOLD = 5
    WARNING_THRESHOLD = 3

    def __init__(self):
        self.patterns = TOXIC_PATTERNS
        self.severity = TOXICITY_SEVERITY

    def check_query(self, query: str) -> Dict[str, Any]:
        """
        Check a natural language query for toxicity.

        Returns dict with: is_toxic, should_block, requires_hitl,
        toxicity_score (0-10), violations, message.
        """
        result = {
            "is_toxic": False,
            "should_block": False,
            "requires_hitl": False,
            "toxicity_score": 0.0,
            "violations": [],
            "message": None,
        }

        total_severity = 0
        max_severity = 0

        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(query)
            if matches:
                severity = self.severity.get(pattern_name, 5)
                max_severity = max(max_severity, severity)
                total_severity += severity

                for match in matches:
                    result["violations"].append({
                        "type": pattern_name,
                        "severity": severity,
                        "match": match if isinstance(match, str) else match[0],
                    })

        result["toxicity_score"] = min(10.0, total_severity)

        if result["violations"]:
            result["is_toxic"] = True

            if max_severity >= self.BLOCK_THRESHOLD:
                result["should_block"] = True
                result["message"] = self._get_block_message(result["violations"])
            elif max_severity >= self.HITL_THRESHOLD:
                result["requires_hitl"] = True
                result["message"] = self._get_review_message(result["violations"])
            else:
                result["message"] = self._get_warning_message(result["violations"])

        return result

    def check_sql(self, sql: str) -> Dict[str, Any]:
        """
        Check generated SQL for potential malicious patterns.
        Catches things that might have bypassed the NL check.
        """
        result = {
            "is_suspicious": False,
            "violations": [],
            "message": None,
        }

        suspicious_patterns = {
            "union_injection": re.compile(r"UNION\s+SELECT", re.IGNORECASE),
            "stacked_queries": re.compile(
                r";\s*(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER)", re.IGNORECASE
            ),
            "comment_injection": re.compile(r"--\s*$|/\*.*\*/"),
            "or_true": re.compile(
                r"OR\s+['\"]?1['\"]?\s*=\s*['\"]?1['\"]?", re.IGNORECASE
            ),
            "bulk_select": re.compile(
                r"SELECT\s+\*\s+FROM\s+\w+\s*(?:;|$)", re.IGNORECASE
            ),
            "information_schema": re.compile(
                r"INFORMATION_SCHEMA|PG_CATALOG|SYS\.", re.IGNORECASE
            ),
            "sleep_benchmark": re.compile(
                r"SLEEP\s*\(|BENCHMARK\s*\(|WAITFOR\s+DELAY", re.IGNORECASE
            ),
        }

        for pattern_name, pattern in suspicious_patterns.items():
            if pattern.search(sql):
                result["is_suspicious"] = True
                result["violations"].append({
                    "type": pattern_name,
                    "description": self._get_sql_violation_description(pattern_name),
                })

        if result["violations"]:
            result["message"] = (
                "SQL query contains suspicious patterns that may indicate "
                "injection or malicious intent. Query has been blocked."
            )

        return result

    def _get_block_message(self, violations: List[Dict]) -> str:
        types = set(v["type"] for v in violations)

        if "hate_speech" in types:
            return (
                "Your query has been blocked due to inappropriate content. "
                "Please rephrase your request in a professional manner."
            )
        if "malicious" in types:
            return (
                "Your query appears to be attempting unauthorized access. "
                "This incident has been logged."
            )
        if "bulk_request" in types:
            return (
                "Bulk requests for sensitive data (SSN, passport, etc.) are not permitted. "
                "Please request specific records with appropriate justification."
            )
        if "privacy_violation" in types:
            return (
                "Your query suggests unauthorized surveillance or tracking. "
                "This type of request is not permitted."
            )
        return (
            "Your query has been blocked due to policy violations. "
            "Please contact an administrator if you believe this is an error."
        )

    def _get_review_message(self, violations: List[Dict]) -> str:
        return (
            "Your query requires additional review before processing. "
            "A healthcare administrator will review this request."
        )

    def _get_warning_message(self, violations: List[Dict]) -> str:
        return (
            "Please use professional language when interacting with "
            "the healthcare database system."
        )

    def _get_sql_violation_description(self, pattern_name: str) -> str:
        descriptions = {
            "union_injection": "UNION-based SQL injection attempt",
            "stacked_queries": "Stacked query injection attempt",
            "comment_injection": "SQL comment injection",
            "or_true": "Boolean-based SQL injection",
            "bulk_select": "Unrestricted bulk data selection",
            "information_schema": "Database schema reconnaissance",
            "sleep_benchmark": "Time-based SQL injection",
        }
        return descriptions.get(pattern_name, "Unknown SQL injection pattern")


# Module-level convenience functions
_filter = ToxicityFilter()


def check_query_toxicity(query: str) -> Dict[str, Any]:
    """Check query for toxicity."""
    return _filter.check_query(query)


def check_sql_toxicity(sql: str) -> Dict[str, Any]:
    """Check SQL for suspicious patterns."""
    return _filter.check_sql(sql)
