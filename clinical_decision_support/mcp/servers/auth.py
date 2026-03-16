"""
JWT Authentication for MCP Servers
Provides secure authentication and authorization for healthcare API access.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, Header, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User roles for authorization"""
    ADMIN = "admin"
    PHYSICIAN = "physician"
    NURSE = "nurse"
    TECHNICIAN = "technician"
    PATIENT = "patient"
    SYSTEM = "system"


@dataclass
class TokenPayload:
    """JWT token payload"""
    user_id: str
    username: str
    role: UserRole
    permissions: List[str]
    exp: datetime
    iat: datetime
    patient_ids: List[str] = None  # For patient-specific access control


@dataclass
class AuthenticatedUser:
    """Authenticated user context"""
    user_id: str
    username: str
    role: UserRole
    permissions: List[str]
    patient_ids: List[str]
    token: str


# Role-based permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "read:all", "write:all", "admin:users", "admin:audit",
        "mcp:fhir:read", "mcp:fhir:write",
        "mcp:labs:read", "mcp:labs:write",
        "mcp:rag:read", "mcp:pharmacy:read", "mcp:pharmacy:write"
    ],
    UserRole.PHYSICIAN: [
        "read:patients", "write:patients", "read:vitals", "write:vitals",
        "read:orders", "write:orders", "read:prescriptions", "write:prescriptions",
        "mcp:fhir:read", "mcp:fhir:write",
        "mcp:labs:read", "mcp:rag:read", "mcp:pharmacy:read", "mcp:pharmacy:write"
    ],
    UserRole.NURSE: [
        "read:patients", "read:vitals", "write:vitals",
        "read:orders", "read:medications",
        "mcp:fhir:read", "mcp:labs:read", "mcp:rag:read"
    ],
    UserRole.TECHNICIAN: [
        "read:vitals", "write:vitals", "read:labs", "write:labs",
        "mcp:fhir:read", "mcp:labs:read", "mcp:labs:write"
    ],
    UserRole.PATIENT: [
        "read:own_data",
        "mcp:fhir:read:own"
    ],
    UserRole.SYSTEM: [
        "read:all", "write:all",
        "mcp:fhir:read", "mcp:fhir:write",
        "mcp:labs:read", "mcp:labs:write",
        "mcp:rag:read", "mcp:pharmacy:read", "mcp:pharmacy:write"
    ]
}


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    username: str,
    role: UserRole,
    patient_ids: List[str] = None,
    extra_permissions: List[str] = None,
    expires_delta: timedelta = None
) -> str:
    """Create a JWT access token"""
    if expires_delta is None:
        expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)

    now = datetime.utcnow()
    expire = now + expires_delta

    # Get role-based permissions
    permissions = ROLE_PERMISSIONS.get(role, []).copy()
    if extra_permissions:
        permissions.extend(extra_permissions)

    payload = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "permissions": list(set(permissions)),
        "patient_ids": patient_ids or [],
        "iat": now,
        "exp": expire
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        return TokenPayload(
            user_id=payload["sub"],
            username=payload["username"],
            role=UserRole(payload["role"]),
            permissions=payload["permissions"],
            patient_ids=payload.get("patient_ids", []),
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"])
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    authorization: str = Header(default=None)
) -> Optional[AuthenticatedUser]:
    """
    Get the current authenticated user from JWT token.
    Returns None if auth is not required and no token provided.
    """
    token = None

    # Try to get token from security scheme first
    if credentials:
        token = credentials.credentials
    # Fall back to Authorization header
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        if REQUIRE_AUTH:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return None

    payload = decode_token(token)

    return AuthenticatedUser(
        user_id=payload.user_id,
        username=payload.username,
        role=payload.role,
        permissions=payload.permissions,
        patient_ids=payload.patient_ids,
        token=token
    )


def require_auth(user: Optional[AuthenticatedUser] = Depends(get_current_user)) -> AuthenticatedUser:
    """Dependency that requires authentication"""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_permission(permission: str):
    """Factory for permission-checking dependency"""
    def check_permission(user: AuthenticatedUser = Depends(require_auth)) -> AuthenticatedUser:
        if permission not in user.permissions and "read:all" not in user.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission} required"
            )
        return user
    return check_permission


def require_role(allowed_roles: List[UserRole]):
    """Factory for role-checking dependency"""
    def check_role(user: AuthenticatedUser = Depends(require_auth)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Requires role {[r.value for r in allowed_roles]}"
            )
        return user
    return check_role


def require_patient_access(patient_id: str):
    """Check if user has access to specific patient"""
    def check_access(user: AuthenticatedUser = Depends(require_auth)) -> AuthenticatedUser:
        # Admins and physicians can access all patients
        if user.role in [UserRole.ADMIN, UserRole.PHYSICIAN, UserRole.SYSTEM]:
            return user

        # Patients can only access their own data
        if user.role == UserRole.PATIENT:
            if patient_id not in user.patient_ids:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Not authorized for this patient's data"
                )

        # Nurses and technicians check patient_ids list
        if user.patient_ids and patient_id not in user.patient_ids:
            # Check if they have general read access
            if "read:patients" not in user.permissions:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Not authorized for this patient's data"
                )

        return user
    return check_access


class AuthMiddleware:
    """
    Authentication middleware for FastAPI.
    Can be used to add auth checking to all routes.
    """

    def __init__(self, app, exclude_paths: List[str] = None):
        self.app = app
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]

    async def __call__(self, request: Request, call_next):
        # Skip auth for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Skip if auth not required
        if not REQUIRE_AUTH:
            return await call_next(request)

        # Check for token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"}
            )

        try:
            token = auth_header.split(" ", 1)[1]
            decode_token(token)  # Validate token
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

        return await call_next(request)


# Token generation utilities for testing
def create_test_token(role: UserRole = UserRole.PHYSICIAN) -> str:
    """Create a test token for development"""
    return create_access_token(
        user_id="test_user",
        username="testuser",
        role=role,
        patient_ids=["*"]  # Access to all patients
    )


def create_system_token() -> str:
    """Create a system token for inter-service communication"""
    return create_access_token(
        user_id="system",
        username="system",
        role=UserRole.SYSTEM,
        expires_delta=timedelta(days=365)
    )
