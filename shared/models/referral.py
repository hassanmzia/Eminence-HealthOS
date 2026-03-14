"""Referral model — tracks specialist referral coordination."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin


class Referral(Base, UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = "referrals"
    __table_args__ = (
        Index("ix_referrals_tenant_status", "tenant_id", "status"),
        Index("ix_referrals_patient", "patient_id"),
    )

    # Foreign keys
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    referring_provider_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False,
    )
    specialist_provider_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )
    encounter_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=True,
    )

    # Referral details
    referral_type: Mapped[str] = mapped_column(String(50), nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    urgency: Mapped[str] = mapped_column(
        String(20), default="routine",
    )  # routine, urgent, stat
    status: Mapped[str] = mapped_column(
        String(30), default="draft",
    )  # draft, submitted, accepted, scheduled, completed, cancelled

    # Clinical
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    icd10_codes: Mapped[dict] = mapped_column(JSONB, default=list)

    # Tracking
    turnaround_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient = relationship("Patient", lazy="joined")
    referring_provider = relationship("Provider", foreign_keys=[referring_provider_id], lazy="joined")
    specialist_provider = relationship("Provider", foreign_keys=[specialist_provider_id], lazy="joined")

    def __repr__(self):
        return f"<Referral specialty={self.specialty} status={self.status}>"
