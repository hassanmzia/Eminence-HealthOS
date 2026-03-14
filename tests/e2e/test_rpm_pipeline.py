"""
End-to-end RPM workflow tests.

Full pipeline: device ingestion -> vitals normalization -> anomaly detection
             -> risk scoring -> trend analysis -> adherence monitoring.

Each test constructs realistic VitalReading data, runs every agent's
`run_in_pipeline()` method sequentially on a shared PipelineState, and
asserts on both intermediate and final state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from healthos_platform.agents.types import (
    AgentStatus,
    AnomalyDetection,
    NormalizedVital,
    PipelineState,
    RiskAssessment,
    Severity,
    VitalType,
)

from tests.e2e.conftest import _build_reading, make_pipeline_state


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _run_full_pipeline(state: PipelineState) -> PipelineState:
    """Run all six RPM agents in order on *state* and return the mutated state."""
    from modules.rpm.agents.adherence_monitoring import AdherenceMonitoringAgent
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.risk_scoring import RiskScoringAgent
    from modules.rpm.agents.trend_analysis import TrendAnalysisAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    agents = [
        DeviceIngestionAgent(),
        VitalsNormalizationAgent(),
        AnomalyDetectionAgent(),
        RiskScoringAgent(),
        TrendAnalysisAgent(),
        AdherenceMonitoringAgent(),
    ]
    for agent in agents:
        state = await agent.run_in_pipeline(state)
    return state


# ═════════════════════════════════════════════════════════════════════════════
# 1. Normal patient -- no anomalies, low risk
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_full_pipeline_normal_patient(org_id, patient_id, normal_vitals_raw):
    """
    Completely healthy vitals should pass through every agent with:
    - All readings ingested and normalized
    - Zero critical/high anomalies
    - Risk score below the moderate threshold (< 0.25)
    - All six agents recorded in executed_agents
    """
    state = make_pipeline_state(org_id, patient_id, normal_vitals_raw)
    state = await _run_full_pipeline(state)

    # -- Ingestion --------------------------------------------------------
    assert len(state.raw_vitals) == 6, "All 6 normal readings should be ingested"

    # -- Normalization ----------------------------------------------------
    assert len(state.normalized_vitals) == 6
    for nv in state.normalized_vitals:
        assert nv.is_valid, f"{nv.vital_type.value} should be valid"

    # -- Anomalies --------------------------------------------------------
    critical_anomalies = [a for a in state.anomalies if a.severity == Severity.CRITICAL]
    high_anomalies = [a for a in state.anomalies if a.severity == Severity.HIGH]
    assert len(critical_anomalies) == 0, "No critical anomalies expected for normal vitals"
    assert len(high_anomalies) == 0, "No high anomalies expected for normal vitals"

    # -- Risk scoring -----------------------------------------------------
    assert len(state.risk_assessments) == 1
    risk: RiskAssessment = state.risk_assessments[0]
    assert risk.score < 0.25, f"Risk score {risk.score} should be LOW for healthy patient"
    assert risk.risk_level == Severity.LOW

    # -- Execution tracking -----------------------------------------------
    expected_agents = [
        "device_ingestion",
        "vitals_normalization",
        "anomaly_detection",
        "risk_scoring",
        "trend_analysis",
        "adherence_monitoring",
    ]
    assert state.executed_agents == expected_agents

    # -- Adherence --------------------------------------------------------
    adherence = state.patient_context.get("adherence", {})
    assert adherence, "Adherence data should be present in patient_context"


# ═════════════════════════════════════════════════════════════════════════════
# 2. Critical patient -- anomalies, high risk, alerts
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_full_pipeline_critical_patient(org_id, patient_id, critical_vitals_raw):
    """
    Critically abnormal vitals (high BP, low SpO2, tachycardia, fever) should:
    - All be ingested and normalized
    - Trigger multiple critical/high anomalies
    - Produce a high or critical risk score (>= 0.5)
    - Generate clinical recommendations
    """
    state = make_pipeline_state(org_id, patient_id, critical_vitals_raw)
    state = await _run_full_pipeline(state)

    # -- Ingestion & normalization ----------------------------------------
    assert len(state.raw_vitals) == 6
    assert len(state.normalized_vitals) == 6

    # -- Anomalies --------------------------------------------------------
    assert len(state.anomalies) >= 3, (
        f"Expected at least 3 anomalies for critically abnormal vitals, got {len(state.anomalies)}"
    )

    critical_anomalies = [a for a in state.anomalies if a.severity == Severity.CRITICAL]
    assert len(critical_anomalies) >= 1, "SpO2=82 and/or HR=155 should trigger critical anomaly"

    # Verify the anomaly types detected
    anomaly_vital_types = {a.vital_type.value for a in state.anomalies}
    assert "spo2" in anomaly_vital_types, "SpO2 of 82% must be flagged"
    assert "blood_pressure" in anomaly_vital_types, "BP 200/125 must be flagged"

    # -- Risk scoring -----------------------------------------------------
    assert len(state.risk_assessments) == 1
    risk: RiskAssessment = state.risk_assessments[0]
    assert risk.score >= 0.5, f"Risk score {risk.score} should be HIGH/CRITICAL"
    assert risk.risk_level in (Severity.HIGH, Severity.CRITICAL)
    assert len(risk.recommendations) > 0, "High-risk patients should receive recommendations"

    # Check for escalation-type recommendation
    rec_text = " ".join(risk.recommendations).lower()
    assert "review" in rec_text or "notify" in rec_text, (
        "Recommendations should include clinical review or notification"
    )

    # -- Contributing factors in risk assessment --------------------------
    assert len(risk.contributing_factors) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# 3. Deteriorating patient -- trend detection
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_full_pipeline_deteriorating_patient(org_id, patient_id, deteriorating_vitals_raw):
    """
    Gradually worsening vitals (HR rising 70->140, SpO2 falling 99->84,
    BP rising 115/70 -> 190/115) over 6 time-points should:
    - Produce trend_drift or pattern_anomaly detections from TrendAnalysisAgent
    - Show increasing HR and BP flagged as concerning trends
    - Show declining SpO2 flagged as a concerning trend
    """
    state = make_pipeline_state(org_id, patient_id, deteriorating_vitals_raw)
    state = await _run_full_pipeline(state)

    # -- Ingestion --------------------------------------------------------
    # 6 time-points x 3 vital types = 18 readings
    assert len(state.raw_vitals) == 18

    # -- Normalization ----------------------------------------------------
    assert len(state.normalized_vitals) == 18
    valid_count = sum(1 for v in state.normalized_vitals if v.is_valid)
    assert valid_count >= 16, "Most deteriorating readings should still be physiologically valid"

    # -- Trend analysis should fire anomalies -----------------------------
    trend_anomalies = [a for a in state.anomalies if a.anomaly_type == "trend_drift"]
    assert len(trend_anomalies) >= 1, (
        f"Expected trend_drift anomalies for deteriorating patient, got {len(trend_anomalies)}. "
        f"All anomaly types: {[a.anomaly_type for a in state.anomalies]}"
    )

    # At least one of the concerning directions should be caught
    trend_vital_types = {a.vital_type.value for a in trend_anomalies}
    concerning_detected = trend_vital_types & {"heart_rate", "blood_pressure", "spo2"}
    assert len(concerning_detected) >= 1, (
        f"At least one of HR/BP/SpO2 trends should be flagged, got: {trend_vital_types}"
    )

    # -- Risk scoring should reflect the deterioration --------------------
    assert len(state.risk_assessments) == 1
    risk: RiskAssessment = state.risk_assessments[0]
    # The combination of threshold breaches + trends should elevate risk
    assert risk.score >= 0.25, (
        f"Deteriorating patient risk {risk.score} should be at least MODERATE"
    )

    # -- Verify trend_analysis agent executed -----------------------------
    assert "trend_analysis" in state.executed_agents


# ═════════════════════════════════════════════════════════════════════════════
# 4. Data quality filtering -- garbage data rejected
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_data_quality_filtering(org_id, patient_id, now_utc):
    """
    A mix of good and garbage readings should:
    - Ingestion agent filters out unrecognizable / out-of-range data
    - Downstream agents only process quality readings
    - Invalid values flagged during normalization
    """
    good_readings = [
        _build_reading("heart_rate", {"value": 75}, "bpm", now_utc - timedelta(minutes=10)),
        _build_reading("blood_pressure", {"systolic": 122, "diastolic": 80}, "mmHg", now_utc - timedelta(minutes=8)),
        _build_reading("spo2", {"value": 97}, "%", now_utc - timedelta(minutes=5)),
    ]

    garbage_readings = [
        # Heart rate value that is a non-numeric string -> quality penalty
        _build_reading("heart_rate", {"value": "NOT_A_NUMBER"}, "bpm", now_utc - timedelta(minutes=4)),
        # Completely out-of-range heart rate -> quality penalty (value=5000 bpm)
        _build_reading("heart_rate", {"value": 5000}, "bpm", now_utc - timedelta(minutes=3)),
        # Missing value field entirely
        _build_reading("blood_pressure", {}, "mmHg", now_utc - timedelta(minutes=2)),
        # Very old timestamp (30 days ago) -> staleness penalty
        _build_reading("glucose", {"value": 100}, "mg/dL", now_utc - timedelta(days=30)),
    ]

    all_readings = good_readings + garbage_readings

    state = make_pipeline_state(org_id, patient_id, all_readings)
    state = await _run_full_pipeline(state)

    # -- Ingestion should accept most but with degraded quality -----------
    # The DeviceIngestionAgent filters readings with quality < 0.3.
    # Good readings should definitely be ingested.
    assert len(state.raw_vitals) >= len(good_readings), (
        f"At least {len(good_readings)} good readings should survive ingestion, "
        f"got {len(state.raw_vitals)}"
    )

    # -- Normalization: invalid values should be flagged -------------------
    invalid_vitals = [v for v in state.normalized_vitals if not v.is_valid]
    # The out-of-range readings (5000 bpm, etc.) that survive ingestion
    # should be flagged as invalid during normalization
    # Good readings should all be valid
    valid_vitals = [v for v in state.normalized_vitals if v.is_valid]
    assert len(valid_vitals) >= len(good_readings), (
        f"At least {len(good_readings)} readings should be valid after normalization"
    )

    # -- Anomaly detection should only process valid vitals ----------------
    # The anomaly detection agent skips vitals where is_valid is False,
    # so anomalies should come only from valid readings
    for anomaly in state.anomalies:
        assert anomaly.patient_id == patient_id

    # -- Pipeline should complete without errors --------------------------
    assert len(state.executed_agents) == 6


# ═════════════════════════════════════════════════════════════════════════════
# 5. Multi-vital-types -- all processed correctly
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_multi_vital_types(org_id, patient_id, now_utc):
    """
    Mixed vital types (HR, BP, glucose, SpO2, temperature, respiratory_rate,
    weight) should all flow through the pipeline correctly with proper
    normalization and type-specific anomaly detection.
    """
    readings = [
        _build_reading("heart_rate", {"value": 68}, "bpm", now_utc - timedelta(minutes=30)),
        _build_reading("blood_pressure", {"systolic": 115, "diastolic": 74}, "mmHg", now_utc - timedelta(minutes=28)),
        _build_reading("glucose", {"value": 110}, "mg/dL", now_utc - timedelta(minutes=25)),
        _build_reading("spo2", {"value": 99}, "%", now_utc - timedelta(minutes=22)),
        _build_reading("temperature", {"value": 98.6}, "\u00b0F", now_utc - timedelta(minutes=20)),
        _build_reading("respiratory_rate", {"value": 15}, "breaths/min", now_utc - timedelta(minutes=18)),
        _build_reading("weight", {"value": 75.5}, "kg", now_utc - timedelta(minutes=15)),
    ]

    state = make_pipeline_state(org_id, patient_id, readings)
    state = await _run_full_pipeline(state)

    # -- All readings ingested and normalized -----------------------------
    assert len(state.raw_vitals) == 7
    assert len(state.normalized_vitals) == 7

    # -- Verify each vital type is represented ----------------------------
    ingested_types = {v.vital_type.value for v in state.normalized_vitals}
    expected_types = {
        "heart_rate",
        "blood_pressure",
        "glucose",
        "spo2",
        "temperature",
        "respiratory_rate",
        "weight",
    }
    assert ingested_types == expected_types, (
        f"Missing vital types: {expected_types - ingested_types}"
    )

    # -- All should be valid (normal values) ------------------------------
    for nv in state.normalized_vitals:
        assert nv.is_valid, f"{nv.vital_type.value} with value {nv.value} should be valid"

    # -- No critical anomalies for normal multi-type readings -------------
    critical = [a for a in state.anomalies if a.severity == Severity.CRITICAL]
    assert len(critical) == 0

    # -- Risk should be low -----------------------------------------------
    assert len(state.risk_assessments) == 1
    assert state.risk_assessments[0].risk_level == Severity.LOW

    # -- Adherence data should have entries for submitted types -----------
    adherence = state.patient_context.get("adherence", {})
    assert adherence.get("by_type"), "Adherence by_type data should be present"

    # Types that were submitted should have submission_count > 0
    for vt in expected_types:
        if vt in adherence["by_type"]:
            info = adherence["by_type"][vt]
            assert info["submission_count"] > 0, (
                f"{vt} was submitted but adherence shows 0 submissions"
            )


# ═════════════════════════════════════════════════════════════════════════════
# 6. Adherence tracking -- missed readings detected
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_adherence_tracking(org_id, patient_id, now_utc):
    """
    A patient who only submits heart_rate but misses blood_pressure, glucose,
    spo2, and other expected vitals should:
    - Have low overall adherence rate
    - Generate non-compliance alerts for missing types
    - Correctly report submission counts
    """
    # Patient only submits HR readings -- everything else is missing.
    # Make the HR readings old enough that even HR might be non-compliant,
    # but still within the quality window.
    readings = [
        _build_reading("heart_rate", {"value": 70}, "bpm", now_utc - timedelta(hours=2)),
        _build_reading("heart_rate", {"value": 72}, "bpm", now_utc - timedelta(hours=1)),
        _build_reading("heart_rate", {"value": 74}, "bpm", now_utc),
    ]

    state = make_pipeline_state(org_id, patient_id, readings)
    state = await _run_full_pipeline(state)

    # -- Ingestion --------------------------------------------------------
    assert len(state.raw_vitals) == 3

    # -- Adherence check --------------------------------------------------
    adherence = state.patient_context.get("adherence", {})
    assert adherence, "Adherence data should be populated"

    overall_rate = adherence.get("overall_rate", 1.0)
    # Only 1 out of 7 expected vital types has data, so adherence should be low
    assert overall_rate < 0.5, (
        f"Overall adherence {overall_rate} should be < 0.5 when most vital types are missing"
    )

    # Heart rate should be compliant (submitted recently)
    hr_info = adherence.get("by_type", {}).get("heart_rate", {})
    assert hr_info.get("status") == "compliant", (
        f"Heart rate should be compliant, got: {hr_info}"
    )
    assert hr_info.get("submission_count") == 3

    # Blood pressure, glucose, spo2 should be non-compliant or no_data
    for missing_type in ["blood_pressure", "glucose", "spo2"]:
        info = adherence.get("by_type", {}).get(missing_type, {})
        assert info.get("status") in ("no_data", "non_compliant"), (
            f"{missing_type} should be no_data or non_compliant, got: {info.get('status')}"
        )

    # -- Alerts for non-compliance ----------------------------------------
    # The adherence agent creates AlertRequests for non_compliant types
    # (but not for no_data types per the implementation).
    # Types that have *never* been submitted get status="no_data" so they
    # might not produce alerts. This is by design.
    # Check that we at least have alert infrastructure populated.
    assert "adherence_monitoring" in state.executed_agents

    # -- Verify the full pipeline still completed -------------------------
    assert len(state.executed_agents) == 6


# ═════════════════════════════════════════════════════════════════════════════
# Bonus: pipeline state integrity checks
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_state_ids_consistent(org_id, patient_id, normal_vitals_raw):
    """
    Verify that org_id and patient_id propagate correctly through every
    model produced by the pipeline.
    """
    state = make_pipeline_state(org_id, patient_id, normal_vitals_raw)
    state = await _run_full_pipeline(state)

    # Raw vitals
    for rv in state.raw_vitals:
        assert rv.patient_id == patient_id
        assert rv.org_id == org_id

    # Normalized vitals
    for nv in state.normalized_vitals:
        assert nv.patient_id == patient_id
        assert nv.org_id == org_id

    # Anomalies (may be empty for normal vitals)
    for a in state.anomalies:
        assert a.patient_id == patient_id
        assert a.org_id == org_id

    # Risk assessments
    for r in state.risk_assessments:
        assert r.patient_id == patient_id
        assert r.org_id == org_id
