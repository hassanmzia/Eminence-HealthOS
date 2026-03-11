"""Clinical alert model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class ClinicalAlert(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "clinical_alerts"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )

    # Alert classification
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
    )  # LOW, MEDIUM, HIGH, CRITICAL, EMERGENCY
    category: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # vital_sign, lab_result, medication, risk_score, device
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Source
    source_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    source_observation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="active",
    )  # active, acknowledged, resolved, dismissed
    acknowledged_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Escalation
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    notifications_sent: Mapped[dict] = mapped_column(JSONB, default=list)

    # Relationships
    patient = relationship("Patient", back_populates="alerts")

    def __repr__(self):
        return f"<ClinicalAlert [{self.severity}] {self.title}>"
