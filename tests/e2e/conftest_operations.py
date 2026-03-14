"""
E2E test fixtures -- shared helpers for Operations workflow end-to-end tests.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from healthos_platform.agents.types import AgentInput
from modules.operations.workflow_engine import WorkflowEngine


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


# ── Workflow engine ──────────────────────────────────────────────────────────


@pytest.fixture
def workflow_engine() -> WorkflowEngine:
    """Return a fresh WorkflowEngine instance (no shared state between tests)."""
    return WorkflowEngine()


# ── Clinical / operational context fixtures ──────────────────────────────────


@pytest.fixture
def sample_prior_auth_context() -> dict[str, Any]:
    """Realistic prior authorization context with CPT, ICD-10, and payer info."""
    return {
        "action": "evaluate",
        "cpt_codes": ["70553", "72148"],
        "diagnosis_codes": ["M54.5", "G89.29"],
        "payer": "aetna",
        "estimated_cost": 3500,
        "procedure_description": "MRI of lumbar spine without and with contrast",
        "clinical_notes": (
            "Patient presents with chronic low back pain radiating to left lower "
            "extremity for 8 weeks. Conservative treatment with physical therapy "
            "and NSAIDs has failed to provide relief. MRI is indicated to evaluate "
            "for disc herniation or spinal stenosis."
        ),
    }


@pytest.fixture
def sample_insurance_context() -> dict[str, Any]:
    """Insurance verification context with member, group, and plan info."""
    return {
        "action": "verify_eligibility",
        "member_id": "MEM-987654321",
        "group_number": "GRP-12345",
        "payer": "BlueCross",
        "plan_type": "PPO",
        "date_of_service": "2026-03-15T09:00:00Z",
        "subscriber_dob": "1974-06-15",
    }


@pytest.fixture
def sample_referral_context() -> dict[str, Any]:
    """Referral coordination context with specialty, reason, and urgency."""
    return {
        "action": "create",
        "specialty": "cardiology",
        "reason": "Persistent chest pain with exertional dyspnea, abnormal stress test",
        "urgency": "urgent",
        "diagnosis_codes": ["R07.9", "R06.0"],
        "referring_provider": "Dr. Martinez (Internal Medicine)",
        "clinical_notes": (
            "52-year-old male with hypertension presenting with 3-week history "
            "of exertional chest tightness. Stress test showed ST depression in "
            "leads V4-V6. Needs cardiology evaluation for possible catheterization."
        ),
        "insurance_verified": True,
    }


@pytest.fixture
def sample_billing_context() -> dict[str, Any]:
    """Billing readiness context with encounter data, CPT, and ICD codes."""
    return {
        "action": "validate",
        "encounter_type": "office_visit",
        "encounter": {
            "patient_id": "PT-001",
            "provider_id": "PROV-001",
            "date_of_service": "2026-03-14T10:00:00Z",
            "cpt_codes": ["99214"],
            "diagnosis_codes": ["E11.65", "I10"],
            "place_of_service": "11",
            "modifier": "25",
            "clinical_notes": "Follow-up visit for type 2 diabetes and hypertension management.",
            "provider_signature": True,
            "review_of_systems": True,
        },
    }


# ── AgentInput factory ──────────────────────────────────────────────────────


def make_ops_input(
    org_id: uuid.UUID,
    patient_id: uuid.UUID | None,
    context: dict[str, Any],
    *,
    trigger: str = "operations.workflow",
) -> AgentInput:
    """Create an AgentInput populated with an operations context."""
    return AgentInput(
        org_id=org_id,
        patient_id=patient_id,
        trigger=trigger,
        context=context,
    )
