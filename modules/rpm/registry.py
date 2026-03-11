"""
RPM Agent Registry.

Registers all RPM module agents with the orchestrator engine.
"""

from platform.orchestrator.engine import OrchestratorEngine


def register_rpm_agents(engine: OrchestratorEngine) -> None:
    """Register all RPM agents with the orchestrator."""
    from modules.rpm.agents.vital_monitor import VitalMonitorAgent
    from modules.rpm.agents.glucose_monitor import GlucoseMonitorAgent
    from modules.rpm.agents.cardiac_monitor import CardiacMonitorAgent
    from modules.rpm.agents.device_integration import DeviceIntegrationAgent
    from modules.rpm.agents.lab_analyzer import LabAnalyzerAgent
    from modules.rpm.agents.medication_checker import MedicationCheckerAgent
    from modules.rpm.agents.clinical_summarizer import ClinicalSummarizerAgent
    from modules.rpm.agents.risk_scorer import RiskScorerAgent
    from modules.rpm.agents.triage_agent import TriageAgent
    from modules.rpm.agents.care_plan_generator import CarePlanGeneratorAgent
    from modules.rpm.agents.alert_manager import AlertManagerAgent
    from modules.rpm.agents.patient_communicator import PatientCommunicatorAgent

    agents = [
        # Tier 1 — Monitoring
        VitalMonitorAgent(),
        GlucoseMonitorAgent(),
        CardiacMonitorAgent(),
        DeviceIntegrationAgent(),
        # Tier 2 — Diagnostic
        LabAnalyzerAgent(),
        MedicationCheckerAgent(),
        ClinicalSummarizerAgent(),
        # Tier 3 — Risk
        RiskScorerAgent(),
        TriageAgent(),
        # Tier 4 — Intervention
        CarePlanGeneratorAgent(),
        # Tier 5 — Action
        AlertManagerAgent(),
        PatientCommunicatorAgent(),
    ]

    for agent in agents:
        engine.register_agent(agent)
