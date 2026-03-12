"""
Unit tests for the HealthOS orchestrator — Engine, Router, and Registry.
Mocks agent execution to test pipeline flow, event routing, and agent registration.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    PipelineState,
)
from healthos_platform.orchestrator.engine import ExecutionEngine
from healthos_platform.orchestrator.registry import AgentRegistry
from healthos_platform.orchestrator.router import EventRouter, ROUTING_TABLE


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers — fake agent for testing
# ═══════════════════════════════════════════════════════════════════════════════


class FakeAgent(BaseAgent):
    """A minimal concrete agent for testing purposes."""

    def __init__(
        self,
        name: str = "fake_agent",
        tier: AgentTier = AgentTier.SENSING,
        version: str = "1.0.0",
        requires_hitl: bool = False,
    ):
        self.name = name
        self.tier = tier
        self.version = version
        self.description = f"Fake agent: {name}"
        self.requires_hitl = requires_hitl
        super().__init__()

    async def process(self, input_data: AgentInput) -> AgentOutput:
        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            confidence=0.95,
            result={"processed": True},
            rationale="Fake processing complete",
        )


def _make_ids():
    return uuid.uuid4(), uuid.uuid4()


def _make_pipeline_runner(name, execution_order):
    """Create a side_effect function that tracks execution and returns valid state."""
    async def runner(state):
        execution_order.append(name)
        state.executed_agents.append(name)
        state.agent_outputs[name] = AgentOutput(
            trace_id=state.trace_id,
            agent_name=name,
            status=AgentStatus.COMPLETED,
            confidence=0.9,
            result={"processed": True},
        )
        return state
    return runner


# ═══════════════════════════════════════════════════════════════════════════════
# Registry Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentRegistry:
    """Tests for AgentRegistry singleton."""

    def setup_method(self):
        """Reset registry state before each test."""
        self.registry = AgentRegistry()
        self.registry.reset()

    def test_singleton_pattern(self):
        """AgentRegistry should return the same instance."""
        r1 = AgentRegistry()
        r2 = AgentRegistry()
        assert r1 is r2

    def test_register_agent(self):
        agent = FakeAgent(name="test_agent_1")
        self.registry.register(agent)
        assert self.registry.agent_count == 1
        assert self.registry.get("test_agent_1") is agent

    def test_get_unregistered_agent_returns_none(self):
        assert self.registry.get("nonexistent") is None

    def test_register_duplicate_agent_is_ignored(self):
        agent1 = FakeAgent(name="dup_agent")
        agent2 = FakeAgent(name="dup_agent", version="2.0.0")
        self.registry.register(agent1)
        self.registry.register(agent2)
        # First registration wins
        assert self.registry.agent_count == 1
        assert self.registry.get("dup_agent").version == "1.0.0"

    def test_get_by_tier(self):
        sensing_agent = FakeAgent(name="sense_1", tier=AgentTier.SENSING)
        interp_agent = FakeAgent(name="interp_1", tier=AgentTier.INTERPRETATION)
        self.registry.register(sensing_agent)
        self.registry.register(interp_agent)

        sensing = self.registry.get_by_tier(AgentTier.SENSING)
        assert len(sensing) == 1
        assert sensing[0].name == "sense_1"

        interp = self.registry.get_by_tier(AgentTier.INTERPRETATION)
        assert len(interp) == 1
        assert interp[0].name == "interp_1"

        # No agents in other tiers
        action = self.registry.get_by_tier(AgentTier.ACTION)
        assert len(action) == 0

    def test_get_by_tier_multiple_agents(self):
        self.registry.register(FakeAgent(name="s1", tier=AgentTier.SENSING))
        self.registry.register(FakeAgent(name="s2", tier=AgentTier.SENSING))
        self.registry.register(FakeAgent(name="s3", tier=AgentTier.SENSING))
        sensing = self.registry.get_by_tier(AgentTier.SENSING)
        assert len(sensing) == 3
        names = {a.name for a in sensing}
        assert names == {"s1", "s2", "s3"}

    def test_list_agents_metadata(self):
        self.registry.register(FakeAgent(name="a1", tier=AgentTier.SENSING))
        self.registry.register(FakeAgent(name="a2", tier=AgentTier.DECISIONING, requires_hitl=True))

        listing = self.registry.list_agents()
        assert len(listing) == 2
        names = {a["name"] for a in listing}
        assert names == {"a1", "a2"}

        for entry in listing:
            assert "name" in entry
            assert "tier" in entry
            assert "version" in entry
            assert "description" in entry
            assert "requires_hitl" in entry

        hitl_agent = next(a for a in listing if a["name"] == "a2")
        assert hitl_agent["requires_hitl"] is True
        assert hitl_agent["tier"] == "decisioning"

    def test_reset_clears_all(self):
        self.registry.register(FakeAgent(name="will_be_cleared"))
        assert self.registry.agent_count == 1
        self.registry.reset()
        assert self.registry.agent_count == 0
        assert self.registry.get("will_be_cleared") is None

    def test_agent_count(self):
        assert self.registry.agent_count == 0
        self.registry.register(FakeAgent(name="c1"))
        assert self.registry.agent_count == 1
        self.registry.register(FakeAgent(name="c2"))
        assert self.registry.agent_count == 2

    def test_register_agents_across_all_tiers(self):
        for tier in AgentTier:
            self.registry.register(FakeAgent(name=f"agent_{tier.value}", tier=tier))
        assert self.registry.agent_count == len(AgentTier)
        for tier in AgentTier:
            agents = self.registry.get_by_tier(tier)
            assert len(agents) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Router Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEventRouter:
    """Tests for EventRouter routing resolution."""

    def setup_method(self):
        self.router = EventRouter()

    def test_resolve_known_event(self):
        agents = self.router.resolve("vitals.ingested")
        assert agents == [
            "device_ingestion",
            "vitals_normalization",
            "anomaly_detection",
            "risk_scoring",
            "trend_analysis",
            "adherence_monitoring",
        ]

    def test_resolve_unknown_event_returns_empty(self):
        agents = self.router.resolve("totally.unknown.event")
        assert agents == []

    def test_custom_route_overrides_static(self):
        self.router.add_route("vitals.ingested", ["custom_agent_1", "custom_agent_2"])
        agents = self.router.resolve("vitals.ingested")
        assert agents == ["custom_agent_1", "custom_agent_2"]

    def test_custom_route_for_new_event(self):
        self.router.add_route("custom.event", ["agent_a", "agent_b"])
        agents = self.router.resolve("custom.event")
        assert agents == ["agent_a", "agent_b"]

    def test_list_routes_includes_static_and_custom(self):
        self.router.add_route("my.custom.event", ["my_agent"])
        routes = self.router.list_routes()
        # Static routes present
        assert "vitals.ingested" in routes
        assert "anomaly.detected" in routes
        # Custom route present
        assert "my.custom.event" in routes
        assert routes["my.custom.event"] == ["my_agent"]

    def test_custom_route_overrides_in_list(self):
        """Custom route should override the static one in list_routes."""
        self.router.add_route("vitals.ingested", ["override_agent"])
        routes = self.router.list_routes()
        assert routes["vitals.ingested"] == ["override_agent"]

    def test_resolve_telehealth_events(self):
        agents = self.router.resolve("telehealth.visit.completed")
        assert "clinical_note" in agents
        assert "visit_summarizer" in agents

    def test_resolve_pharmacy_events(self):
        agents = self.router.resolve("pharmacy.prescription.create")
        assert "drug_interaction" in agents
        assert "formulary" in agents
        assert "prescription" in agents

    def test_resolve_ambient_events(self):
        agents = self.router.resolve("ambient.encounter.complete")
        assert "ambient_listening" in agents
        assert "soap_note_generator" in agents
        assert "provider_attestation" in agents

    def test_resolve_rcm_events(self):
        agents = self.router.resolve("rcm.denial.received")
        assert agents == ["denial_management"]

    def test_resolve_labs_events(self):
        agents = self.router.resolve("labs.results.received")
        assert "lab_results" in agents
        assert "critical_value_alert" in agents
        assert "lab_trend" in agents

    def test_resolve_imaging_events(self):
        agents = self.router.resolve("imaging.study.received")
        assert "imaging_ingestion" in agents
        assert "image_analysis" in agents

    def test_resolve_engagement_events(self):
        agents = self.router.resolve("engagement.sdoh.completed")
        assert "sdoh_screening" in agents
        assert "community_resource" in agents

    def test_resolve_research_events(self):
        agents = self.router.resolve("research.pgx.check")
        assert agents == ["pharmacogenomics"]

    def test_routing_table_has_expected_event_categories(self):
        """Verify the routing table covers major event categories."""
        event_prefixes = {key.split(".")[0] for key in ROUTING_TABLE}
        expected = {
            "vitals", "anomaly", "risk", "alert", "patient",
            "telehealth", "operations", "billing", "analytics",
            "ambient", "rcm", "pharmacy", "labs", "imaging",
            "engagement", "research",
        }
        assert expected.issubset(event_prefixes)

    def test_all_static_routes_have_at_least_one_agent(self):
        """Every entry in the routing table should have at least one agent."""
        for event_type, agents in ROUTING_TABLE.items():
            assert len(agents) >= 1, f"Route '{event_type}' has no agents"

    def test_multiple_custom_routes(self):
        self.router.add_route("custom.a", ["agent_1"])
        self.router.add_route("custom.b", ["agent_2", "agent_3"])
        assert self.router.resolve("custom.a") == ["agent_1"]
        assert self.router.resolve("custom.b") == ["agent_2", "agent_3"]


# ═══════════════════════════════════════════════════════════════════════════════
# Execution Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutionEngine:
    """Tests for ExecutionEngine pipeline execution."""

    def setup_method(self):
        self.engine = ExecutionEngine()
        from healthos_platform.orchestrator.registry import registry
        registry.reset()

    @pytest.mark.asyncio
    async def test_execute_event_no_agents(self):
        """Events with no matching agents should return empty pipeline state."""
        org_id, patient_id = _make_ids()
        state = await self.engine.execute_event(
            event_type="unknown.event",
            org_id=org_id,
            patient_id=patient_id,
        )
        assert isinstance(state, PipelineState)
        assert state.org_id == org_id
        assert state.patient_id == patient_id
        assert state.trigger_event == "unknown.event"
        assert len(state.executed_agents) == 0

    @pytest.mark.asyncio
    async def test_execute_event_runs_agents_in_order(self):
        """Pipeline should execute agents in the order returned by the router."""
        from healthos_platform.orchestrator.registry import registry

        org_id, patient_id = _make_ids()
        execution_order = []

        for name in ["agent_a", "agent_b", "agent_c"]:
            agent = FakeAgent(name=name)
            agent.run_in_pipeline = AsyncMock(
                side_effect=_make_pipeline_runner(name, execution_order)
            )
            registry.register(agent)

        self.engine.router.add_route("test.ordered", ["agent_a", "agent_b", "agent_c"])

        state = await self.engine.execute_event(
            event_type="test.ordered",
            org_id=org_id,
            patient_id=patient_id,
        )

        assert execution_order == ["agent_a", "agent_b", "agent_c"]
        assert state.executed_agents == ["agent_a", "agent_b", "agent_c"]

    @pytest.mark.asyncio
    async def test_execute_event_payload_injected_into_context(self):
        """Payload should be injected into pipeline state's patient_context."""
        from healthos_platform.orchestrator.registry import registry

        agent = FakeAgent(name="context_checker")
        captured_state = {}

        async def capture_state(state):
            captured_state.update(state.patient_context)
            state.executed_agents.append("context_checker")
            state.agent_outputs["context_checker"] = AgentOutput(
                trace_id=state.trace_id,
                agent_name="context_checker",
                status=AgentStatus.COMPLETED,
            )
            return state

        agent.run_in_pipeline = AsyncMock(side_effect=capture_state)
        registry.register(agent)

        self.engine.router.add_route("test.payload", ["context_checker"])

        org_id, patient_id = _make_ids()
        payload = {"glucose_level": 200, "source": "wearable"}

        await self.engine.execute_event(
            event_type="test.payload",
            org_id=org_id,
            patient_id=patient_id,
            payload=payload,
        )

        assert captured_state["glucose_level"] == 200
        assert captured_state["source"] == "wearable"

    @pytest.mark.asyncio
    async def test_execute_event_halts_on_hitl(self):
        """Pipeline should halt when an agent sets requires_hitl=True."""
        from healthos_platform.orchestrator.registry import registry

        execution_order = []

        hitl_agent = FakeAgent(name="hitl_agent")

        async def hitl_runner(state):
            execution_order.append("hitl_agent")
            state.executed_agents.append("hitl_agent")
            state.requires_hitl = True
            state.hitl_reason = "Needs physician review"
            state.agent_outputs["hitl_agent"] = AgentOutput(
                trace_id=state.trace_id,
                agent_name="hitl_agent",
                status=AgentStatus.WAITING_HITL,
                requires_hitl=True,
                hitl_reason="Needs physician review",
            )
            return state

        hitl_agent.run_in_pipeline = AsyncMock(side_effect=hitl_runner)
        registry.register(hitl_agent)

        skipped_agent = FakeAgent(name="skipped_agent")
        skipped_agent.run_in_pipeline = AsyncMock(
            side_effect=_make_pipeline_runner("skipped_agent", execution_order)
        )
        registry.register(skipped_agent)

        self.engine.router.add_route("test.hitl", ["hitl_agent", "skipped_agent"])

        org_id, patient_id = _make_ids()
        state = await self.engine.execute_event(
            event_type="test.hitl",
            org_id=org_id,
            patient_id=patient_id,
        )

        assert state.requires_hitl is True
        assert state.hitl_reason == "Needs physician review"
        assert execution_order == ["hitl_agent"]
        assert "skipped_agent" not in state.executed_agents

    @pytest.mark.asyncio
    async def test_execute_event_halts_on_critical_failure(self):
        """Pipeline should halt when an agent fails critically."""
        from healthos_platform.orchestrator.registry import registry

        execution_order = []

        fail_agent = FakeAgent(name="critical_fail")

        async def fail_runner(state):
            execution_order.append("critical_fail")
            state.executed_agents.append("critical_fail")
            state.agent_outputs["critical_fail"] = AgentOutput(
                trace_id=state.trace_id,
                agent_name="critical_fail",
                status=AgentStatus.FAILED,
                errors=["CRITICAL: system failure"],
            )
            return state

        fail_agent.run_in_pipeline = AsyncMock(side_effect=fail_runner)
        registry.register(fail_agent)

        next_agent = FakeAgent(name="after_fail")
        next_agent.run_in_pipeline = AsyncMock(
            side_effect=_make_pipeline_runner("after_fail", execution_order)
        )
        registry.register(next_agent)

        self.engine.router.add_route("test.critical", ["critical_fail", "after_fail"])

        org_id, patient_id = _make_ids()
        state = await self.engine.execute_event(
            event_type="test.critical",
            org_id=org_id,
            patient_id=patient_id,
        )

        assert execution_order == ["critical_fail"]
        assert "after_fail" not in state.executed_agents

    @pytest.mark.asyncio
    async def test_execute_event_continues_on_non_critical_failure(self):
        """Pipeline should continue when an agent fails non-critically."""
        from healthos_platform.orchestrator.registry import registry

        execution_order = []

        soft_fail = FakeAgent(name="soft_fail")

        async def soft_fail_runner(state):
            execution_order.append("soft_fail")
            state.executed_agents.append("soft_fail")
            state.agent_outputs["soft_fail"] = AgentOutput(
                trace_id=state.trace_id,
                agent_name="soft_fail",
                status=AgentStatus.FAILED,
                errors=["Non-critical: could not fetch optional data"],
            )
            return state

        soft_fail.run_in_pipeline = AsyncMock(side_effect=soft_fail_runner)
        registry.register(soft_fail)

        next_agent = FakeAgent(name="continues")
        next_agent.run_in_pipeline = AsyncMock(
            side_effect=_make_pipeline_runner("continues", execution_order)
        )
        registry.register(next_agent)

        self.engine.router.add_route("test.softfail", ["soft_fail", "continues"])

        org_id, patient_id = _make_ids()
        state = await self.engine.execute_event(
            event_type="test.softfail",
            org_id=org_id,
            patient_id=patient_id,
        )

        assert execution_order == ["soft_fail", "continues"]

    @pytest.mark.asyncio
    async def test_execute_event_handles_agent_exception(self):
        """Pipeline should catch exceptions and record them in agent_outputs."""
        from healthos_platform.orchestrator.registry import registry

        boom_agent = FakeAgent(name="boom_agent")
        boom_agent.run_in_pipeline = AsyncMock(
            side_effect=RuntimeError("Unexpected explosion")
        )
        registry.register(boom_agent)

        self.engine.router.add_route("test.boom", ["boom_agent"])

        org_id, patient_id = _make_ids()
        state = await self.engine.execute_event(
            event_type="test.boom",
            org_id=org_id,
            patient_id=patient_id,
        )

        assert "boom_agent" in state.agent_outputs
        output = state.agent_outputs["boom_agent"]
        assert output.status == AgentStatus.FAILED
        assert "Unexpected explosion" in output.errors[0]

    @pytest.mark.asyncio
    async def test_execute_event_skips_unregistered_agent(self):
        """Pipeline should skip agents not found in the registry."""
        from healthos_platform.orchestrator.registry import registry

        execution_order = []

        real_agent = FakeAgent(name="real_agent")
        real_agent.run_in_pipeline = AsyncMock(
            side_effect=_make_pipeline_runner("real_agent", execution_order)
        )
        registry.register(real_agent)

        # Route includes an unregistered agent
        self.engine.router.add_route("test.skip", ["ghost_agent", "real_agent"])

        org_id, patient_id = _make_ids()
        state = await self.engine.execute_event(
            event_type="test.skip",
            org_id=org_id,
            patient_id=patient_id,
        )

        assert execution_order == ["real_agent"]
        assert "ghost_agent" not in state.agent_outputs

    @pytest.mark.asyncio
    async def test_execute_single_agent_success(self):
        """execute_single should run a single agent and return its output."""
        from healthos_platform.orchestrator.registry import registry

        agent = FakeAgent(name="single_runner")
        registry.register(agent)

        input_data = AgentInput(
            org_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            trigger="manual",
        )

        output = await self.engine.execute_single("single_runner", input_data)
        assert output.status == AgentStatus.COMPLETED
        assert output.agent_name == "single_runner"
        assert output.confidence == 0.95

    @pytest.mark.asyncio
    async def test_execute_single_agent_not_found(self):
        """execute_single should return FAILED output for unknown agents."""
        input_data = AgentInput(
            org_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            trigger="manual",
        )

        output = await self.engine.execute_single("nonexistent_agent", input_data)
        assert output.status == AgentStatus.FAILED
        assert "not found" in output.errors[0]

    @pytest.mark.asyncio
    async def test_execute_event_returns_unique_trace_ids(self):
        """Every pipeline execution should have a unique trace_id."""
        org_id, patient_id = _make_ids()

        state1 = await self.engine.execute_event("unknown.event", org_id, patient_id)
        state2 = await self.engine.execute_event("unknown.event", org_id, patient_id)

        assert state1.trace_id != state2.trace_id

    @pytest.mark.asyncio
    async def test_execute_event_no_payload(self):
        """When no payload is provided, patient_context should stay empty."""
        from healthos_platform.orchestrator.registry import registry

        agent = FakeAgent(name="no_payload_agent")
        captured_context = {}

        async def capture(state):
            captured_context.update(state.patient_context)
            state.executed_agents.append("no_payload_agent")
            state.agent_outputs["no_payload_agent"] = AgentOutput(
                trace_id=state.trace_id,
                agent_name="no_payload_agent",
                status=AgentStatus.COMPLETED,
            )
            return state

        agent.run_in_pipeline = AsyncMock(side_effect=capture)
        registry.register(agent)

        self.engine.router.add_route("test.nopayload", ["no_payload_agent"])

        org_id, patient_id = _make_ids()
        await self.engine.execute_event("test.nopayload", org_id, patient_id)

        assert captured_context == {}

    @pytest.mark.asyncio
    async def test_execute_event_exception_does_not_stop_next_agents(self):
        """After an exception, pipeline should continue to next agents."""
        from healthos_platform.orchestrator.registry import registry

        execution_order = []

        boom = FakeAgent(name="boom")
        boom.run_in_pipeline = AsyncMock(side_effect=ValueError("boom"))
        registry.register(boom)

        survivor = FakeAgent(name="survivor")
        survivor.run_in_pipeline = AsyncMock(
            side_effect=_make_pipeline_runner("survivor", execution_order)
        )
        registry.register(survivor)

        self.engine.router.add_route("test.exception_continue", ["boom", "survivor"])

        org_id, patient_id = _make_ids()
        state = await self.engine.execute_event(
            "test.exception_continue", org_id, patient_id
        )

        # Exception agent is recorded as failed
        assert state.agent_outputs["boom"].status == AgentStatus.FAILED
        # Next agent still runs
        assert "survivor" in execution_order


# ═══════════════════════════════════════════════════════════════════════════════
# BaseAgent Pipeline Integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestBaseAgentPipeline:
    """Tests for BaseAgent.run_in_pipeline state management."""

    @pytest.mark.asyncio
    async def test_run_in_pipeline_merges_output(self):
        agent = FakeAgent(name="merger")
        org_id, patient_id = _make_ids()
        state = PipelineState(
            org_id=org_id,
            patient_id=patient_id,
            trigger_event="test.merge",
        )

        result_state = await agent.run_in_pipeline(state)

        assert "merger" in result_state.executed_agents
        assert "merger" in result_state.agent_outputs
        assert result_state.agent_outputs["merger"].status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_in_pipeline_propagates_hitl(self):
        agent = FakeAgent(name="hitl_test", requires_hitl=True)
        org_id, patient_id = _make_ids()
        state = PipelineState(
            org_id=org_id,
            patient_id=patient_id,
            trigger_event="test.hitl",
        )

        result_state = await agent.run_in_pipeline(state)

        assert result_state.requires_hitl is True
        assert result_state.agent_outputs["hitl_test"].requires_hitl is True

    @pytest.mark.asyncio
    async def test_run_in_pipeline_passes_context(self):
        """Agent should receive patient_context, vitals, anomalies, and risk assessments."""
        captured_context = {}

        class ContextCapture(BaseAgent):
            name = "context_capture"
            tier = AgentTier.INTERPRETATION
            version = "1.0.0"
            description = "Captures context for testing"

            async def process(self, input_data: AgentInput) -> AgentOutput:
                captured_context.update(input_data.context)
                return AgentOutput(
                    trace_id=input_data.trace_id,
                    agent_name=self.name,
                    status=AgentStatus.COMPLETED,
                )

        agent = ContextCapture()
        org_id, patient_id = _make_ids()
        state = PipelineState(
            org_id=org_id,
            patient_id=patient_id,
            trigger_event="test.context",
            patient_context={"key": "value"},
        )

        await agent.run_in_pipeline(state)

        assert "patient_context" in captured_context
        assert captured_context["patient_context"]["key"] == "value"
        assert "normalized_vitals" in captured_context
        assert "anomalies" in captured_context
        assert "risk_assessments" in captured_context

    @pytest.mark.asyncio
    async def test_run_in_pipeline_records_agent_name(self):
        agent = FakeAgent(name="name_check")
        org_id, patient_id = _make_ids()
        state = PipelineState(org_id=org_id, patient_id=patient_id)

        result = await agent.run_in_pipeline(state)

        assert result.agent_outputs["name_check"].agent_name == "name_check"

    @pytest.mark.asyncio
    async def test_run_in_pipeline_error_handling(self):
        """Agent exceptions should be caught and produce a FAILED output."""

        class FailingAgent(BaseAgent):
            name = "failing_agent"
            tier = AgentTier.SENSING
            version = "1.0.0"
            description = "Always fails"

            async def process(self, input_data: AgentInput) -> AgentOutput:
                raise RuntimeError("Process failed")

        agent = FailingAgent()
        org_id, patient_id = _make_ids()
        state = PipelineState(org_id=org_id, patient_id=patient_id)

        result = await agent.run_in_pipeline(state)

        assert "failing_agent" in result.executed_agents
        output = result.agent_outputs["failing_agent"]
        assert output.status == AgentStatus.FAILED
        assert output.requires_hitl is True

    @pytest.mark.asyncio
    async def test_run_in_pipeline_preserves_existing_state(self):
        """Running an agent should not clear previously executed agents."""
        agent1 = FakeAgent(name="first")
        agent2 = FakeAgent(name="second")
        org_id, patient_id = _make_ids()
        state = PipelineState(org_id=org_id, patient_id=patient_id)

        state = await agent1.run_in_pipeline(state)
        state = await agent2.run_in_pipeline(state)

        assert state.executed_agents == ["first", "second"]
        assert "first" in state.agent_outputs
        assert "second" in state.agent_outputs
