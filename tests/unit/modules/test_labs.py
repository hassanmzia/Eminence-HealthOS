"""Tests for the Labs module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"labs.{action}",
        context={"action": action, **extra},
    )


# ── Lab Order Agent ──────────────────────────────────────────────


class TestLabOrderAgent:
    @pytest.fixture
    def agent(self):
        from modules.labs.agents.lab_order import LabOrderAgent
        return LabOrderAgent()

    @pytest.mark.asyncio
    async def test_create_order(self, agent):
        out = await agent.run(_input("create_order",
            panels=["bmp", "hba1c"], priority="routine"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_panels"] == 2
        assert out.result["status"] == "ordered"

    @pytest.mark.asyncio
    async def test_create_order_with_unknown_panel(self, agent):
        out = await agent.run(_input("create_order",
            panels=["bmp", "nonexistent_panel"]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_panels"] == 1  # only bmp recognized

    @pytest.mark.asyncio
    async def test_cancel_order(self, agent):
        out = await agent.run(_input("cancel_order",
            lab_order_id="LO-001", reason="Patient rescheduled"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_order_status(self, agent):
        out = await agent.run(_input("order_status",
            lab_order_id="LO-001"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_suggest_panels_diabetes(self, agent):
        out = await agent.run(_input("suggest_panels",
            conditions=["diabetes"], medications=["metformin"]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_suggested"] >= 3  # hba1c, bmp, lipid, renal

    @pytest.mark.asyncio
    async def test_suggest_panels_empty(self, agent):
        out = await agent.run(_input("suggest_panels",
            conditions=[], medications=[]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_suggested"] == 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Lab Results Agent ────────────────────────────────────────────


class TestLabResultsAgent:
    @pytest.fixture
    def agent(self):
        from modules.labs.agents.lab_results import LabResultsAgent
        return LabResultsAgent()

    @pytest.mark.asyncio
    async def test_ingest_results_defaults(self, agent):
        out = await agent.run(_input("ingest_results"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_results"] > 0
        assert out.result["source_format"] == "HL7_ORU"

    @pytest.mark.asyncio
    async def test_ingest_results_with_criticals(self, agent):
        results = [
            {"test": "potassium", "value": 6.8, "unit": "mEq/L"},
            {"test": "glucose", "value": 85, "unit": "mg/dL"},
        ]
        out = await agent.run(_input("ingest_results", results=results, format="FHIR"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["critical_count"] >= 1
        assert out.result["requires_critical_alert"] is True

    @pytest.mark.asyncio
    async def test_flag_abnormals(self, agent):
        results = [
            {"test": "glucose", "value": 118, "unit": "mg/dL"},
            {"test": "sodium", "value": 141, "unit": "mEq/L"},
        ]
        out = await agent.run(_input("flag_abnormals", results=results))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_abnormal"] >= 1  # glucose high

    @pytest.mark.asyncio
    async def test_get_results(self, agent):
        out = await agent.run(_input("get_results"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["result_sets"]) > 0

    @pytest.mark.asyncio
    async def test_compare_to_prior(self, agent):
        current = [{"test": "glucose", "value": 118}]
        prior = [{"test": "glucose", "value": 100}]
        out = await agent.run(_input("compare_to_prior",
            current_results=current, prior_results=prior))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_compared"] == 1
        assert out.result["comparisons"][0]["trend"] == "increasing"

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Lab Trend Agent ──────────────────────────────────────────────


class TestLabTrendAgent:
    @pytest.fixture
    def agent(self):
        from modules.labs.agents.lab_trend import LabTrendAgent
        return LabTrendAgent()

    @pytest.mark.asyncio
    async def test_analyze_trends_defaults(self, agent):
        out = await agent.run(_input("analyze_trends"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_tests_analyzed"] >= 3
        assert out.result["concerning_trends"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_trends_custom(self, agent):
        lab_history = {
            "hba1c": [
                {"date": "2025-06-15", "value": 6.0},
                {"date": "2025-12-15", "value": 6.1},
            ],
        }
        out = await agent.run(_input("analyze_trends", lab_history=lab_history))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_tests_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_single_test_trend(self, agent):
        out = await agent.run(_input("single_test_trend", test="hba1c"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["test"] == "hba1c"
        assert out.result["data_points"] > 0

    @pytest.mark.asyncio
    async def test_project_trajectory(self, agent):
        out = await agent.run(_input("project_trajectory",
            test="hba1c", months_ahead=6))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["projected_value"] is not None
        assert out.result["projection_months"] == 6

    @pytest.mark.asyncio
    async def test_trend_summary(self, agent):
        out = await agent.run(_input("trend_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["key_trends"]) > 0
        assert out.result["overall_assessment"] != ""

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Critical Value Alert Agent ───────────────────────────────────


class TestCriticalValueAlertAgent:
    @pytest.fixture
    def agent(self):
        from modules.labs.agents.critical_value_alert import CriticalValueAlertAgent
        return CriticalValueAlertAgent()

    @pytest.mark.asyncio
    async def test_evaluate_no_criticals(self, agent):
        results = [
            {"test": "glucose", "value": 90},
            {"test": "potassium", "value": 4.0},
        ]
        out = await agent.run(_input("evaluate_critical", results=results))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["critical_values_found"] == 0
        assert out.result["requires_escalation"] is False

    @pytest.mark.asyncio
    async def test_evaluate_with_criticals(self, agent):
        results = [
            {"test": "potassium", "value": 6.8},
            {"test": "troponin", "value": 0.12},
            {"test": "glucose", "value": 85},
        ]
        out = await agent.run(_input("evaluate_critical", results=results))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["critical_values_found"] == 2
        assert out.result["requires_escalation"] is True
        # Stat (troponin) should be sorted before immediate (potassium)
        assert out.result["alerts"][0]["urgency"] == "stat"

    @pytest.mark.asyncio
    async def test_evaluate_critically_low(self, agent):
        results = [{"test": "glucose", "value": 40}]
        out = await agent.run(_input("evaluate_critical", results=results))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["critical_values_found"] == 1
        assert out.result["alerts"][0]["direction"] == "critically_low"

    @pytest.mark.asyncio
    async def test_escalate(self, agent):
        out = await agent.run(_input("escalate",
            alert_id="ALERT-001", test="potassium", value=6.8, urgency="immediate"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["notifications_sent"]) >= 3
        assert out.result["acknowledgment_required"] is True

    @pytest.mark.asyncio
    async def test_acknowledge(self, agent):
        out = await agent.run(_input("acknowledge",
            alert_id="ALERT-001", acknowledged_by="Dr. Williams"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "acknowledged"
        assert out.result["clia_compliant"] is True

    @pytest.mark.asyncio
    async def test_critical_log(self, agent):
        out = await agent.run(_input("critical_log"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_critical_alerts"] > 0
        assert out.result["all_within_target"] is True

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Registration & Routing ───────────────────────────────────────


class TestLabsRegistration:
    def test_register_labs_agents(self):
        from modules.labs.agents import register_labs_agents
        from healthos_platform.orchestrator.registry import registry
        register_labs_agents()
        for name in ["lab_order", "lab_results", "lab_trend", "critical_value_alert"]:
            assert registry.get(name) is not None, f"Agent '{name}' not registered"

    def test_labs_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        labs_events = [k for k in ROUTING_TABLE if k.startswith("labs.")]
        assert len(labs_events) >= 5, f"Expected >=5 labs routes, got {len(labs_events)}"
