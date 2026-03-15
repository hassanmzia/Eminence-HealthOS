"""PortalMessage model — secure messages between patients and care teams."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class PortalMessage(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A secure message in the patient portal."""

    __tablename__ = "portal_messages"
    __table_args__ = (
        Index("ix_portal_messages_patient", "patient_id"),
        Index("ix_portal_messages_org_patient", "tenant_id", "patient_id"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # patient, provider, system
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<PortalMessage {self.subject!r} from={self.sender_type}>"
