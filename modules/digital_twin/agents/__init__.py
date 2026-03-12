"""
Eminence HealthOS — Digital Twin & Simulation Module Agent Registration
"""


def register_digital_twin_agents() -> None:
    """Register all digital twin agents with the global registry."""
    from healthos_platform.orchestrator.registry import registry

    from .patient_digital_twin import PatientDigitalTwinAgent
    from .predictive_trajectory import PredictiveTrajectoryAgent
    from .treatment_optimization import TreatmentOptimizationAgent
    from .whatif_scenario import WhatIfScenarioAgent

    registry.register(PatientDigitalTwinAgent())
    registry.register(WhatIfScenarioAgent())
    registry.register(PredictiveTrajectoryAgent())
    registry.register(TreatmentOptimizationAgent())
