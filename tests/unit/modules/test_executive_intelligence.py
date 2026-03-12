"""
Eminence HealthOS — Executive Intelligence Agent Tests
Tests for Sprint 23-24: Cost/Risk Insight + Executive Insight agents.
"""

from __future__ import annotations

import uuid

import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus


# ── Helpers ──────────────────────────────────────────────────────────────────

def _input(context: dict) -> AgentInput:
    return AgentInput(
        org_id=uuid.uuid4(),
        trigger="test",
        context=context,
    )


def _status_ok(output) -> bool:
    return output.status == AgentStatus.COMPLETED


# ═══════════════════════════════════════════════════════════════════════════════
# COST/RISK INSIGHT AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestCostRiskInsightAgent:

    @pytest.fixture
    def agent(self):
        from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent
        return CostRiskInsightAgent()

    @pytest.mark.asyncio
    async def test_cost_drivers(self, agent):
        output = await agent.run(_input({
            "action": "cost_drivers",
            "patient_count": 1000,
            "period_months": 12,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["total_cost"] > 0
        assert len(output.result["top_drivers"]) == 5
        assert output.result["top_drivers"][0]["pct_of_total"] > 0

    @pytest.mark.asyncio
    async def test_risk_cost_correlation(self, agent):
        output = await agent.run(_input({"action": "risk_cost_correlation"}))
        assert output.status == AgentStatus.COMPLETED
        assert len(output.result["correlations"]) == 4
        assert len(output.result["insights"]) > 0
        # Critical patients should cost more than low
        corrs = {c["risk_level"]: c for c in output.result["correlations"]}
        assert corrs["critical"]["monthly_cost_per_patient"] > corrs["low"]["monthly_cost_per_patient"]

    @pytest.mark.asyncio
    async def test_intervention_impact(self, agent):
        output = await agent.run(_input({
            "action": "intervention_impact",
            "intervention": "rpm_monitoring",
            "patient_count": 500,
            "current_costs": {
                "ed_visits": 1250000,
                "inpatient_admissions": 4500000,
                "readmissions": 1800000,
            },
        }))
        assert _status_ok(output)
        assert output.result["intervention"] == "Remote Patient Monitoring"
        assert output.result["roi_percent"] > 0
        assert "savings_by_category" in output.result

    @pytest.mark.asyncio
    async def test_intervention_impact_invalid(self, agent):
        output = await agent.run(_input({
            "action": "intervention_impact",
            "intervention": "nonexistent",
        }))
        assert output.status == AgentStatus.WAITING_HITL
        assert "available" in output.result

    @pytest.mark.asyncio
    async def test_cost_trends(self, agent):
        output = await agent.run(_input({"action": "cost_trends"}))
        assert output.status == AgentStatus.COMPLETED
        assert len(output.result["monthly_data"]) == 6
        assert output.result["overall_trend"] == "decreasing"

    @pytest.mark.asyncio
    async def test_opportunity_scan(self, agent):
        output = await agent.run(_input({"action": "opportunity_scan"}))
        assert output.status == AgentStatus.COMPLETED
        assert len(output.result["opportunities"]) > 0
        assert output.result["total_potential_savings"] > 0
        assert len(output.result["quick_wins"]) > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        output = await agent.run(_input({"action": "invalid"}))
        assert output.status == AgentStatus.WAITING_HITL
        assert "error" in output.result


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE INSIGHT AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutiveInsightAgent:

    @pytest.fixture
    def agent(self):
        from modules.analytics.agents.executive_insight import ExecutiveInsightAgent
        return ExecutiveInsightAgent()

    @pytest.mark.asyncio
    async def test_executive_summary(self, agent):
        output = await agent.run(_input({"action": "executive_summary"}))
        assert output.status == AgentStatus.COMPLETED
        r = output.result
        assert "headline" in r
        assert "clinical_overview" in r
        assert "operational_overview" in r
        assert "financial_overview" in r
        assert len(r["key_achievements"]) > 0
        assert len(r["strategic_recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_kpi_scorecard(self, agent):
        output = await agent.run(_input({"action": "kpi_scorecard"}))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["total_kpis"] == 10
        assert output.result["on_target"] + output.result["off_target"] == 10
        assert output.result["overall_health"] in (
            "excellent", "good", "needs_attention", "critical"
        )

    @pytest.mark.asyncio
    async def test_kpi_scorecard_custom_actuals(self, agent):
        output = await agent.run(_input({
            "action": "kpi_scorecard",
            "actuals": {
                "readmission_rate_30day": 0.05,
                "sla_compliance": 0.98,
                "quality_score": 0.90,
            },
        }))
        assert output.status == AgentStatus.COMPLETED
        scorecard = output.result["scorecard"]
        readmit = next(s for s in scorecard if s["key"] == "readmission_rate_30day")
        assert readmit["actual"] == 0.05
        assert readmit["status"] == "on_target"

    @pytest.mark.asyncio
    async def test_strategic_brief(self, agent):
        output = await agent.run(_input({"action": "strategic_brief"}))
        assert output.status == AgentStatus.COMPLETED
        assert len(output.result["strategic_themes"]) == 4
        assert "projected_impact" in output.result
        assert output.result["projected_impact"]["12_month_savings"] > 0

    @pytest.mark.asyncio
    async def test_department_report_clinical(self, agent):
        output = await agent.run(_input({
            "action": "department_report",
            "department": "clinical",
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["department"] == "Clinical Operations"
        assert len(output.result["highlights"]) > 0

    @pytest.mark.asyncio
    async def test_department_report_finance(self, agent):
        output = await agent.run(_input({
            "action": "department_report",
            "department": "finance",
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["department"] == "Finance"
        assert output.result["metrics"]["rpm_roi_pct"] > 0

    @pytest.mark.asyncio
    async def test_department_report_operations(self, agent):
        output = await agent.run(_input({
            "action": "department_report",
            "department": "operations",
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["department"] == "Operations"

    @pytest.mark.asyncio
    async def test_trend_digest(self, agent):
        output = await agent.run(_input({"action": "trend_digest"}))
        assert output.status == AgentStatus.COMPLETED
        assert len(output.result["trends"]) == 6
        assert "narrative" in output.result

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

        reg_mod.registry.reset()

        try:
            register_analytics_agents()
            agents = reg_mod.registry.list_agents()
            names = [a["name"] for a in agents]
            assert "cost_risk_insight" in names
            assert "executive_insight" in names
        finally:
            reg_mod.registry.reset()


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING TABLE
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutiveRouting:

    def test_executive_events_in_routing_table(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE

        assert "analytics.cost_risk.analyze" in ROUTING_TABLE
        assert "analytics.executive.summary" in ROUTING_TABLE
        assert "analytics.executive.scorecard" in ROUTING_TABLE
        assert "analytics.executive.brief" in ROUTING_TABLE
        assert "analytics.pipeline.scheduled" in ROUTING_TABLE

    def test_scheduled_pipeline(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE

        agents = ROUTING_TABLE["analytics.pipeline.scheduled"]
        assert "cost_risk_insight" in agents
        assert "executive_insight" in agents

    def test_executive_summary_pipeline(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE

        agents = ROUTING_TABLE["analytics.executive.summary"]
        assert "cost_risk_insight" in agents
        assert "executive_insight" in agents
