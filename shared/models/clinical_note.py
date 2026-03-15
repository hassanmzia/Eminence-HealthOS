"""ClinicalNote model — SOAP / progress / procedure notes tied to encounters."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class ClinicalNote(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A clinical note (SOAP, progress, procedure) for an encounter."""

    __tablename__ = "clinical_notes"
    __table_args__ = (
        Index("ix_clinical_notes_encounter", "encounter_id"),
        Index("ix_clinical_notes_session", "session_id"),
        Index("ix_clinical_notes_status", "status"),
    )

    # Links
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("telehealth_sessions.id"), nullable=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    # Note classification
    note_type: Mapped[str] = mapped_column(
        String(30), default="soap",
    )  # soap, progress, procedure
    status: Mapped[str] = mapped_column(
        String(30), default="draft",
    )  # draft, pending_review, signed, amended

    # SOAP sections
    subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Coding
    icd10_codes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cpt_codes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # AI provenance
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Signing
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    signed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    # Amendment history — list of {amended_at, amended_by, reason, changes}
    amendments: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    encounter = relationship("Encounter", backref="clinical_note_records")

    def __repr__(self) -> str:
        return f"<ClinicalNote {self.note_type} status={self.status}>"
