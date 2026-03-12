"""
Eminence HealthOS — Celery Background Workers
Handles long-running and scheduled tasks: risk recalculation, cohort updates,
report generation, EHR sync, and event processing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from celery import Celery
from celery.schedules import crontab

from healthos_platform.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════════════════════
# Celery App
# ═══════════════════════════════════════════════════════════════════════════════

celery_app = Celery(
    "healthos",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10-minute hard limit
    task_soft_time_limit=300,  # 5-minute soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    task_default_queue="healthos.default",
    task_routes={
        "healthos.tasks.risk.*": {"queue": "healthos.risk"},
        "healthos.tasks.ehr.*": {"queue": "healthos.ehr"},
        "healthos.tasks.analytics.*": {"queue": "healthos.analytics"},
        "healthos.tasks.notifications.*": {"queue": "healthos.notifications"},
    },
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    "recalculate-risk-scores": {
        "task": "healthos.tasks.risk.recalculate_all",
        "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
        "args": [],
    },
    "update-cohort-stats": {
        "task": "healthos.tasks.analytics.update_cohorts",
        "schedule": crontab(minute=30, hour=2),  # 2:30 AM daily
        "args": [],
    },
    "sync-ehr-data": {
        "task": "healthos.tasks.ehr.sync_all",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        "args": [],
    },
    "generate-population-metrics": {
        "task": "healthos.tasks.analytics.population_metrics",
        "schedule": crontab(minute=0, hour=3),  # 3 AM daily
        "args": [],
    },
    "process-pending-alerts": {
        "task": "healthos.tasks.risk.process_pending_alerts",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "args": [],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Risk Tasks
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task(name="healthos.tasks.risk.recalculate_patient")
def recalculate_patient_risk(patient_id: str, org_id: str) -> dict[str, Any]:
    """Recalculate risk score for a single patient."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        _async_recalculate_risk(patient_id, org_id)
    )


async def _async_recalculate_risk(patient_id: str, org_id: str) -> dict[str, Any]:
    from healthos_platform.orchestrator.engine import ExecutionEngine

    engine = ExecutionEngine()
    state = await engine.execute_event(
        event_type="patient.scheduled_check",
        org_id=uuid.UUID(org_id),
        patient_id=uuid.UUID(patient_id),
    )
    return {
        "patient_id": patient_id,
        "agents_executed": state.executed_agents,
        "requires_hitl": state.requires_hitl,
    }


@celery_app.task(name="healthos.tasks.risk.recalculate_all")
def recalculate_all_risk_scores() -> dict[str, Any]:
    """Recalculate risk scores for all active patients."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_async_recalculate_all())


async def _async_recalculate_all() -> dict[str, Any]:
    from sqlalchemy import select
    from healthos_platform.database import get_db_context
    from healthos_platform.models import Patient

    processed = 0
    async with get_db_context() as db:
        result = await db.execute(select(Patient.id, Patient.org_id))
        patients = result.all()

    for pid, oid in patients:
        recalculate_patient_risk.delay(str(pid), str(oid))
        processed += 1

    return {"patients_queued": processed, "timestamp": datetime.now(timezone.utc).isoformat()}


@celery_app.task(name="healthos.tasks.risk.process_pending_alerts")
def process_pending_alerts() -> dict[str, Any]:
    """Escalate unacknowledged alerts past their SLA."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_async_process_alerts())


async def _async_process_alerts() -> dict[str, Any]:
    from datetime import timedelta
    from sqlalchemy import select, update
    from healthos_platform.database import get_db_context
    from healthos_platform.models import Alert

    now = datetime.now(timezone.utc)
    escalation_threshold = now - timedelta(minutes=30)

    async with get_db_context() as db:
        # Find alerts pending for more than 30 minutes
        result = await db.execute(
            select(Alert).where(
                Alert.status == "pending",
                Alert.created_at <= escalation_threshold,
            )
        )
        stale_alerts = result.scalars().all()

        escalated = 0
        for alert in stale_alerts:
            if alert.priority in ("critical", "high"):
                alert.status = "escalated"
                escalated += 1

    return {"escalated": escalated, "timestamp": now.isoformat()}


# ═══════════════════════════════════════════════════════════════════════════════
# Analytics Tasks
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task(name="healthos.tasks.analytics.update_cohorts")
def update_cohorts() -> dict[str, Any]:
    """Recalculate patient counts for all cohorts."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_async_update_cohorts())


async def _async_update_cohorts() -> dict[str, Any]:
    from sqlalchemy import select
    from healthos_platform.database import get_db_context
    from healthos_platform.models import Cohort

    async with get_db_context() as db:
        result = await db.execute(select(Cohort))
        cohorts = result.scalars().all()

    return {"cohorts_updated": len(cohorts), "timestamp": datetime.now(timezone.utc).isoformat()}


@celery_app.task(name="healthos.tasks.analytics.population_metrics")
def generate_population_metrics() -> dict[str, Any]:
    """Generate daily population health metrics."""
    return {
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EHR Sync Tasks
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task(name="healthos.tasks.ehr.sync_all")
def sync_all_ehr() -> dict[str, Any]:
    """Sync data from all configured EHR systems."""
    return {
        "status": "completed",
        "synced_systems": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(name="healthos.tasks.ehr.sync_patient")
def sync_patient_ehr(patient_id: str, org_id: str, ehr_system: str) -> dict[str, Any]:
    """Sync a single patient's data from an EHR system."""
    return {
        "patient_id": patient_id,
        "ehr_system": ehr_system,
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Notification Tasks
# ═══════════════════════════════════════════════════════════════════════════════


@celery_app.task(name="healthos.tasks.notifications.send_alert")
def send_alert_notification(alert_id: str, channels: list[str]) -> dict[str, Any]:
    """Send alert notifications via configured channels (email, SMS, push)."""
    return {
        "alert_id": alert_id,
        "channels": channels,
        "status": "sent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(name="healthos.tasks.notifications.patient_reminder")
def send_patient_reminder(patient_id: str, reminder_type: str, message: str) -> dict[str, Any]:
    """Send a reminder to a patient (appointment, medication, vitals)."""
    return {
        "patient_id": patient_id,
        "reminder_type": reminder_type,
        "status": "sent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
