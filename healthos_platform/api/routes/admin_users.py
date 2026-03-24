"""
Eminence HealthOS — Admin User Management API Routes
Allows admins to list, create, update, and deactivate users.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.api.schemas import UserResponse
from healthos_platform.database import get_db
from healthos_platform.models import User
from healthos_platform.security.auth import hash_password

router = APIRouter(prefix="/admin/users", tags=["Admin - User Management"])


def _require_admin(ctx: TenantContext) -> None:
    if ctx.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Self-Promote (bootstrap) ───────────────────────────────────────────────


@router.post("/promote-self", response_model=AdminUserResponse)
async def promote_self_to_admin(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Promote the current user to admin role.
    Only allowed when no admin exists in the organization (bootstrap scenario).
    """
    # Check if any admin already exists in the org
    admin_check = await db.execute(
        select(func.count())
        .select_from(User)
        .where(User.org_id == ctx.org_id, User.role.in_(("admin", "super_admin")), User.is_active == True)
    )
    admin_count = admin_check.scalar() or 0
    if admin_count > 0:
        raise HTTPException(
            status_code=403,
            detail="An admin already exists in this organization. Ask an existing admin to update your role.",
        )

    # Promote the current user
    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = "admin"
    await db.flush()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=user.org_id,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        phone=user.phone,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


# ── Schemas ──────────────────────────────────────────────────────────────────


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    org_id: uuid.UUID
    is_active: bool
    mfa_enabled: bool
    phone: str | None = None
    avatar_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_login: str | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "clinician"


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    phone: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the organization (admin only)."""
    _require_admin(ctx)

    query = select(User).where(User.org_id == ctx.org_id)
    count_query = select(func.count()).select_from(User).where(User.org_id == ctx.org_id)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            User.full_name.ilike(pattern) | User.email.ilike(pattern)
        )
        count_query = count_query.where(
            User.full_name.ilike(pattern) | User.email.ilike(pattern)
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        users=[
            AdminUserResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                org_id=u.org_id,
                is_active=u.is_active,
                mfa_enabled=u.mfa_enabled,
                phone=u.phone,
                avatar_url=u.avatar_url,
                created_at=u.created_at.isoformat() if u.created_at else None,
                updated_at=u.updated_at.isoformat() if u.updated_at else None,
            )
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AdminUserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user in the organization (admin only)."""
    _require_admin(ctx)

    existing = await db.execute(
        select(User).where(User.org_id == ctx.org_id, User.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User with this email already exists")

    user = User(
        org_id=ctx.org_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=user.org_id,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        phone=user.phone,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.get("/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific user's details (admin only)."""
    _require_admin(ctx)

    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == ctx.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=user.org_id,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        phone=user.phone,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's details (admin only)."""
    _require_admin(ctx)

    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == ctx.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.phone is not None:
        user.phone = body.phone

    await db.flush()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=user.org_id,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        phone=user.phone,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user (admin only). Does not permanently delete."""
    _require_admin(ctx)

    if user_id == ctx.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == ctx.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.flush()
    return {"message": f"User {user.email} deactivated"}
