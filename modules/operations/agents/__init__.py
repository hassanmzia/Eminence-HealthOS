"""
Eminence HealthOS — Operations Module Agent Registration
"""

from modules.operations.agents.prior_authorization import PriorAuthorizationAgent
from modules.operations.agents.insurance_verification import InsuranceVerificationAgent
from modules.operations.agents.referral_coordination import ReferralCoordinationAgent
from modules.operations.agents.task_orchestration import TaskOrchestrationAgent


def register_operations_agents() -> None:
    """Register all operations agents with the global registry."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(PriorAuthorizationAgent())
    registry.register(InsuranceVerificationAgent())
    registry.register(ReferralCoordinationAgent())
    registry.register(TaskOrchestrationAgent())
