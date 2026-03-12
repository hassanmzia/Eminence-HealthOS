"""Patient Engagement & SDOH module agents — health literacy, multilingual, triage, care navigation, SDOH, community resources, engagement."""


def register_patient_engagement_agents() -> None:
    """Register all Patient Engagement & SDOH agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .care_navigation import CareNavigationAgent
    from .community_resource import CommunityResourceAgent
    from .conversational_triage import ConversationalTriageAgent
    from .health_literacy import HealthLiteracyAgent
    from .motivational_engagement import MotivationalEngagementAgent
    from .multilingual_communication import MultilingualCommunicationAgent
    from .sdoh_screening import SDOHScreeningAgent

    registry.register(HealthLiteracyAgent())
    registry.register(MultilingualCommunicationAgent())
    registry.register(ConversationalTriageAgent())
    registry.register(CareNavigationAgent())
    registry.register(SDOHScreeningAgent())
    registry.register(CommunityResourceAgent())
    registry.register(MotivationalEngagementAgent())
