"""
Eminence HealthOS — Core Platform Agent Unit Tests
Tests for the 4 core control agents: Master Orchestrator, HITL, Audit/Trace,
and Quality/Confidence.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    AnomalyDetection,
    NormalizedVital,
    PipelineState,
    RiskAssessment,
    Severity,
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
def basic_state(org_id, patient_id):
    """Minimal pipeline state for testing."""
    return PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="vitals.ingested",
    )


@pytest.fixture
def populated_state(org_id, patient_id):
    """Pipeline state with vitals, anomalies, and risk assessments."""
    state = PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="vitals.ingested",
        normalized_vitals=[
            NormalizedVital(
                patient_id=patient_id,
                org_id=org_id,
                vital_type=VitalType.HEART_RATE,
                value={"value": 72},
                unit="bpm",
                recorded_at=datetime.now(timezone.utc),
                source="wearable",
                quality_score=1.0,
            ),
            NormalizedVital(
                patient_id=patient_id,
                org_id=org_id,
                vital_type=VitalType.SPO2,
                value={"value": 88},
                unit="%",
                recorded_at=datetime.now(timezone.utc),
                source="wearable",
                quality_score=0.95,
            ),
        ],
        anomalies=[
            AnomalyDetection(
                patient_id=patient_id,
                org_id=org_id,
                anomaly_type="threshold_breach",
                vital_type=VitalType.SPO2,
                severity=Severity.CRITICAL,
                description="SpO2 below critical threshold",
                confidence_score=0.92,
            ),
        ],
        risk_assessments=[
            RiskAssessment(
                patient_id=patient_id,
                org_id=org_id,
                score_type="deterioration",
                score=0.82,
                risk_level=Severity.HIGH,
                recommendations=["Immediate clinician review"],
            ),
        ],
    )
    return state


@pytest.fixture
def state_with_agent_outputs(populated_state):
    """Pipeline state with some agent outputs already recorded."""
    state = populated_state
    trace_id = state.trace_id

    state.executed_agents = ["context_assembly", "policy_rules"]
    state.agent_outputs = {
        "context_assembly": AgentOutput(
            trace_id=trace_id,
            agent_name="context_assembly",
            status=AgentStatus.COMPLETED,
            confidence=0.90,
            result={"patient_context": {"demographics": {}}},
            rationale="Context assembled",
            duration_ms=15,
        ),
        "policy_rules": AgentOutput(
            trace_id=trace_id,
            agent_name="policy_rules",
            status=AgentStatus.COMPLETED,
            confidence=0.85,
            result={"violations": [], "compliant": True},
            rationale="All policies passed",
            duration_ms=10,
            requires_hitl=True,
            hitl_reason="Risk score 0.82 requires human review",
        ),
    }
    state.policy_violations = ["Risk score exceeds critical threshold"]
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_master_orchestrator_basic(basic_state):
    from healthos_platform.agents.master_orchestrator import MasterOrchestratorAgent

    agent = MasterOrchestratorAgent()
    assert agent.name == "master_orchestrator"
    assert agent.tier == AgentTier.DECISIONING

    state = await agent.run_in_pipeline(basic_state)

    assert "master_orchestrator" in state.executed_agents
    assert "execution_plan" in state.patient_context
    assert "event_priority" in state.patient_context

    plan = state.patient_context["execution_plan"]
    assert isinstance(plan, list)
    assert len(plan) > 0


@pytest.mark.asyncio
async def test_master_orchestrator_priority_classification():
    from healthos_platform.agents.master_orchestrator import MasterOrchestratorAgent

    agent = MasterOrchestratorAgent()

    # Critical keyword
    assert agent._classify_priority("labs.critical.detected", {}) == "critical"

    # Emergency keyword
    assert agent._classify_priority("patient.emergency.alert", {}) == "emergency"

    # Scheduled keyword
    assert agent._classify_priority("analytics.pipeline.scheduled", {}) == "scheduled"

    # Routine default
    assert agent._classify_priority("vitals.ingested", {}) == "routine"

    # Context override
    assert agent._classify_priority("vitals.ingested", {"priority": "high"}) == "high"

    # Critical anomalies override
    assert agent._classify_priority(
        "vitals.ingested", {"has_critical_anomalies": True}
    ) == "critical"


@pytest.mark.asyncio
async def test_master_orchestrator_execution_plan_includes_control_agents(basic_state):
    from healthos_platform.agents.master_orchestrator import MasterOrchestratorAgent

    agent = MasterOrchestratorAgent()
    state = await agent.run_in_pipeline(basic_state)

    plan = state.patient_context["execution_plan"]
    agent_names = [p["agent"] for p in plan]

    # Should include control suffix agents
    assert "policy_rules" in agent_names
    assert "quality_confidence" in agent_names
    assert "audit_trace" in agent_names


@pytest.mark.asyncio
async def test_master_orchestrator_critical_adds_hitl_checkpoint():
    from healthos_platform.agents.master_orchestrator import MasterOrchestratorAgent

    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    state = PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="labs.critical.detected",
    )

    agent = MasterOrchestratorAgent()
    state = await agent.run_in_pipeline(state)

    plan = state.patient_context["execution_plan"]
    agent_names = [p["agent"] for p in plan]
    assert "hitl" in agent_names


@pytest.mark.asyncio
async def test_master_orchestrator_standalone():
    from healthos_platform.agents.master_orchestrator import MasterOrchestratorAgent

    agent = MasterOrchestratorAgent()
    input_data = AgentInput(
        org_id=uuid.uuid4(),
        trigger="vitals.ingested",
    )
    output = await agent.run(input_data)

    assert output.status == AgentStatus.COMPLETED
    assert "execution_plan" in output.result
    assert output.confidence > 0


# ═══════════════════════════════════════════════════════════════════════════════
# HUMAN-IN-THE-LOOP AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_hitl_no_review_needed(basic_state):
    from healthos_platform.agents.hitl import HumanInTheLoopAgent

    agent = HumanInTheLoopAgent()
    assert agent.name == "hitl"
    assert agent.tier == AgentTier.DECISIONING

    state = await agent.run_in_pipeline(basic_state)

    assert "hitl" in state.executed_agents
    result = state.agent_outputs["hitl"].result
    assert result["requires_review"] is False
    assert result["trigger_count"] == 0


@pytest.mark.asyncio
async def test_hitl_high_risk_triggers_review(state_with_agent_outputs):
    from healthos_platform.agents.hitl import HumanInTheLoopAgent

    agent = HumanInTheLoopAgent()
    state = await agent.run_in_pipeline(state_with_agent_outputs)

    result = state.agent_outputs["hitl"].result
    assert result["requires_review"] is True
    assert result["trigger_count"] > 0
    assert state.requires_hitl is True

    # Should have a structured review request
    assert result["review_request"] is not None
    assert "urgency" in result["review_request"]


@pytest.mark.asyncio
async def test_hitl_policy_violations_trigger_review():
    from healthos_platform.agents.hitl import HumanInTheLoopAgent

    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    state = PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="test",
        policy_violations=[
            "Violation 1",
            "Violation 2",
            "Violation 3",
        ],
    )

    agent = HumanInTheLoopAgent()
    state = await agent.run_in_pipeline(state)

    result = state.agent_outputs["hitl"].result
    assert result["requires_review"] is True
    # Find policy violation trigger
    policy_triggers = [t for t in result["triggers"] if t["type"] == "policy_violations"]
    assert len(policy_triggers) == 1


@pytest.mark.asyncio
async def test_hitl_upstream_flags(state_with_agent_outputs):
    from healthos_platform.agents.hitl import HumanInTheLoopAgent

    agent = HumanInTheLoopAgent()
    state = await agent.run_in_pipeline(state_with_agent_outputs)

    result = state.agent_outputs["hitl"].result
    upstream_triggers = [t for t in result["triggers"] if t["type"] == "upstream_flag"]
    assert len(upstream_triggers) >= 1


@pytest.mark.asyncio
async def test_hitl_urgency_classification():
    from healthos_platform.agents.hitl import HumanInTheLoopAgent

    agent = HumanInTheLoopAgent()

    assert agent._compute_urgency([{"severity": "critical"}]) == "stat"
    assert agent._compute_urgency([{"severity": "high"}]) == "urgent"
    assert agent._compute_urgency([{"severity": "moderate"}]) == "routine"
    assert agent._compute_urgency([]) == "routine"


@pytest.mark.asyncio
async def test_hitl_standalone():
    from healthos_platform.agents.hitl import HumanInTheLoopAgent

    agent = HumanInTheLoopAgent()
    input_data = AgentInput(
        org_id=uuid.uuid4(),
        context={
            "risk_assessments": [{"score": 0.90, "score_type": "deterioration"}],
        },
    )
    output = await agent.run(input_data)

    assert output.requires_hitl is True
    assert output.result["requires_review"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT / TRACE AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_audit_trace_basic(state_with_agent_outputs):
    from healthos_platform.agents.audit import AuditTraceAgent

    agent = AuditTraceAgent()
    assert agent.name == "audit_trace"
    assert agent.tier == AgentTier.MEASUREMENT

    state = await agent.run_in_pipeline(state_with_agent_outputs)

    assert "audit_trace" in state.executed_agents
    audit_log = state.patient_context["audit_log"]

    assert audit_log["trace_id"] == str(state.trace_id)
    assert audit_log["entry_count"] == 2  # context_assembly + policy_rules
    assert len(audit_log["entries"]) == 2
    assert "integrity_hash" in audit_log


@pytest.mark.asyncio
async def test_audit_trace_entries_content(state_with_agent_outputs):
    from healthos_platform.agents.audit import AuditTraceAgent

    agent = AuditTraceAgent()
    state = await agent.run_in_pipeline(state_with_agent_outputs)

    entries = state.patient_context["audit_log"]["entries"]

    for entry in entries:
        assert "agent_name" in entry
        assert "action" in entry
        assert "confidence" in entry
        assert "status" in entry
        assert "rationale" in entry
        assert "timestamp" in entry
        assert "inputs_summary" in entry
        assert "outputs_summary" in entry


@pytest.mark.asyncio
async def test_audit_trace_integrity_hash(state_with_agent_outputs):
    from healthos_platform.agents.audit import AuditTraceAgent

    agent = AuditTraceAgent()
    state1 = await agent.run_in_pipeline(state_with_agent_outputs)

    hash1 = state1.patient_context["audit_log"]["integrity_hash"]
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_audit_trace_records_policy_violations(state_with_agent_outputs):
    from healthos_platform.agents.audit import AuditTraceAgent

    agent = AuditTraceAgent()
    state = await agent.run_in_pipeline(state_with_agent_outputs)

    audit_log = state.patient_context["audit_log"]
    assert audit_log["policy_record"]["total_violations"] == 1


@pytest.mark.asyncio
async def test_audit_trace_standalone():
    from healthos_platform.agents.audit import AuditTraceAgent

    agent = AuditTraceAgent()
    input_data = AgentInput(
        org_id=uuid.uuid4(),
        context={
            "agent_outputs": {
                "test_agent": {
                    "confidence": 0.85,
                    "status": "completed",
                    "rationale": "Test rationale",
                    "result": {"key": "value"},
                    "duration_ms": 20,
                }
            }
        },
    )
    output = await agent.run(input_data)

    assert output.status == AgentStatus.COMPLETED
    assert output.result["audit_log"]["entry_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY / CONFIDENCE AGENT
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_quality_confidence_basic(state_with_agent_outputs):
    from healthos_platform.agents.quality import QualityConfidenceAgent

    agent = QualityConfidenceAgent()
    assert agent.name == "quality_confidence"
    assert agent.tier == AgentTier.MEASUREMENT

    state = await agent.run_in_pipeline(state_with_agent_outputs)

    assert "quality_confidence" in state.executed_agents
    scorecard = state.patient_context["quality_scorecard"]

    assert "composite_score" in scorecard
    assert "grade" in scorecard
    assert "dimensions" in scorecard
    assert scorecard["grade"] in ("A", "B", "C", "D")
    assert 0 <= scorecard["composite_score"] <= 1.0


@pytest.mark.asyncio
async def test_quality_confidence_dimensions(state_with_agent_outputs):
    from healthos_platform.agents.quality import QualityConfidenceAgent

    agent = QualityConfidenceAgent()
    state = await agent.run_in_pipeline(state_with_agent_outputs)

    dims = state.patient_context["quality_scorecard"]["dimensions"]
    expected_dims = ["agent_confidence", "data_completeness", "output_consistency", "clinical_safety"]
    for dim in expected_dims:
        assert dim in dims
        assert 0 <= dims[dim] <= 1.0


@pytest.mark.asyncio
async def test_quality_confidence_grade_classification():
    from healthos_platform.agents.quality import QualityConfidenceAgent

    agent = QualityConfidenceAgent()
    assert agent._classify_grade(0.90) == "A"
    assert agent._classify_grade(0.85) == "A"
    assert agent._classify_grade(0.75) == "B"
    assert agent._classify_grade(0.60) == "C"
    assert agent._classify_grade(0.40) == "D"


@pytest.mark.asyncio
async def test_quality_confidence_low_quality_triggers_hitl():
    from healthos_platform.agents.quality import QualityConfidenceAgent

    org_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    trace_id = uuid.uuid4()

    state = PipelineState(
        trace_id=trace_id,
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="test",
        executed_agents=["failing_agent"],
        agent_outputs={
            "failing_agent": AgentOutput(
                trace_id=trace_id,
                agent_name="failing_agent",
                status=AgentStatus.FAILED,
                confidence=0.2,
                result={},
                rationale="Failed",
            ),
        },
    )

    agent = QualityConfidenceAgent()
    state = await agent.run_in_pipeline(state)

    scorecard = state.patient_context["quality_scorecard"]
    # With a single failed agent at 0.2 confidence, quality should be low
    assert scorecard["grade"] in ("C", "D")
    assert scorecard["requires_review"] is True


@pytest.mark.asyncio
async def test_quality_confidence_standalone():
    from healthos_platform.agents.quality import QualityConfidenceAgent

    agent = QualityConfidenceAgent()
    input_data = AgentInput(
        org_id=uuid.uuid4(),
        context={
            "agent_outputs": {
                "agent_a": {"confidence": 0.95, "status": "completed"},
                "agent_b": {"confidence": 0.88, "status": "completed"},
            },
            "normalized_vitals": [{"value": 72}],
            "anomalies": [],
            "risk_assessments": [{"score": 0.3}],
        },
    )
    output = await agent.run(input_data)

    assert output.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_HITL)
    assert "quality_scorecard" in output.result
    scorecard = output.result["quality_scorecard"]
    assert "composite_score" in scorecard
    assert "grade" in scorecard


@pytest.mark.asyncio
async def test_quality_high_confidence_pipeline(populated_state):
    """A well-populated state with good agent outputs should score well."""
    from healthos_platform.agents.quality import QualityConfidenceAgent

    state = populated_state
    trace_id = state.trace_id

    # Add high-confidence agent outputs
    state.executed_agents = ["agent_a", "agent_b", "agent_c"]
    state.agent_outputs = {
        "agent_a": AgentOutput(
            trace_id=trace_id, agent_name="agent_a",
            status=AgentStatus.COMPLETED, confidence=0.95,
            result={"data": "ok"}, rationale="Good",
        ),
        "agent_b": AgentOutput(
            trace_id=trace_id, agent_name="agent_b",
            status=AgentStatus.COMPLETED, confidence=0.90,
            result={"data": "ok"}, rationale="Good",
        ),
        "agent_c": AgentOutput(
            trace_id=trace_id, agent_name="agent_c",
            status=AgentStatus.COMPLETED, confidence=0.88,
            result={"data": "ok"}, rationale="Good",
        ),
    }
    # Mark HITL to satisfy clinical safety for high risk
    state.requires_hitl = True

    agent = QualityConfidenceAgent()
    state = await agent.run_in_pipeline(state)

    scorecard = state.patient_context["quality_scorecard"]
    assert scorecard["composite_score"] >= 0.70


# ═══════════════════════════════════════════════════════════════════════════════
# CORE AGENT REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


def test_core_agent_registration():
    """All 6 core agents should be registered."""
    from healthos_platform.agents import register_core_agents

    reg = AgentRegistry()
    reg.reset()
    register_core_agents()

    assert reg.agent_count == 6
    assert reg.get("master_orchestrator") is not None
    assert reg.get("context_assembly") is not None
    assert reg.get("policy_rules") is not None
    assert reg.get("hitl") is not None
    assert reg.get("audit_trace") is not None
    assert reg.get("quality_confidence") is not None

    # Check tier assignments
    decisioning = reg.get_by_tier(AgentTier.DECISIONING)
    measurement = reg.get_by_tier(AgentTier.MEASUREMENT)

    decisioning_names = [a.name for a in decisioning]
    assert "master_orchestrator" in decisioning_names
    assert "context_assembly" in decisioning_names
    assert "policy_rules" in decisioning_names
    assert "hitl" in decisioning_names

    measurement_names = [a.name for a in measurement]
    assert "audit_trace" in measurement_names
    assert "quality_confidence" in measurement_names


# ═══════════════════════════════════════════════════════════════════════════════
# FULL CONTROL PLANE PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_full_control_plane_pipeline(populated_state):
    """Run all 6 core agents in sequence as a control plane pipeline."""
    from healthos_platform.agents.audit import AuditTraceAgent
    from healthos_platform.agents.context_assembly import ContextAssemblyAgent
    from healthos_platform.agents.hitl import HumanInTheLoopAgent
    from healthos_platform.agents.master_orchestrator import MasterOrchestratorAgent
    from healthos_platform.agents.policy_rules import PolicyRulesAgent
    from healthos_platform.agents.quality import QualityConfidenceAgent

    agents = [
        MasterOrchestratorAgent(),
        ContextAssemblyAgent(),
        PolicyRulesAgent(),
        HumanInTheLoopAgent(),
        QualityConfidenceAgent(),
        AuditTraceAgent(),
    ]

    state = populated_state
    for agent in agents:
        state = await agent.run_in_pipeline(state)

    # All 6 agents should have executed
    assert len(state.executed_agents) == 6
    assert "master_orchestrator" in state.executed_agents
    assert "context_assembly" in state.executed_agents
    assert "policy_rules" in state.executed_agents
    assert "hitl" in state.executed_agents
    assert "quality_confidence" in state.executed_agents
    assert "audit_trace" in state.executed_agents

    # Master orchestrator should have produced an execution plan in its output
    orchestrator_output = state.agent_outputs["master_orchestrator"]
    assert "execution_plan" in orchestrator_output.result

    # Quality scorecard and audit log should be in patient context
    # (these agents run after context_assembly so their writes persist)
    assert "quality_scorecard" in state.patient_context
    assert "audit_log" in state.patient_context

    # Audit should have captured all prior agents
    audit_log = state.patient_context["audit_log"]
    assert audit_log["entry_count"] == 5  # All except audit_trace itself
