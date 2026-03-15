"""Cohort and PopulationMetric models for population health analytics."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.config.database import Base
from shared.models.base import UUIDMixin, TimestampMixin, TenantMixin


class Cohort(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "cohorts"
    __table_args__ = (
        Index("ix_cohorts_org_name", "tenant_id", "name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    criteria: Mapped[dict] = mapped_column(JSONB, default=dict)
    patient_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_distribution: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by_agent: Mapped[str] = mapped_column(String(100), default="")

    # Relationships
    population_metrics = relationship(
        "PopulationMetric", back_populates="cohort", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Cohort {self.name} ({self.patient_count} patients)>"


class PopulationMetric(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "population_metrics"
    __table_args__ = (
        Index("ix_pop_metrics_cohort_type", "cohort_id", "metric_type"),
        Index("ix_pop_metrics_period", "period_start", "period_end"),
    )

    cohort_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorts.id"), nullable=True
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    cohort = relationship("Cohort", back_populates="population_metrics")

    def __repr__(self):
        return f"<PopulationMetric {self.metric_type}={self.value}>"
