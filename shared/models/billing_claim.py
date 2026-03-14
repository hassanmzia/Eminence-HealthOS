"""BillingClaim model — tracks insurance claim lifecycle."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin


class BillingClaim(Base, UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = "billing_claims"
    __table_args__ = (
        Index("ix_billing_claims_tenant_status", "tenant_id", "status"),
        Index("ix_billing_claims_patient", "patient_id"),
        Index("ix_billing_claims_encounter", "encounter_id"),
    )

    # Foreign keys
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    encounter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False,
    )
    rendering_provider_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    # Payer
    payer_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Claim identity
    claim_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    claim_type: Mapped[str] = mapped_column(
        String(30), default="professional",
    )  # professional, institutional

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="draft",
    )  # draft, validated, submitted, accepted, denied, paid, appealed

    # Codes
    cpt_codes: Mapped[dict] = mapped_column(JSONB, default=list)
    icd10_codes: Mapped[dict] = mapped_column(JSONB, default=list)

    # Financial
    total_charge: Mapped[float] = mapped_column(Float, nullable=False)
    allowed_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    paid_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    patient_responsibility: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Claim details
    place_of_service: Mapped[str] = mapped_column(String(10), nullable=False)
    billing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Submission tracking
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    adjudicated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Denial / EDI
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    edi_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    patient = relationship("Patient", lazy="joined")
    encounter = relationship("Encounter", lazy="joined")
    rendering_provider = relationship("Provider", lazy="joined")

    def __repr__(self):
        return f"<BillingClaim claim={self.claim_number} status={self.status}>"
