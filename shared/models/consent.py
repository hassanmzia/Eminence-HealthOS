"""Consent record model for patient data processing consent."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class ConsentRecord(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "consent_records"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True,
    )

    consent_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # treatment, research, data_sharing, ai_processing, rpm_monitoring
    status: Mapped[str] = mapped_column(
        String(20), default="active",
    )  # active, revoked, expired
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Scope
    scope: Mapped[dict] = mapped_column(JSONB, default=dict)
    data_categories: Mapped[dict] = mapped_column(JSONB, default=list)

    # Dates
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Source
    source: Mapped[str] = mapped_column(String(50), default="patient_portal")
    verification_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<ConsentRecord {self.consent_type} status={self.status}>"
