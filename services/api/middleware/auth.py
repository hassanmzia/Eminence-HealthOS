"""
Authentication middleware and dependencies.

Supports JWT tokens and Keycloak OIDC.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from healthos_platform.config.settings import get_settings

logger = logging.getLogger("healthos.middleware.auth")

security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Represents the authenticated user."""
    def __init__(
        self,
        user_id: str,
        email: str,
        role: str,
        tenant_id: str,
        permissions: list[str] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id
        self.permissions = permissions or []

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or self.role == "admin"


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    tenant_id: str,
    permissions: list[str] = None,
) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    from datetime import timedelta
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "permissions": permissions or [],
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """Extract and validate current user from JWT token."""
    if credentials is None:
        return None

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return CurrentUser(
            user_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            role=payload.get("role", "viewer"),
            tenant_id=payload.get("tenant_id", settings.default_tenant_id),
            permissions=payload.get("permissions", []),
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from e


async def require_auth(
    user: Optional[CurrentUser] = Depends(get_current_user),
) -> CurrentUser:
    """Dependency that requires authentication."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def require_role(*roles: str):
    """Dependency factory that requires specific roles."""
    async def _check(user: CurrentUser = Depends(require_auth)):
        if user.role not in roles and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return user
    return _check
