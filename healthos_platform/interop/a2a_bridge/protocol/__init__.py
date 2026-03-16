"""
HealthOS A2A Protocol Module

Redis-backed agent-to-agent communication with typed messages,
correlation IDs, capability-based routing, and discovery.
"""

from .protocol import A2AMessage, A2AProtocol
from .registry import AgentRegistry

__all__ = ["A2AMessage", "A2AProtocol", "AgentRegistry"]
