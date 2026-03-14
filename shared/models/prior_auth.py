"""PriorAuthRequest model — tracks prior authorization lifecycle."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin


class PriorAuthRequest(Base, UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = "prior_auth_requests"
    __table_args__ = (
        Index("ix_prior_auth_requests_tenant_status", "tenant_id", "status"),
        Index("ix_prior_auth_requests_patient", "patient_id"),
    )

    # Foreign keys
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    provider_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )
    encounter_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=True,
    )

    # Payer / procedure info
    payer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    cpt_code: Mapped[str] = mapped_column(String(20), nullable=False)
    icd10_codes: Mapped[dict] = mapped_column(JSONB, default=list)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(30), default="pending",
    )  # pending, submitted, approved, denied, appealed
    urgency: Mapped[str] = mapped_column(
        String(20), default="routine",
    )  # routine, urgent, emergency

    # Clinical assessment
    clinical_necessity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    documentation_checklist: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Payer response
    payer_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    auth_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # AI
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient = relationship("Patient", lazy="joined")
    provider = relationship("Provider", lazy="joined")

    def __repr__(self):
        return f"<PriorAuthRequest cpt={self.cpt_code} status={self.status}>"
