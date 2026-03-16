"""
Bridge to register clinical decision support agents in the HealthOS agent registry.

The clinical agents use their own BaseAgent class, so we wrap them as HealthOS agents
for discovery and monitoring via the platform's agent registry.
"""

from __future__ import annotations

import structlog

from healthos_platform.agents.base import BaseAgent as HealthOSBaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentStatus, AgentTier
from healthos_platform.orchestrator.registry import registry

logger = structlog.get_logger()

# Agent definitions: (name, tier, version, description, requires_hitl)
CLINICAL_AGENTS = [
    ("ClinicalSupervisor", AgentTier.DECISIONING, "2.0.0",
     "Orchestrates multi-agent clinical assessment pipeline with specialist routing", True),
    ("Diagnostician", AgentTier.INTERPRETATION, "2.0.0",
     "Generates differential diagnoses with ICD-10 codes from patient context", True),
    ("TreatmentPlanner", AgentTier.DECISIONING, "2.0.0",
     "Creates evidence-based treatment plans with CPT codes", True),
    ("SafetyChecker", AgentTier.DECISIONING, "2.0.0",
     "Validates drug interactions, allergies, and contraindications", False),
    ("MedicalCoder", AgentTier.ACTION, "2.0.0",
     "Assigns and validates ICD-10 and CPT codes for clinical encounters", False),
    ("CardiologySpecialist", AgentTier.INTERPRETATION, "2.0.0",
     "Cardiovascular assessment: Framingham risk, GDMT, arrhythmia analysis", True),
    ("RadiologySpecialist", AgentTier.INTERPRETATION, "2.0.0",
     "Imaging interpretation for X-ray, CT, and MRI findings", True),
    ("PathologySpecialist", AgentTier.INTERPRETATION, "2.0.0",
     "Laboratory result interpretation and tissue analysis", False),
    ("GastroenterologySpecialist", AgentTier.INTERPRETATION, "2.0.0",
     "GI procedure analysis: colonoscopy, endoscopy, hepatology", True),
    ("OncologySpecialist", AgentTier.INTERPRETATION, "2.0.0",
     "Cancer screening, staging, tumor marker interpretation", True),
]


class ClinicalAgentProxy(HealthOSBaseAgent):
    """Proxy that represents a clinical decision support agent in the HealthOS registry."""

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """
        Clinical agents run in the orchestrator service, not in-process.
        This proxy exists for registry visibility and monitoring.
        """
        return self.build_output(
            trace_id=input_data.trace_id,
            result={"note": "Runs via clinical-orchestrator service"},
            confidence=1.0,
            rationale="Clinical assessment delegated to orchestrator microservice",
        )


def register_clinical_agents() -> None:
    """Register all clinical decision support agents in the HealthOS registry."""
    for name, tier, version, description, requires_hitl in CLINICAL_AGENTS:
        agent = ClinicalAgentProxy()
        agent.name = name
        agent.tier = tier
        agent.version = version
        agent.description = description
        agent.requires_hitl = requires_hitl
        registry.register(agent)

    logger.info("agents.clinical_decision_support.all_registered", count=len(CLINICAL_AGENTS))
