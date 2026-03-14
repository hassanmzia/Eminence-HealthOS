"""
Eminence HealthOS — Cohort Service

CRUD and stats helpers for the ``cohorts`` table.
All functions accept an ``AsyncSession`` as first argument so callers
(agents, routes, background tasks) control the unit-of-work boundary.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.cohort import Cohort

logger = logging.getLogger(__name__)


# ── Create ────────────────────────────────────────────────────────────────────


async def create_cohort(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str,
    criteria: dict,
    created_by_agent: str = "",
) -> Cohort:
    """Persist a new patient cohort.

    Parameters
    ----------
    db:
        Active async database session.
    org_id:
        Organisation / tenant identifier (stored in ``tenant_id``).
    name:
        Human-readable cohort name.
    criteria:
        JSON-serialisable filter criteria that define the cohort.
    created_by_agent:
        Name of the agent that requested creation.
    """
    cohort = Cohort(
        tenant_id=str(org_id),
        name=name,
        criteria=criteria,
        created_by_agent=created_by_agent,
    )
    db.add(cohort)
    await db.flush()
    logger.info("Created cohort %s (%s) for org %s", cohort.id, name, org_id)
    return cohort


# ── Read ──────────────────────────────────────────────────────────────────────


async def get_cohort(db: AsyncSession, cohort_id: uuid.UUID) -> Cohort | None:
    """Fetch a single cohort by primary key."""
    result = await db.execute(
        select(Cohort).where(Cohort.id == cohort_id)
    )
    return result.scalars().first()


async def list_cohorts(db: AsyncSession, org_id: uuid.UUID) -> Sequence[Cohort]:
    """Return all cohorts belonging to an organisation."""
    result = await db.execute(
        select(Cohort)
        .where(Cohort.tenant_id == str(org_id))
        .order_by(Cohort.created_at.desc())
    )
    return result.scalars().all()


# ── Update ────────────────────────────────────────────────────────────────────


async def update_cohort_stats(
    db: AsyncSession,
    cohort_id: uuid.UUID,
    patient_count: int,
    risk_distribution: dict,
) -> Cohort | None:
    """Refresh the cached statistics on a cohort row.

    Typically called after a background re-computation of the cohort
    membership.
    """
    await db.execute(
        update(Cohort)
        .where(Cohort.id == cohort_id)
        .values(
            patient_count=patient_count,
            risk_distribution=risk_distribution,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.flush()
    logger.info(
        "Updated cohort %s stats — %d patients", cohort_id, patient_count
    )
    return await get_cohort(db, cohort_id)


# ── Delete ────────────────────────────────────────────────────────────────────


async def delete_cohort(db: AsyncSession, cohort_id: uuid.UUID) -> bool:
    """Delete a cohort by primary key.

    Returns ``True`` if the row existed and was removed.
    """
    cohort = await get_cohort(db, cohort_id)
    if cohort is None:
        return False
    await db.delete(cohort)
    await db.flush()
    logger.info("Deleted cohort %s", cohort_id)
    return True
