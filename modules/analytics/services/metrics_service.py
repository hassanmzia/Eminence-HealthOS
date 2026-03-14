"""
Eminence HealthOS — Metrics Service

Recording and querying population-health metrics, plus an aggregate
population summary computed from live DB tables (patients, risk_scores,
observations).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.analytics import AnalyticsRiskScore
from shared.models.cohort import Cohort, PopulationMetric
from shared.models.observation import Observation
from shared.models.patient import Patient

logger = logging.getLogger(__name__)


# ── Record ────────────────────────────────────────────────────────────────────


async def record_metric(
    db: AsyncSession,
    org_id: uuid.UUID,
    cohort_id: uuid.UUID | None,
    metric_type: str,
    value: float,
    period_start: datetime,
    period_end: datetime,
    breakdown: dict | None = None,
) -> PopulationMetric:
    """Insert a new population metric row.

    Parameters
    ----------
    db:
        Active async database session.
    org_id:
        Organisation / tenant identifier (stored in ``tenant_id``).
    cohort_id:
        Optional FK to the cohort this metric belongs to.
    metric_type:
        Label such as ``"readmission_rate"``, ``"avg_a1c"``, etc.
    value:
        The numeric metric value.
    period_start / period_end:
        The time window the metric covers.
    breakdown:
        Optional JSON breakdown (e.g. by age band or condition).
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
        "Recorded metric %s=%s for org %s (cohort %s)",
        metric_type, value, org_id, cohort_id,
    )
    return metric


# ── Query ─────────────────────────────────────────────────────────────────────


async def get_metrics(
    db: AsyncSession,
    org_id: uuid.UUID,
    metric_type: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> Sequence[PopulationMetric]:
    """Query population metrics with optional filters.

    All filter parameters are optional; omit to return all metrics for the
    organisation.
    """
    stmt = select(PopulationMetric).where(
        PopulationMetric.tenant_id == str(org_id)
    )
    if metric_type is not None:
        stmt = stmt.where(PopulationMetric.metric_type == metric_type)
    if period_start is not None:
        stmt = stmt.where(PopulationMetric.period_start >= period_start)
    if period_end is not None:
        stmt = stmt.where(PopulationMetric.period_end <= period_end)

    stmt = stmt.order_by(PopulationMetric.period_start.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_cohort_metrics(
    db: AsyncSession,
    cohort_id: uuid.UUID,
) -> Sequence[PopulationMetric]:
    """Return every metric associated with a given cohort."""
    result = await db.execute(
        select(PopulationMetric)
        .where(PopulationMetric.cohort_id == cohort_id)
        .order_by(PopulationMetric.period_start.desc())
    )
    return result.scalars().all()


# ── Aggregate Summary ─────────────────────────────────────────────────────────


async def compute_population_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Build an aggregate population-health snapshot from live DB tables.

    Queries ``patients``, ``risk_scores``, and ``observations`` to produce
    a summary dict suitable for dashboards / executive reports.

    Returns
    -------
    dict with keys:
        total_patients, avg_risk_score, risk_level_distribution,
        observation_count, cohort_count.
    """
    org_str = str(org_id)

    # Total patients
    total_patients_q = await db.execute(
        select(func.count(Patient.id)).where(
            and_(
                Patient.tenant_id == org_str,
                Patient.is_deleted.is_(False),
            )
        )
    )
    total_patients: int = total_patients_q.scalar() or 0

    # Average risk score (from patients table)
    avg_risk_q = await db.execute(
        select(func.avg(Patient.risk_score)).where(
            and_(
                Patient.tenant_id == org_str,
                Patient.is_deleted.is_(False),
                Patient.risk_score.isnot(None),
            )
        )
    )
    avg_risk_score: float = round(avg_risk_q.scalar() or 0.0, 4)

    # Risk-level distribution from risk_scores table
    risk_dist_q = await db.execute(
        select(
            AnalyticsRiskScore.risk_level,
            func.count(AnalyticsRiskScore.id),
        )
        .where(AnalyticsRiskScore.tenant_id == org_str)
        .group_by(AnalyticsRiskScore.risk_level)
    )
    risk_level_distribution: dict[str, int] = {
        row[0] or "unknown": row[1] for row in risk_dist_q.all()
    }

    # Observation count
    obs_count_q = await db.execute(
        select(func.count(Observation.id)).where(
            Observation.tenant_id == org_str,
        )
    )
    observation_count: int = obs_count_q.scalar() or 0

    # Cohort count
    cohort_count_q = await db.execute(
        select(func.count(Cohort.id)).where(
            Cohort.tenant_id == org_str,
        )
    )
    cohort_count: int = cohort_count_q.scalar() or 0

    summary = {
        "total_patients": total_patients,
        "avg_risk_score": avg_risk_score,
        "risk_level_distribution": risk_level_distribution,
        "observation_count": observation_count,
        "cohort_count": cohort_count,
    }
    logger.info("Computed population summary for org %s", org_id)
    return summary
