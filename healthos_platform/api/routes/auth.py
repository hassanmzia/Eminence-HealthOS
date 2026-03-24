"""
Eminence HealthOS — Auth API Routes
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from healthos_platform.database import get_db
from healthos_platform.models import Organization, User
from healthos_platform.security.auth import create_tokens, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Find organization
    result = await db.execute(select(Organization).where(Organization.slug == request.org_slug))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check for existing user
    result = await db.execute(
        select(User).where(User.org_id == org.id, User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(
        org_id=org.id,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        full_name=request.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and return JWT tokens."""
    # Fetch all matching users — unique constraint is (org_id, email), so the
    # same email can exist in multiple orgs.
    result = await db.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    users = result.scalars().all()

    # Try each matching user until password matches
    matched_user = None
    for u in users:
        if verify_password(request.password, u.hashed_password):
            matched_user = u
            break

    if not matched_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tokens = create_tokens(matched_user.id, matched_user.org_id, matched_user.role)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )
