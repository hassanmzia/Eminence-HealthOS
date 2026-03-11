"""HIPAA audit log model — tamper-evident via hash chaining."""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class AuditLog(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "audit_logs"

    # Event
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(30), default="agent")  # agent, physician, system
    patient_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Resource
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Details
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Network
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Hash chain
    previous_hash: Mapped[str] = mapped_column(String(64), default="genesis")
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog {self.event_type} actor={self.actor_id}>"
