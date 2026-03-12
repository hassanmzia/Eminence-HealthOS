"""Labs module agents — lab orders, results ingestion, trend analysis, critical value alerting."""


def register_labs_agents() -> None:
    """Register all Labs agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .critical_value_alert import CriticalValueAlertAgent
    from .lab_order import LabOrderAgent
    from .lab_results import LabResultsAgent
    from .lab_trend import LabTrendAgent

    registry.register(LabOrderAgent())
    registry.register(LabResultsAgent())
    registry.register(LabTrendAgent())
    registry.register(CriticalValueAlertAgent())
