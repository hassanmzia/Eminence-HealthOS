"""
Eminence HealthOS — Telehealth Module Agent Registration
"""

from modules.telehealth.agents.clinical_note import ClinicalNoteAgent
from modules.telehealth.agents.escalation_routing import EscalationRoutingAgent
from modules.telehealth.agents.follow_up_plan import FollowUpPlanAgent
from modules.telehealth.agents.medication_review import MedicationReviewAgent
from modules.telehealth.agents.patient_communication import PatientCommunicationAgent
from modules.telehealth.agents.scheduling import SchedulingAgent
from modules.telehealth.agents.session_manager import SessionManagerAgent
from modules.telehealth.agents.symptom_checker import SymptomCheckerAgent
from modules.telehealth.agents.visit_preparation import VisitPreparationAgent
from modules.telehealth.agents.visit_summarizer import VisitSummarizerAgent


def register_telehealth_agents() -> None:
    """Register all telehealth agents with the global registry."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(SessionManagerAgent())
    registry.register(SymptomCheckerAgent())
    registry.register(VisitSummarizerAgent())
    registry.register(VisitPreparationAgent())
    registry.register(ClinicalNoteAgent())
    registry.register(FollowUpPlanAgent())
    registry.register(EscalationRoutingAgent())
    registry.register(MedicationReviewAgent())
    registry.register(PatientCommunicationAgent())
    registry.register(SchedulingAgent())
