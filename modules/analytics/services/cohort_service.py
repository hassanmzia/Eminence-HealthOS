"""
Cohort service layer.

CRUD and stats operations for patient cohorts backed by async SQLAlchemy.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.cohort import Cohort

logger = logging.getLogger("healthos.analytics.cohort_service")


async def create_cohort(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str,
    criteria: dict[str, Any],
    created_by_agent: str = "",
) -> Cohort:
    """Persist a new patient cohort.

    Parameters
    ----------
    db:
        Active async database session.
    org_id:
        Organisation / tenant identifier.
    name:
        Human-readable cohort name.
    criteria:
        JSON-serializable filter criteria that define cohort membership.
    created_by_agent:
        Identifier of the agent that requested creation.

    Returns
    -------
    Cohort
        The newly created ORM instance (already flushed, not yet committed).
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


async def get_cohort(
    db: AsyncSession,
    cohort_id: uuid.UUID,
) -> Optional[Cohort]:
    """Fetch a single cohort by primary key."""
    result = await db.execute(
        select(Cohort).where(Cohort.id == cohort_id)
    )
    return result.scalars().first()


async def list_cohorts(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> Sequence[Cohort]:
    """Return all cohorts belonging to an organisation, ordered by creation date."""
    result = await db.execute(
        select(Cohort)
        .where(Cohort.tenant_id == str(org_id))
        .order_by(Cohort.created_at.desc())
    )
    return result.scalars().all()


async def update_cohort_stats(
    db: AsyncSession,
    cohort_id: uuid.UUID,
    patient_count: int,
    risk_distribution: dict[str, Any],
) -> Optional[Cohort]:
    """Refresh the cached statistics on a cohort.

    Typically called after a background re-computation of cohort membership.
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
        "Updated cohort %s stats — patients=%d",
        cohort_id,
        patient_count,
    )
    return await get_cohort(db, cohort_id)


async def delete_cohort(
    db: AsyncSession,
    cohort_id: uuid.UUID,
) -> bool:
    """Delete a cohort.

    Uses soft-delete if the model supports it, otherwise performs a hard delete.
    Returns ``True`` if a row was affected.
    """
    cohort = await get_cohort(db, cohort_id)
    if cohort is None:
        return False

    # Soft-delete when the mixin is present
    if hasattr(cohort, "is_deleted"):
        cohort.is_deleted = True
        cohort.deleted_at = datetime.now(timezone.utc)
    else:
        await db.delete(cohort)

    await db.flush()
    logger.info("Deleted cohort %s", cohort_id)
    return True
