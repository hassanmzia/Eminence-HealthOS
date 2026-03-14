"""
Risk-score service layer.

Records, retrieves, and analyses patient risk scores backed by async
SQLAlchemy and the ``risk_scores`` table (AnalyticsRiskScore model).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.analytics import AnalyticsRiskScore
from shared.models.patient import Patient

logger = logging.getLogger("healthos.analytics.risk_service")


async def record_risk_score(
    db: AsyncSession,
    patient_id: uuid.UUID,
    org_id: uuid.UUID,
    score_type: str,
    score: float,
    risk_level: str,
    factors: Optional[list[Any]] = None,
    recommendations: Optional[list[Any]] = None,
) -> AnalyticsRiskScore:
    """Insert or update a risk-score record for a patient.

    An *upsert* semantic is used: if a row already exists for the same
    ``(patient_id, score_type)`` it is updated in place; otherwise a new row is
    created.

    Parameters
    ----------
    db:
        Active async database session.
    patient_id:
        Patient UUID.
    org_id:
        Organisation / tenant identifier.
    score_type:
        Risk model identifier (e.g. ``"readmission_30d"``, ``"hcc"``).
    score:
        Numeric risk score.
    risk_level:
        Categorical level — ``"low"``, ``"moderate"``, ``"high"``, or ``"critical"``.
    factors:
        Contributing risk factors (stored as JSONB list).
    recommendations:
        Suggested interventions (stored as JSONB list).

    Returns
    -------
    AnalyticsRiskScore
        The upserted ORM instance.
    """
    # Check for existing row (same patient + score_type)
    result = await db.execute(
        select(AnalyticsRiskScore).where(
            and_(
                AnalyticsRiskScore.patient_id == str(patient_id),
                AnalyticsRiskScore.score_type == score_type,
            )
        )
    )
    existing: Optional[AnalyticsRiskScore] = result.scalars().first()

    if existing is not None:
        existing.score = score
        existing.risk_level = risk_level
        existing.contributing_factors = factors or []
        existing.recommendations = recommendations or []
        await db.flush()
        logger.info(
            "Updated risk score %s for patient %s: %s (%s)",
            score_type,
            patient_id,
            score,
            risk_level,
        )
        return existing

    record = AnalyticsRiskScore(
        patient_id=str(patient_id),
        tenant_id=str(org_id),
        score_type=score_type,
        score=score,
        risk_level=risk_level,
        contributing_factors=factors or [],
        recommendations=recommendations or [],
    )
    db.add(record)
    await db.flush()
    logger.info(
        "Recorded risk score %s for patient %s: %s (%s)",
        score_type,
        patient_id,
        score,
        risk_level,
    )
    return record


async def get_patient_risk(
    db: AsyncSession,
    patient_id: uuid.UUID,
) -> Sequence[AnalyticsRiskScore]:
    """Retrieve all risk-score records for a given patient."""
    result = await db.execute(
        select(AnalyticsRiskScore)
        .where(AnalyticsRiskScore.patient_id == str(patient_id))
        .order_by(AnalyticsRiskScore.updated_at.desc())
    )
    return result.scalars().all()


async def get_high_risk_patients(
    db: AsyncSession,
    org_id: uuid.UUID,
    threshold: float = 0.7,
) -> Sequence[AnalyticsRiskScore]:
    """Return risk-score rows where ``score >= threshold`` for an org.

    Results are sorted descending by score so the highest-risk patients
    appear first.
    """
    result = await db.execute(
        select(AnalyticsRiskScore)
        .where(
            and_(
                AnalyticsRiskScore.tenant_id == str(org_id),
                AnalyticsRiskScore.score >= threshold,
            )
        )
        .order_by(AnalyticsRiskScore.score.desc())
    )
    return result.scalars().all()


async def get_risk_distribution(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, int]:
    """Count risk-score records grouped by ``risk_level`` for an organisation.

    Returns
    -------
    dict
        Mapping of risk-level label to patient count, e.g.
        ``{"low": 120, "moderate": 45, "high": 18, "critical": 3}``.
    """
    result = await db.execute(
        select(
            AnalyticsRiskScore.risk_level,
            func.count(AnalyticsRiskScore.id),
        )
        .where(AnalyticsRiskScore.tenant_id == str(org_id))
        .group_by(AnalyticsRiskScore.risk_level)
    )
    distribution: dict[str, int] = {
        row[0]: row[1] for row in result.all() if row[0] is not None
    }
    logger.info("Risk distribution for org %s: %s", org_id, distribution)
    return distribution
