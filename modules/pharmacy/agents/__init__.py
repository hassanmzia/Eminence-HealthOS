"""Pharmacy agents — prescription management, drug interactions, formulary, routing, refills, adherence."""


def register_pharmacy_agents() -> None:
    """Register all Pharmacy agents with the platform registry."""
    from healthos_platform.orchestrator.registry import registry

    from .drug_interaction import DrugInteractionAgent
    from .formulary import FormularyAgent
    from .medication_adherence import MedicationAdherenceAgent
    from .pharmacy_routing import PharmacyRoutingAgent
    from .prescription import PrescriptionAgent
    from .refill_automation import RefillAutomationAgent

    registry.register(PrescriptionAgent())
    registry.register(DrugInteractionAgent())
    registry.register(FormularyAgent())
    registry.register(PharmacyRoutingAgent())
    registry.register(RefillAutomationAgent())
    registry.register(MedicationAdherenceAgent())
