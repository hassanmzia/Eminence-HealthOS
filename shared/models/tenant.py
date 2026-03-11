"""Tenant model for multi-tenant SaaS isolation."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    organization_type: Mapped[str] = mapped_column(
        String(50), default="clinic",
    )  # clinic, hospital, health_system, research
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tier: Mapped[str] = mapped_column(
        String(30), default="standard",
    )  # starter, standard, enterprise

    # Configuration
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    feature_flags: Mapped[dict] = mapped_column(JSONB, default=dict)
    llm_config: Mapped[dict] = mapped_column(
        JSONB, default=dict,
    )  # per-tenant LLM provider overrides

    # Limits
    max_patients: Mapped[int] = mapped_column(Integer, default=1000)
    max_agents: Mapped[int] = mapped_column(Integer, default=30)
    max_api_calls_per_hour: Mapped[int] = mapped_column(Integer, default=10000)

    # Contact
    admin_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<Tenant {self.slug}>"
