"""
Eminence HealthOS — Messaging & Notification Routes (Phase 4)
Threaded messaging, typed notifications, alert responses.
Imported from InhealthUSA Message/Notification system.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.database import get_db
from healthos_platform.models import (
    Message,
    Notification,
    NotificationPreference,
    VitalSignAlertResponse,
)

router = APIRouter(prefix="/messaging", tags=["messaging"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class MessageCreate(BaseModel):
    recipient_id: uuid.UUID
    subject: str
    body: str
    parent_message_id: uuid.UUID | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    subject: str
    body: str
    is_read: bool
    read_at: datetime | None
    parent_message_id: uuid.UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    notification_type: str
    is_read: bool
    read_at: datetime | None
    link: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool | None = None
    email_emergency: bool | None = None
    email_critical: bool | None = None
    email_warning: bool | None = None
    sms_enabled: bool | None = None
    sms_emergency: bool | None = None
    sms_critical: bool | None = None
    sms_warning: bool | None = None
    whatsapp_enabled: bool | None = None
    whatsapp_number: str | None = None
    enable_quiet_hours: bool | None = None
    quiet_start_time: str | None = None
    quiet_end_time: str | None = None
    digest_mode: bool | None = None
    digest_frequency_hours: int | None = None


class NotificationPreferenceResponse(BaseModel):
    email_enabled: bool
    sms_enabled: bool
    whatsapp_enabled: bool
    enable_quiet_hours: bool
    digest_mode: bool
    model_config = {"from_attributes": True}


class AlertResponseCreate(BaseModel):
    response_status: str  # ok, help_needed
    wants_doctor: bool = False
    wants_nurse: bool = False
    wants_ems: bool = False
    response_method: str = "web"


# ── Message Endpoints ────────────────────────────────────────────────────────


@router.get("/inbox", response_model=list[MessageResponse])
async def inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Message)
        .where(Message.recipient_id == ctx.user_id, Message.org_id == ctx.org_id)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()


@router.get("/sent", response_model=list[MessageResponse])
async def sent_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Message)
        .where(Message.sender_id == ctx.user_id, Message.org_id == ctx.org_id)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()


@router.post("/send", response_model=MessageResponse, status_code=201)
async def send_message(
    body: MessageCreate,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    msg = Message(
        org_id=ctx.org_id,
        sender_id=ctx.user_id,
        **body.model_dump(),
    )
    db.add(msg)
    await db.flush()

    # Create notification for recipient
    notif = Notification(
        org_id=ctx.org_id,
        user_id=body.recipient_id,
        title=f"New message: {body.subject}",
        message=body.body[:200],
        notification_type="message",
        link=f"/messaging/{msg.id}",
    )
    db.add(notif)

    return msg


@router.get("/thread/{message_id}", response_model=list[MessageResponse])
async def message_thread(
    message_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get root and all replies
    result = await db.execute(
        select(Message).where(
            Message.org_id == ctx.org_id,
            or_(Message.id == message_id, Message.parent_message_id == message_id),
        ).order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{message_id}/read")
async def mark_read(
    message_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.recipient_id == ctx.user_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")
    msg.is_read = True
    msg.read_at = datetime.now(timezone.utc)
    return {"status": "read"}


# ── Notification Endpoints ───────────────────────────────────────────────────


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Notification).where(
        Notification.user_id == ctx.user_id, Notification.org_id == ctx.org_id
    )
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    offset = (page - 1) * page_size
    result = await db.execute(q.order_by(Notification.created_at.desc()).offset(offset).limit(page_size))
    return result.scalars().all()


@router.get("/notifications/unread-count")
async def unread_count(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == ctx.user_id,
            Notification.org_id == ctx.org_id,
            Notification.is_read.is_(False),
        )
    )
    return {"unread_count": result.scalar() or 0}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == ctx.user_id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(404, "Notification not found")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    return {"status": "read"}


@router.post("/notifications/mark-all-read")
async def mark_all_read(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == ctx.user_id,
            Notification.org_id == ctx.org_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    return {"status": "all_read"}


# ── Notification Preferences ─────────────────────────────────────────────────


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == ctx.user_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        # Create default
        pref = NotificationPreference(user_id=ctx.user_id)
        db.add(pref)
        await db.flush()
    return pref


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    body: NotificationPreferenceUpdate,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == ctx.user_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        pref = NotificationPreference(user_id=ctx.user_id)
        db.add(pref)

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(pref, k, v)
    await db.flush()
    return pref


# ── Vital Sign Alert Response ────────────────────────────────────────────────


@router.post("/alerts/respond/{response_token}")
async def respond_to_alert(
    response_token: uuid.UUID,
    body: AlertResponseCreate,
    db: AsyncSession = Depends(get_db),
):
    """Patient responds to a vital sign alert (token-based, no auth required)."""
    result = await db.execute(
        select(VitalSignAlertResponse).where(VitalSignAlertResponse.response_token == response_token)
    )
    alert_resp = result.scalar_one_or_none()
    if not alert_resp:
        raise HTTPException(404, "Alert response not found")

    alert_resp.patient_response_status = body.response_status
    alert_resp.patient_wants_doctor = body.wants_doctor
    alert_resp.patient_wants_nurse = body.wants_nurse
    alert_resp.patient_wants_ems = body.wants_ems
    alert_resp.patient_response_time = datetime.now(timezone.utc)
    alert_resp.patient_response_method = body.response_method

    return {"status": "response_recorded"}
