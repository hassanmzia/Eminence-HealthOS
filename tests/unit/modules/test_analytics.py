"""
Eminence HealthOS — Analytics Module Tests
Tests for all Phase 4 analytics agents: population health, outcome tracker,
cost analyzer, cohort segmentation, and readmission risk.
"""

from __future__ import annotations

import uuid

import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.uuid4()


def _input(context: dict, patient_id: uuid.UUID | None = PATIENT_ID) -> AgentInput:
    return AgentInput(
        org_id=ORG_ID,
        patient_id=patient_id,
        trigger="test",
        context=context,
    )


def _status_ok(output) -> bool:
    """Check that output completed (or went to HITL with valid results)."""
    return output.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_HITL)


# ═══════════════════════════════════════════════════════════════════════════════
# POPULATION HEALTH AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestPopulationHealthAgent:

    @pytest.fixture
    def agent(self):
        from modules.analytics.agents.population_health import PopulationHealthAgent
        return PopulationHealthAgent()

    @pytest.mark.asyncio
    async def test_overview(self, agent):
        output = await agent.run(_input({
            "action": "overview",
            "patients": [
                {"risk_score": 0.3, "risk_level": "low", "active_alerts": 0},
                {"risk_score": 0.7, "risk_level": "high", "active_alerts": 2},
                {"risk_score": 0.5, "risk_level": "moderate", "active_alerts": 0},
            ],
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["total_patients"] == 3
        assert output.result["metrics"]["avg_risk_score"] == 0.5

    @pytest.mark.asyncio
    async def test_overview_empty(self, agent):
        output = await agent.run(_input({"action": "overview", "total_patients": 100}))
        # Low confidence (0.65) triggers HITL, but result is still valid
        assert _status_ok(output)
        assert output.result["total_patients"] == 100

    @pytest.mark.asyncio
    async def test_risk_stratification(self, agent):
        patients = [
            {"risk_level": "critical", "risk_score": 0.9, "patient_id": "P1"},
            {"risk_level": "high", "risk_score": 0.7, "patient_id": "P2"},
            {"risk_level": "low", "risk_score": 0.2, "patient_id": "P3"},
            {"risk_level": "low", "risk_score": 0.1, "patient_id": "P4"},
            {"risk_level": "moderate", "risk_score": 0.4, "patient_id": "P5"},
        ]
        output = await agent.run(_input({"action": "risk_stratification", "patients": patients}))
        assert output.status == AgentStatus.COMPLETED
        dist = output.result["distribution"]
        assert dist["critical"] == 1
        assert dist["high"] == 1
        assert dist["low"] == 2
        assert len(output.result["recommendations"]) == 4
        assert len(output.result["high_risk_patients"]) == 2

    @pytest.mark.asyncio
    async def test_quality_metrics(self, agent):
        output = await agent.run(_input({
            "action": "quality_metrics",
            "bp_control_rate": 0.74,
            "hba1c_control_rate": 0.62,
            "screening_rate": 0.78,
            "adherence_rate": 0.83,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["hedis_measures"]["bp_control"] == 0.74
        assert len(output.result["quality_gaps"]) > 0

    @pytest.mark.asyncio
    async def test_quality_metrics_all_met(self, agent):
        output = await agent.run(_input({
            "action": "quality_metrics",
            "bp_control_rate": 0.85,
            "hba1c_control_rate": 0.80,
            "screening_rate": 0.90,
            "adherence_rate": 0.95,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert len(output.result["quality_gaps"]) == 0

    @pytest.mark.asyncio
    async def test_cohort_analysis(self, agent):
        output = await agent.run(_input({
            "action": "cohort_analysis",
            "criteria": {"risk_level": "high"},
            "matched_count": 50,
            "total_patients": 200,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["matched_patients"] == 50
        assert output.result["match_rate"] == 0.25

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        output = await agent.run(_input({"action": "invalid"}))
        # Confidence 0.0 < min_confidence → WAITING_HITL (overrides FAILED)
        assert output.status == AgentStatus.WAITING_HITL
        assert "error" in output.result


# ═══════════════════════════════════════════════════════════════════════════════
# OUTCOME TRACKER AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestOutcomeTrackerAgent:

    @pytest.fixture
    def agent(self):
        from modules.analytics.agents.outcome_tracker import OutcomeTrackerAgent
        return OutcomeTrackerAgent()

    @pytest.mark.asyncio
    async def test_track_outcomes_all_goals_met(self, agent):
        output = await agent.run(_input({
            "action": "track",
            "care_plan": {
                "goals": [
                    {"description": "Lower BP", "metric": "systolic_bp", "target_value": 130},
                    {"description": "Steps > 5000", "metric": "daily_steps", "target_value": 5000},
                ],
                "activities": [
                    {"name": "Daily BP check", "completed": True},
                    {"name": "Weekly exercise", "completed": True},
                ],
            },
            "observations": [
                {"metric": "systolic_bp", "value": 135},  # 135/130 > 1.0 → met
                {"metric": "daily_steps", "value": 6000},  # 6000/5000 > 1.0 → met
            ],
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["outcome_status"] == "excellent"
        assert len(output.result["goal_progress"]) == 2
        assert output.result["goal_progress"][0]["status"] == "met"

    @pytest.mark.asyncio
    async def test_track_outcomes_partial(self, agent):
        output = await agent.run(_input({
            "action": "track",
            "care_plan": {
                "goals": [
                    {"description": "Lower BP", "metric": "systolic_bp", "target_value": 130},
                    {"description": "HbA1c < 7", "metric": "hba1c", "target_value": 7.0},
                ],
                "activities": [],
            },
            "observations": [
                {"metric": "systolic_bp", "value": 128},  # 128/130 = 0.98 → in_progress
                {"metric": "hba1c", "value": 6.5},  # 6.5/7.0 = 0.93 → in_progress
            ],
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["outcome_status"] == "needs_improvement"

    @pytest.mark.asyncio
    async def test_track_no_goals(self, agent):
        output = await agent.run(_input({
            "action": "track",
            "care_plan": {},
            "observations": [],
        }))
        # No goals → confidence 0.65 → HITL
        assert _status_ok(output)
        assert output.result["outcome_status"] == "no_goals"

    @pytest.mark.asyncio
    async def test_adherence_check(self, agent):
        output = await agent.run(_input({
            "action": "adherence",
            "care_plan": {
                "activities": [
                    {"name": "Daily BP check", "completed": True},
                    {"name": "Exercise", "completed": True},
                    {"name": "Medication", "completed": False},
                    {"name": "Diet log", "completed": True},
                ],
            },
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["adherence_rate"] == 0.75
        assert output.result["adherence_level"] == "good"
        assert len(output.result["non_adherent_activities"]) == 1

    @pytest.mark.asyncio
    async def test_adherence_perfect(self, agent):
        output = await agent.run(_input({
            "action": "adherence",
            "care_plan": {
                "activities": [
                    {"name": "A", "completed": True},
                    {"name": "B", "completed": True},
                ],
            },
        }))
        assert output.result["adherence_rate"] == 1.0
        assert output.result["adherence_level"] == "excellent"

    @pytest.mark.asyncio
    async def test_treatment_effectiveness(self, agent):
        output = await agent.run(_input({
            "action": "effectiveness",
            "treatments": [
                {"name": "Drug A", "outcomes": [{"improved": True}, {"improved": True}, {"improved": False}]},
                {"name": "Drug B", "outcomes": [{"improved": False}, {"improved": False}]},
            ],
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["treatments_analyzed"] == 2
        assert output.result["most_effective"] == "Drug A"
        assert output.result["assessments"][0]["effectiveness_rate"] > 0.5

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        output = await agent.run(_input({"action": "invalid"}))
        assert output.status == AgentStatus.WAITING_HITL
        assert "error" in output.result


# ═══════════════════════════════════════════════════════════════════════════════
# COST ANALYZER AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestCostAnalyzerAgent:

    @pytest.fixture
    def agent(self):
        from modules.analytics.agents.cost_analyzer import CostAnalyzerAgent
        return CostAnalyzerAgent()

    @pytest.mark.asyncio
    async def test_rpm_roi(self, agent):
        output = await agent.run(_input({
            "action": "rpm_roi",
            "patient_count": 100,
            "monthly_rpm_cost": 150,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["annual_rpm_cost"] == 180000
        assert output.result["roi_percent"] > 0
        assert output.result["net_benefit"] > 0

    @pytest.mark.asyncio
    async def test_cost_per_patient(self, agent):
        output = await agent.run(_input({"action": "cost_per_patient"}))
        assert output.status == AgentStatus.COMPLETED
        assert "avg_monthly_cost" in output.result
        assert "cost_by_risk_level" in output.result
        assert output.result["cost_by_risk_level"]["critical"] == 1200

    @pytest.mark.asyncio
    async def test_savings_forecast(self, agent):
        output = await agent.run(_input({
            "action": "savings_forecast",
            "current_annual_savings": 200000,
            "patient_growth_rate": 0.15,
        }))
        # Savings forecast has confidence 0.72 < min_confidence 0.75 → HITL
        assert _status_ok(output)
        assert len(output.result["forecast"]) == 3
        assert output.result["forecast"][0]["projected_savings"] > 200000
        assert output.result["three_year_total"] > 0

    @pytest.mark.asyncio
    async def test_cost_summary(self, agent):
        output = await agent.run(_input({
            "action": "summary",
            "patient_count": 500,
            "monthly_cost": 75000,
            "efficiency_score": 0.82,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["total_patients"] == 500
        assert output.result["monthly_operating_cost"] == 75000

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        output = await agent.run(_input({"action": "invalid"}))
        assert output.status == AgentStatus.WAITING_HITL
        assert "error" in output.result


# ═══════════════════════════════════════════════════════════════════════════════
# COHORT SEGMENTATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestCohortSegmentationAgent:

    @pytest.fixture
    def agent(self):
        from modules.analytics.agents.cohort_segmentation import CohortSegmentationAgent
        return CohortSegmentationAgent()

    @pytest.mark.asyncio
    async def test_create_cohort(self, agent):
        output = await agent.run(_input({
            "action": "create",
            "name": "Test Cohort",
            "criteria": {"risk_level": ["high", "critical"]},
            "patients": [
                {"patient_id": "P1", "risk_level": "high", "age": 70, "risk_score": 0.7},
                {"patient_id": "P2", "risk_level": "low", "age": 45, "risk_score": 0.2},
                {"patient_id": "P3", "risk_level": "critical", "age": 80, "risk_score": 0.9},
            ],
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["patient_count"] == 2
        assert output.result["total_evaluated"] == 3

    @pytest.mark.asyncio
    async def test_create_from_template(self, agent):
        output = await agent.run(_input({
            "action": "from_template",
            "template": "diabetes_management",
            "patients": [
                {"patient_id": "P1", "diagnosis_codes": ["E11.9"]},
                {"patient_id": "P2", "diagnosis_codes": ["I10"]},
            ],
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["template"] == "diabetes_management"
        assert output.result["patient_count"] == 1

    @pytest.mark.asyncio
    async def test_create_from_invalid_template(self, agent):
        output = await agent.run(_input({
            "action": "from_template",
            "template": "nonexistent",
        }))
        # Confidence 0.0 → HITL overrides FAILED
        assert output.status == AgentStatus.WAITING_HITL
        assert "available_templates" in output.result

    @pytest.mark.asyncio
    async def test_list_templates(self, agent):
        output = await agent.run(_input({"action": "list_templates"}))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["total"] == 7
        assert len(output.result["templates"]) == 7

    @pytest.mark.asyncio
    async def test_analyze_cohort(self, agent):
        output = await agent.run(_input({
            "action": "analyze",
            "cohort_id": "COH-TEST-001",
        }))
        assert output.status == AgentStatus.COMPLETED
        assert "demographics" in output.result
        assert "risk_profile" in output.result

    @pytest.mark.asyncio
    async def test_compare_cohorts(self, agent):
        output = await agent.run(_input({
            "action": "compare",
            "cohort_a": "COH-A",
            "cohort_b": "COH-B",
        }))
        assert output.status == AgentStatus.COMPLETED
        assert len(output.result["metrics"]) > 0
        assert len(output.result["insights"]) > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        output = await agent.run(_input({"action": "invalid"}))
        assert output.status == AgentStatus.WAITING_HITL
        assert "error" in output.result


# ═══════════════════════════════════════════════════════════════════════════════
# READMISSION RISK AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestReadmissionRiskAgent:

    @pytest.fixture
    def agent(self):
        from modules.analytics.agents.readmission_risk import ReadmissionRiskAgent
        return ReadmissionRiskAgent()

    @pytest.mark.asyncio
    async def test_predict_low_risk(self, agent):
        output = await agent.run(_input({
            "action": "predict",
            "age": 45,
            "conditions": [],
            "prior_admissions_6m": 0,
            "length_of_stay_days": 2,
            "ed_visits_6m": 0,
            "medication_count": 2,
            "pcp_follow_up_scheduled": True,
        }))
        assert _status_ok(output)
        assert output.result["risk_level"] == "low"
        assert output.result["risk_score"] < 0.30

    @pytest.mark.asyncio
    async def test_predict_high_risk(self, agent):
        output = await agent.run(_input({
            "action": "predict",
            "age": 78,
            "conditions": ["I50.9", "J44.1"],
            "prior_admissions_6m": 2,
            "length_of_stay_days": 8,
            "ed_visits_6m": 3,
            "medication_count": 10,
            "lives_alone": True,
            "pcp_follow_up_scheduled": False,
            "medication_adherence": 0.6,
            "hba1c": 10.2,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["risk_level"] in ("high", "critical")
        assert output.result["risk_score"] >= 0.50
        assert len(output.result["recommended_interventions"]) > 0
        assert len(output.result["top_factors"]) <= 5

    @pytest.mark.asyncio
    async def test_predict_has_contributing_factors(self, agent):
        output = await agent.run(_input({
            "action": "predict",
            "age": 70,
            "conditions": ["heart_failure"],
            "prior_admissions_6m": 1,
        }))
        assert _status_ok(output)
        factors = output.result["contributing_factors"]
        assert len(factors) > 0
        hf_factor = next((f for f in factors if f["factor"] == "heart_failure"), None)
        assert hf_factor is not None
        assert hf_factor["present"] is True

    @pytest.mark.asyncio
    async def test_batch_predict(self, agent):
        output = await agent.run(_input({
            "action": "batch_predict",
            "patients": [
                {"patient_id": "P1", "age": 45, "conditions": [], "prior_admissions_6m": 0},
                {"patient_id": "P2", "age": 78, "conditions": ["I50.9"], "prior_admissions_6m": 3},
                {"patient_id": "P3", "age": 65, "conditions": ["J44.1"], "prior_admissions_6m": 1},
            ],
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["total_patients"] == 3
        preds = output.result["predictions"]
        assert preds[0]["risk_score"] >= preds[1]["risk_score"]  # sorted desc
        assert "risk_distribution" in output.result

    @pytest.mark.asyncio
    async def test_explain_prediction(self, agent):
        output = await agent.run(_input({
            "action": "explain",
            "age": 72,
            "conditions": ["copd"],
            "prior_admissions_6m": 2,
            "medication_count": 8,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert "factor_breakdown" in output.result
        assert output.result["baseline_risk"] == 0.10
        assert output.result["model_info"]["factors_present"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        output = await agent.run(_input({"action": "invalid"}))
        assert output.status == AgentStatus.WAITING_HITL
        assert "error" in output.result


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnalyticsRegistration:

    def test_register_analytics_agents(self):
        import healthos_platform.orchestrator.registry as reg_mod
        from modules.analytics.agents import register_analytics_agents

        original = reg_mod.registry
        # Reset the singleton to get a clean registry
        reg_mod.registry.reset()

        try:
            register_analytics_agents()
            agents = reg_mod.registry.list_agents()
            names = [a["name"] for a in agents]
            assert "population_health" in names
            assert "outcome_tracker" in names
            assert "cost_analyzer" in names
            assert "cohort_segmentation" in names
            assert "readmission_risk" in names
        finally:
            reg_mod.registry.reset()


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING TABLE
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnalyticsRouting:

    def test_analytics_events_in_routing_table(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE

        assert "analytics.population_health" in ROUTING_TABLE
        assert "analytics.readmission.predict" in ROUTING_TABLE
        assert "analytics.cohort.create" in ROUTING_TABLE
        assert "analytics.cost.analyze" in ROUTING_TABLE
        assert "analytics.outcome.track" in ROUTING_TABLE
        assert "analytics.discharge.assess" in ROUTING_TABLE

    def test_discharge_assess_pipeline(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE

        agents = ROUTING_TABLE["analytics.discharge.assess"]
        assert "readmission_risk" in agents
        assert "outcome_tracker" in agents
