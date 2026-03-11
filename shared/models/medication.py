"""Medication models — current medications + medication orders."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class Medication(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "medications"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )

    # Drug identification
    rxnorm_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ndc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Dosage
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dosage_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    dosage_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    route: Mapped[str | None] = mapped_column(String(30), nullable=True)  # oral, IV, topical, etc.

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active",
    )  # active, on-hold, cancelled, completed, stopped
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_prn: Mapped[bool] = mapped_column(Boolean, default=False)

    # Prescriber
    prescriber_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    # Relationships
    patient = relationship("Patient", back_populates="medications")

    def __repr__(self):
        return f"<Medication {self.name} {self.dosage}>"


class MedicationOrder(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "medication_orders"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )
    medication_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medications.id"), nullable=True,
    )
    prescriber_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    # Order details
    order_type: Mapped[str] = mapped_column(String(30), default="new")  # new, refill, modify
    status: Mapped[str] = mapped_column(
        String(30), default="draft",
    )  # draft, pending_approval, approved, rejected, filled, cancelled
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refills: Mapped[int] = mapped_column(Integer, default=0)

    # AI-generated
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_hitl: Mapped[bool] = mapped_column(Boolean, default=True)

    # Approval
    approved_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<MedicationOrder {self.medication_name} status={self.status}>"
