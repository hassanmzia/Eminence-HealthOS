"""Patient model — FHIR R4 Patient resource mapped to PostgreSQL."""

from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin


class Patient(Base, UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = "patients"
    __table_args__ = (
        Index("ix_patients_tenant_mrn", "tenant_id", "mrn", unique=True),
        Index("ix_patients_tenant_active", "tenant_id", "is_deleted"),
    )

    # FHIR identifiers
    mrn: Mapped[str] = mapped_column(String(50), nullable=False)  # Medical Record Number
    fhir_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    # Demographics
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)  # male, female, other, unknown
    gender_identity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    race: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")

    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(3), default="US")

    # Emergency contact
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emergency_contact_relationship: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Insurance
    insurance_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    insurance_member_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insurance_group_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Clinical
    primary_provider_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )
    blood_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # FHIR extensions
    extensions: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    observations = relationship("Observation", back_populates="patient", lazy="dynamic")
    conditions = relationship("Condition", back_populates="patient", lazy="dynamic")
    encounters = relationship("Encounter", back_populates="patient", lazy="dynamic")
    medications = relationship("Medication", back_populates="patient", lazy="dynamic")
    alerts = relationship("ClinicalAlert", back_populates="patient", lazy="dynamic")
    care_plans = relationship("CarePlan", back_populates="patient", lazy="dynamic")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Patient {self.mrn}: {self.full_name}>"
