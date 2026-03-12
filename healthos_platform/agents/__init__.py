"""
Eminence HealthOS — Core Agent Registration
"""

from healthos_platform.agents.audit import AuditTraceAgent
from healthos_platform.agents.context_assembly import ContextAssemblyAgent
from healthos_platform.agents.hitl import HumanInTheLoopAgent
from healthos_platform.agents.master_orchestrator import MasterOrchestratorAgent
from healthos_platform.agents.policy_rules import PolicyRulesAgent
from healthos_platform.agents.quality import QualityConfidenceAgent


def register_core_agents() -> None:
    """Register all 6 core platform control agents."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(MasterOrchestratorAgent())
    registry.register(ContextAssemblyAgent())
    registry.register(PolicyRulesAgent())
    registry.register(HumanInTheLoopAgent())
    registry.register(AuditTraceAgent())
    registry.register(QualityConfidenceAgent())
