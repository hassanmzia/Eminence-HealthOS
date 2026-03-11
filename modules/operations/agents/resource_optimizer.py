"""
Resource Optimizer Agent — optimizes clinical resource allocation.

Analyzes patient demand patterns, provider capacity, and resource
utilization to recommend staffing and scheduling optimizations.
"""

import logging
from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.resource_optimizer")


class ResourceOptimizerAgent(HealthOSAgent):
    """Optimizes clinical resource allocation and scheduling."""

    def __init__(self):
        super().__init__(
            name="resource_optimizer",
            tier=AgentTier.INTERVENTION,
            description="Optimizes provider scheduling and resource allocation",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        # Analyze current utilization
        providers = data.get("providers", [])
        patient_demand = data.get("patient_demand", {})
        capacity = data.get("capacity", {})

        recommendations = []

        # Provider utilization analysis
        for provider in providers:
            utilization = provider.get("utilization_percent", 0)
            if utilization > 90:
                recommendations.append({
                    "type": "staffing",
                    "priority": "high",
                    "description": f"Provider {provider.get('name', 'unknown')} at {utilization}% capacity",
                    "action": "Consider adding coverage or redistributing patients",
                })
            elif utilization < 30:
                recommendations.append({
                    "type": "efficiency",
                    "priority": "low",
                    "description": f"Provider {provider.get('name', 'unknown')} at {utilization}% — underutilized",
                    "action": "Review scheduling for optimization opportunities",
                })

        # Demand forecasting
        high_risk_count = patient_demand.get("high_risk_patients", 0)
        if high_risk_count > capacity.get("high_risk_capacity", 50):
            recommendations.append({
                "type": "capacity",
                "priority": "high",
                "description": f"{high_risk_count} high-risk patients exceed capacity threshold",
                "action": "Increase monitoring capacity or escalate to management",
            })

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="optimization_complete",
            rationale=f"Resource analysis complete: {len(recommendations)} recommendation(s)",
            confidence=0.80,
            data={
                "recommendations": recommendations,
                "provider_count": len(providers),
                "high_priority": len([r for r in recommendations if r["priority"] == "high"]),
            },
            feature_contributions=[
                {"feature": "provider_utilization", "contribution": 0.4, "value": len(providers)},
                {"feature": "patient_demand", "contribution": 0.35, "value": patient_demand},
                {"feature": "capacity", "contribution": 0.25, "value": capacity},
            ],
        )
