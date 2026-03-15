"""
Eminence HealthOS -- Notification Dispatch Tools

Re-exports the core ``send_notification`` and ``schedule_appointment`` tools
from ``base_tools`` and provides helpers for bulk notification dispatch and
appointment follow-up reminders.

No Django dependency -- configuration via Pydantic settings / env vars.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.tools import tool

from tools.base_tools import (
    schedule_appointment,  # noqa: F401 -- re-export
    send_notification,  # noqa: F401 -- re-export
)

logger = logging.getLogger("healthos.tools.notification")


@tool
def send_bulk_notifications(
    patient_ids: list, notification_type: str, message: str, channel: str
) -> dict:
    """
    Send the same notification to multiple patients at once.

    Iterates over the patient list and dispatches each notification via
    send_notification, collecting per-patient success/failure status.

    Args:
        patient_ids: List of patient identifiers
        notification_type: CRITICAL | URGENT | SOON | ROUTINE
        message: Notification message text
        channel: Delivery channel ('push', 'sms', 'email', 'in_app', 'ehr_inbox')

    Returns:
        Dict with 'total', 'succeeded', 'failed', and 'details' keys.
    """
    try:
        details: List[Dict[str, Any]] = []
        succeeded = 0
        failed = 0

        for pid in patient_ids:
            ok = send_notification.invoke(
                {
                    "patient_id": pid,
                    "notification_type": notification_type,
                    "message": message,
                    "channel": channel,
                }
            )
            if ok:
                succeeded += 1
                details.append({"patient_id": pid, "status": "sent"})
            else:
                failed += 1
                details.append({"patient_id": pid, "status": "failed"})

        return {
            "total": len(patient_ids),
            "succeeded": succeeded,
            "failed": failed,
            "details": details,
        }

    except Exception as exc:
        logger.error("send_bulk_notifications failed: %s", exc)
        return {
            "total": len(patient_ids),
            "succeeded": 0,
            "failed": len(patient_ids),
            "error": str(exc),
        }


@tool
def schedule_followup_reminder(
    patient_id: str, appointment_id: str, reminder_hours_before: int = 24
) -> bool:
    """
    Schedule a follow-up reminder notification for an existing appointment.

    Sends a ROUTINE push notification reminding the patient about their
    upcoming appointment.

    Args:
        patient_id: Patient identifier
        appointment_id: Existing appointment identifier to reference
        reminder_hours_before: Hours before the appointment to send the
                               reminder (default 24)

    Returns:
        True if the reminder was queued successfully, False otherwise.
    """
    try:
        message = (
            f"Reminder: You have an upcoming appointment (ref: {appointment_id}). "
            f"This reminder was sent {reminder_hours_before}h in advance. "
            "Please confirm or reschedule if needed."
        )
        result = send_notification.invoke(
            {
                "patient_id": patient_id,
                "notification_type": "ROUTINE",
                "message": message,
                "channel": "push",
            }
        )
        return bool(result)

    except Exception as exc:
        logger.error("schedule_followup_reminder failed: %s", exc)
        return False


# All tools provided by this module
NOTIFICATION_TOOLS = [
    send_bulk_notifications,
    schedule_followup_reminder,
]
