"""
HealthOS PHI Filter Module

Provides HIPAA-compliant PHI detection, masking, and toxicity filtering
for clinical data queries and agent outputs.
"""

from .config import (
    MaskingLevel,
    SENSITIVE_COLUMNS,
    BLOCKED_COLUMNS,
    HITL_REQUIRED_COLUMNS,
    PHI_PATTERNS,
    TOXIC_PATTERNS,
    TOXICITY_SEVERITY,
    MASK_FORMATS,
)
from .detector import PHIDetector, detect_phi_columns, detect_phi_in_text, has_phi
from .masker import PHIMasker, mask_phi_in_dict, mask_phi_in_text, mask_phi_in_rows
from .toxicity import ToxicityFilter, check_query_toxicity, check_sql_toxicity

__all__ = [
    "MaskingLevel",
    "SENSITIVE_COLUMNS",
    "BLOCKED_COLUMNS",
    "HITL_REQUIRED_COLUMNS",
    "PHI_PATTERNS",
    "TOXIC_PATTERNS",
    "TOXICITY_SEVERITY",
    "MASK_FORMATS",
    "PHIDetector",
    "detect_phi_columns",
    "detect_phi_in_text",
    "has_phi",
    "PHIMasker",
    "mask_phi_in_dict",
    "mask_phi_in_text",
    "mask_phi_in_rows",
    "ToxicityFilter",
    "check_query_toxicity",
    "check_sql_toxicity",
]
