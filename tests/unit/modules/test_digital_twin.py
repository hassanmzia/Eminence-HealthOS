"""Tests for the Digital Twin & Simulation module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"digital_twin.{action}",
        context={"action": action, **extra},
    )


# ── Patient Digital Twin Agent ──────────────────────────────────────

class TestPatientDigitalTwinAgent:
    @pytest.fixture
    def agent(self):
        from modules.digital_twin.agents.patient_digital_twin import PatientDigitalTwinAgent
        return PatientDigitalTwinAgent()

    @pytest.mark.asyncio
    async def test_build_twin(self, agent):
        inp = _input("build_twin", vitals={
            "heart_rate": 78, "bp_systolic": 130, "bp_diastolic": 82,
            "bmi": 28.5, "hba1c": 7.1, "egfr": 55, "cholesterol_ldl": 130,
        }, conditions=["Type 2 Diabetes", "CKD Stage 3"])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "twin" in out.result
        assert "overall_health_score" in out.result["twin"]

    @pytest.mark.asyncio
    async def test_update_twin(self, agent):
        inp = _input("update_twin", observations={
            "heart_rate": 75, "bp_systolic": 128,
        })
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_state(self, agent):
        out = await agent.run(_input("get_state"))
        assert out.status == AgentStatus.COMPLETED
        assert "twin_state" in out.result

    @pytest.mark.asyncio
    async def test_health_timeline(self, agent):
        out = await agent.run(_input("health_timeline", months=6))
        assert out.status == AgentStatus.COMPLETED
        assert "timeline" in out.result

    @pytest.mark.asyncio
    async def test_compare_baseline(self, agent):
        out = await agent.run(_input("compare_baseline"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent_action"))
        assert out.status == AgentStatus.FAILED


# ── What-If Scenario Agent ──────────────────────────────────────────

class TestWhatIfScenarioAgent:
    @pytest.fixture
    def agent(self):
        from modules.digital_twin.agents.whatif_scenario import WhatIfScenarioAgent
        return WhatIfScenarioAgent()

    @pytest.mark.asyncio
    async def test_simulate_medication_change(self, agent):
        inp = _input("simulate_medication_change", medication="metformin",
                      change_type="add", dosage="500mg")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "projection" in out.result

    @pytest.mark.asyncio
    async def test_simulate_lifestyle_change(self, agent):
        inp = _input("simulate_lifestyle_change",
                      changes=["exercise_30min_daily", "dash_diet"])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_simulate_treatment_stop(self, agent):
        inp = _input("simulate_treatment_stop", treatment="ace_inhibitor")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_compare_scenarios(self, agent):
        inp = _input("compare_scenarios", scenarios=[
            {"type": "medication", "name": "add_metformin"},
            {"type": "lifestyle", "name": "exercise_program"},
        ])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "ranked_scenarios" in out.result

    @pytest.mark.asyncio
    async def test_risk_impact(self, agent):
        inp = _input("risk_impact", intervention="care_coordination")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED


# ── Predictive Trajectory Agent ─────────────────────────────────────

class TestPredictiveTrajectoryAgent:
    @pytest.fixture
    def agent(self):
        from modules.digital_twin.agents.predictive_trajectory import PredictiveTrajectoryAgent
        return PredictiveTrajectoryAgent()

    @pytest.mark.asyncio
    async def test_forecast(self, agent):
        inp = _input("forecast", vitals={"heart_rate": 80, "bp_systolic": 135},
                      history_months=6)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "forecast" in out.result

    @pytest.mark.asyncio
    async def test_trend_analysis(self, agent):
        out = await agent.run(_input("trend_analysis"))
        assert out.status == AgentStatus.COMPLETED
        assert "trends" in out.result

    @pytest.mark.asyncio
    async def test_deterioration_risk(self, agent):
        out = await agent.run(_input("deterioration_risk"))
        assert out.status == AgentStatus.COMPLETED
        assert "risk_events" in out.result

    @pytest.mark.asyncio
    async def test_milestone_prediction(self, agent):
        inp = _input("milestone_prediction", targets={"hba1c": 6.5, "bp_systolic": 130})
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED


# ── Treatment Optimization Agent ────────────────────────────────────

class TestTreatmentOptimizationAgent:
    @pytest.fixture
    def agent(self):
        from modules.digital_twin.agents.treatment_optimization import TreatmentOptimizationAgent
        return TreatmentOptimizationAgent()

    @pytest.mark.asyncio
    async def test_optimize_plan(self, agent):
        inp = _input("optimize_plan", conditions=["diabetes", "hypertension"],
                      current_medications=["metformin", "lisinopril"])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "plans" in out.result

    @pytest.mark.asyncio
    async def test_rank_interventions(self, agent):
        out = await agent.run(_input("rank_interventions",
                                      condition="diabetes"))
        assert out.status == AgentStatus.COMPLETED
        assert "interventions" in out.result

    @pytest.mark.asyncio
    async def test_dosage_optimization(self, agent):
        inp = _input("dosage_optimization", medication="metformin",
                      current_dose="500mg", response_data={"hba1c_change": -0.3})
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_care_pathway(self, agent):
        out = await agent.run(_input("care_pathway", condition="chf"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cost_effectiveness(self, agent):
        out = await agent.run(_input("cost_effectiveness",
                                      treatments=["medication_a", "medication_b"]))
        assert out.status == AgentStatus.COMPLETED


# ── Registration & Routing ──────────────────────────────────────────

class TestDigitalTwinRegistration:
    def test_register_agents(self):
        from modules.digital_twin.agents import register_digital_twin_agents
        register_digital_twin_agents()
        from healthos_platform.orchestrator.registry import registry
        assert registry.get("patient_digital_twin") is not None
        assert registry.get("whatif_scenario") is not None
        assert registry.get("predictive_trajectory") is not None
        assert registry.get("treatment_optimization") is not None

    def test_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        assert "digital_twin.build" in ROUTING_TABLE
        assert "digital_twin.simulate" in ROUTING_TABLE
        assert "digital_twin.forecast" in ROUTING_TABLE
        assert "digital_twin.optimize" in ROUTING_TABLE
