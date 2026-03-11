"""
Master Orchestrator Engine.

Implements the LangGraph-based supervisor pattern for routing patient data
through the 5-tier agent architecture. The orchestrator decides which agents
to invoke, manages data flow, and handles escalation.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.orchestrator")


@dataclass
class OrchestratorContext:
    """State carried through an orchestration pipeline run."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: Optional[str] = None
    tenant_id: str = "default"
    trigger: str = "manual"  # manual, scheduled, event, device
    trigger_data: dict = field(default_factory=dict)
    agent_outputs: list[AgentOutput] = field(default_factory=list)
    escalation_path: list[str] = field(default_factory=list)
    requires_hitl: bool = False
    errors: list[dict] = field(default_factory=list)


class OrchestratorEngine:
    """
    Central orchestrator that routes data through the agent tiers.

    Architecture:
        Tier 1 (Monitoring) → Tier 2 (Diagnostic) → Tier 3 (Risk) →
        Tier 4 (Intervention) → Tier 5 (Action)

    Not all tiers are invoked for every event — the orchestrator decides
    based on the trigger type and Tier 1 outputs.
    """

    def __init__(self):
        self._agents: dict[str, HealthOSAgent] = {}
        self._tier_agents: dict[AgentTier, list[HealthOSAgent]] = {
            tier: [] for tier in AgentTier
        }
        self._capability_index: dict[AgentCapability, list[HealthOSAgent]] = {}

    def register_agent(self, agent: HealthOSAgent) -> None:
        """Register an agent with the orchestrator."""
        self._agents[agent.name] = agent
        self._tier_agents[agent.tier].append(agent)

        for cap in agent.capabilities:
            self._capability_index.setdefault(cap, []).append(agent)

        logger.info(
            "Registered agent=%s tier=%s capabilities=%s",
            agent.name,
            agent.tier.value,
            [c.value for c in agent.capabilities],
        )

    def get_agent(self, name: str) -> Optional[HealthOSAgent]:
        return self._agents.get(name)

    def get_agents_by_tier(self, tier: AgentTier) -> list[HealthOSAgent]:
        return self._tier_agents.get(tier, [])

    def get_agents_by_capability(self, capability: AgentCapability) -> list[HealthOSAgent]:
        return self._capability_index.get(capability, [])

    async def initialize_all(self) -> None:
        """Initialize all registered agents."""
        for agent in self._agents.values():
            try:
                await agent.initialize()
                logger.info("Initialized agent=%s", agent.name)
            except Exception as e:
                logger.error("Failed to initialize agent=%s: %s", agent.name, e)

    async def shutdown_all(self) -> None:
        """Shutdown all registered agents."""
        for agent in self._agents.values():
            try:
                await agent.shutdown()
            except Exception as e:
                logger.warning("Error shutting down agent=%s: %s", agent.name, e)

    async def run_pipeline(
        self,
        context: OrchestratorContext,
        tiers: Optional[list[AgentTier]] = None,
    ) -> OrchestratorContext:
        """
        Execute the agent pipeline for a given context.

        Args:
            context: The orchestration context with patient/trigger data.
            tiers: Optional list of specific tiers to run. Defaults to all tiers.
        """
        tiers = tiers or list(AgentTier)
        start = time.monotonic()

        logger.info(
            "Pipeline start trace=%s patient=%s trigger=%s tiers=%s",
            context.trace_id[:12],
            context.patient_id,
            context.trigger,
            [t.value for t in tiers],
        )

        for tier in tiers:
            agents = self.get_agents_by_tier(tier)
            if not agents:
                continue

            logger.info(
                "Running tier=%s agents=%s",
                tier.value,
                [a.name for a in agents],
            )

            for agent in agents:
                try:
                    agent_input = AgentInput(
                        patient_id=context.patient_id,
                        tenant_id=context.tenant_id,
                        trace_id=context.trace_id,
                        data=context.trigger_data,
                        context={
                            "trigger": context.trigger,
                            "prior_outputs": [
                                {
                                    "agent": o.agent_name,
                                    "decision": o.decision,
                                    "confidence": o.confidence,
                                }
                                for o in context.agent_outputs
                            ],
                        },
                    )

                    output = await agent.execute(agent_input)
                    context.agent_outputs.append(output)

                    if output.requires_hitl:
                        context.requires_hitl = True
                        context.escalation_path.append(agent.name)

                except Exception as e:
                    context.errors.append({
                        "agent": agent.name,
                        "tier": tier.value,
                        "error": str(e),
                    })
                    logger.error(
                        "Agent %s failed in pipeline: %s", agent.name, e
                    )

            # Check if any tier output requires stopping the pipeline
            if context.requires_hitl and tier.value in ("intervention", "action"):
                logger.info(
                    "Pipeline paused at tier=%s — HITL required (agents: %s)",
                    tier.value,
                    context.escalation_path,
                )
                break

        duration = int((time.monotonic() - start) * 1000)
        logger.info(
            "Pipeline complete trace=%s duration=%dms agents_run=%d errors=%d hitl=%s",
            context.trace_id[:12],
            duration,
            len(context.agent_outputs),
            len(context.errors),
            context.requires_hitl,
        )

        return context

    async def run_single_agent(
        self,
        agent_name: str,
        agent_input: AgentInput,
    ) -> AgentOutput:
        """Execute a single named agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {agent_name}")
        return await agent.execute(agent_input)

    @property
    def registered_agents(self) -> dict[str, dict]:
        """Summary of all registered agents."""
        return {
            name: {
                "tier": agent.tier.value,
                "capabilities": [c.value for c in agent.capabilities],
                "version": agent.version,
                "description": agent.description,
            }
            for name, agent in self._agents.items()
        }
