"""
End-to-end test for the full RPM agent pipeline flow.
Simulates: vitals ingestion → normalization → anomaly detection → risk scoring
→ trend analysis → adherence monitoring → clinical summary → care plan
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from healthos_platform.agents.types import (
    AgentInput,
    AgentStatus,
    PipelineState,
    Severity,
    VitalType,
)


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def patient_id():
    return uuid.uuid4()


@pytest.fixture
def critical_vitals(org_id, patient_id):
    """Vitals data with critical values that should trigger the full pipeline."""
    now = datetime.now(timezone.utc)
    return [
        {
            "vital_type": "heart_rate",
            "value": {"value": 130},  # Tachycardia
            "unit": "bpm",
            "recorded_at": (now - timedelta(minutes=30)).isoformat(),
            "source": "wearable",
            "device_id": "watch-001",
        },
        {
            "vital_type": "blood_pressure",
            "value": {"systolic": 185, "diastolic": 110},  # Hypertensive crisis
            "unit": "mmHg",
            "recorded_at": (now - timedelta(minutes=15)).isoformat(),
            "source": "home_device",
            "device_id": "bp-001",
        },
        {
            "vital_type": "spo2",
            "value": {"value": 85},  # Critical hypoxemia
            "unit": "%",
            "recorded_at": now.isoformat(),
            "source": "wearable",
            "device_id": "watch-001",
        },
        {
            "vital_type": "temperature",
            "value": {"value": 103.5},  # High fever
            "unit": "°F",
            "recorded_at": now.isoformat(),
            "source": "home_device",
            "device_id": "therm-001",
        },
    ]


@pytest.fixture
def critical_pipeline_state(org_id, patient_id, critical_vitals):
    return PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="vitals.ingested",
        patient_context={"raw_vitals": critical_vitals},
    )


@pytest.mark.asyncio
async def test_critical_vitals_trigger_high_risk(critical_pipeline_state):
    """Critical vitals should flow through the pipeline and produce high risk."""
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.risk_scoring import RiskScoringAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    state = critical_pipeline_state

    # Run the core pipeline
    state = await DeviceIngestionAgent().run_in_pipeline(state)
    assert len(state.raw_vitals) == 4

    state = await VitalsNormalizationAgent().run_in_pipeline(state)
    assert len(state.normalized_vitals) == 4

    state = await AnomalyDetectionAgent().run_in_pipeline(state)
    # Multiple critical vitals should produce multiple anomalies
    assert len(state.anomalies) >= 2
    critical_anomalies = [a for a in state.anomalies if a.severity == Severity.CRITICAL]
    assert len(critical_anomalies) >= 1, "SpO2 of 85% should trigger critical anomaly"

    state = await RiskScoringAgent().run_in_pipeline(state)
    assert len(state.risk_assessments) == 1
    risk = state.risk_assessments[0]
    # With multiple critical anomalies, risk should be high
    assert risk.score >= 0.5
    assert risk.level in ("high", "critical")


@pytest.mark.asyncio
async def test_normal_vitals_produce_low_risk():
    """Normal vitals should flow through and produce low risk."""
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.risk_scoring import RiskScoringAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    now = datetime.now(timezone.utc)
    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()

    normal_vitals = [
        {
            "vital_type": "heart_rate",
            "value": {"value": 72},
            "unit": "bpm",
            "recorded_at": now.isoformat(),
            "source": "wearable",
            "device_id": "watch-001",
        },
        {
            "vital_type": "blood_pressure",
            "value": {"systolic": 120, "diastolic": 78},
            "unit": "mmHg",
            "recorded_at": now.isoformat(),
            "source": "home_device",
            "device_id": "bp-001",
        },
        {
            "vital_type": "spo2",
            "value": {"value": 98},
            "unit": "%",
            "recorded_at": now.isoformat(),
            "source": "wearable",
            "device_id": "watch-001",
        },
    ]

    state = PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="vitals.ingested",
        patient_context={"raw_vitals": normal_vitals},
    )

    state = await DeviceIngestionAgent().run_in_pipeline(state)
    state = await VitalsNormalizationAgent().run_in_pipeline(state)
    state = await AnomalyDetectionAgent().run_in_pipeline(state)
    state = await RiskScoringAgent().run_in_pipeline(state)

    # Normal vitals should produce few/no anomalies
    critical_anomalies = [a for a in state.anomalies if a.severity == Severity.CRITICAL]
    assert len(critical_anomalies) == 0

    # Risk should be low
    assert len(state.risk_assessments) == 1
    risk = state.risk_assessments[0]
    assert risk.score < 0.5


@pytest.mark.asyncio
async def test_pipeline_execution_order(critical_pipeline_state):
    """All agents should execute in correct tier order."""
    from modules.rpm.agents.adherence_monitoring import AdherenceMonitoringAgent
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
    from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
    from modules.rpm.agents.risk_scoring import RiskScoringAgent
    from modules.rpm.agents.trend_analysis import TrendAnalysisAgent
    from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent

    agents = [
        DeviceIngestionAgent(),       # Tier 1: Sensing
        VitalsNormalizationAgent(),   # Tier 1: Sensing
        AnomalyDetectionAgent(),      # Tier 2: Interpretation
        RiskScoringAgent(),           # Tier 3: Decisioning
        TrendAnalysisAgent(),         # Tier 2: Interpretation
        AdherenceMonitoringAgent(),   # Tier 2: Interpretation
    ]

    state = critical_pipeline_state
    for agent in agents:
        state = await agent.run_in_pipeline(state)

    assert len(state.executed_agents) == 6
    # Verify each agent recorded its output
    for agent in agents:
        assert agent.name in state.agent_outputs
        output = state.agent_outputs[agent.name]
        assert output.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_HITL)


@pytest.mark.asyncio
async def test_drug_interaction_full_safety():
    """Drug interaction agent should detect unsafe combinations."""
    from modules.pharmacy.agents.drug_interaction import DrugInteractionAgent

    agent = DrugInteractionAgent()
    inp = AgentInput(
        trace_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        trigger="prescription.create",
        context={
            "action": "full_safety_check",
            "new_drug": "tramadol",
            "current_medications": ["sertraline", "gabapentin"],
            "allergies": ["nsaid"],
            "patient_age": 70,
            "conditions": [],
        },
    )
    out = await agent.process(inp)

    assert out.result["safe_to_prescribe"] is False
    assert out.result["total_issues"] >= 2  # DDI + age warning
    # Serotonin syndrome risk
    ddi = out.result["drug_interactions"]
    assert any("serotonin" in i["description"].lower() for i in ddi)
