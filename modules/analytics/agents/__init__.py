"""Analytics agents — population health, outcomes, cost analysis, cohorts, and readmission risk."""


def register_analytics_agents() -> None:
    """Register all analytics agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .cohort_segmentation import CohortSegmentationAgent
    from .cost_analyzer import CostAnalyzerAgent
    from .outcome_tracker import OutcomeTrackerAgent
    from .population_health import PopulationHealthAgent
    from .readmission_risk import ReadmissionRiskAgent

    registry.register(PopulationHealthAgent())
    registry.register(OutcomeTrackerAgent())
    registry.register(CostAnalyzerAgent())
    registry.register(CohortSegmentationAgent())
    registry.register(ReadmissionRiskAgent())
