"""
Eminence HealthOS — Multi-Tenant Middleware
Extracts and validates tenant context from JWT claims on every request.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from healthos_platform.security.auth import TokenPayload, decode_token
from healthos_platform.security.rbac import Permission, has_permission

security = HTTPBearer()


@dataclass
class TenantContext:
    """Current request's tenant and user context."""

    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str

    def has_permission(self, permission: Permission) -> bool:
        return has_permission(self.role, permission)

    def require_permission(self, permission: Permission) -> None:
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}",
            )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TenantContext:
    """FastAPI dependency that extracts and validates the current user from JWT."""
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return TenantContext(
        user_id=uuid.UUID(payload.sub),
        org_id=uuid.UUID(payload.org_id),
        role=payload.role,
    )


async def require_admin(ctx: TenantContext = Depends(get_current_user)) -> TenantContext:
    """Dependency that requires admin role."""
    if ctx.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return ctx


async def require_clinician(ctx: TenantContext = Depends(get_current_user)) -> TenantContext:
    """Dependency that requires clinician or higher role."""
    if ctx.role not in ("admin", "clinician", "care_manager"):
        raise HTTPException(status_code=403, detail="Clinician access required")
    return ctx
