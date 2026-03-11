"""Agent decision and interaction models for observability and audit."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class AgentDecision(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Persisted record of every agent decision for audit and explainability."""
    __tablename__ = "agent_decisions"
    __table_args__ = (
        Index("ix_agent_decisions_trace", "trace_id"),
        Index("ix_agent_decisions_patient", "patient_id"),
        Index("ix_agent_decisions_agent_tier", "agent_name", "agent_tier"),
    )

    # Trace context
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Agent identity
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_tier: Mapped[str] = mapped_column(String(30), nullable=False)

    # Patient context
    patient_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True,
    )

    # Decision
    decision_type: Mapped[str] = mapped_column(
        String(30), default="recommendation",
    )  # risk_assessment, recommendation, intervention, alert, hitl_request
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Explainability
    feature_contributions: Mapped[dict] = mapped_column(JSONB, default=list)
    alternatives: Mapped[dict] = mapped_column(JSONB, default=list)
    evidence_references: Mapped[dict] = mapped_column(JSONB, default=list)

    # Safety
    requires_hitl: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_flags: Mapped[dict] = mapped_column(JSONB, default=list)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Context
    input_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    # LLM usage
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    def __repr__(self):
        return f"<AgentDecision {self.agent_name}: {self.decision[:50]}>"


class AgentInteraction(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Record of agent-to-agent communication."""
    __tablename__ = "agent_interactions"
    __table_args__ = (
        Index("ix_agent_interactions_trace", "trace_id"),
    )

    trace_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sender_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # request, response, event, error
    capability: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Content
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    response: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self):
        return f"<AgentInteraction {self.sender_agent} → {self.receiver_agent}>"
