"""
E2E test fixtures -- shared helpers for Telehealth workflow end-to-end tests.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from healthos_platform.agents.types import AgentInput


# ── Identifiers ──────────────────────────────────────────────────────────────


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def patient_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def provider_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Clinical context fixtures ────────────────────────────────────────────────


@pytest.fixture
def sample_session_context() -> dict[str, Any]:
    """Standard session context for a routine telehealth visit."""
    return {
        "visit_type": "follow_up",
        "urgency": "routine",
        "chief_complaint": "headache",
        "symptoms": ["headache", "fatigue", "nausea"],
    }


@pytest.fixture
def sample_clinical_context() -> dict[str, Any]:
    """Comprehensive clinical context for visit documentation."""
    return {
        "symptoms": ["headache", "fatigue", "nausea"],
        "vitals": {
            "heart_rate": {"value": 78, "unit": "bpm"},
            "blood_pressure": {"systolic": 128, "diastolic": 82, "unit": "mmHg"},
            "temperature": {"value": 98.6, "unit": "°F"},
            "spo2": {"value": 97, "unit": "%"},
        },
        "assessment": "Tension-type headache with associated fatigue",
        "plan": [
            "Continue current medications",
            "OTC analgesics as needed",
            "Follow up in 2 weeks if symptoms persist",
        ],
        "medications": ["ibuprofen", "acetaminophen"],
        "conditions": ["hypertension", "diabetes"],
        "demographics": {
            "first_name": "Jane",
            "last_name": "Doe",
            "age": 52,
            "gender": "female",
        },
        "allergies": ["penicillin"],
    }


@pytest.fixture
def sample_medication_list() -> list[dict[str, Any]]:
    """Medication list containing known interaction pairs from the agent DB."""
    return [
        {"name": "warfarin 5mg", "dosage": "5mg daily"},
        {"name": "aspirin 81mg", "dosage": "81mg daily"},
        {"name": "lisinopril 10mg", "dosage": "10mg daily"},
        {"name": "metformin 500mg", "dosage": "500mg twice daily"},
    ]


# ── AgentInput factory functions ─────────────────────────────────────────────


def make_telehealth_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    context: dict[str, Any],
    *,
    trigger: str = "telehealth.visit",
) -> AgentInput:
    """Create an AgentInput populated with the given context."""
    return AgentInput(
        org_id=org_id,
        patient_id=patient_id,
        trigger=trigger,
        context=context,
    )


def make_session_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    action: str = "create",
    visit_type: str = "follow_up",
    urgency: str = "routine",
    extra: dict[str, Any] | None = None,
) -> AgentInput:
    """Create an AgentInput for the SessionManagerAgent."""
    ctx: dict[str, Any] = {
        "action": action,
        "visit_type": visit_type,
        "urgency": urgency,
    }
    if extra:
        ctx.update(extra)
    return make_telehealth_input(org_id, patient_id, ctx, trigger="session.create")


def make_symptom_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    symptoms: list[str],
    *,
    duration: str = "2 days",
    severity_rating: int = 5,
) -> AgentInput:
    """Create an AgentInput for the SymptomCheckerAgent."""
    return make_telehealth_input(
        org_id,
        patient_id,
        {
            "symptoms": symptoms,
            "duration": duration,
            "severity_rating": severity_rating,
        },
        trigger="symptom.check",
    )


def make_escalation_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    severity: str = "low",
    systems_affected: list[str] | None = None,
    red_flags: list[str] | None = None,
    risk_score: float = 0.0,
    urgency: str = "routine",
) -> AgentInput:
    """Create an AgentInput for the EscalationRoutingAgent."""
    return make_telehealth_input(
        org_id,
        patient_id,
        {
            "severity": severity,
            "systems_affected": systems_affected or [],
            "red_flags": red_flags or [],
            "risk_score": risk_score,
            "urgency": urgency,
        },
        trigger="escalation.route",
    )


def make_medication_review_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    medications: list[Any],
    *,
    conditions: list[Any] | None = None,
) -> AgentInput:
    """Create an AgentInput for the MedicationReviewAgent."""
    return make_telehealth_input(
        org_id,
        patient_id,
        {
            "medications": medications,
            "conditions": conditions or [],
        },
        trigger="medication.review",
    )


def make_scheduling_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    action: str = "schedule",
    visit_type: str = "follow_up",
    urgency: str = "routine",
    follow_up_days: int = 14,
) -> AgentInput:
    """Create an AgentInput for the SchedulingAgent."""
    return make_telehealth_input(
        org_id,
        patient_id,
        {
            "action": action,
            "visit_type": visit_type,
            "urgency": urgency,
            "follow_up_days": follow_up_days,
        },
        trigger="scheduling.request",
    )


def make_communication_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    message_type: str = "follow_up_instructions",
    urgency: str = "routine",
    patient_name: str = "Jane Doe",
    template_vars: dict[str, str] | None = None,
) -> AgentInput:
    """Create an AgentInput for the PatientCommunicationAgent."""
    return make_telehealth_input(
        org_id,
        patient_id,
        {
            "message_type": message_type,
            "urgency": urgency,
            "patient_name": patient_name,
            "template_vars": template_vars or {},
        },
        trigger="communication.send",
    )
