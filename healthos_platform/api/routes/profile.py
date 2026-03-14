"""
Eminence HealthOS — User Profile API Routes
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pyotp
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.api.schemas import (
    ChangePasswordRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from healthos_platform.database import get_db
from healthos_platform.models import User
from healthos_platform.security.auth import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["User Profile"])

AVATAR_DIR = Path("/app/uploads/avatars")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


async def _get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    return await _get_user(db, ctx.user_id)


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    body: UserProfileUpdateRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile information."""
    user = await _get_user(db, ctx.user_id)

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None:
        # Check email not taken by another user in same org
        existing = await db.execute(
            select(User).where(
                User.org_id == user.org_id,
                User.email == body.email,
                User.id != user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = body.email
    if body.phone is not None:
        user.phone = body.phone
    if body.profile is not None:
        user.profile = {**user.profile, **body.profile}

    await db.flush()
    await db.refresh(user)
    return user


@router.post("/me/avatar", response_model=UserProfileResponse)
async def upload_avatar(
    file: UploadFile,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a profile picture."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")

    data = await file.read()
    if len(data) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 5 MB")

    # Generate unique filename from user id + content hash
    content_hash = hashlib.sha256(data).hexdigest()[:12]
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{ctx.user_id}_{content_hash}.{ext}"

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    avatar_path = AVATAR_DIR / filename
    avatar_path.write_bytes(data)

    user = await _get_user(db, ctx.user_id)
    user.avatar_url = f"/uploads/avatars/{filename}"
    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/me/avatar", response_model=UserProfileResponse)
async def delete_avatar(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the current user's avatar."""
    user = await _get_user(db, ctx.user_id)
    if user.avatar_url:
        old_path = Path("/app") / user.avatar_url.lstrip("/")
        if old_path.exists():
            old_path.unlink()
    user.avatar_url = None
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/me/change-password")
async def change_password(
    body: ChangePasswordRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    user = await _get_user(db, ctx.user_id)

    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = hash_password(body.new_password)
    await db.flush()
    return {"message": "Password changed successfully"}


@router.post("/me/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new MFA secret. User must verify with a code to activate."""
    user = await _get_user(db, ctx.user_id)
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")

    secret = pyotp.random_base32()
    user.mfa_secret = secret
    await db.flush()

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name="Eminence HealthOS")
    return MFASetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/me/mfa/verify")
async def verify_and_enable_mfa(
    body: MFAVerifyRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a TOTP code and enable MFA."""
    user = await _get_user(db, ctx.user_id)
    if not user.mfa_secret:
        raise HTTPException(status_code=400, detail="Run MFA setup first")
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(body.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user.mfa_enabled = True
    await db.flush()
    return {"message": "MFA enabled successfully"}


@router.post("/me/mfa/disable")
async def disable_mfa(
    body: MFAVerifyRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA after verifying a valid code."""
    user = await _get_user(db, ctx.user_id)
    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(body.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user.mfa_enabled = False
    user.mfa_secret = None
    await db.flush()
    return {"message": "MFA disabled successfully"}


@router.delete("/me")
async def delete_my_account(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete the current user's account by deactivating it."""
    user = await _get_user(db, ctx.user_id)
    user.is_active = False
    await db.flush()
    return {"message": "Account deactivated successfully"}
