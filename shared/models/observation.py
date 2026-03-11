"""Observation model — FHIR R4 Observation (vitals, labs, device readings)."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class Observation(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "observations"
    __table_args__ = (
        Index("ix_observations_patient_category", "patient_id", "category"),
        Index("ix_observations_patient_loinc", "patient_id", "loinc_code"),
        Index("ix_observations_effective", "effective_datetime"),
    )

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )
    encounter_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=True,
    )

    # FHIR Observation fields
    fhir_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="final")  # final, preliminary, amended
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )  # vital-signs, laboratory, device, survey

    # Coding
    loinc_code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "8480-6" (systolic BP)
    display: Mapped[str] = mapped_column(String(255), nullable=False)   # e.g., "Systolic Blood Pressure"

    # Value
    value_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    value_string: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Reference ranges
    reference_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_high: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Interpretation
    interpretation: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )  # N (normal), H (high), L (low), HH (critical high), LL (critical low)

    # Source
    data_source: Mapped[str] = mapped_column(
        String(50), default="manual",
    )  # manual, device, ehr_import, lab_interface
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timing
    effective_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    # Components (e.g., systolic + diastolic for blood pressure)
    components: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="observations")

    def __repr__(self):
        return f"<Observation {self.display}: {self.value_quantity} {self.value_unit}>"
