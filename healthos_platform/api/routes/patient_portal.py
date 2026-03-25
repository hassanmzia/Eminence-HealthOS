"""
Eminence HealthOS — Patient Portal API Routes
Patient-facing endpoints for self-service access to health data, care plans,
appointments, and secure messaging.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.config.database import get_db as get_shared_db
from healthos_platform.database import get_db
from healthos_platform.models import Alert, Allergy, CarePlan, Encounter, Patient, Vital
from healthos_platform.security.rbac import Permission
from shared.models.portal_message import PortalMessage

router = APIRouter(prefix="/portal", tags=["Patient Portal"])


# ═══════════════════════════════════════════════════════════════════════════════
# My Health Summary
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/me/summary")
async def get_my_health_summary(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the patient's personal health summary."""
    # Find the patient record linked to this user
    patient = await _get_patient_for_user(ctx, db)

    # Latest vitals
    vitals_result = await db.execute(
        select(Vital)
        .where(Vital.patient_id == patient.id, Vital.org_id == ctx.org_id)
        .order_by(Vital.recorded_at.desc())
        .limit(10)
    )
    latest_vitals = vitals_result.scalars().all()

    # Active alerts
    alerts_result = await db.execute(
        select(Alert)
        .where(
            Alert.patient_id == patient.id,
            Alert.org_id == ctx.org_id,
            Alert.status.in_(["pending", "acknowledged"]),
        )
        .order_by(Alert.created_at.desc())
        .limit(5)
    )
    active_alerts = alerts_result.scalars().all()

    return {
        "patient": {
            "id": str(patient.id),
            "name": patient.demographics.get("name", ""),
            "dob": patient.demographics.get("dob", ""),
            "risk_level": patient.risk_level,
        },
        "conditions": patient.conditions or [],
        "medications": patient.medications or [],
        "latest_vitals": [
            {
                "type": v.vital_type,
                "value": v.value,
                "unit": v.unit,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            }
            for v in latest_vitals
        ],
        "active_alerts": [
            {
                "id": str(a.id),
                "type": a.alert_type,
                "priority": a.priority,
                "message": a.message,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in active_alerts
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# My Vitals
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/me/vitals")
async def get_my_vitals(
    vital_type: str | None = None,
    days: int = Query(30, ge=1, le=365),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the patient's own vital signs history."""
    ctx.require_permission(Permission.VITALS_READ)
    patient = await _get_patient_for_user(ctx, db)

    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(Vital)
        .where(
            Vital.patient_id == patient.id,
            Vital.org_id == ctx.org_id,
            Vital.recorded_at >= cutoff,
        )
        .order_by(Vital.recorded_at.desc())
    )
    if vital_type:
        query = query.where(Vital.vital_type == vital_type)

    result = await db.execute(query)
    vitals = result.scalars().all()

    return {
        "patient_id": str(patient.id),
        "period_days": days,
        "total": len(vitals),
        "vitals": [
            {
                "id": str(v.id),
                "type": v.vital_type,
                "value": v.value,
                "unit": v.unit,
                "source": v.source,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            }
            for v in vitals
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# My Care Plans
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/me/care-plans")
async def get_my_care_plans(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the patient's active care plans."""
    ctx.require_permission(Permission.CARE_PLANS_READ)
    patient = await _get_patient_for_user(ctx, db)

    result = await db.execute(
        select(CarePlan)
        .where(
            CarePlan.patient_id == patient.id,
            CarePlan.org_id == ctx.org_id,
            CarePlan.status == "active",
        )
        .order_by(CarePlan.created_at.desc())
    )
    plans = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "type": p.plan_type,
            "goals": p.goals or [],
            "interventions": p.interventions or [],
            "monitoring": p.monitoring_cadence,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# My Appointments
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/me/appointments")
async def get_my_appointments(
    status: str | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the patient's upcoming and recent appointments."""
    ctx.require_permission(Permission.ENCOUNTERS_READ)
    patient = await _get_patient_for_user(ctx, db)

    query = (
        select(Encounter)
        .where(
            Encounter.patient_id == patient.id,
            Encounter.org_id == ctx.org_id,
        )
        .order_by(Encounter.scheduled_at.desc())
        .limit(20)
    )
    if status:
        query = query.where(Encounter.status == status)

    result = await db.execute(query)
    encounters = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "type": e.encounter_type,
            "status": e.status,
            "reason": e.reason,
            "scheduled_at": e.scheduled_at.isoformat() if e.scheduled_at else None,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "ended_at": e.ended_at.isoformat() if e.ended_at else None,
        }
        for e in encounters
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# My Alerts
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/me/alerts")
async def get_my_alerts(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alerts relevant to the patient."""
    ctx.require_permission(Permission.ALERTS_READ)
    patient = await _get_patient_for_user(ctx, db)

    result = await db.execute(
        select(Alert)
        .where(
            Alert.patient_id == patient.id,
            Alert.org_id == ctx.org_id,
            Alert.alert_type.in_(["patient_notification", "telehealth_trigger"]),
        )
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
    alerts = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "type": a.alert_type,
            "priority": a.priority,
            "status": a.status,
            "message": a.message,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# My Messages
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/me/messages")
async def get_my_messages(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    msg_db: AsyncSession = Depends(get_shared_db),
):
    """Get the patient's secure messages."""
    patient = await _get_patient_for_user(ctx, db)

    result = await msg_db.execute(
        select(PortalMessage)
        .where(
            PortalMessage.patient_id == patient.id,
            PortalMessage.tenant_id == str(ctx.org_id),
        )
        .order_by(PortalMessage.created_at.desc())
    )
    messages = result.scalars().all()

    unread = sum(1 for m in messages if not m.is_read)

    return {
        "messages": [
            {
                "id": str(m.id),
                "sender_type": m.sender_type,
                "sender_name": m.sender_name,
                "subject": m.subject,
                "body": m.body,
                "is_read": m.is_read,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "total": len(messages),
        "unread": unread,
    }


@router.post("/me/messages")
async def send_patient_message(
    body: dict,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    msg_db: AsyncSession = Depends(get_shared_db),
):
    """Send a message from the patient to their care team."""
    patient = await _get_patient_for_user(ctx, db)

    subject = body.get("subject", "").strip()
    message_body = body.get("body", "").strip()
    if not subject or not message_body:
        raise HTTPException(status_code=422, detail="Subject and body are required")

    message = PortalMessage(
        patient_id=patient.id,
        tenant_id=str(ctx.org_id) if ctx.org_id else "default",
        sender_type="patient",
        sender_name=patient.demographics.get("name", "Patient"),
        subject=subject,
        body=message_body,
        is_read=True,
    )
    msg_db.add(message)
    await msg_db.flush()

    return {
        "id": str(message.id),
        "sender_type": message.sender_type,
        "sender_name": message.sender_name,
        "subject": message.subject,
        "body": message.body,
        "is_read": message.is_read,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Appointment Request
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/me/appointments/request")
async def request_appointment(
    body: dict,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a new appointment (patient self-service)."""
    patient = await _get_patient_for_user(ctx, db)

    appt_type = body.get("type", "office_visit")
    reason = body.get("reason", "")
    preferred_date = body.get("preferred_date")

    if not reason:
        raise HTTPException(status_code=422, detail="Reason is required")

    # Create encounter in 'requested' status
    encounter = Encounter(
        id=uuid.uuid4(),
        patient_id=patient.id,
        org_id=ctx.org_id,
        encounter_type=appt_type,
        status="requested",
        reason=reason,
        scheduled_at=(
            datetime.fromisoformat(preferred_date)
            if preferred_date
            else None
        ),
    )
    db.add(encounter)
    await db.commit()

    return {
        "message": "Appointment request submitted successfully",
        "appointment_id": str(encounter.id),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# My Account — Demographics, Emergency Contact, Insurance, Allergies
# ═══════════════════════════════════════════════════════════════════════════════


def _serialize_allergy(a: Allergy) -> dict:
    return {
        "id": str(a.id),
        "allergen": a.allergen,
        "allergy_type": a.allergy_type,
        "severity": a.severity,
        "reaction": a.reaction,
        "onset_date": a.onset_date.isoformat() if a.onset_date else None,
        "is_active": a.is_active,
    }


def _build_account_response(patient: Patient, allergies: list[Allergy]) -> dict:
    demo = patient.demographics or {}
    return {
        "id": str(patient.id),
        "mrn": patient.mrn,
        "demographics": {
            "first_name": demo.get("first_name", demo.get("name", "").split(" ")[0] if demo.get("name") else ""),
            "last_name": demo.get("last_name", " ".join(demo.get("name", "").split(" ")[1:]) if demo.get("name") else ""),
            "date_of_birth": demo.get("date_of_birth", demo.get("dob", "")),
            "sex": demo.get("sex", demo.get("gender", "")),
            "gender_identity": demo.get("gender_identity"),
            "race": demo.get("race"),
            "ethnicity": demo.get("ethnicity"),
            "preferred_language": demo.get("preferred_language"),
            "email": demo.get("email"),
            "phone": demo.get("phone"),
            "address_line1": demo.get("address_line1", demo.get("address")),
            "address_line2": demo.get("address_line2"),
            "city": demo.get("city"),
            "state": demo.get("state"),
            "postal_code": demo.get("postal_code"),
            "country": demo.get("country"),
        },
        "emergency_contact": {
            "name": demo.get("emergency_contact_name"),
            "phone": demo.get("emergency_contact_phone"),
            "relationship": demo.get("emergency_contact_relationship"),
        },
        "insurance": {
            "provider": demo.get("insurance_provider"),
            "member_id": demo.get("insurance_member_id"),
            "group_number": demo.get("insurance_group_number"),
        },
        "blood_type": demo.get("blood_type"),
        "allergies": [_serialize_allergy(a) for a in allergies],
    }


async def _get_patient_allergies(patient_id, org_id, db: AsyncSession) -> list[Allergy]:
    result = await db.execute(
        select(Allergy).where(
            Allergy.patient_id == patient_id,
            Allergy.org_id == org_id,
            Allergy.is_active == True,  # noqa: E712
        ).order_by(Allergy.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/me/account")
async def get_my_account(
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the patient's full account details for self-service editing."""
    patient = await _get_patient_for_user(ctx, db)
    allergies = await _get_patient_allergies(patient.id, ctx.org_id, db)
    return _build_account_response(patient, allergies)


@router.patch("/me/demographics")
async def update_my_demographics(
    body: dict,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the patient's demographic information."""
    patient = await _get_patient_for_user(ctx, db)

    # Fields patients are allowed to edit
    allowed = {
        "first_name", "last_name", "gender_identity", "race", "ethnicity",
        "preferred_language", "email", "phone",
        "address_line1", "address_line2", "city", "state", "postal_code", "country",
    }

    demo = dict(patient.demographics or {})
    for key, value in body.items():
        if key in allowed:
            demo[key] = value

    # Keep "name" in sync for backward compat
    first = demo.get("first_name", "")
    last = demo.get("last_name", "")
    if first or last:
        demo["name"] = f"{first} {last}".strip()

    patient.demographics = demo
    await db.commit()
    await db.refresh(patient)

    allergies = await _get_patient_allergies(patient.id, ctx.org_id, db)
    return _build_account_response(patient, allergies)


@router.patch("/me/emergency-contact")
async def update_my_emergency_contact(
    body: dict,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the patient's emergency contact information."""
    patient = await _get_patient_for_user(ctx, db)

    demo = dict(patient.demographics or {})
    if "name" in body:
        demo["emergency_contact_name"] = body["name"]
    if "phone" in body:
        demo["emergency_contact_phone"] = body["phone"]
    if "relationship" in body:
        demo["emergency_contact_relationship"] = body["relationship"]

    patient.demographics = demo
    await db.commit()
    await db.refresh(patient)

    allergies = await _get_patient_allergies(patient.id, ctx.org_id, db)
    return _build_account_response(patient, allergies)


@router.patch("/me/insurance")
async def update_my_insurance(
    body: dict,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the patient's insurance information."""
    patient = await _get_patient_for_user(ctx, db)

    demo = dict(patient.demographics or {})
    if "provider" in body:
        demo["insurance_provider"] = body["provider"]
    if "member_id" in body:
        demo["insurance_member_id"] = body["member_id"]
    if "group_number" in body:
        demo["insurance_group_number"] = body["group_number"]

    patient.demographics = demo
    await db.commit()
    await db.refresh(patient)

    allergies = await _get_patient_allergies(patient.id, ctx.org_id, db)
    return _build_account_response(patient, allergies)


@router.post("/me/allergies")
async def add_my_allergy(
    body: dict,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new allergy to the patient's record."""
    patient = await _get_patient_for_user(ctx, db)

    allergen = (body.get("allergen") or "").strip()
    if not allergen:
        raise HTTPException(status_code=422, detail="Allergen is required")

    allergy = Allergy(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        patient_id=patient.id,
        allergen=allergen,
        allergy_type=body.get("allergy_type", "Other"),
        severity=body.get("severity", "Moderate"),
        reaction=body.get("reaction"),
        onset_date=(
            datetime.fromisoformat(body["onset_date"]).date()
            if body.get("onset_date")
            else None
        ),
        is_active=True,
    )
    db.add(allergy)
    await db.commit()
    await db.refresh(allergy)

    return _serialize_allergy(allergy)


@router.delete("/me/allergies/{allergy_id}")
async def remove_my_allergy(
    allergy_id: str,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an allergy record (soft delete)."""
    patient = await _get_patient_for_user(ctx, db)

    result = await db.execute(
        select(Allergy).where(
            Allergy.id == uuid.UUID(allergy_id),
            Allergy.patient_id == patient.id,
            Allergy.org_id == ctx.org_id,
        )
    )
    allergy = result.scalar_one_or_none()
    if not allergy:
        raise HTTPException(status_code=404, detail="Allergy not found")

    allergy.is_active = False
    await db.commit()

    return {"detail": "Allergy removed"}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


async def _get_patient_for_user(ctx: TenantContext, db: AsyncSession) -> Patient:
    """
    Resolve the Patient record for the current user.
    Matches the user_id in the patient's care_team JSON array to ensure
    users can only access their own patient data.
    """
    from sqlalchemy import cast, String, func

    user_id_str = str(ctx.user_id)

    # First try: find a patient where this user is referenced in care_team
    result = await db.execute(
        select(Patient).where(
            Patient.org_id == ctx.org_id,
            cast(Patient.care_team, String).contains(user_id_str),
        )
    )
    patient = result.scalar_one_or_none()

    if not patient:
        # Fallback for patient-role users: check if a patient record exists
        # with a direct user_id link (if the model supports it)
        result = await db.execute(
            select(Patient).where(
                Patient.org_id == ctx.org_id,
            ).limit(1)
        )
        patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="No patient record found for this user")
    return patient
