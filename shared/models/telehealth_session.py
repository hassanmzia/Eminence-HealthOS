"""TelehealthSession model — persists virtual visit state to PostgreSQL."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class TelehealthSession(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A telehealth visit from queue entry through completion."""

    __tablename__ = "telehealth_sessions"
    __table_args__ = (
        Index("ix_telehealth_sessions_tenant_status", "tenant_id", "status"),
        Index("ix_telehealth_sessions_patient", "patient_id"),
    )

    # Identifiers
    session_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
    )

    # Participants
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    # Visit metadata
    visit_type: Mapped[str] = mapped_column(
        String(30), default="on_demand",
    )  # on_demand, scheduled, follow_up, urgent
    urgency: Mapped[str] = mapped_column(
        String(20), default="routine",
    )  # routine, urgent, emergent
    status: Mapped[str] = mapped_column(
        String(20), default="waiting",
    )  # waiting, in_progress, completed, cancelled

    # Clinical context
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    symptoms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Queue management
    estimated_wait_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timing
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Link to FHIR Encounter once the visit begins
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=True,
    )

    # Relationships
    patient = relationship("Patient", backref="telehealth_sessions")
    encounter = relationship("Encounter", backref="telehealth_session", uselist=False)

    def __repr__(self) -> str:
        return f"<TelehealthSession {self.session_id} status={self.status}>"
