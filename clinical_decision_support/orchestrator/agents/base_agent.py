"""
Base Agent Framework for Multi-Agent Healthcare System
Provides common functionality for all specialized agents
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging
import httpx
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Agent Communication Protocol (A2A)
# ============================================================================

class AgentMessage(BaseModel):
    """Message format for agent-to-agent communication"""
    message_id: str
    sender: str
    recipient: str
    message_type: str  # request, response, notification, error
    action: str        # what action to perform
    payload: dict
    context: dict = {}
    timestamp: str = None
    correlation_id: str = None  # For tracking related messages

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)


class AgentCapability(BaseModel):
    """Describes what an agent can do"""
    name: str
    description: str
    input_schema: dict
    output_schema: dict


class AgentCard(BaseModel):
    """Agent identity and capabilities (A2A protocol)"""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[AgentCapability]
    specialties: List[str] = []
    requires_human_approval: bool = False


# ============================================================================
# Clinical Data Types
# ============================================================================

class PatientContext(BaseModel):
    """Comprehensive patient context for agent processing"""
    patient_id: str
    fhir_id: Optional[str] = None

    # Demographics
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    date_of_birth: Optional[str] = None

    # Current state
    vitals: Optional[List[dict]] = None
    labs: Optional[List[dict]] = None
    medications: Optional[List[dict]] = None
    allergies: Optional[List[dict]] = None
    conditions: Optional[List[dict]] = None
    encounters: Optional[List[dict]] = None

    # Clinical notes
    chief_complaint: Optional[str] = None
    history_present_illness: Optional[str] = None
    past_medical_history: Optional[List[str]] = None
    social_history: Optional[dict] = None
    family_history: Optional[List[str]] = None
    physician_notes: Optional[str] = None  # Doctor's observations and notes
    review_of_systems: Optional[dict] = None  # Symptom checklist by system
    physical_exam: Optional[dict] = None  # Physical examination findings

    # Additional context
    recent_procedures: Optional[List[dict]] = None
    imaging_results: Optional[List[dict]] = None


class ClinicalFinding(BaseModel):
    """A single clinical finding or observation"""
    type: str  # vital, lab, symptom, sign, imaging
    name: str
    value: Any
    unit: Optional[str] = None
    status: str  # normal, abnormal, critical
    interpretation: Optional[str] = None
    confidence: float = 1.0
    source: Optional[str] = None
    timestamp: Optional[str] = None


class DiagnosisRecommendation(BaseModel):
    """Recommended diagnosis with supporting evidence"""
    diagnosis: str
    icd10_code: str
    confidence: float
    supporting_findings: List[ClinicalFinding]
    differential_diagnoses: List[dict] = []
    rationale: str


class TreatmentRecommendation(BaseModel):
    """Recommended treatment or intervention"""
    treatment_type: str  # medication, procedure, referral, monitoring
    description: str
    cpt_code: Optional[str] = None
    priority: str  # immediate, urgent, routine
    rationale: str
    contraindications: List[str] = []
    alternatives: List[str] = []


class AgentOutput(BaseModel):
    """Standard output from any agent"""
    agent_id: str
    agent_name: str
    timestamp: str
    success: bool

    # Clinical outputs
    findings: List[ClinicalFinding] = []
    diagnoses: List[DiagnosisRecommendation] = []
    treatments: List[TreatmentRecommendation] = []

    # Codes
    icd10_codes: List[dict] = []
    cpt_codes: List[dict] = []

    # Metadata
    confidence: float = 0.0
    reasoning_steps: List[str] = []
    warnings: List[str] = []
    errors: List[str] = []

    # For supervisor aggregation
    requires_human_review: bool = False
    review_reason: Optional[str] = None


# ============================================================================
# MCP Client for Agent Use
# ============================================================================

class MCPClient:
    """Client for agents to call MCP servers"""

    def __init__(self, base_urls: dict = None):
        import os
        self.base_urls = base_urls or {
            "fhir": os.getenv("MCP_FHIR_SERVER_URL", "http://mcp-fhir-server:8005"),
            "labs": os.getenv("MCP_LABS_SERVER_URL", "http://mcp-labs-server:8006"),
            "rag": os.getenv("MCP_RAG_SERVER_URL", "http://mcp-rag-server:8007"),
            "adapter": os.getenv("MCP_FHIR_ADAPTER_URL", "http://mcp-fhir-adapter:8002"),
        }

    async def call_tool(self, server: str, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool on a server"""
        base_url = self.base_urls.get(server)
        if not base_url:
            raise ValueError(f"Unknown MCP server: {server}")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{base_url}/tools/{tool_name}",
                json={"arguments": arguments}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("data", result)

    async def get_patient_context(self, patient_id: str) -> PatientContext:
        """Gather full patient context from MCP servers"""
        data = await self.call_tool("fhir", "get_full_patient_context", {"patient_id": patient_id})

        # Handle case where data itself is None or not a dict
        if not data or not isinstance(data, dict):
            data = {}

        # Use `or {}` to handle fields that are explicitly None
        # (e.g. when an MCP sub-tool call fails and returns None)
        patient_data = data.get("patient") or {}
        vitals_data = data.get("vitals") or {}

        return PatientContext(
            patient_id=patient_id,
            fhir_id=patient_id,
            name=self._extract_name(patient_data),
            age=self._calculate_age(patient_data.get("birthDate")),
            sex=patient_data.get("gender"),
            date_of_birth=patient_data.get("birthDate"),
            vitals=vitals_data.get("vitals") or [],
            labs=(data.get("labs") or {}).get("labs") or [],
            medications=(data.get("medications") or {}).get("medications") or [],
            allergies=(data.get("allergies") or {}).get("allergies") or [],
            conditions=(data.get("conditions") or {}).get("conditions") or [],
            encounters=(data.get("encounters") or {}).get("encounters") or [],
        )

    def _extract_name(self, patient: dict) -> str:
        names = patient.get("name", [])
        if names:
            name = names[0]
            given = " ".join(name.get("given", []))
            family = name.get("family", "")
            return f"{given} {family}".strip()
        return "Unknown"

    def _calculate_age(self, birth_date: str) -> Optional[int]:
        if not birth_date:
            return None
        try:
            from datetime import datetime
            bd = datetime.fromisoformat(birth_date.replace("Z", "+00:00"))
            today = datetime.now()
            return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except:
            return None


# ============================================================================
# Base Agent Class
# ============================================================================

class BaseAgent(ABC):
    """
    Base class for all healthcare agents.
    Implements A2A protocol and common agent functionality.
    """

    def __init__(self, agent_id: str, name: str, description: str, version: str = "1.0.0"):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.version = version
        self.mcp = MCPClient()
        self.capabilities: List[AgentCapability] = []
        self.specialties: List[str] = []
        self._setup_capabilities()

    @abstractmethod
    def _setup_capabilities(self):
        """Override to define agent capabilities"""
        pass

    @abstractmethod
    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """
        Main processing method. Override in subclasses.

        Args:
            context: Patient clinical context
            task: Optional specific task to perform

        Returns:
            AgentOutput with findings, diagnoses, treatments, etc.
        """
        pass

    def get_agent_card(self) -> AgentCard:
        """Return agent's identity and capabilities (A2A protocol)"""
        return AgentCard(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            version=self.version,
            capabilities=self.capabilities,
            specialties=self.specialties
        )

    async def receive_message(self, message: AgentMessage) -> AgentMessage:
        """
        Handle incoming A2A message.
        Override for custom message handling.
        """
        logger.info(f"Agent {self.agent_id} received message: {message.action}")

        if message.action == "get_capabilities":
            return AgentMessage(
                message_id=f"resp-{message.message_id}",
                sender=self.agent_id,
                recipient=message.sender,
                message_type="response",
                action="capabilities",
                payload=self.get_agent_card().dict(),
                correlation_id=message.message_id
            )

        elif message.action == "process":
            context = PatientContext(**message.payload.get("context", {}))
            task = message.payload.get("task")
            result = await self.process(context, task)

            return AgentMessage(
                message_id=f"resp-{message.message_id}",
                sender=self.agent_id,
                recipient=message.sender,
                message_type="response",
                action="result",
                payload=result.dict(),
                correlation_id=message.message_id
            )

        else:
            return AgentMessage(
                message_id=f"resp-{message.message_id}",
                sender=self.agent_id,
                recipient=message.sender,
                message_type="error",
                action="unknown_action",
                payload={"error": f"Unknown action: {message.action}"},
                correlation_id=message.message_id
            )

    async def send_message(self, recipient: str, action: str, payload: dict) -> AgentMessage:
        """
        Send message to another agent (via message broker in production).
        For now, this is a placeholder for direct agent communication.
        """
        import uuid
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient=recipient,
            message_type="request",
            action=action,
            payload=payload
        )
        logger.info(f"Agent {self.agent_id} sending message to {recipient}: {action}")
        # In production, route through message broker (Redis, RabbitMQ, etc.)
        return message

    def _create_output(
        self,
        findings: List[ClinicalFinding] = None,
        diagnoses: List[DiagnosisRecommendation] = None,
        treatments: List[TreatmentRecommendation] = None,
        icd10_codes: List[dict] = None,
        cpt_codes: List[dict] = None,
        confidence: float = 0.0,
        reasoning: List[str] = None,
        warnings: List[str] = None,
        requires_review: bool = False,
        review_reason: str = None
    ) -> AgentOutput:
        """Helper to create standardized agent output"""
        # Use provided codes or auto-generate from diagnoses/treatments
        final_icd10 = icd10_codes if icd10_codes is not None else [
            {"code": d.icd10_code, "description": d.diagnosis} for d in (diagnoses or [])
        ]
        final_cpt = cpt_codes if cpt_codes is not None else [
            {"code": t.cpt_code, "description": t.description} for t in (treatments or []) if t.cpt_code
        ]

        return AgentOutput(
            agent_id=self.agent_id,
            agent_name=self.name,
            timestamp=datetime.utcnow().isoformat(),
            success=True,
            findings=findings or [],
            diagnoses=diagnoses or [],
            treatments=treatments or [],
            icd10_codes=final_icd10,
            cpt_codes=final_cpt,
            confidence=confidence,
            reasoning_steps=reasoning or [],
            warnings=warnings or [],
            requires_human_review=requires_review,
            review_reason=review_reason
        )
