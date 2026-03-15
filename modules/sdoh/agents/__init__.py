"""SDOH agents — risk assessment and community resource matching."""


def register_sdoh_agents() -> None:
    """Register all SDOH agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .sdoh_risk_agent import SDOHRiskAgent

    registry.register(SDOHRiskAgent())
