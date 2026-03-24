"""
Eminence HealthOS — Organization Management API Routes
CRUD for organizations, self-service signup, and super-admin management.
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_admin,
)
from healthos_platform.database import get_db
from healthos_platform.models import Organization, User
from healthos_platform.security.auth import create_tokens, hash_password

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class OrgSignupRequest(BaseModel):
    """Self-service: create organization + first admin user in one call."""
    org_name: str = Field(min_length=2, max_length=255)
    org_slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    tier: str = Field(default="starter", pattern=r"^(starter|standard)$")
    admin_email: str
    admin_password: str = Field(min_length=8)
    admin_full_name: str

class OrgSignupResponse(BaseModel):
    org_id: uuid.UUID
    org_name: str
    org_slug: str
    tier: str
    admin_user_id: uuid.UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class OrgCreateByAdminRequest(BaseModel):
    """Super-admin: create an organization (enterprise provisioning)."""
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100)
    tier: str = Field(default="enterprise", pattern=r"^(starter|standard|enterprise)$")
    admin_email: str | None = None
    admin_password: str | None = Field(default=None, min_length=8)
    admin_full_name: str | None = None
    hipaa_baa_signed: bool = False
    settings: dict | None = None

class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    tier: str
    hipaa_baa_signed: bool
    user_count: int = 0
    patient_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}

class OrgUpdateRequest(BaseModel):
    name: str | None = None
    tier: str | None = Field(default=None, pattern=r"^(starter|standard|enterprise)$")
    hipaa_baa_signed: bool | None = None
    settings: dict | None = None

class OrgListResponse(BaseModel):
    organizations: list[OrgResponse]
    total: int
    page: int
    page_size: int


# ── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:100]


async def _require_super_admin(ctx: TenantContext = Depends(get_current_user)) -> TenantContext:
    """Only super_admin role can manage all organizations."""
    if ctx.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return ctx


# ── Self-Service Signup (public) ─────────────────────────────────────────────

@router.post("/signup", response_model=OrgSignupResponse, status_code=201)
async def org_signup(req: OrgSignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Self-service organization registration.
    Creates the org + first admin user, returns JWT tokens.
    Available for starter and standard tiers.
    """
    # Check slug uniqueness
    existing = await db.execute(select(Organization).where(Organization.slug == req.org_slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    # Create organization
    org = Organization(
        name=req.org_name,
        slug=req.org_slug,
        tier=req.tier,
        settings={"onboarding_complete": False},
    )
    db.add(org)
    await db.flush()

    # Create the first admin user
    admin_user = User(
        org_id=org.id,
        email=req.admin_email,
        hashed_password=hash_password(req.admin_password),
        role="admin",
        full_name=req.admin_full_name,
    )
    db.add(admin_user)
    await db.flush()
    await db.refresh(admin_user)

    # Issue JWT
    tokens = create_tokens(admin_user.id, org.id, "admin")

    return OrgSignupResponse(
        org_id=org.id,
        org_name=org.name,
        org_slug=org.slug,
        tier=org.tier,
        admin_user_id=admin_user.id,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


# ── Super-Admin: List all organizations ──────────────────────────────────────

@router.get("/", response_model=OrgListResponse)
async def list_organizations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    tier: str | None = None,
    ctx: TenantContext = Depends(_require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations (super_admin only)."""
    query = select(Organization)
    count_query = select(func.count(Organization.id))

    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))
        count_query = count_query.where(Organization.name.ilike(f"%{search}%"))
    if tier:
        query = query.where(Organization.tier == tier)
        count_query = count_query.where(Organization.tier == tier)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Organization.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orgs = result.scalars().all()

    # Get counts per org
    org_responses = []
    for org in orgs:
        user_count = (await db.execute(
            select(func.count(User.id)).where(User.org_id == org.id)
        )).scalar() or 0
        org_responses.append(OrgResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            tier=org.tier,
            hipaa_baa_signed=org.hipaa_baa_signed,
            user_count=user_count,
            patient_count=0,
            created_at=org.created_at.isoformat() if org.created_at else "",
        ))

    return OrgListResponse(
        organizations=org_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Super-Admin: Create organization (enterprise provisioning) ───────────────

@router.post("/", response_model=OrgResponse, status_code=201)
async def create_organization(
    req: OrgCreateByAdminRequest,
    ctx: TenantContext = Depends(_require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create an organization (super_admin only). For enterprise provisioning."""
    existing = await db.execute(select(Organization).where(Organization.slug == req.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Organization slug already taken")

    org = Organization(
        name=req.name,
        slug=req.slug,
        tier=req.tier,
        hipaa_baa_signed=req.hipaa_baa_signed,
        settings=req.settings or {},
    )
    db.add(org)
    await db.flush()

    # Optionally create the initial admin user
    if req.admin_email and req.admin_password and req.admin_full_name:
        admin_user = User(
            org_id=org.id,
            email=req.admin_email,
            hashed_password=hash_password(req.admin_password),
            role="admin",
            full_name=req.admin_full_name,
        )
        db.add(admin_user)
        await db.flush()

    user_count = 1 if req.admin_email else 0

    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        hipaa_baa_signed=org.hipaa_baa_signed,
        user_count=user_count,
        patient_count=0,
        created_at=org.created_at.isoformat() if org.created_at else "",
    )


# ── Super-Admin: Get specific organization ───────────────────────────────────

@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(_require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get organization details (super_admin only)."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    user_count = (await db.execute(
        select(func.count(User.id)).where(User.org_id == org.id)
    )).scalar() or 0

    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        hipaa_baa_signed=org.hipaa_baa_signed,
        user_count=user_count,
        patient_count=0,
        created_at=org.created_at.isoformat() if org.created_at else "",
    )


# ── Super-Admin: Update organization ─────────────────────────────────────────

@router.patch("/{org_id}", response_model=OrgResponse)
async def update_organization(
    org_id: uuid.UUID,
    req: OrgUpdateRequest,
    ctx: TenantContext = Depends(_require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update organization details (super_admin only)."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if req.name is not None:
        org.name = req.name
    if req.tier is not None:
        org.tier = req.tier
    if req.hipaa_baa_signed is not None:
        org.hipaa_baa_signed = req.hipaa_baa_signed
    if req.settings is not None:
        org.settings = {**(org.settings or {}), **req.settings}

    await db.flush()
    await db.refresh(org)

    user_count = (await db.execute(
        select(func.count(User.id)).where(User.org_id == org.id)
    )).scalar() or 0

    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        hipaa_baa_signed=org.hipaa_baa_signed,
        user_count=user_count,
        patient_count=0,
        created_at=org.created_at.isoformat() if org.created_at else "",
    )


# ── Org Admin: Get own organization settings ─────────────────────────────────

@router.get("/me/settings")
async def get_my_org_settings(
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's organization settings (org admin only)."""
    result = await db.execute(select(Organization).where(Organization.id == ctx.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    user_count = (await db.execute(
        select(func.count(User.id)).where(User.org_id == org.id)
    )).scalar() or 0

    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "tier": org.tier,
        "hipaa_baa_signed": org.hipaa_baa_signed,
        "settings": org.settings or {},
        "user_count": user_count,
        "created_at": org.created_at.isoformat() if org.created_at else "",
    }


# ── Org Admin: Update own organization settings ──────────────────────────────

@router.patch("/me/settings")
async def update_my_org_settings(
    req: OrgUpdateRequest,
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's organization settings (org admin only).
    Note: tier changes require super_admin — ignored here."""
    result = await db.execute(select(Organization).where(Organization.id == ctx.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if req.name is not None:
        org.name = req.name
    if req.hipaa_baa_signed is not None:
        org.hipaa_baa_signed = req.hipaa_baa_signed
    if req.settings is not None:
        org.settings = {**(org.settings or {}), **req.settings}
    # tier change ignored — requires super_admin

    await db.flush()
    await db.refresh(org)

    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "tier": org.tier,
        "hipaa_baa_signed": org.hipaa_baa_signed,
        "settings": org.settings or {},
    }
