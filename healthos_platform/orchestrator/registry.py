"""
Eminence HealthOS — Agent Registry
Central registry for agent discovery, registration, and lifecycle management.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentTier

logger = structlog.get_logger()


class AgentRegistry:
    """
    Singleton registry that tracks all registered agents.
    Supports lookup by name, tier, and capability.
    """

    _instance: AgentRegistry | None = None
    _agents: dict[str, BaseAgent]
    _tiers: dict[AgentTier, list[str]]

    def __new__(cls) -> AgentRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._tiers = {tier: [] for tier in AgentTier}
        return cls._instance

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        if agent.name in self._agents:
            logger.warning("agent.registry.duplicate", agent=agent.name)
            return

        self._agents[agent.name] = agent
        self._tiers[agent.tier].append(agent.name)
        logger.info(
            "agent.registry.registered",
            agent=agent.name,
            tier=agent.tier.value,
            version=agent.version,
        )

    def get(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        return self._agents.get(name)

    def get_by_tier(self, tier: AgentTier) -> list[BaseAgent]:
        """Get all agents in a given tier."""
        return [self._agents[name] for name in self._tiers.get(tier, []) if name in self._agents]

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents with metadata."""
        return [
            {
                "name": agent.name,
                "tier": agent.tier.value,
                "version": agent.version,
                "description": agent.description,
                "requires_hitl": agent.requires_hitl,
            }
            for agent in self._agents.values()
        ]

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    def reset(self) -> None:
        """Clear all registrations. Used in testing."""
        self._agents.clear()
        self._tiers = {tier: [] for tier in AgentTier}


# Module-level singleton
registry = AgentRegistry()
