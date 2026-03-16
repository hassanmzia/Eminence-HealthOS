"""
State definitions for the NL-to-SQL multi-agent workflow.
"""

from typing import TypedDict, Optional, List
from enum import Enum


class QueryType(str, Enum):
    """Classification of SQL query types."""
    READ = "READ"
    WRITE = "WRITE"
    UNSAFE = "UNSAFE"


class ApprovalStatus(str, Enum):
    """Status of query approval process."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_EXECUTED = "AUTO_EXECUTED"
    BLOCKED = "BLOCKED"


class HealthcareState(TypedDict, total=False):
    """
    State schema for the Healthcare NL-to-SQL workflow.
    Flows through LangGraph nodes: toxicity check -> schema fetch ->
    SQL generation -> classification -> guardrails -> execution/HITL -> audit.
    """

    # Input
    user_query: str
    session_id: str
    user_id: str
    timestamp: str

    # SQL Generation
    generated_sql: str
    sql_confidence: float

    # Classification
    query_type: str
    risk_score: float
    risk_assessment: str
    guardrail_violations: List[str]

    # HITL
    requires_approval: bool
    approval_status: str
    reviewer_id: Optional[str]
    review_notes: Optional[str]

    # Execution
    execution_result: Optional[str]
    execution_time_ms: Optional[int]
    error_message: Optional[str]

    # Schema context
    schema_context: Optional[str]

    # Audit
    audit_logged: bool


class GuardrailViolation(TypedDict):
    """Guardrail violation details."""
    type: str
    pattern: str
    severity: str
    message: str
