"""
Metrics service layer.

Records and queries PopulationMetric rows and computes aggregate
population-health statistics from core clinical tables.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.cohort import PopulationMetric
from shared.models.patient import Patient
from shared.models.analytics import AnalyticsRiskScore
from shared.models.observation import Observation

logger = logging.getLogger("healthos.analytics.metrics_service")


async def record_metric(
    db: AsyncSession,
    org_id: uuid.UUID,
    cohort_id: Optional[uuid.UUID],
    metric_type: str,
    value: float,
    period_start: datetime,
    period_end: datetime,
    breakdown: Optional[dict[str, Any]] = None,
) -> PopulationMetric:
    """Insert a new population-health metric row.

    Parameters
    ----------
    db:
        Active async database session.
    org_id:
        Organisation / tenant identifier.
    cohort_id:
        Optional cohort the metric is scoped to.
    metric_type:
        Metric name / code (e.g. ``"hedis_a1c_control"``).
    value:
        Numeric metric value.
    period_start / period_end:
        Reporting period boundaries.
    breakdown:
        Optional JSON breakdown (e.g. per-condition counts).

    Returns
    -------
    PopulationMetric
        The persisted ORM instance.
    """
    metric = PopulationMetric(
        tenant_id=str(org_id),
        cohort_id=cohort_id,
        metric_type=metric_type,
        value=value,
        period_start=period_start,
        period_end=period_end,
        breakdown=breakdown or {},
    )
    db.add(metric)
    await db.flush()
    logger.info(
        "Recorded metric %s=%s for org %s (cohort=%s)",
        metric_type,
        value,
        org_id,
        cohort_id,
    )
    return metric


async def get_metrics(
    db: AsyncSession,
    org_id: uuid.UUID,
    metric_type: Optional[str] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Sequence[PopulationMetric]:
    """Query population metrics with optional filters.

    Filters are combined with AND when supplied.  Omitting a filter skips that
    condition (i.e. all values match).
    """
    conditions = [PopulationMetric.tenant_id == str(org_id)]

    if metric_type is not None:
        conditions.append(PopulationMetric.metric_type == metric_type)
    if period_start is not None:
        conditions.append(PopulationMetric.period_start >= period_start)
    if period_end is not None:
        conditions.append(PopulationMetric.period_end <= period_end)

    result = await db.execute(
        select(PopulationMetric)
        .where(and_(*conditions))
        .order_by(PopulationMetric.period_start.desc())
    )
    return result.scalars().all()


async def get_cohort_metrics(
    db: AsyncSession,
    cohort_id: uuid.UUID,
) -> Sequence[PopulationMetric]:
    """Return all metrics associated with a specific cohort."""
    result = await db.execute(
        select(PopulationMetric)
        .where(PopulationMetric.cohort_id == cohort_id)
        .order_by(PopulationMetric.period_start.desc())
    )
    return result.scalars().all()


async def compute_population_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Aggregate population-health statistics from core clinical tables.

    Queries ``patients``, ``risk_scores``, and ``observations`` to produce a
    single summary dict suitable for dashboards and executive reports.

    Returns
    -------
    dict
        Keys: ``total_patients``, ``avg_risk_score``, ``risk_distribution``,
        ``recent_observations_count``.
    """
    tenant = str(org_id)

    # Total patients
    total_q = await db.execute(
        select(func.count(Patient.id)).where(
            and_(
                Patient.tenant_id == tenant,
                Patient.is_deleted.is_(False),
            )
        )
    )
    total_patients: int = total_q.scalar() or 0

    # Average risk score from the risk_scores table
    avg_q = await db.execute(
        select(func.avg(AnalyticsRiskScore.score)).where(
            AnalyticsRiskScore.tenant_id == tenant,
        )
    )
    avg_risk: Optional[float] = avg_q.scalar()

    # Risk-level distribution
    dist_q = await db.execute(
        select(
            AnalyticsRiskScore.risk_level,
            func.count(AnalyticsRiskScore.id),
        )
        .where(AnalyticsRiskScore.tenant_id == tenant)
        .group_by(AnalyticsRiskScore.risk_level)
    )
    risk_distribution: dict[str, int] = {
        row[0]: row[1] for row in dist_q.all() if row[0] is not None
    }

    # Recent observations (last 30 days proxy — count all for tenant)
    obs_q = await db.execute(
        select(func.count(Observation.id)).where(
            Observation.tenant_id == tenant,
        )
    )
    recent_observations: int = obs_q.scalar() or 0

    summary = {
        "total_patients": total_patients,
        "avg_risk_score": round(avg_risk, 4) if avg_risk is not None else None,
        "risk_distribution": risk_distribution,
        "recent_observations_count": recent_observations,
    }
    logger.info("Computed population summary for org %s: %s", org_id, summary)
    return summary
