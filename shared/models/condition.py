"""Condition model — FHIR R4 Condition (diagnoses)."""

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class Condition(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "conditions"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )

    fhir_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    clinical_status: Mapped[str] = mapped_column(
        String(20), default="active",
    )  # active, recurrence, relapse, inactive, remission, resolved
    verification_status: Mapped[str] = mapped_column(
        String(20), default="confirmed",
    )  # unconfirmed, provisional, differential, confirmed, refuted
    category: Mapped[str] = mapped_column(
        String(30), default="encounter-diagnosis",
    )  # problem-list-item, encounter-diagnosis

    # ICD-10 coding
    icd10_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    display: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mild, moderate, severe

    # Dates
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    abatement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recorded_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Clinical
    body_site: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="conditions")

    def __repr__(self):
        return f"<Condition {self.icd10_code}: {self.display}>"
