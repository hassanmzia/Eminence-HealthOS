"""Revenue Cycle Management agents — charge capture, claims optimization, denial management, revenue integrity, payment posting."""


def register_rcm_agents() -> None:
    """Register all RCM agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .charge_capture import ChargeCaptureAgent
    from .claims_optimization import ClaimsOptimizationAgent
    from .denial_management import DenialManagementAgent
    from .payment_posting import PaymentPostingAgent
    from .revenue_integrity import RevenueIntegrityAgent

    registry.register(ChargeCaptureAgent())
    registry.register(ClaimsOptimizationAgent())
    registry.register(DenialManagementAgent())
    registry.register(RevenueIntegrityAgent())
    registry.register(PaymentPostingAgent())
