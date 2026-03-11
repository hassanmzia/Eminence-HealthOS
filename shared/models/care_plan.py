"""Care plan model — FHIR R4 CarePlan resource."""

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class CarePlan(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "care_plans"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )
    provider_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )

    fhir_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active",
    )  # draft, active, on-hold, revoked, completed
    intent: Mapped[str] = mapped_column(String(20), default="plan")  # proposal, plan, order

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), default="chronic_care",
    )  # chronic_care, discharge, wellness, rpm

    # Dates
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Structured content
    goals: Mapped[dict] = mapped_column(JSONB, default=list)
    activities: Mapped[dict] = mapped_column(JSONB, default=list)
    addresses: Mapped[dict] = mapped_column(JSONB, default=list)  # condition references

    # AI-generated
    ai_generated: Mapped[bool] = mapped_column(default=False)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="care_plans")

    def __repr__(self):
        return f"<CarePlan {self.title} status={self.status}>"
