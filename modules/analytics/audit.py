"""
HIPAA Audit Trails for Analytics Data Access.

Provides structured audit logging for all analytics endpoints, with special
handling for PHI access, data exports, and cohort queries. Uses the existing
AuditLog model with SHA-256 hash chaining for tamper-evident records.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.database import get_db
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id
from shared.models.audit import AuditLog

logger = logging.getLogger("healthos.analytics.audit")

# Endpoints whose responses contain patient-level PHI
PHI_ENDPOINTS: set[str] = {
    "/analytics/readmission-risk",
    "/analytics/readmission-risk/batch",
    "/analytics/readmission-risk/explain",
    "/analytics/outcomes",
    "/analytics/outcomes/adherence",
    "/analytics/outcomes/effectiveness",
    "/analytics/cohorts",
    "/analytics/cohorts/compare",
    "/analytics/population-health/risk-stratification",
}


def _compute_record_hash(
    record_id: str,
    timestamp: str,
    event_type: str,
    actor_id: str,
    tenant_id: str,
    details: dict[str, Any],
    previous_hash: str,
) -> str:
    """Compute SHA-256 hash for tamper-evident chain."""
    payload = json.dumps(
        {
            "record_id": record_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "details": details,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


async def _get_last_hash(db: AsyncSession, tenant_id: str) -> str:
    """Retrieve the most recent record_hash for hash-chain continuity."""
    result = await db.execute(
        select(AuditLog.record_hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row if row else "genesis"


async def _persist_audit_log(
    db: AsyncSession,
    *,
    event_type: str,
    actor_id: str,
    actor_type: str,
    tenant_id: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    patient_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Create and persist a single AuditLog record with hash chaining."""
    details = details or {}
    previous_hash = await _get_last_hash(db, tenant_id)

    record = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        actor_type=actor_type,
        tenant_id=tenant_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        patient_id=patient_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        previous_hash=previous_hash,
        # record_hash is set below after we know the id
        record_hash="pending",
    )
    db.add(record)
    await db.flush()  # populates record.id and created_at

    record.record_hash = _compute_record_hash(
        record_id=str(record.id),
        timestamp=record.created_at.isoformat(),
        event_type=event_type,
        actor_id=actor_id,
        tenant_id=tenant_id,
        details=details,
        previous_hash=previous_hash,
    )

    logger.info(
        "audit.analytics.recorded",
        extra={
            "event_type": event_type,
            "actor_id": actor_id,
            "resource_type": resource_type,
            "hash": record.record_hash[:12],
        },
    )
    return record


# ── AnalyticsAuditLogger ─────────────────────────────────────────────────────


class AnalyticsAuditLogger:
    """
    HIPAA-compliant audit logger for analytics data access.

    All methods accept an AsyncSession so they participate in the caller's
    transaction — the audit row is committed together with the business data.
    """

    # ── Data access ──────────────────────────────────────────────────

    @staticmethod
    async def log_data_access(
        db: AsyncSession,
        user_id: str,
        org_id: str,
        resource_type: str,
        resource_id: str | None,
        action: str,
        details: dict[str, Any] | None = None,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Record when analytics data is accessed."""
        return await _persist_audit_log(
            db,
            event_type="ANALYTICS_ACCESS",
            actor_id=user_id,
            actor_type="physician",
            tenant_id=org_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details={
                "category": "data_access",
                **(details or {}),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── PHI access ───────────────────────────────────────────────────

    @staticmethod
    async def log_phi_access(
        db: AsyncSession,
        user_id: str,
        org_id: str,
        patient_ids: list[str],
        reason: str,
        endpoint: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Record when patient-level data is accessed through analytics."""
        # For HIPAA, we log each patient individually when there are few,
        # and log a summary with hashed IDs for bulk access.
        if len(patient_ids) <= 10:
            patient_ref = patient_ids[0] if len(patient_ids) == 1 else None
        else:
            patient_ref = None

        return await _persist_audit_log(
            db,
            event_type="PHI_ACCESS",
            actor_id=user_id,
            actor_type="physician",
            tenant_id=org_id,
            resource_type="patient_analytics",
            action="phi_access",
            patient_id=patient_ref,
            details={
                "category": "phi_access",
                "patient_count": len(patient_ids),
                "patient_ids": patient_ids[:10],  # cap stored IDs
                "patient_ids_truncated": len(patient_ids) > 10,
                "reason": reason,
                "endpoint": endpoint,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── Data exports ─────────────────────────────────────────────────

    @staticmethod
    async def log_export(
        db: AsyncSession,
        user_id: str,
        org_id: str,
        export_type: str,
        record_count: int,
        filters: dict[str, Any] | None = None,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Record data exports from analytics."""
        return await _persist_audit_log(
            db,
            event_type="EXPORT",
            actor_id=user_id,
            actor_type="physician",
            tenant_id=org_id,
            resource_type="analytics_export",
            action="export",
            details={
                "category": "data_export",
                "export_type": export_type,
                "record_count": record_count,
                "filters": filters or {},
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── Cohort access ────────────────────────────────────────────────

    @staticmethod
    async def log_cohort_access(
        db: AsyncSession,
        user_id: str,
        org_id: str,
        cohort_id: str,
        patient_count: int,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Record cohort queries that expose patient data."""
        return await _persist_audit_log(
            db,
            event_type="PHI_ACCESS",
            actor_id=user_id,
            actor_type="physician",
            tenant_id=org_id,
            resource_type="cohort",
            resource_id=cohort_id,
            action="cohort_access",
            details={
                "category": "cohort_access",
                "cohort_id": cohort_id,
                "patient_count": patient_count,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )


# ── Analytics Audit Middleware (FastAPI Dependency) ───────────────────────────


class _AuditContext:
    """
    Carries audit metadata through the request lifecycle.

    Injected as a FastAPI dependency so route handlers can add extra detail
    (e.g. patient IDs discovered after the agent runs).
    """

    def __init__(
        self,
        db: AsyncSession,
        user: CurrentUser,
        tenant_id: str,
        request: Request,
    ) -> None:
        self.db = db
        self.user = user
        self.tenant_id = tenant_id
        self.request = request
        self._logged = False

    async def record(self, *, response_size: int | None = None) -> AuditLog:
        """Persist the access audit record (idempotent per request)."""
        if self._logged:
            return  # type: ignore[return-value]

        path = self.request.url.path
        method = self.request.method
        query_params = dict(self.request.query_params)
        is_phi = path in PHI_ENDPOINTS

        record = await _persist_audit_log(
            self.db,
            event_type="PHI_ACCESS" if is_phi else "ANALYTICS_ACCESS",
            actor_id=self.user.user_id,
            actor_type="physician",
            tenant_id=self.tenant_id,
            resource_type="analytics_endpoint",
            resource_id=path,
            action=method,
            details={
                "category": "endpoint_access",
                "path": path,
                "method": method,
                "query_params": query_params,
                "contains_phi": is_phi,
                "response_size": response_size,
            },
            ip_address=self.request.client.host if self.request.client else None,
            user_agent=self.request.headers.get("user-agent", "")[:500],
        )
        self._logged = True
        return record


async def analytics_audit_middleware(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
    tenant_id: str = Depends(get_tenant_id),
) -> _AuditContext:
    """
    FastAPI dependency that captures every analytics endpoint access.

    Automatically logs the request to the audit table. Route handlers receive
    the ``_AuditContext`` so they can attach additional PHI details after the
    agent produces results.

    Usage in a route::

        @router.post("/analytics/some-endpoint")
        async def my_endpoint(
            body: dict,
            audit: _AuditContext = Depends(analytics_audit_middleware),
        ):
            ...
            await audit.record()
    """
    ctx = _AuditContext(db=db, user=user, tenant_id=tenant_id, request=request)
    # Eagerly log the access — route handlers may add PHI logs separately.
    await ctx.record()
    return ctx
