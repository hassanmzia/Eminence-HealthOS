"""
Eminence HealthOS — Analytics Module Agent Registration
"""

from modules.analytics.agents.cost_risk_insight import CostRiskInsightAgent
from modules.analytics.agents.executive_insight import ExecutiveInsightAgent


def register_analytics_agents() -> None:
    """Register all analytics agents with the global registry."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(CostRiskInsightAgent())
    registry.register(ExecutiveInsightAgent())
