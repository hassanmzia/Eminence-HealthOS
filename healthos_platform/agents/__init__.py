"""
Eminence HealthOS — Core Agent Registration
"""

from healthos_platform.agents.context_assembly import ContextAssemblyAgent
from healthos_platform.agents.policy_rules import PolicyRulesAgent


def register_core_agents() -> None:
    """Register core platform agents (context assembly, policy rules, etc.)."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(ContextAssemblyAgent())
    registry.register(PolicyRulesAgent())
