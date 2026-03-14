"""InsuranceVerification model — tracks insurance eligibility checks."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin


class InsuranceVerification(Base, UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = "insurance_verifications"
    __table_args__ = (
        Index("ix_insurance_verifications_tenant_status", "tenant_id", "status"),
        Index("ix_insurance_verifications_patient", "patient_id"),
    )

    # Foreign keys
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )

    # Payer info
    payer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    payer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    member_id: Mapped[str] = mapped_column(String(100), nullable=False)
    group_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="pending",
    )  # pending, verified, failed, expired
    eligibility_status: Mapped[str] = mapped_column(
        String(30), default="active",
    )  # active, inactive, terminated

    # Coverage dates
    coverage_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Financial details
    copay_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    deductible: Mapped[float | None] = mapped_column(Float, nullable=True)
    deductible_met: Mapped[float | None] = mapped_column(Float, nullable=True)
    out_of_pocket_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Benefits
    benefits_summary: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Verification timestamp
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    patient = relationship("Patient", lazy="joined")

    def __repr__(self):
        return f"<InsuranceVerification payer={self.payer_name} status={self.status}>"
