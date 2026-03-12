"""Mental Health agents — screening, behavioral health workflows, crisis detection, therapeutic engagement."""


def register_mental_health_agents() -> None:
    """Register all mental health agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .behavioral_health_workflow import BehavioralHealthWorkflowAgent
    from .crisis_detection import CrisisDetectionAgent
    from .mental_health_screening import MentalHealthScreeningAgent
    from .therapeutic_engagement import TherapeuticEngagementAgent

    registry.register(MentalHealthScreeningAgent())
    registry.register(BehavioralHealthWorkflowAgent())
    registry.register(CrisisDetectionAgent())
    registry.register(TherapeuticEngagementAgent())
