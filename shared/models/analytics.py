"""Analytics models — risk scoring and predictive analytics."""

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class AnalyticsRiskScore(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "risk_scores"
    __table_args__ = (
        Index("ix_risk_scores_patient_type", "patient_id", "score_type"),
        Index("ix_risk_scores_risk_level", "risk_level"),
    )

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    score_type: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contributing_factors: Mapped[list] = mapped_column(JSONB, default=list)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    recommendations: Mapped[list] = mapped_column(JSONB, default=list)

    def __repr__(self):
        return f"<AnalyticsRiskScore {self.score_type}: {self.score} ({self.risk_level})>"
