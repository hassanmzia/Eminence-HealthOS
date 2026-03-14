"""
E2E test fixtures -- shared helpers for RPM pipeline end-to-end tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from healthos_platform.agents.types import PipelineState, VitalType


# ── Identifiers ──────────────────────────────────────────────────────────────


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def patient_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Agent factory ────────────────────────────────────────────────────────────


@pytest.fixture
def pipeline_agents():
    """Instantiate the full ordered RPM pipeline agent list."""
    from modules.rpm.agents.adherence_monitoring import AdherenceMonitoringAgent
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.risk_scoring import RiskScoringAgent
    from modules.rpm.agents.trend_analysis import TrendAnalysisAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    return [
        DeviceIngestionAgent(),
        VitalsNormalizationAgent(),
        AnomalyDetectionAgent(),
        RiskScoringAgent(),
        TrendAnalysisAgent(),
        AdherenceMonitoringAgent(),
    ]


# ── Vital-reading builders ──────────────────────────────────────────────────


def _build_reading(
    vital_type: str,
    value: dict,
    unit: str,
    recorded_at: datetime,
    *,
    source: str = "wearable",
    device_id: str = "dev-001",
) -> dict:
    return {
        "vital_type": vital_type,
        "value": value,
        "unit": unit,
        "recorded_at": recorded_at.isoformat(),
        "source": source,
        "device_id": device_id,
    }


@pytest.fixture
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def normal_vitals_raw(now_utc):
    """Completely normal vital readings for a healthy patient."""
    return [
        _build_reading("heart_rate", {"value": 72}, "bpm", now_utc - timedelta(minutes=30)),
        _build_reading("blood_pressure", {"systolic": 118, "diastolic": 76}, "mmHg", now_utc - timedelta(minutes=25)),
        _build_reading("spo2", {"value": 98}, "%", now_utc - timedelta(minutes=20)),
        _build_reading("glucose", {"value": 95}, "mg/dL", now_utc - timedelta(minutes=15)),
        _build_reading("temperature", {"value": 98.4}, "\u00b0F", now_utc - timedelta(minutes=10)),
        _build_reading("respiratory_rate", {"value": 16}, "breaths/min", now_utc - timedelta(minutes=5)),
    ]


@pytest.fixture
def critical_vitals_raw(now_utc):
    """Vitals that should trigger critical anomalies and high risk."""
    return [
        _build_reading("heart_rate", {"value": 155}, "bpm", now_utc - timedelta(minutes=30)),
        _build_reading("blood_pressure", {"systolic": 200, "diastolic": 125}, "mmHg", now_utc - timedelta(minutes=25)),
        _build_reading("spo2", {"value": 82}, "%", now_utc - timedelta(minutes=20)),
        _build_reading("glucose", {"value": 350}, "mg/dL", now_utc - timedelta(minutes=15)),
        _build_reading("temperature", {"value": 104.5}, "\u00b0F", now_utc - timedelta(minutes=10)),
        _build_reading("respiratory_rate", {"value": 32}, "breaths/min", now_utc - timedelta(minutes=5)),
    ]


@pytest.fixture
def deteriorating_vitals_raw(now_utc):
    """
    Gradually worsening vitals over 6 readings spanning ~5 hours.
    Heart rate creeping up, SpO2 declining, BP rising.
    """
    readings = []
    for i in range(6):
        ts = now_utc - timedelta(hours=5 - i)
        # HR: 60 -> 160  (strong increasing trend, relative slope ~0.22)
        readings.append(
            _build_reading("heart_rate", {"value": 60 + i * 20}, "bpm", ts)
        )
        # BP: 110/65 -> 210/115 (steep rise, relative slope ~0.17)
        readings.append(
            _build_reading(
                "blood_pressure",
                {"systolic": 110 + i * 20, "diastolic": 65 + i * 10},
                "mmHg",
                ts + timedelta(seconds=30),
            )
        )
        # SpO2: 99 -> 84 (decline)
        readings.append(
            _build_reading("spo2", {"value": 99 - i * 3}, "%", ts + timedelta(seconds=60))
        )
    return readings


# ── Pipeline state builders ──────────────────────────────────────────────────


def make_pipeline_state(
    org_id: uuid.UUID,
    patient_id: uuid.UUID,
    raw_vitals: list[dict],
    *,
    patient_context_extra: dict | None = None,
) -> PipelineState:
    ctx: dict = {"raw_vitals": raw_vitals}
    if patient_context_extra:
        ctx.update(patient_context_extra)
    return PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="vitals.ingested",
        patient_context=ctx,
    )
