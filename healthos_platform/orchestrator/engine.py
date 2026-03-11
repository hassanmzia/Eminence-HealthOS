"""
Eminence HealthOS — Agent Execution Engine
Builds and executes agent pipeline graphs using the registry and router.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentStatus, PipelineState
from healthos_platform.orchestrator.registry import registry
from healthos_platform.orchestrator.router import EventRouter

logger = structlog.get_logger()


class ExecutionEngine:
    """
    Executes agent pipelines by:
    1. Resolving event → agent list via the router
    2. Running agents sequentially (with future support for parallel tiers)
    3. Managing shared pipeline state
    4. Halting on HITL flags or critical errors
    """

    def __init__(self) -> None:
        self.router = EventRouter()

    async def execute_event(
        self,
        event_type: str,
        org_id: uuid.UUID,
        patient_id: uuid.UUID,
        payload: dict[str, Any] | None = None,
    ) -> PipelineState:
        """
        Process an event through the full agent pipeline.
        Returns the final pipeline state with all agent outputs.
        """
        trace_id = uuid.uuid4()
        agent_names = self.router.resolve(event_type)

        if not agent_names:
            logger.warning("engine.no_agents", event_type=event_type, trace_id=str(trace_id))
            return PipelineState(
                trace_id=trace_id,
                org_id=org_id,
                patient_id=patient_id,
                trigger_event=event_type,
            )

        state = PipelineState(
            trace_id=trace_id,
            org_id=org_id,
            patient_id=patient_id,
            trigger_event=event_type,
        )

        # Inject raw payload into state
        if payload:
            state.patient_context.update(payload)

        logger.info(
            "engine.pipeline.start",
            trace_id=str(trace_id),
            event_type=event_type,
            agent_count=len(agent_names),
            agents=agent_names,
        )

        for agent_name in agent_names:
            agent = registry.get(agent_name)

            if agent is None:
                logger.warning("engine.agent_not_found", agent=agent_name, trace_id=str(trace_id))
                continue

            try:
                state = await agent.run_in_pipeline(state)

                # Check if pipeline should halt for HITL review
                if state.requires_hitl:
                    logger.info(
                        "engine.hitl_halt",
                        trace_id=str(trace_id),
                        agent=agent_name,
                        reason=state.hitl_reason,
                    )
                    break

                # Check if the last agent failed critically
                last_output = state.agent_outputs.get(agent_name)
                if last_output and last_output.status == AgentStatus.FAILED:
                    logger.error(
                        "engine.agent_failed",
                        trace_id=str(trace_id),
                        agent=agent_name,
                        errors=last_output.errors,
                    )
                    # Continue pipeline unless it's a critical failure
                    if last_output.errors and "critical" in str(last_output.errors).lower():
                        break

            except Exception as exc:
                logger.error(
                    "engine.agent_exception",
                    trace_id=str(trace_id),
                    agent=agent_name,
                    error=str(exc),
                )
                state.agent_outputs[agent_name] = AgentOutput(
                    trace_id=trace_id,
                    agent_name=agent_name,
                    status=AgentStatus.FAILED,
                    errors=[str(exc)],
                )

        logger.info(
            "engine.pipeline.complete",
            trace_id=str(trace_id),
            event_type=event_type,
            agents_executed=state.executed_agents,
            requires_hitl=state.requires_hitl,
        )

        return state

    async def execute_single(
        self,
        agent_name: str,
        input_data: AgentInput,
    ) -> AgentOutput:
        """Execute a single agent directly (outside pipeline)."""
        agent = registry.get(agent_name)
        if agent is None:
            return AgentOutput(
                trace_id=input_data.trace_id,
                agent_name=agent_name,
                status=AgentStatus.FAILED,
                errors=[f"Agent '{agent_name}' not found in registry"],
            )
        return await agent.run(input_data)
