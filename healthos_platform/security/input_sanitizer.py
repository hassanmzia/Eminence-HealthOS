"""
Eminence HealthOS — Input Sanitizer
Validates and sanitizes API inputs to prevent injection attacks.
"""

from __future__ import annotations

import html
import re
from typing import Any

import structlog

logger = structlog.get_logger()

# Dangerous patterns to detect
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\b\s)", re.IGNORECASE),
    re.compile(r"(--|;|/\*|\*/|'OR\s)", re.IGNORECASE),
    re.compile(r"(\bOR\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
]

XSS_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"<iframe", re.IGNORECASE),
    re.compile(r"<object", re.IGNORECASE),
    re.compile(r"<embed", re.IGNORECASE),
]

PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"%2e%2e", re.IGNORECASE),
]

# Maximum sizes
MAX_STRING_LENGTH = 10_000
MAX_FIELD_NAME_LENGTH = 100
MAX_NESTED_DEPTH = 10


class InputSanitizer:
    """Validates and sanitizes input data for security threats."""

    @staticmethod
    def detect_sql_injection(value: str) -> bool:
        """Check for SQL injection patterns."""
        for pattern in SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                return True
        return False

    @staticmethod
    def detect_xss(value: str) -> bool:
        """Check for XSS attack patterns."""
        for pattern in XSS_PATTERNS:
            if pattern.search(value):
                return True
        return False

    @staticmethod
    def detect_path_traversal(value: str) -> bool:
        """Check for path traversal attempts."""
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if pattern.search(value):
                return True
        return False

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize a string value — HTML-encode special characters."""
        if len(value) > MAX_STRING_LENGTH:
            value = value[:MAX_STRING_LENGTH]
        return html.escape(value, quote=True)

    @classmethod
    def validate_input(cls, data: Any, depth: int = 0) -> list[str]:
        """
        Validate input data for security threats.
        Returns a list of threat descriptions found.
        """
        threats: list[str] = []

        if depth > MAX_NESTED_DEPTH:
            threats.append(f"Input nesting depth exceeds {MAX_NESTED_DEPTH}")
            return threats

        if isinstance(data, str):
            if len(data) > MAX_STRING_LENGTH:
                threats.append(f"String exceeds max length ({len(data)} > {MAX_STRING_LENGTH})")
            if cls.detect_sql_injection(data):
                threats.append(f"Possible SQL injection detected")
            if cls.detect_xss(data):
                threats.append(f"Possible XSS detected")
            if cls.detect_path_traversal(data):
                threats.append(f"Possible path traversal detected")
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(key, str) and len(key) > MAX_FIELD_NAME_LENGTH:
                    threats.append(f"Field name exceeds max length: {key[:20]}...")
                threats.extend(cls.validate_input(value, depth + 1))
        elif isinstance(data, list):
            for item in data:
                threats.extend(cls.validate_input(item, depth + 1))

        return threats

    @classmethod
    def sanitize_dict(cls, data: dict, depth: int = 0) -> dict:
        """Recursively sanitize all string values in a dictionary."""
        if depth > MAX_NESTED_DEPTH:
            return data

        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, depth + 1)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_dict(item, depth + 1) if isinstance(item, dict)
                    else cls.sanitize_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
