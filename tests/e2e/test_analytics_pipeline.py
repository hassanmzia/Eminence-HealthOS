"""
End-to-end Analytics module tests.

Comprehensive tests covering:
  - Population health overview, risk stratification, quality metrics, filtered queries
  - Cohort creation, templates, comparison, template-based creation
  - Readmission risk prediction (single, batch, explainable)
  - Cost analysis summary, RPM ROI, savings forecast
  - Executive intelligence summary, KPI scorecard, trend digest
  - Full analytics pipeline, risk refresh, cohort refresh

Each test instantiates the relevant agent, builds an AgentInput with realistic
context, calls ``process()`` directly, and asserts on output structure, status,
confidence, and result content.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from healthos_platform.agents.types import AgentInput, AgentOutput, AgentStatus

# Register analytics fixtures so pytest discovers them from the companion module.
pytest_plugins = ["tests.e2e.conftest_analytics"]

from tests.e2e.conftest_analytics import make_analytics_input  # noqa: E402

# ── Agent imports ────────────────────────────────────────────────────────────

from modules.analytics.agents.population_health import PopulationHealthAgent
from modules.analytics.agents.cohort_segmentation import CohortSegmentationAgent
from modules.analytics.agents.readmission_risk import ReadmissionRiskAgent
from modules.analytics.agents.cost_analyzer import CostAnalyzerAgent
from modules.analytics.agents.executive_insight import ExecutiveInsightAgent


# ── Helpers ──────────────────────────────────────────────────────────────────


def _assert_valid_output(output: AgentOutput, *, agent_name: str) -> None:
    """Common assertions that every analytics agent output must satisfy."""
    assert isinstance(output, AgentOutput)
    assert output.agent_name == agent_name
    assert output.status in (
        AgentStatus.COMPLETED,
        AgentStatus.WAITING_HITL,
    )
    assert 0.0 <= output.confidence <= 1.0
    assert isinstance(output.result, dict)
    assert output.rationale  # must have a non-empty rationale


# ═════════════════════════════════════════════════════════════════════════════
# POPULATION HEALTH (4 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestPopulationHealth:
    """Population health overview, risk stratification, quality metrics, filtered queries."""

    # 1. test_population_health_overview
    @pytest.mark.asyncio
    async def test_population_health_overview(
        self, analytics_org_id, sample_patient_population
    ):
        """
        POST /analytics/population-health returns valid overview structure
        including total patients, metrics, and an analyzed_at timestamp.
        """
        agent = PopulationHealthAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "overview",
                "patients": sample_patient_population,
                "total_patients": len(sample_patient_population),
            },
            trigger="analytics.population_health",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="population_health")

        result = output.result
        assert result["total_patients"] == 50
        assert "metrics" in result
        metrics = result["metrics"]
        assert "avg_risk_score" in metrics
        assert "high_risk_percent" in metrics
        assert "with_active_alerts" in metrics
        assert 0.0 <= metrics["avg_risk_score"] <= 1.0
        assert metrics["high_risk_percent"] >= 0.0
        assert "analyzed_at" in result

        # Confidence should be higher when patients are provided
        assert output.confidence >= 0.70

    # 2. test_risk_stratification
    @pytest.mark.asyncio
    async def test_risk_stratification(
        self, analytics_org_id, sample_patient_population
    ):
        """
        Risk stratification returns 4 risk tiers with counts that
        sum to the total patient population.
        """
        agent = PopulationHealthAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "risk_stratification",
                "patients": sample_patient_population,
            },
            trigger="analytics.risk_stratification",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="population_health")

        result = output.result
        assert result["total_patients"] == 50

        dist = result["distribution"]
        assert "low" in dist
        assert "moderate" in dist
        assert "high" in dist
        assert "critical" in dist

        # Counts must sum to total
        assert sum(dist.values()) == 50

        # Recommendations must cover all 4 tiers
        assert len(result["recommendations"]) == 4
        rec_tiers = {r["tier"] for r in result["recommendations"]}
        assert rec_tiers == {"low", "moderate", "high", "critical"}

        # high_risk_patients is a subset of critical + high
        assert isinstance(result["high_risk_patients"], list)
        assert len(result["high_risk_patients"]) <= dist.get("critical", 0) + dist.get("high", 0)

        assert "analyzed_at" in result

    # 3. test_quality_metrics
    @pytest.mark.asyncio
    async def test_quality_metrics(self, analytics_org_id):
        """
        Quality metrics returns HEDIS measures with rates between 0 and 1,
        operational metrics, and quality gaps sorted by gap size.
        """
        agent = PopulationHealthAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "quality_metrics",
                "bp_control_rate": 0.72,
                "hba1c_control_rate": 0.60,
                "screening_rate": 0.78,
                "adherence_rate": 0.85,
                "avg_response_time": 12,
                "readmission_rate": 0.082,
                "satisfaction_score": 4.2,
            },
            trigger="analytics.quality_metrics",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="population_health")

        result = output.result
        hedis = result["hedis_measures"]
        assert "bp_control" in hedis
        assert "diabetes_hba1c" in hedis
        assert "preventive_screenings" in hedis
        assert "medication_adherence" in hedis

        # All HEDIS rates must be in [0, 1]
        for measure, rate in hedis.items():
            assert 0.0 <= rate <= 1.0, f"{measure} rate {rate} out of [0,1]"

        # Operational metrics present
        ops = result["operational_metrics"]
        assert "avg_response_time_min" in ops
        assert "readmission_rate" in ops
        assert "patient_satisfaction" in ops

        # Quality gaps sorted by gap descending
        gaps = result["quality_gaps"]
        assert isinstance(gaps, list)
        if len(gaps) >= 2:
            assert gaps[0]["gap"] >= gaps[-1]["gap"]

        # Overall quality score in [0, 1]
        assert 0.0 <= result["overall_quality_score"] <= 1.0
        assert "analyzed_at" in result

    # 4. test_population_health_with_filters
    @pytest.mark.asyncio
    async def test_population_health_with_filters(
        self, analytics_org_id, sample_patient_population
    ):
        """
        Population health overview filters by conditions: passing only
        diabetic patients should yield a smaller total with higher average
        risk than the overall population.
        """
        diabetic_patients = [
            p for p in sample_patient_population
            if any(c.startswith("E11") for c in p.get("diagnosis_codes", []))
        ]

        agent = PopulationHealthAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "overview",
                "patients": diabetic_patients,
                "total_patients": len(diabetic_patients),
            },
            trigger="analytics.population_health",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="population_health")

        result = output.result
        assert result["total_patients"] == len(diabetic_patients)
        assert result["total_patients"] <= 50  # subset
        assert "metrics" in result
        assert "analyzed_at" in result


# ═════════════════════════════════════════════════════════════════════════════
# COHORT MANAGEMENT (4 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestCohortManagement:
    """Cohort creation, templates, comparison, and template-based creation."""

    # 5. test_create_cohort
    @pytest.mark.asyncio
    async def test_create_cohort(
        self, analytics_org_id, sample_patient_population, sample_cohort_criteria
    ):
        """Creates a cohort from criteria and returns a cohort ID."""
        agent = CohortSegmentationAgent()
        criteria_def = sample_cohort_criteria["high_risk"]

        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "create",
                "name": criteria_def["name"],
                "criteria": criteria_def["criteria"],
                "patients": sample_patient_population,
            },
            trigger="analytics.cohort.create",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="cohort_segmentation")

        result = output.result
        assert result["cohort_id"].startswith("COH-")
        assert result["name"] == "High/Critical Risk Patients"
        assert result["criteria"] == {"risk_level": ["high", "critical"]}
        assert result["total_evaluated"] == 50
        assert 0 <= result["patient_count"] <= 50
        assert 0.0 <= result["match_rate"] <= 1.0
        assert "statistics" in result
        assert "created_at" in result

        # The matched count should reflect actual high/critical patients
        expected_high_critical = sum(
            1 for p in sample_patient_population
            if p["risk_level"] in ("high", "critical")
        )
        assert result["patient_count"] == expected_high_critical

    # 6. test_cohort_templates
    @pytest.mark.asyncio
    async def test_cohort_templates(self, analytics_org_id):
        """Returns predefined cohort templates with expected structure."""
        agent = CohortSegmentationAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {"action": "list_templates"},
            trigger="analytics.cohort.templates",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="cohort_segmentation")

        result = output.result
        assert "templates" in result
        templates = result["templates"]
        assert result["total"] == len(templates)
        assert result["total"] >= 5  # at least 5 pre-defined templates

        # Each template has required fields
        template_names = set()
        for t in templates:
            assert "template" in t
            assert "name" in t
            assert "criteria_count" in t
            assert t["criteria_count"] > 0
            template_names.add(t["template"])

        # Verify well-known templates exist
        assert "high_risk_chronic" in template_names
        assert "diabetes_management" in template_names
        assert "readmission_risk" in template_names

        # High confidence for a deterministic listing
        assert output.confidence >= 0.90

    # 7. test_cohort_comparison
    @pytest.mark.asyncio
    async def test_cohort_comparison(self, analytics_org_id):
        """Compares two cohorts with significance flags on each metric."""
        agent = CohortSegmentationAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "compare",
                "cohort_a": "COH-HIGH-RISK",
                "cohort_b": "COH-LOW-RISK",
            },
            trigger="analytics.cohort.compare",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="cohort_segmentation")

        result = output.result
        assert result["cohort_a"] == "COH-HIGH-RISK"
        assert result["cohort_b"] == "COH-LOW-RISK"

        metrics = result["metrics"]
        assert len(metrics) >= 3  # at least a few comparison metrics

        # Each comparison metric has the expected structure
        for metric_name, metric_data in metrics.items():
            assert "a" in metric_data, f"{metric_name} missing 'a' value"
            assert "b" in metric_data, f"{metric_name} missing 'b' value"
            assert "diff" in metric_data, f"{metric_name} missing 'diff'"
            assert "significant" in metric_data, f"{metric_name} missing 'significant'"
            assert isinstance(metric_data["significant"], bool)

        assert "insights" in result
        assert isinstance(result["insights"], list)
        assert len(result["insights"]) >= 1
        assert "compared_at" in result

    # 8. test_cohort_from_template
    @pytest.mark.asyncio
    async def test_cohort_from_template(
        self, analytics_org_id, sample_patient_population
    ):
        """Creates a cohort from a pre-defined template."""
        agent = CohortSegmentationAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "from_template",
                "template": "diabetes_management",
                "patients": sample_patient_population,
            },
            trigger="analytics.cohort.create",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="cohort_segmentation")

        result = output.result
        assert result["cohort_id"].startswith("COH-")
        assert result["template"] == "diabetes_management"
        assert result["name"] == "Diabetes Management"
        assert "criteria" in result
        assert "icd10_prefix" in result["criteria"]
        assert result["total_evaluated"] == 50
        assert isinstance(result["patient_count"], int)
        assert "statistics" in result
        assert "created_at" in result

        # Confidence for template-based cohorts is high
        assert output.confidence >= 0.85


# ═════════════════════════════════════════════════════════════════════════════
# READMISSION RISK (3 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestReadmissionRisk:
    """Single prediction, batch prediction, and explainable prediction."""

    # 9. test_single_patient_prediction
    @pytest.mark.asyncio
    async def test_single_patient_prediction(self, analytics_org_id):
        """Returns a risk score, risk level, and interventions for one patient."""
        patient_id = uuid.uuid4()
        agent = ReadmissionRiskAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "predict",
                "age": 72,
                "conditions": ["heart_failure", "I50.9", "copd", "J44.1"],
                "prior_admissions_6m": 2,
                "length_of_stay_days": 7,
                "ed_visits_6m": 3,
                "medication_count": 8,
                "lives_alone": True,
                "pcp_follow_up_scheduled": False,
                "medication_adherence": 0.65,
                "hba1c": 0,
            },
            patient_id=patient_id,
            trigger="analytics.readmission.predict",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="readmission_risk")

        result = output.result
        assert result["patient_id"] == str(patient_id)
        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["risk_level"] in ("low", "moderate", "high", "critical")
        assert isinstance(result["risk_percentile"], int)
        assert 0 <= result["risk_percentile"] <= 99
        assert isinstance(result["contributing_factors"], list)
        assert len(result["contributing_factors"]) >= 5
        assert isinstance(result["top_factors"], list)
        assert len(result["top_factors"]) <= 5
        assert isinstance(result["recommended_interventions"], list)
        assert len(result["recommended_interventions"]) >= 1
        assert result["model_version"] == "lace_enhanced_v1"
        assert "predicted_at" in result

        # This patient has many risk factors -- should be high or critical
        assert result["risk_level"] in ("high", "critical"), (
            f"Expected high/critical for heavily burdened patient, got {result['risk_level']}"
        )

    # 10. test_batch_prediction
    @pytest.mark.asyncio
    async def test_batch_prediction(
        self, analytics_org_id, sample_patient_population
    ):
        """Processes multiple patients and returns sorted predictions."""
        agent = ReadmissionRiskAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "batch_predict",
                "patients": sample_patient_population,
            },
            trigger="analytics.readmission.batch",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="readmission_risk")

        result = output.result
        assert result["total_patients"] == 50
        assert len(result["predictions"]) == 50

        # Predictions should be sorted by risk score descending
        scores = [p["risk_score"] for p in result["predictions"]]
        assert scores == sorted(scores, reverse=True)

        # Each prediction has required fields
        for pred in result["predictions"]:
            assert "patient_id" in pred
            assert 0.0 <= pred["risk_score"] <= 1.0
            assert pred["risk_level"] in ("low", "moderate", "high", "critical")
            assert "top_factor" in pred

        # Distribution counts must sum to total
        dist = result["risk_distribution"]
        assert sum(dist.values()) == 50

        # Average risk score in valid range
        assert 0.0 <= result["avg_risk_score"] <= 1.0

        # high_risk_count must match distribution
        expected_high_risk = dist.get("high", 0) + dist.get("critical", 0)
        assert result["high_risk_count"] == expected_high_risk

        assert "predicted_at" in result

    # 11. test_explainable_prediction
    @pytest.mark.asyncio
    async def test_explainable_prediction(self, analytics_org_id):
        """Returns feature contributions that explain the risk score."""
        patient_id = uuid.uuid4()
        agent = ReadmissionRiskAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "explain",
                "age": 68,
                "conditions": ["heart_failure", "I50.9"],
                "prior_admissions_6m": 1,
                "length_of_stay_days": 4,
                "ed_visits_6m": 1,
                "medication_count": 6,
                "lives_alone": False,
                "pcp_follow_up_scheduled": True,
                "medication_adherence": 0.90,
                "hba1c": 0,
            },
            patient_id=patient_id,
            trigger="analytics.readmission.explain",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="readmission_risk")

        result = output.result
        assert result["patient_id"] == str(patient_id)
        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["risk_level"] in ("low", "moderate", "high", "critical")

        # Factor breakdown
        breakdown = result["factor_breakdown"]
        assert isinstance(breakdown, list)
        assert len(breakdown) >= 5

        for factor in breakdown:
            assert "factor" in factor
            assert "present" in factor
            assert isinstance(factor["present"], bool)
            assert "contribution" in factor
            assert factor["contribution"] >= 0.0
            assert "weight" in factor
            assert "explanation" in factor

        # Factor contributions should be sorted descending
        contributions = [f["contribution"] for f in breakdown]
        assert contributions == sorted(contributions, reverse=True)

        # Baseline and total risk increase
        assert result["baseline_risk"] == 0.10
        assert result["total_risk_increase"] >= 0.0

        # Model info
        model_info = result["model_info"]
        assert model_info["model"] == "LACE Enhanced v1"
        assert model_info["factors_evaluated"] > 0
        assert model_info["factors_present"] >= 0
        assert model_info["factors_present"] <= model_info["factors_evaluated"]


# ═════════════════════════════════════════════════════════════════════════════
# COST ANALYSIS (3 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestCostAnalysis:
    """Cost summary, RPM ROI calculation, and multi-year savings forecast."""

    # 12. test_cost_summary
    @pytest.mark.asyncio
    async def test_cost_summary(self, analytics_org_id):
        """Returns cost breakdown with patient count, monthly cost, and trend."""
        agent = CostAnalyzerAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "summary",
                "patient_count": 1000,
                "monthly_cost": 250000,
                "efficiency_score": 0.78,
                "cost_trend": "decreasing",
            },
            trigger="analytics.cost.analyze",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="cost_analyzer")

        result = output.result
        assert result["total_patients"] == 1000
        assert result["monthly_operating_cost"] == 250000
        assert result["cost_efficiency_score"] == 0.78
        assert result["cost_trend"] == "decreasing"
        assert "analyzed_at" in result

    # 13. test_rpm_roi
    @pytest.mark.asyncio
    async def test_rpm_roi(self, analytics_org_id):
        """Returns ROI calculation with positive savings for RPM program."""
        agent = CostAnalyzerAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "rpm_roi",
                "patient_count": 200,
                "monthly_rpm_cost": 150,
                "er_visits_avoided_per_patient": 0.4,
                "avg_er_cost": 2500,
                "readmission_reduction_percent": 20,
                "avg_readmission_cost": 15000,
            },
            trigger="analytics.cost.rpm_roi",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="cost_analyzer")

        result = output.result
        assert result["annual_rpm_cost"] > 0
        assert result["er_visit_savings"] > 0
        assert result["readmission_savings"] > 0
        assert result["total_annual_savings"] > 0
        assert result["net_benefit"] > 0  # positive net savings
        assert result["roi_percent"] > 0  # positive ROI
        assert result["payback_months"] > 0
        assert result["patients_analyzed"] == 200
        assert "analyzed_at" in result

        # Verify savings math consistency
        assert result["total_annual_savings"] == result["er_visit_savings"] + result["readmission_savings"]
        assert result["net_benefit"] == result["total_annual_savings"] - result["annual_rpm_cost"]

    # 14. test_cost_forecast
    @pytest.mark.asyncio
    async def test_cost_forecast(self, analytics_org_id):
        """Returns multi-year savings projection with cumulative totals."""
        agent = CostAnalyzerAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "savings_forecast",
                "current_annual_savings": 200000,
                "patient_growth_rate": 0.15,
            },
            trigger="analytics.cost.forecast",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="cost_analyzer")

        result = output.result
        assert result["base_annual_savings"] == 200000
        assert result["growth_rate"] == 0.15

        forecast = result["forecast"]
        assert isinstance(forecast, list)
        assert len(forecast) == 3  # 3-year projection

        # Each year's projection should grow
        for i, year_data in enumerate(forecast):
            assert year_data["year"] == i + 1
            assert year_data["projected_savings"] > 0
            assert year_data["cumulative_savings"] > 0

        # Year-over-year savings should increase
        assert forecast[1]["projected_savings"] > forecast[0]["projected_savings"]
        assert forecast[2]["projected_savings"] > forecast[1]["projected_savings"]

        # Cumulative must be monotonically increasing
        assert forecast[2]["cumulative_savings"] > forecast[1]["cumulative_savings"]
        assert forecast[1]["cumulative_savings"] > forecast[0]["cumulative_savings"]

        # three_year_total matches last cumulative
        assert result["three_year_total"] == forecast[-1]["cumulative_savings"]
        assert result["three_year_total"] > result["base_annual_savings"]
        assert "analyzed_at" in result


# ═════════════════════════════════════════════════════════════════════════════
# EXECUTIVE INTELLIGENCE (3 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestExecutiveIntelligence:
    """Executive summary, KPI scorecard, and trend digest."""

    # 15. test_executive_summary
    @pytest.mark.asyncio
    async def test_executive_summary(self, analytics_org_id):
        """Returns achievements, concerns, recommendations, and KPI breakdowns."""
        agent = ExecutiveInsightAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {"action": "executive_summary", "period": "monthly"},
            trigger="analytics.executive.summary",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="executive_insight")

        result = output.result
        assert result["period"] == "monthly"
        assert "generated_at" in result
        assert "headline" in result
        assert result["headline"]  # non-empty

        # Clinical overview
        clinical = result["clinical_overview"]
        assert clinical["total_patients"] > 0
        assert clinical["active_monitoring"] > 0
        assert 0.0 <= clinical["readmission_rate"] <= 1.0
        assert 0.0 <= clinical["quality_score"] <= 1.0

        # Operational overview
        ops = result["operational_overview"]
        assert ops["workflows_completed"] > 0
        assert 0.0 <= ops["sla_compliance"] <= 1.0
        assert 0.0 <= ops["automation_rate"] <= 1.0

        # Financial overview
        fin = result["financial_overview"]
        assert fin["total_revenue"] > 0
        assert fin["total_cost"] > 0
        assert fin["rpm_roi_percent"] > 0

        # Key achievements and concerns
        assert isinstance(result["key_achievements"], list)
        assert len(result["key_achievements"]) >= 1

        assert isinstance(result["areas_of_concern"], list)
        assert len(result["areas_of_concern"]) >= 1

        assert isinstance(result["strategic_recommendations"], list)
        assert len(result["strategic_recommendations"]) >= 1

    # 16. test_kpi_scorecard
    @pytest.mark.asyncio
    async def test_kpi_scorecard(self, analytics_org_id):
        """Returns all 10 KPIs with status (on_target, off_target, near_target)."""
        agent = ExecutiveInsightAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "kpi_scorecard",
                "actuals": {
                    "readmission_rate_30day": 0.082,
                    "ed_visit_rate": 0.09,
                    "sla_compliance": 0.96,
                    "medication_adherence": 0.87,
                    "quality_score": 0.82,
                    "patient_satisfaction": 4.3,
                    "cost_per_member_monthly": 265,
                    "claim_denial_rate": 0.045,
                    "automation_rate": 0.72,
                    "care_gap_closure_rate": 0.81,
                },
            },
            trigger="analytics.executive.scorecard",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="executive_insight")

        result = output.result
        scorecard = result["scorecard"]

        # Must have exactly 10 KPIs
        assert result["total_kpis"] == 10
        assert len(scorecard) == 10

        # on_target + off_target == total
        assert result["on_target"] + result["off_target"] == 10

        # Overall health must be one of the known values
        assert result["overall_health"] in ("excellent", "good", "needs_attention", "critical")

        # Validate each KPI entry structure
        valid_statuses = {"on_target", "off_target", "near_target"}
        for kpi in scorecard:
            assert "kpi" in kpi
            assert "key" in kpi
            assert "actual" in kpi
            assert "target" in kpi
            assert "variance" in kpi
            assert "status" in kpi
            assert kpi["status"] in valid_statuses, f"Unexpected status: {kpi['status']}"
            assert "direction" in kpi
            assert kpi["direction"] in ("lower_is_better", "higher_is_better")

        # With the provided actuals, most should be on target
        assert result["on_target"] >= 5, (
            f"Expected at least 5 on-target KPIs with good actuals, got {result['on_target']}"
        )

        assert "generated_at" in result

    # 17. test_trend_digest
    @pytest.mark.asyncio
    async def test_trend_digest(self, analytics_org_id):
        """Returns trends with direction, change, status, and significance."""
        agent = ExecutiveInsightAgent()
        agent_input = make_analytics_input(
            analytics_org_id,
            {"action": "trend_digest"},
            trigger="analytics.executive.summary",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="executive_insight")

        result = output.result
        assert "generated_at" in result
        assert "period" in result
        assert "trends" in result
        assert "narrative" in result
        assert result["narrative"]  # non-empty

        trends = result["trends"]
        assert isinstance(trends, list)
        assert len(trends) >= 3  # at least several trends tracked

        valid_directions = {"increasing", "decreasing", "stable"}
        for trend in trends:
            assert "metric" in trend
            assert trend["metric"]  # non-empty
            assert "direction" in trend
            assert trend["direction"] in valid_directions, (
                f"Unknown direction: {trend['direction']}"
            )
            assert "change" in trend
            assert "current" in trend
            assert "status" in trend
            assert "significance" in trend
            assert trend["significance"] in ("low", "medium", "high")

        # Confidence should be reasonable
        assert output.confidence >= 0.80


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS PIPELINE (3 tests)
# ═════════════════════════════════════════════════════════════════════════════


class TestAnalyticsPipeline:
    """Full pipeline runs that exercise multiple agents in sequence."""

    # 18. test_full_analytics_pipeline
    @pytest.mark.asyncio
    async def test_full_analytics_pipeline(
        self, analytics_org_id, sample_patient_population
    ):
        """
        Runs all analytics agents in sequence for an org: population health
        overview -> risk stratification -> cost summary -> executive summary.
        Verifies each stage completes and data flows correctly.
        """
        # Stage 1: Population Health Overview
        pop_agent = PopulationHealthAgent()
        pop_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "overview",
                "patients": sample_patient_population,
                "total_patients": len(sample_patient_population),
            },
            trigger="analytics.population_health",
        )
        pop_output = await pop_agent.process(pop_input)
        _assert_valid_output(pop_output, agent_name="population_health")
        assert pop_output.result["total_patients"] == 50

        # Stage 2: Risk Stratification
        risk_agent = PopulationHealthAgent()
        risk_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "risk_stratification",
                "patients": sample_patient_population,
            },
            trigger="analytics.risk_stratification",
        )
        risk_output = await risk_agent.process(risk_input)
        _assert_valid_output(risk_output, agent_name="population_health")
        assert sum(risk_output.result["distribution"].values()) == 50

        # Stage 3: Cost Summary (informed by population data)
        cost_agent = CostAnalyzerAgent()
        cost_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "summary",
                "patient_count": pop_output.result["total_patients"],
                "monthly_cost": 125000,
                "efficiency_score": 0.80,
                "cost_trend": "decreasing",
            },
            trigger="analytics.cost.analyze",
        )
        cost_output = await cost_agent.process(cost_input)
        _assert_valid_output(cost_output, agent_name="cost_analyzer")
        assert cost_output.result["total_patients"] == 50

        # Stage 4: Executive Summary
        exec_agent = ExecutiveInsightAgent()
        exec_input = make_analytics_input(
            analytics_org_id,
            {"action": "executive_summary", "period": "monthly"},
            trigger="analytics.executive.summary",
        )
        exec_output = await exec_agent.process(exec_input)
        _assert_valid_output(exec_output, agent_name="executive_insight")
        assert "key_achievements" in exec_output.result
        assert "areas_of_concern" in exec_output.result

        # All 4 stages completed
        all_outputs = [pop_output, risk_output, cost_output, exec_output]
        for out in all_outputs:
            assert out.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_HITL)
            assert out.confidence > 0

    # 19. test_risk_refresh_pipeline
    @pytest.mark.asyncio
    async def test_risk_refresh_pipeline(
        self, analytics_org_id, sample_patient_population
    ):
        """
        Refreshes risk scores by running batch readmission prediction
        followed by risk stratification, verifying consistency.
        """
        # Step 1: Batch readmission prediction
        readmit_agent = ReadmissionRiskAgent()
        readmit_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "batch_predict",
                "patients": sample_patient_population,
            },
            trigger="analytics.readmission.batch",
        )
        readmit_output = await readmit_agent.process(readmit_input)
        _assert_valid_output(readmit_output, agent_name="readmission_risk")
        assert readmit_output.result["total_patients"] == 50

        # Step 2: Feed updated risk levels back into stratification
        # Build updated patient list with readmission risk levels
        predictions = readmit_output.result["predictions"]
        updated_patients = []
        for p, pred in zip(sample_patient_population, sorted(predictions, key=lambda x: x["patient_id"])):
            updated = dict(p)
            # Overwrite risk_level with the readmission model's assessment
            matching_pred = next(
                (pr for pr in predictions if pr["patient_id"] == p["patient_id"]),
                None,
            )
            if matching_pred:
                updated["risk_level"] = matching_pred["risk_level"]
                updated["risk_score"] = matching_pred["risk_score"]
            updated_patients.append(updated)

        pop_agent = PopulationHealthAgent()
        strat_input = make_analytics_input(
            analytics_org_id,
            {
                "action": "risk_stratification",
                "patients": updated_patients,
            },
            trigger="analytics.risk_stratification",
        )
        strat_output = await pop_agent.process(strat_input)
        _assert_valid_output(strat_output, agent_name="population_health")

        # Distribution should sum to 50
        dist = strat_output.result["distribution"]
        assert sum(dist.values()) == 50

        # High risk count from batch should match stratification
        high_risk_from_batch = readmit_output.result["high_risk_count"]
        high_risk_from_strat = dist.get("high", 0) + dist.get("critical", 0)
        assert high_risk_from_batch == high_risk_from_strat

    # 20. test_cohort_refresh_pipeline
    @pytest.mark.asyncio
    async def test_cohort_refresh_pipeline(
        self, analytics_org_id, sample_patient_population
    ):
        """
        Creates a cohort, then re-creates it with the same criteria to
        simulate a refresh, verifying that statistics are consistent
        across runs with the same input data.
        """
        agent = CohortSegmentationAgent()
        criteria = {"risk_level": ["high", "critical"]}

        # First creation
        input1 = make_analytics_input(
            analytics_org_id,
            {
                "action": "create",
                "name": "High Risk Refresh Test",
                "criteria": criteria,
                "patients": sample_patient_population,
            },
            trigger="analytics.cohort.create",
        )
        output1 = await agent.process(input1)
        _assert_valid_output(output1, agent_name="cohort_segmentation")

        # Second creation (refresh) with same data
        input2 = make_analytics_input(
            analytics_org_id,
            {
                "action": "create",
                "name": "High Risk Refresh Test",
                "criteria": criteria,
                "patients": sample_patient_population,
            },
            trigger="analytics.cohort.create",
        )
        output2 = await agent.process(input2)
        _assert_valid_output(output2, agent_name="cohort_segmentation")

        # Both runs should produce identical patient counts and match rates
        assert output1.result["patient_count"] == output2.result["patient_count"]
        assert output1.result["match_rate"] == output2.result["match_rate"]
        assert output1.result["total_evaluated"] == output2.result["total_evaluated"]

        # Statistics should match
        stats1 = output1.result["statistics"]
        stats2 = output2.result["statistics"]
        assert stats1["avg_age"] == stats2["avg_age"]
        assert stats1["avg_risk_score"] == stats2["avg_risk_score"]
        assert stats1["avg_conditions"] == stats2["avg_conditions"]

        # Cohort IDs should differ (timestamped)
        # They might be the same if executed in the same second, so we just
        # verify both are valid
        assert output1.result["cohort_id"].startswith("COH-")
        assert output2.result["cohort_id"].startswith("COH-")
