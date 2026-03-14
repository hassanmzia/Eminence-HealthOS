"""
E2E test fixtures -- shared helpers for Analytics module end-to-end tests.

Provides:
  - analytics_org_id: deterministic org UUID for analytics tests
  - sample_patient_population: 50 mock patient records with varying conditions
  - sample_risk_scores: pre-computed risk scores keyed by patient_id
  - sample_cohort_criteria: various cohort filter criteria
  - mock_db_session: async mock database session
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from healthos_platform.agents.types import AgentInput


# ── Deterministic seed for reproducible patient data ────────────────────────

_RNG = random.Random(42)

# ── Identifiers ─────────────────────────────────────────────────────────────


@pytest.fixture
def analytics_org_id() -> uuid.UUID:
    """Deterministic org UUID used across all analytics tests."""
    return uuid.UUID("a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e4e4")


# ── Patient population ──────────────────────────────────────────────────────

_CONDITIONS = [
    ("Type 2 Diabetes", "E11.65"),
    ("Hypertension", "I10"),
    ("Heart Failure", "I50.9"),
    ("COPD", "J44.1"),
    ("CKD Stage 4", "N18.4"),
    ("Hyperlipidemia", "E78.5"),
    ("Obesity", "E66.01"),
    ("Atrial Fibrillation", "I48.91"),
    ("Asthma", "J45.20"),
    ("Depression", "F32.1"),
]

_RISK_LEVELS = ["low", "moderate", "high", "critical"]


def _make_patient(index: int) -> dict[str, Any]:
    """Generate a single mock patient record."""
    pid = str(uuid.UUID(int=index + 1000))
    age = _RNG.randint(25, 90)
    num_conditions = _RNG.randint(0, 5)
    conditions = _RNG.sample(_CONDITIONS, min(num_conditions, len(_CONDITIONS)))

    # Distribute risk: ~40% low, ~30% moderate, ~20% high, ~10% critical
    r = _RNG.random()
    if r < 0.40:
        risk_level = "low"
        risk_score = round(_RNG.uniform(0.05, 0.25), 3)
    elif r < 0.70:
        risk_level = "moderate"
        risk_score = round(_RNG.uniform(0.25, 0.50), 3)
    elif r < 0.90:
        risk_level = "high"
        risk_score = round(_RNG.uniform(0.50, 0.75), 3)
    else:
        risk_level = "critical"
        risk_score = round(_RNG.uniform(0.75, 0.95), 3)

    return {
        "patient_id": pid,
        "age": age,
        "gender": _RNG.choice(["male", "female"]),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "conditions": [c[0] for c in conditions],
        "diagnosis_codes": [c[1] for c in conditions],
        "active_alerts": _RNG.randint(0, 3) if risk_level in ("high", "critical") else 0,
        "medication_count": _RNG.randint(1, 12),
        "prior_admissions_6m": _RNG.randint(0, 3) if risk_level != "low" else 0,
        "ed_visits_6m": _RNG.randint(0, 4),
        "hba1c": round(_RNG.uniform(5.0, 12.0), 1) if any(c[1].startswith("E11") for c in conditions) else 0,
        "lives_alone": _RNG.random() < 0.25,
        "pcp_follow_up_scheduled": _RNG.random() > 0.15,
        "medication_adherence": round(_RNG.uniform(0.5, 1.0), 2),
        "length_of_stay_days": _RNG.randint(1, 10) if _RNG.random() < 0.3 else 0,
    }


@pytest.fixture
def sample_patient_population() -> list[dict[str, Any]]:
    """50 mock patient records with realistic clinical variation."""
    return [_make_patient(i) for i in range(50)]


# ── Pre-computed risk scores ────────────────────────────────────────────────


@pytest.fixture
def sample_risk_scores(sample_patient_population) -> dict[str, float]:
    """Risk scores keyed by patient_id, derived from the population fixture."""
    return {p["patient_id"]: p["risk_score"] for p in sample_patient_population}


# ── Cohort criteria library ─────────────────────────────────────────────────


@pytest.fixture
def sample_cohort_criteria() -> dict[str, dict[str, Any]]:
    """Various cohort filter criteria for testing segmentation."""
    return {
        "high_risk": {
            "name": "High/Critical Risk Patients",
            "criteria": {"risk_level": ["high", "critical"]},
        },
        "diabetic": {
            "name": "Diabetes Cohort",
            "criteria": {"icd10_prefix": ["E11", "E10"]},
        },
        "heart_failure": {
            "name": "Heart Failure Cohort",
            "criteria": {"icd10_prefix": ["I50"]},
        },
        "elderly_multi_morbid": {
            "name": "Elderly with Multiple Conditions",
            "criteria": {"risk_level": ["high", "critical"]},
        },
    }


# ── Mock DB session ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Async mock database session for analytics queries."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    # Support async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


# ── AgentInput factory ──────────────────────────────────────────────────────


def make_analytics_input(
    org_id: uuid.UUID,
    context: dict[str, Any],
    *,
    patient_id: uuid.UUID | None = None,
    trigger: str = "analytics.test",
) -> AgentInput:
    """Create an AgentInput populated with analytics context."""
    return AgentInput(
        org_id=org_id,
        patient_id=patient_id,
        trigger=trigger,
        context=context,
    )
