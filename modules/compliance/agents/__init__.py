"""Compliance & Governance agents — HIPAA monitoring, AI governance, consent management, regulatory reporting."""


def register_compliance_agents() -> None:
    """Register all compliance agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .ai_governance import AIGovernanceAgent
    from .consent_management import ConsentManagementAgent
    from .hipaa_compliance_monitor import HIPAAComplianceMonitorAgent
    from .regulatory_reporting import RegulatoryReportingAgent

    registry.register(HIPAAComplianceMonitorAgent())
    registry.register(AIGovernanceAgent())
    registry.register(ConsentManagementAgent())
    registry.register(RegulatoryReportingAgent())
