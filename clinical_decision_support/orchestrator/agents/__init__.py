"""
Multi-Agent Healthcare System

This package contains specialized AI agents for clinical decision support:

Core Agents:
- SupervisorAgent: Orchestrates all specialist agents
- DiagnosticianAgent: Generates differential diagnoses with ICD-10 codes
- TreatmentAgent: Creates treatment plans with CPT codes

Safety & Compliance:
- SafetyAgent: Drug interaction and allergy checking
- CodingAgent: ICD-10 and CPT code validation

Specialist Agents:
- CardiologyAgent: Cardiovascular conditions and GDMT
- RadiologyAgent: X-ray, CT, MRI imaging analysis
- PathologyAgent: Laboratory results and tissue analysis
- GastroenterologyAgent: Colonoscopy, endoscopy, GI procedures
- OncologyAgent: Cancer detection, staging, tumor markers

A2A Protocol:
Agents communicate using a standardized message format (AgentMessage)
enabling coordination and information sharing.
"""

from .base_agent import (
    BaseAgent,
    AgentMessage,
    AgentCapability,
    AgentCard,
    PatientContext,
    ClinicalFinding,
    DiagnosisRecommendation,
    TreatmentRecommendation,
    AgentOutput,
    MCPClient
)

from .diagnostician_agent import DiagnosticianAgent
from .treatment_agent import TreatmentAgent
from .supervisor_agent import SupervisorAgent, ComprehensiveRecommendation
from .safety_agent import SafetyAgent
from .coding_agent import CodingAgent
from .cardiology_agent import CardiologyAgent
from .radiology_agent import RadiologyAgent
from .pathology_agent import PathologyAgent
from .gastroenterology_agent import GastroenterologyAgent
from .oncology_agent import OncologyAgent

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentMessage",
    "AgentCapability",
    "AgentCard",
    "PatientContext",
    "ClinicalFinding",
    "DiagnosisRecommendation",
    "TreatmentRecommendation",
    "AgentOutput",
    "MCPClient",

    # Core Agents
    "DiagnosticianAgent",
    "TreatmentAgent",
    "SupervisorAgent",

    # Safety & Compliance
    "SafetyAgent",
    "CodingAgent",

    # Specialist Agents
    "CardiologyAgent",
    "RadiologyAgent",
    "PathologyAgent",
    "GastroenterologyAgent",
    "OncologyAgent",

    # Outputs
    "ComprehensiveRecommendation"
]
