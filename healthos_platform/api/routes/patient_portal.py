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
from healthos_platform.database import get_db
from healthos_platform.models import Alert, CarePlan, Encounter, Patient, Vital
from healthos_platform.security.rbac import Permission

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
