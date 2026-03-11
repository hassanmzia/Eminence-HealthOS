"""
Eminence HealthOS — Agent Unit Tests
Tests for the RPM agent pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from healthos_platform.agents.types import (
    AgentInput,
    AgentStatus,
    AgentTier,
    NormalizedVital,
    PipelineState,
    Severity,
    VitalReading,
    VitalType,
)
from healthos_platform.orchestrator.registry import AgentRegistry


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def patient_id():
    return uuid.uuid4()


@pytest.fixture
def sample_vitals(org_id, patient_id):
    now = datetime.now(timezone.utc)
    return [
        {
            "vital_type": "heart_rate",
            "value": {"value": 72},
            "unit": "bpm",
            "recorded_at": (now - timedelta(hours=2)).isoformat(),
            "source": "wearable",
            "device_id": "sim-001",
        },
        {
            "vital_type": "blood_pressure",
            "value": {"systolic": 145, "diastolic": 95},
            "unit": "mmHg",
            "recorded_at": (now - timedelta(hours=1)).isoformat(),
            "source": "home_device",
            "device_id": "sim-002",
        },
        {
            "vital_type": "glucose",
            "value": {"value": 250},
            "unit": "mg/dL",
            "recorded_at": now.isoformat(),
            "source": "home_device",
            "device_id": "sim-003",
        },
        {
            "vital_type": "spo2",
            "value": {"value": 88},
            "unit": "%",
            "recorded_at": now.isoformat(),
            "source": "wearable",
            "device_id": "sim-004",
        },
    ]


@pytest.fixture
def pipeline_state(org_id, patient_id, sample_vitals):
    return PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="vitals.ingested",
        patient_context={"raw_vitals": sample_vitals},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE INGESTION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_device_ingestion(pipeline_state):
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent

    agent = DeviceIngestionAgent()
    assert agent.name == "device_ingestion"
    assert agent.tier == AgentTier.SENSING

    state = await agent.run_in_pipeline(pipeline_state)

    assert len(state.raw_vitals) == 4
    assert state.raw_vitals[0].vital_type == VitalType.HEART_RATE
    assert "device_ingestion" in state.executed_agents


@pytest.mark.asyncio
async def test_device_ingestion_quality_scoring():
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent

    agent = DeviceIngestionAgent()

    # Valid reading should have high quality
    quality = agent._score_quality({
        "vital_type": "heart_rate",
        "value": {"value": 72},
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    assert quality >= 0.8

    # Out-of-range reading should have lower quality
    quality = agent._score_quality({
        "vital_type": "heart_rate",
        "value": {"value": 500},
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    assert quality < 0.8


# ═══════════════════════════════════════════════════════════════════════════════
# VITALS NORMALIZATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_vitals_normalization(pipeline_state):
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    # First run ingestion to populate raw_vitals
    ingestion = DeviceIngestionAgent()
    state = await ingestion.run_in_pipeline(pipeline_state)

    normalizer = VitalsNormalizationAgent()
    state = await normalizer.run_in_pipeline(state)

    assert len(state.normalized_vitals) == 4
    assert "vitals_normalization" in state.executed_agents

    # Verify all vitals have standard units
    for nv in state.normalized_vitals:
        assert nv.unit != ""


# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_anomaly_detection(pipeline_state):
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    # Run pipeline up to anomaly detection
    state = await DeviceIngestionAgent().run_in_pipeline(pipeline_state)
    state = await VitalsNormalizationAgent().run_in_pipeline(state)

    detector = AnomalyDetectionAgent()
    state = await detector.run_in_pipeline(state)

    assert "anomaly_detection" in state.executed_agents

    # Our sample data has abnormal BP (145/95), glucose (250), and spo2 (88)
    # These should trigger anomalies
    assert len(state.anomalies) >= 2


@pytest.mark.asyncio
async def test_anomaly_detection_critical_spo2():
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent

    detector = AnomalyDetectionAgent()

    # Create a state with critically low SpO2
    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    state = PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        normalized_vitals=[
            NormalizedVital(
                patient_id=patient_id,
                org_id=org_id,
                vital_type=VitalType.SPO2,
                value={"value": 82},
                unit="%",
                recorded_at=datetime.now(timezone.utc),
                source="wearable",
                quality_score=1.0,
            )
        ],
    )

    state = await detector.run_in_pipeline(state)
    assert len(state.anomalies) >= 1
    # SpO2 of 82 should be critical
    critical = [a for a in state.anomalies if a.severity == Severity.CRITICAL]
    assert len(critical) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# RISK SCORING AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_risk_scoring(pipeline_state):
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.risk_scoring import RiskScoringAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    # Run full pipeline
    state = await DeviceIngestionAgent().run_in_pipeline(pipeline_state)
    state = await VitalsNormalizationAgent().run_in_pipeline(state)
    state = await AnomalyDetectionAgent().run_in_pipeline(state)

    scorer = RiskScoringAgent()
    state = await scorer.run_in_pipeline(state)

    assert "risk_scoring" in state.executed_agents
    assert len(state.risk_assessments) == 1

    assessment = state.risk_assessments[0]
    assert 0 <= assessment.score <= 1
    assert assessment.score_type == "deterioration"
    assert len(assessment.recommendations) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TREND ANALYSIS AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_trend_analysis_linear():
    from modules.rpm.agents.trend_analysis import TrendAnalysisAgent

    agent = TrendAnalysisAgent()

    # Test increasing trend detection
    values = [100, 105, 112, 118, 125, 130]
    direction, strength = agent._linear_trend(values)
    assert direction == "increasing"
    assert strength > 0.05


@pytest.mark.asyncio
async def test_trend_analysis_volatility():
    from modules.rpm.agents.trend_analysis import TrendAnalysisAgent

    agent = TrendAnalysisAgent()

    # High volatility
    volatile = [100, 80, 120, 75, 130, 85]
    vol = agent._compute_volatility(volatile)
    assert vol > 0.1

    # Stable
    stable = [100, 101, 99, 100, 101, 100]
    vol = agent._compute_volatility(stable)
    assert vol < 0.05


# ═══════════════════════════════════════════════════════════════════════════════
# ADHERENCE MONITORING AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_adherence_monitoring(pipeline_state):
    from modules.rpm.agents.adherence_monitoring import AdherenceMonitoringAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    state = await DeviceIngestionAgent().run_in_pipeline(pipeline_state)
    state = await VitalsNormalizationAgent().run_in_pipeline(state)

    monitor = AdherenceMonitoringAgent()
    state = await monitor.run_in_pipeline(state)

    assert "adherence_monitoring" in state.executed_agents
    adherence = state.patient_context.get("adherence", {})
    assert "overall_rate" in adherence
    assert "by_type" in adherence


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


def test_agent_registry():
    from modules.rpm.agents import register_rpm_agents

    reg = AgentRegistry()
    reg.reset()
    register_rpm_agents()

    assert reg.agent_count == 6
    assert reg.get("device_ingestion") is not None
    assert reg.get("anomaly_detection") is not None
    assert reg.get("risk_scoring") is not None

    sensing_agents = reg.get_by_tier(AgentTier.SENSING)
    assert len(sensing_agents) == 2  # device_ingestion + vitals_normalization

    agents_list = reg.list_agents()
    assert len(agents_list) == 6


# ═══════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_full_rpm_pipeline(pipeline_state):
    """Run the complete RPM agent pipeline end-to-end."""
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

    state = pipeline_state
    for agent in agents:
        state = await agent.run_in_pipeline(state)

    # Verify full pipeline execution
    assert len(state.executed_agents) == 6
    assert "device_ingestion" in state.executed_agents
    assert "vitals_normalization" in state.executed_agents
    assert "anomaly_detection" in state.executed_agents
    assert "risk_scoring" in state.executed_agents
    assert "trend_analysis" in state.executed_agents
    assert "adherence_monitoring" in state.executed_agents

    # Verify data flowed through pipeline
    assert len(state.raw_vitals) > 0
    assert len(state.normalized_vitals) > 0
    assert len(state.risk_assessments) > 0
