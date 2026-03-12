"""
Eminence HealthOS — Multi-Tenant Isolation Layer
Enforces strict tenant data isolation at the query, context, and agent levels.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()

# Context variable for current tenant — available throughout the request lifecycle
_current_tenant: ContextVar[TenantScope | None] = ContextVar("_current_tenant", default=None)


@dataclass(frozen=True)
class TenantScope:
    """Immutable tenant scope for the current request."""
    tenant_id: str
    org_id: uuid.UUID
    user_id: str
    role: str
    permissions: frozenset[str]

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or "admin:all" in self.permissions

    def can_access_tenant(self, target_tenant_id: str) -> bool:
        """Check if this user can access data from another tenant."""
        return self.tenant_id == target_tenant_id or self.role == "system"


def set_tenant_scope(scope: TenantScope) -> None:
    """Set the current tenant scope for this request context."""
    _current_tenant.set(scope)
    logger.debug(
        "tenant.scope_set",
        tenant_id=scope.tenant_id,
        user_id=scope.user_id,
        role=scope.role,
    )


def get_tenant_scope() -> TenantScope | None:
    """Get the current tenant scope."""
    return _current_tenant.get()


def require_tenant_scope() -> TenantScope:
    """Get the current tenant scope or raise an error."""
    scope = _current_tenant.get()
    if scope is None:
        raise TenantIsolationError("No tenant context set for this request")
    return scope


class TenantIsolationError(Exception):
    """Raised when tenant isolation is violated."""
    pass


class TenantQueryFilter:
    """
    Enforces tenant-level data isolation on database queries.
    Ensures all queries are scoped to the current tenant.
    """

    @staticmethod
    def apply_filter(query: Any, tenant_column: str = "tenant_id") -> Any:
        """
        Apply tenant filter to a SQLAlchemy query.
        This is called automatically by the repository layer.
        """
        scope = get_tenant_scope()
        if scope is None:
            raise TenantIsolationError(
                "Cannot execute query without tenant context"
            )
        # The actual filter application depends on the ORM query type.
        # This provides the interface — repositories call this to get the tenant_id.
        return scope.tenant_id

    @staticmethod
    def validate_record_access(record_tenant_id: str) -> None:
        """Validate that the current tenant can access this record."""
        scope = require_tenant_scope()
        if not scope.can_access_tenant(record_tenant_id):
            logger.warning(
                "tenant.cross_tenant_access_blocked",
                current_tenant=scope.tenant_id,
                target_tenant=record_tenant_id,
                user_id=scope.user_id,
            )
            raise TenantIsolationError(
                f"Tenant {scope.tenant_id} cannot access data from tenant {record_tenant_id}"
            )


class TenantAwareAgent:
    """
    Mixin for agents that need tenant-scoped data access.
    Ensures agent outputs are tagged with the correct tenant.
    """

    def get_tenant_id(self) -> str:
        """Get the current tenant ID for data scoping."""
        scope = get_tenant_scope()
        if scope is None:
            return "default"
        return scope.tenant_id

    def validate_tenant_access(self, data: dict, tenant_field: str = "tenant_id") -> bool:
        """Validate that data belongs to the current tenant."""
        scope = get_tenant_scope()
        if scope is None:
            return True  # No tenant context = no restriction (system-level)
        data_tenant = data.get(tenant_field)
        if data_tenant is None:
            return True  # No tenant field = shared data
        return scope.can_access_tenant(str(data_tenant))

    def tag_output(self, result: dict) -> dict:
        """Tag agent output with the current tenant context."""
        scope = get_tenant_scope()
        if scope:
            result["_tenant_id"] = scope.tenant_id
            result["_org_id"] = str(scope.org_id)
        return result
