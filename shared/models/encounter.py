"""Encounter model — FHIR R4 Encounter resource."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class Encounter(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "encounters"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )
    provider_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    # FHIR Encounter fields
    fhir_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="in-progress",
    )  # planned, arrived, triaged, in-progress, onleave, finished, cancelled
    encounter_class: Mapped[str] = mapped_column(
        String(30), default="AMB",
    )  # AMB, IMP, EMER, VR (virtual), HH (home health)
    encounter_type: Mapped[str] = mapped_column(
        String(50), default="office_visit",
    )  # office_visit, telehealth, rpm_review, emergency, inpatient
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Timing
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Clinical
    reason_code: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ICD-10
    reason_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    discharge_disposition: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # AI-generated
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_follow_up_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="encounters")

    def __repr__(self):
        return f"<Encounter {self.encounter_type} status={self.status}>"
