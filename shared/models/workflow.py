"""
Workflow persistence models — stores workflow definitions and steps in PostgreSQL.

Supports the PersistentWorkflowEngine with full state tracking, JSONB context
storage, and multi-tenant isolation.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class Workflow(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Persisted workflow definition."""

    __tablename__ = "workflows"

    workflow_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    patient_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="created", index=True)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to steps
    steps: Mapped[list["WorkflowStepModel"]] = relationship(
        "WorkflowStepModel",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStepModel.created_at",
    )

    def __repr__(self) -> str:
        return f"<Workflow {self.workflow_id} type={self.workflow_type} status={self.status}>"


class WorkflowStepModel(Base, UUIDMixin, TimestampMixin):
    """Persisted workflow step."""

    __tablename__ = "workflow_steps"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True,
    )
    step_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    depends_on: Mapped[list] = mapped_column(JSONB, default=list)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    timeout_minutes: Mapped[int] = mapped_column(Integer, default=60)
    sla_hours: Mapped[float] = mapped_column(Float, default=24.0)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship back to workflow
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="steps")

    def __repr__(self) -> str:
        return f"<WorkflowStepModel {self.step_id} status={self.status}>"
