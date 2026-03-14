"""FollowUpPlan model — post-visit care instructions and next steps."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class FollowUpPlan(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Post-encounter follow-up plan with action items, meds, referrals."""

    __tablename__ = "follow_up_plans"
    __table_args__ = (
        Index("ix_follow_up_plans_encounter", "encounter_id"),
        Index("ix_follow_up_plans_session", "session_id"),
        Index("ix_follow_up_plans_status", "status"),
    )

    # Links
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("telehealth_sessions.id"), nullable=True,
    )

    # Plan details
    follow_up_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monitoring_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_items: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    patient_education: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    medications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    referrals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="draft",
    )  # draft, active, completed

    # AI provenance
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    encounter = relationship("Encounter", backref="follow_up_plans")

    def __repr__(self) -> str:
        return f"<FollowUpPlan encounter={self.encounter_id} status={self.status}>"
