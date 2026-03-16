"""
Model Context Protocol (MCP) implementation for healthcare agent communication.

MCP provides a standardized way for AI agents to:
- Discover available tools and resources
- Exchange structured context about patients and workflows
- Maintain conversation state across agent interactions
- Enforce governance and safety constraints on agent actions
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger('mcp')


@dataclass
class MCPResource:
    """A resource that can be accessed through MCP."""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class MCPTool:
    """A tool that can be invoked through MCP."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class MCPMessage:
    """A message in the MCP protocol."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "assistant"
    content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return asdict(self)


class MCPServer:
    """
    MCP Server that exposes healthcare agent tools and resources.
    
    Implements the Model Context Protocol for:
    - Tool discovery and invocation
    - Resource listing and reading
    - Context management for multi-agent workflows
    """

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()
        self._register_default_resources()

    def _register_default_tools(self):
        """Register all available healthcare agent tools."""
        self.register_tool(MCPTool(
            name="screen_patient",
            description="Run MS risk screening on a specific patient using the multi-agent pipeline",
            input_schema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "Patient identifier (e.g., P00001)"},
                },
                "required": ["patient_id"]
            }
        ))
        self.register_tool(MCPTool(
            name="run_screening_workflow",
            description="Execute full screening workflow across all patients with specified policy",
            input_schema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Policy configuration UUID"},
                    "patient_limit": {"type": "integer", "description": "Max patients to screen"},
                },
            }
        ))
        self.register_tool(MCPTool(
            name="get_patient_risk_card",
            description="Generate detailed risk explanation card for a patient",
            input_schema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "run_id": {"type": "string"},
                },
                "required": ["patient_id"]
            }
        ))
        self.register_tool(MCPTool(
            name="analyze_fairness",
            description="Run fairness analysis on screening results by demographic group",
            input_schema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Workflow run UUID"},
                    "group_by": {
                        "type": "string",
                        "enum": ["sex", "age_band", "lookalike_dx"],
                        "description": "Grouping variable for fairness analysis"
                    },
                },
                "required": ["run_id", "group_by"]
            }
        ))
        self.register_tool(MCPTool(
            name="what_if_policy",
            description="Run what-if analysis with alternative policy thresholds",
            input_schema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "risk_review_threshold": {"type": "number"},
                    "draft_order_threshold": {"type": "number"},
                    "auto_order_threshold": {"type": "number"},
                    "max_auto_actions_per_day": {"type": "integer"},
                },
                "required": ["run_id"]
            }
        ))
        self.register_tool(MCPTool(
            name="review_assessment",
            description="Submit clinician review for a risk assessment",
            input_schema={
                "type": "object",
                "properties": {
                    "assessment_id": {"type": "string"},
                    "reviewed_by": {"type": "string"},
                    "review_notes": {"type": "string"},
                    "override_action": {"type": "string"},
                },
                "required": ["assessment_id", "reviewed_by"]
            }
        ))
        self.register_tool(MCPTool(
            name="get_workflow_metrics",
            description="Get comprehensive metrics for a workflow run",
            input_schema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                },
                "required": ["run_id"]
            }
        ))
        self.register_tool(MCPTool(
            name="summarize_note",
            description="Use LLM to summarize a clinical note for MS evidence",
            input_schema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                },
                "required": ["patient_id"]
            }
        ))

    def _register_default_resources(self):
        """Register available data resources."""
        self.register_resource(MCPResource(
            uri="msrisk://patients",
            name="Patient Registry",
            description="Access to the patient population database"
        ))
        self.register_resource(MCPResource(
            uri="msrisk://assessments",
            name="Risk Assessments",
            description="Historical risk assessment results"
        ))
        self.register_resource(MCPResource(
            uri="msrisk://policies",
            name="Policy Configurations",
            description="Screening policy threshold configurations"
        ))
        self.register_resource(MCPResource(
            uri="msrisk://governance",
            name="Governance Rules",
            description="Safety and governance rule definitions"
        ))
        self.register_resource(MCPResource(
            uri="msrisk://analytics",
            name="Analytics Dashboard",
            description="Aggregated metrics and fairness data"
        ))

    def register_tool(self, tool: MCPTool):
        self._tools[tool.name] = tool

    def register_resource(self, resource: MCPResource):
        self._resources[resource.uri] = resource

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]

    def list_resources(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._resources.values()]

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            'id': session_id,
            'created_at': datetime.utcnow().isoformat(),
            'messages': [],
            'context': {},
        }
        logger.info(f"MCP session created: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def invoke_tool(self, session_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a registered tool and return the result."""
        if tool_name not in self._tools:
            return {"error": f"Tool '{tool_name}' not found"}

        session = self._sessions.get(session_id)
        if not session:
            session_id = self.create_session()
            session = self._sessions[session_id]

        logger.info(f"MCP tool invocation: {tool_name} with args {arguments}")

        try:
            result = self._execute_tool(tool_name, arguments)
            
            # Record in session
            session['messages'].append(MCPMessage(
                role="tool",
                content=json.dumps(result),
                tool_calls=[{"name": tool_name, "arguments": arguments}],
                tool_results=[result],
            ).to_dict())
            
            return {"success": True, "result": result, "session_id": session_id}
        except Exception as e:
            logger.error(f"MCP tool error: {tool_name} - {e}")
            return {"success": False, "error": str(e), "session_id": session_id}

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute the actual tool logic."""
        from patients.models import Patient, RiskAssessment, WorkflowRun, PolicyConfiguration
        from analytics.services import (
            compute_workflow_metrics, subgroup_analysis, what_if_analysis
        )
        from agents.llm_agent import llm_summarize_note

        if tool_name == "screen_patient":
            patient = Patient.objects.get(patient_id=arguments['patient_id'])
            from agents.phenotyping import PhenotypingAgentV2
            from agents.notes_imaging import NotesImagingAgent
            from agents.safety import SafetyGovernanceAgent
            from agents.coordinator import Coordinator
            from django.conf import settings

            phenotyper = PhenotypingAgentV2()
            notes_agent = NotesImagingAgent()
            safety_agent = SafetyGovernanceAgent()
            coordinator = Coordinator(settings.MS_RISK_POLICY)

            patient_data = {
                'patient_id': patient.patient_id,
                'age': patient.age,
                'sex': patient.sex,
                'note': patient.note,
                'has_mri': patient.has_mri,
                'mri_lesions': patient.mri_lesions,
                'note_has_ms_terms': patient.note_has_ms_terms,
                'optic_neuritis': patient.optic_neuritis,
                'paresthesia': patient.paresthesia,
                'weakness': patient.weakness,
                'gait_instability': patient.gait_instability,
                'vertigo': patient.vertigo,
                'fatigue': patient.fatigue,
                'bladder_issues': patient.bladder_issues,
                'cognitive_fog': patient.cognitive_fog,
                'lookalike_dx': patient.lookalike_dx,
                'vitamin_d_deficient': patient.vitamin_d_deficient or False,
                'infectious_mono_history': patient.infectious_mono_history or False,
                'smartform_neuro_symptom_score': patient.smartform_neuro_symptom_score or 0,
                'paths_like_function_score': patient.paths_like_function_score or 100,
                'visits_last_year': patient.visits_last_year,
            }

            import pandas as pd
            row = pd.Series(patient_data)
            risk, contrib = phenotyper.score(row)
            notes_out = notes_agent.execute(patient_data)
            safety_out = safety_agent.execute(patient_data, risk)
            decision = coordinator.execute(risk, safety_out.payload)

            return {
                'patient_id': patient.patient_id,
                'risk_score': risk,
                'feature_contributions': contrib,
                'notes_analysis': notes_out.payload,
                'safety': safety_out.payload,
                'decision': decision.payload,
            }

        elif tool_name == "run_screening_workflow":
            from agents.tasks import run_screening_workflow_task
            task = run_screening_workflow_task.delay(
                arguments.get('policy_id'),
                arguments.get('patient_limit')
            )
            return {"task_id": task.id, "status": "queued"}

        elif tool_name == "get_patient_risk_card":
            patient_id = arguments['patient_id']
            run_id = arguments.get('run_id')
            qs = RiskAssessment.objects.filter(patient__patient_id=patient_id)
            if run_id:
                qs = qs.filter(run_id=run_id)
            assessment = qs.order_by('-created_at').first()
            if not assessment:
                return {"error": "No assessment found"}
            return {
                'patient_id': patient_id,
                'risk_score': assessment.risk_score,
                'action': assessment.action,
                'autonomy_level': assessment.autonomy_level,
                'feature_contributions': assessment.feature_contributions,
                'flags': assessment.flags,
                'rationale': assessment.rationale,
                'patient_card': assessment.patient_card,
            }

        elif tool_name == "analyze_fairness":
            return subgroup_analysis(arguments['run_id'], arguments['group_by'])

        elif tool_name == "what_if_policy":
            run_id = arguments.pop('run_id')
            return what_if_analysis(run_id, arguments)

        elif tool_name == "get_workflow_metrics":
            return compute_workflow_metrics(arguments['run_id'])

        elif tool_name == "summarize_note":
            patient = Patient.objects.get(patient_id=arguments['patient_id'])
            summary = llm_summarize_note(patient.note)
            return {"patient_id": patient.patient_id, "note_summary": summary}

        elif tool_name == "review_assessment":
            assessment = RiskAssessment.objects.get(id=arguments['assessment_id'])
            assessment.reviewed_by = arguments['reviewed_by']
            assessment.review_notes = arguments.get('review_notes', '')
            from django.utils import timezone
            assessment.reviewed_at = timezone.now()
            if 'override_action' in arguments:
                assessment.action = arguments['override_action']
            assessment.save()
            return {"status": "reviewed", "assessment_id": str(assessment.id)}

        return {"error": f"Unknown tool: {tool_name}"}

    def read_resource(self, uri: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Read a registered resource."""
        from patients.models import Patient, RiskAssessment, WorkflowRun, PolicyConfiguration

        if uri == "msrisk://patients":
            limit = (params or {}).get('limit', 50)
            patients = Patient.objects.all()[:limit]
            return {
                "total": Patient.objects.count(),
                "data": list(patients.values('patient_id', 'age', 'sex', 'true_at_risk'))
            }
        elif uri == "msrisk://assessments":
            run_id = (params or {}).get('run_id')
            qs = RiskAssessment.objects.all()
            if run_id:
                qs = qs.filter(run_id=run_id)
            return {
                "total": qs.count(),
                "data": list(qs.values(
                    'patient__patient_id', 'risk_score', 'action', 'autonomy_level'
                )[:100])
            }
        elif uri == "msrisk://policies":
            return {
                "data": list(PolicyConfiguration.objects.values())
            }
        elif uri == "msrisk://governance":
            from governance.models import GovernanceRule
            return {
                "data": list(GovernanceRule.objects.values())
            }
        return {"error": f"Unknown resource: {uri}"}


# Singleton instance
mcp_server = MCPServer()
