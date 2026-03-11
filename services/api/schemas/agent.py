"""Agent decision and interaction schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from services.api.schemas.common import HealthOSBase


class AgentDecisionResponse(HealthOSBase):
    id: UUID
    trace_id: str
    agent_name: str
    agent_tier: str
    patient_id: Optional[UUID] = None
    decision_type: str
    decision: str
    rationale: str
    confidence: float
    feature_contributions: list
    alternatives: list
    evidence_references: list
    requires_hitl: bool
    safety_flags: list
    risk_level: Optional[str] = None
    input_summary: dict
    output_summary: dict
    duration_ms: int
    model_used: Optional[str] = None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    created_at: datetime


class AgentInteractionResponse(HealthOSBase):
    id: UUID
    trace_id: str
    sender_agent: str
    receiver_agent: str
    message_type: str
    capability: Optional[str] = None
    payload: dict
    response: dict
    success: bool
    error: Optional[str] = None
    duration_ms: int
    created_at: datetime


class AgentStatusResponse(BaseModel):
    agent_name: str
    agent_tier: str
    status: str  # active, idle, error
    total_decisions: int
    avg_confidence: float
    avg_duration_ms: float
    last_active: Optional[datetime] = None
