"""Unit tests for the HealthOS orchestrator — registry, router, and execution engine."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    PipelineState,
)


# ── Registry Tests ──────────────────────────────────────────────────────────


class TestAgentRegistry:
    def setup_method(self):
        from healthos_platform.orchestrator.registry import AgentRegistry

        self.registry = AgentRegistry()
        self.registry.reset()

    def _make_agent(self, name: str = "test-agent", tier: AgentTier = AgentTier.SENSING):
        agent = MagicMock()
        agent.name = name
        agent.tier = tier
        agent.version = "1.0.0"
        agent.description = f"Test agent {name}"
        agent.requires_hitl = False
        return agent

    def test_register_agent(self):
        agent = self._make_agent()
        self.registry.register(agent)
        assert self.registry.get("test-agent") is agent
        assert self.registry.agent_count == 1

    def test_register_duplicate_ignored(self):
        agent = self._make_agent()
        self.registry.register(agent)
        self.registry.register(agent)
        assert self.registry.agent_count == 1

    def test_get_nonexistent_returns_none(self):
        assert self.registry.get("nonexistent") is None

    def test_get_by_tier(self):
        a1 = self._make_agent("sensing-1", AgentTier.SENSING)
        a2 = self._make_agent("action-1", AgentTier.ACTION)
        self.registry.register(a1)
        self.registry.register(a2)
        sensing = self.registry.get_by_tier(AgentTier.SENSING)
        assert len(sensing) == 1
        assert sensing[0].name == "sensing-1"

    def test_list_agents(self):
        self.registry.register(self._make_agent("a1"))
        self.registry.register(self._make_agent("a2"))
        agents_list = self.registry.list_agents()
        assert len(agents_list) == 2
        names = {a["name"] for a in agents_list}
        assert names == {"a1", "a2"}

    def test_reset_clears_all(self):
        self.registry.register(self._make_agent())
        self.registry.reset()
        assert self.registry.agent_count == 0


# ── Router Tests ────────────────────────────────────────────────────────────


class TestEventRouter:
    def test_resolve_known_event(self):
        from healthos_platform.orchestrator.router import EventRouter

        router = EventRouter()
        agents = router.resolve("vitals.ingested")
        assert isinstance(agents, list)
        assert len(agents) > 0

    def test_resolve_unknown_event_empty(self):
        from healthos_platform.orchestrator.router import EventRouter

        router = EventRouter()
        agents = router.resolve("completely.unknown.event.xyz")
        assert agents == []


# ── Execution Engine Tests ──────────────────────────────────────────────────


class TestExecutionEngine:
    @pytest.fixture
    def engine(self):
        from healthos_platform.orchestrator.engine import ExecutionEngine

        return ExecutionEngine()

    @pytest.mark.asyncio
    async def test_execute_event_no_agents(self, engine):
        org_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        state = await engine.execute_event("no.such.event.xyz", org_id, patient_id)
        assert isinstance(state, PipelineState)
        assert state.org_id == org_id
        assert state.patient_id == patient_id

    @pytest.mark.asyncio
    async def test_execute_single_agent_not_found(self, engine):
        input_data = AgentInput(
            trace_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            context={},
        )
        result = await engine.execute_single("nonexistent-agent", input_data)
        assert result.status == AgentStatus.FAILED
        assert "not found" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_event_with_registered_agent(self, engine):
        from healthos_platform.orchestrator.registry import registry

        # Create a mock agent
        mock_agent = AsyncMock()
        mock_agent.name = "test-pipeline-agent"
        mock_agent.tier = AgentTier.SENSING
        mock_agent.version = "1.0"
        mock_agent.description = "test"
        mock_agent.requires_hitl = False

        async def mock_run_in_pipeline(state):
            state.agent_outputs[mock_agent.name] = AgentOutput(
                trace_id=state.trace_id,
                agent_name=mock_agent.name,
                status=AgentStatus.SUCCESS,
                result={"test": True},
            )
            state.executed_agents.append(mock_agent.name)
            return state

        mock_agent.run_in_pipeline = mock_run_in_pipeline
        registry.register(mock_agent)

        # Patch router to return our agent
        with patch.object(engine.router, "resolve", return_value=["test-pipeline-agent"]):
            org_id = uuid.uuid4()
            patient_id = uuid.uuid4()
            state = await engine.execute_event("test.event", org_id, patient_id)

        assert "test-pipeline-agent" in state.agent_outputs
        assert state.agent_outputs["test-pipeline-agent"].status == AgentStatus.SUCCESS

        # Cleanup
        registry.reset()

    @pytest.mark.asyncio
    async def test_execute_event_hitl_halt(self, engine):
        from healthos_platform.orchestrator.registry import registry

        mock_agent = AsyncMock()
        mock_agent.name = "hitl-trigger-agent"
        mock_agent.tier = AgentTier.DECISIONING
        mock_agent.version = "1.0"
        mock_agent.description = "test"
        mock_agent.requires_hitl = False

        async def mock_run_with_hitl(state):
            state.requires_hitl = True
            state.hitl_reason = "Low confidence score"
            state.executed_agents.append(mock_agent.name)
            return state

        mock_agent.run_in_pipeline = mock_run_with_hitl
        registry.register(mock_agent)

        second_agent = AsyncMock()
        second_agent.name = "should-not-run"
        second_agent.tier = AgentTier.ACTION
        second_agent.version = "1.0"
        second_agent.description = "test"
        second_agent.requires_hitl = False
        registry.register(second_agent)

        with patch.object(
            engine.router, "resolve", return_value=["hitl-trigger-agent", "should-not-run"]
        ):
            state = await engine.execute_event("test.event", uuid.uuid4(), uuid.uuid4())

        assert state.requires_hitl is True
        assert "should-not-run" not in state.agent_outputs

        registry.reset()
