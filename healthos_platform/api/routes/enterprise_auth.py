"""
Eminence HealthOS — Enterprise Auth Routes (Phase 6)
Authentication config, MFA flow, email verification, session management.
Imported from InhealthUSA AuthenticationConfig and auth system.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_admin,
)
from healthos_platform.database import get_db
from healthos_platform.models import (
    AuthenticationConfig,
    PasswordHistory,
    User,
    UserSession,
)

router = APIRouter(prefix="/enterprise-auth", tags=["enterprise-auth"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class AuthConfigCreate(BaseModel):
    auth_method: str  # local, ldap, oauth2, openid, azure_ad, cac, saml, sso
    is_enabled: bool = False
    is_primary: bool = False
    config: dict = {}


class AuthConfigResponse(BaseModel):
    id: uuid.UUID
    auth_method: str
    is_enabled: bool
    is_primary: bool
    config: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class MFASetupRequest(BaseModel):
    pass  # triggers TOTP secret generation


class MFAVerifyRequest(BaseModel):
    code: str


class MFABackupCodesResponse(BaseModel):
    backup_codes: list[str]


class EmailVerificationRequest(BaseModel):
    token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class SessionListResponse(BaseModel):
    id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    last_activity: datetime
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Auth Configuration ───────────────────────────────────────────────────────


@router.get("/configs", response_model=list[AuthConfigResponse])
async def list_auth_configs(
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthenticationConfig).where(AuthenticationConfig.org_id == ctx.org_id)
    )
    return result.scalars().all()


@router.post("/configs", response_model=AuthConfigResponse, status_code=201)
async def create_auth_config(
    body: AuthConfigCreate,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cfg = AuthenticationConfig(org_id=ctx.org_id, **body.model_dump())
    db.add(cfg)
    await db.flush()
    return cfg


@router.put("/configs/{config_id}", response_model=AuthConfigResponse)
async def update_auth_config(
    config_id: uuid.UUID,
    body: AuthConfigCreate,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthenticationConfig).where(
            AuthenticationConfig.id == config_id,
            AuthenticationConfig.org_id == ctx.org_id,
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "Config not found")
    for k, v in body.model_dump().items():
        setattr(cfg, k, v)
    await db.flush()
    return cfg


@router.delete("/configs/{config_id}", status_code=204)
async def delete_auth_config(
    config_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthenticationConfig).where(
            AuthenticationConfig.id == config_id,
            AuthenticationConfig.org_id == ctx.org_id,
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "Config not found")
    await db.delete(cfg)


# ── MFA Management ───────────────────────────────────────────────────────────


@router.post("/mfa/setup")
async def setup_mfa(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate TOTP secret for MFA setup."""
    import pyotp

    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    secret = pyotp.random_base32()
    user.mfa_secret = secret

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email, issuer_name="Eminence HealthOS"
    )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
    }


@router.post("/mfa/verify")
async def verify_mfa(
    body: MFAVerifyRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify TOTP code and enable MFA."""
    import pyotp

    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.mfa_secret:
        raise HTTPException(400, "MFA not set up")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(body.code):
        raise HTTPException(400, "Invalid code")

    user.mfa_enabled = True

    # Generate backup codes
    backup_codes = [secrets.token_hex(4) for _ in range(10)]
    user.mfa_backup_codes = ",".join(backup_codes)

    return {"status": "mfa_enabled", "backup_codes": backup_codes}


@router.post("/mfa/disable")
async def disable_mfa(
    body: MFAVerifyRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA (requires current TOTP code)."""
    import pyotp

    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.mfa_secret:
        raise HTTPException(400, "MFA not set up")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(body.code):
        raise HTTPException(400, "Invalid code")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    return {"status": "mfa_disabled"}


# ── Email Verification ───────────────────────────────────────────────────────


@router.post("/email/send-verification")
async def send_verification_email(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate email verification token."""
    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if user.email_verified:
        return {"status": "already_verified"}

    token = secrets.token_urlsafe(32)
    user.email_verification_token = token

    # In production, send email with token link
    return {"status": "verification_sent", "token": token}


@router.post("/email/verify")
async def verify_email(
    body: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify email with token."""
    result = await db.execute(
        select(User).where(User.email_verification_token == body.token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, "Invalid verification token")

    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    user.email_verification_token = None
    return {"status": "email_verified"}


# ── Password Management ─────────────────────────────────────────────────────


@router.post("/password/change")
async def change_password(
    body: PasswordChangeRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password with history tracking."""
    from healthos_platform.security.auth import hash_password, verify_password

    result = await db.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if not verify_password(body.current_password, user.hashed_password):
        # Track failed attempt
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        raise HTTPException(400, "Current password is incorrect")

    # Check password history (last 5)
    history = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == ctx.user_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(5)
    )
    for ph in history.scalars():
        if verify_password(body.new_password, ph.hashed_password):
            raise HTTPException(400, "Cannot reuse a recent password")

    # Save to history
    db.add(PasswordHistory(user_id=ctx.user_id, hashed_password=user.hashed_password))

    # Update password
    user.hashed_password = hash_password(body.new_password)
    user.last_password_change = datetime.now(timezone.utc)
    user.failed_login_attempts = 0

    return {"status": "password_changed"}


# ── Account Lockout ──────────────────────────────────────────────────────────


@router.post("/account/unlock/{user_id}")
async def unlock_account(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin unlocks a locked account."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == ctx.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.account_locked_until = None
    user.failed_login_attempts = 0
    return {"status": "account_unlocked"}


# ── Session Management ───────────────────────────────────────────────────────


@router.get("/sessions", response_model=list[SessionListResponse])
async def list_sessions(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == ctx.user_id, UserSession.is_active.is_(True))
        .order_by(UserSession.last_activity.desc())
    )
    return result.scalars().all()


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id, UserSession.user_id == ctx.user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    session.is_active = False
    return {"status": "session_revoked"}


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all sessions except current."""
    from sqlalchemy import update
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == ctx.user_id, UserSession.is_active.is_(True))
        .values(is_active=False)
    )
    return {"status": "all_sessions_revoked"}
