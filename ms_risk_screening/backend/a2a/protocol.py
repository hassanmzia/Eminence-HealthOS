"""
Agent-to-Agent (A2A) Protocol implementation.

A2A enables direct communication between healthcare agents:
- Agent discovery via Agent Cards
- Task delegation and result collection
- Multi-step workflow orchestration
- Streaming updates for long-running operations
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger('a2a')


@dataclass
class AgentCard:
    """Agent Card describing an agent's capabilities (A2A spec)."""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class A2ATask:
    """A task in the A2A protocol."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    action: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class A2AGateway:
    """
    Agent-to-Agent Gateway for multi-agent healthcare workflow orchestration.
    
    Manages agent discovery, task routing, and inter-agent communication
    following the A2A protocol specification.
    """

    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
        self._tasks: Dict[str, A2ATask] = {}
        self._register_healthcare_agents()

    def _register_healthcare_agents(self):
        """Register all healthcare domain agents."""
        self.register_agent(AgentCard(
            agent_id="retrieval-agent",
            name="Retrieval Agent",
            description="Identifies candidate patients from EHR database using broad screening criteria",
            capabilities=["patient_retrieval", "candidate_selection", "ehr_search"],
            input_schema={
                "type": "object",
                "properties": {
                    "criteria": {"type": "object"},
                    "patient_limit": {"type": "integer"},
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "candidate_ids": {"type": "array", "items": {"type": "string"}},
                    "total_screened": {"type": "integer"},
                }
            }
        ))
        self.register_agent(AgentCard(
            agent_id="phenotyping-agent",
            name="Phenotyping Agent",
            description="Computes interpretable MS risk scores using weighted feature analysis",
            capabilities=["risk_scoring", "feature_analysis", "phenotyping"],
            input_schema={
                "type": "object",
                "properties": {
                    "patient_data": {"type": "object"},
                    "version": {"type": "string", "enum": ["v1", "v2"]},
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "risk_score": {"type": "number"},
                    "feature_contributions": {"type": "object"},
                }
            }
        ))
        self.register_agent(AgentCard(
            agent_id="notes-imaging-agent",
            name="Notes & Imaging Agent",
            description="Extracts clinical evidence from unstructured notes and imaging reports",
            capabilities=["note_analysis", "term_extraction", "imaging_review"],
        ))
        self.register_agent(AgentCard(
            agent_id="safety-governance-agent",
            name="Safety & Governance Agent",
            description="Enforces safety guardrails, PHI checks, and governance rules",
            capabilities=["safety_check", "phi_detection", "demographic_guard", "rate_limiting"],
        ))
        self.register_agent(AgentCard(
            agent_id="coordinator-agent",
            name="Coordinator Agent",
            description="Synthesizes evidence and makes autonomous/semi-autonomous decisions",
            capabilities=["decision_making", "autonomy_management", "action_selection"],
        ))
        self.register_agent(AgentCard(
            agent_id="llm-agent",
            name="LLM Analysis Agent",
            description="Provides LLM-powered clinical note summarization and explanations",
            capabilities=["note_summarization", "card_explanation", "threshold_proposal"],
        ))
        self.register_agent(AgentCard(
            agent_id="analytics-agent",
            name="Analytics Agent",
            description="Generates fairness reports, calibration data, and what-if analysis",
            capabilities=["fairness_analysis", "calibration", "what_if", "metrics"],
        ))

    def register_agent(self, agent_card: AgentCard):
        self._agents[agent_card.agent_id] = agent_card
        logger.info(f"A2A agent registered: {agent_card.agent_id}")

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values()]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        agent = self._agents.get(agent_id)
        return agent.to_dict() if agent else None

    def create_task(self, from_agent: str, to_agent: str, action: str,
                    payload: Dict[str, Any]) -> A2ATask:
        """Create a new inter-agent task."""
        task = A2ATask(
            from_agent=from_agent,
            to_agent=to_agent,
            action=action,
            payload=payload,
        )
        self._tasks[task.id] = task
        logger.info(f"A2A task created: {task.id} ({from_agent} -> {to_agent}: {action})")
        return task

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a pending task by routing to the appropriate agent."""
        task = self._tasks.get(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}

        task.status = "running"
        logger.info(f"A2A executing task: {task_id}")

        try:
            result = self._route_task(task)
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.utcnow().isoformat()
            return {"task_id": task_id, "status": "completed", "result": result}
        except Exception as e:
            task.status = "failed"
            task.result = {"error": str(e)}
            logger.error(f"A2A task failed: {task_id} - {e}")
            return {"task_id": task_id, "status": "failed", "error": str(e)}

    def _route_task(self, task: A2ATask) -> Any:
        """Route task to the appropriate agent implementation."""
        from mcp.protocol import mcp_server

        agent_tool_map = {
            "retrieval-agent": {
                "retrieve_candidates": "run_screening_workflow",
            },
            "phenotyping-agent": {
                "score_patient": "screen_patient",
            },
            "notes-imaging-agent": {
                "analyze_notes": "summarize_note",
            },
            "safety-governance-agent": {
                "check_safety": "screen_patient",
            },
            "coordinator-agent": {
                "make_decision": "screen_patient",
            },
            "llm-agent": {
                "summarize": "summarize_note",
                "explain_card": "get_patient_risk_card",
            },
            "analytics-agent": {
                "fairness": "analyze_fairness",
                "metrics": "get_workflow_metrics",
                "what_if": "what_if_policy",
            },
        }

        agent_map = agent_tool_map.get(task.to_agent, {})
        tool_name = agent_map.get(task.action)

        if tool_name:
            session_id = mcp_server.create_session()
            result = mcp_server.invoke_tool(session_id, tool_name, task.payload)
            return result.get("result", result)

        return {"error": f"No handler for {task.to_agent}/{task.action}"}

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = self._tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [t.to_dict() for t in tasks]

    def orchestrate_screening(self, patient_id: str) -> Dict[str, Any]:
        """
        Orchestrate a full multi-agent screening pipeline for a single patient.
        Demonstrates A2A agent-to-agent communication flow.
        """
        results = {}

        # Step 1: Phenotyping
        t1 = self.create_task("coordinator-agent", "phenotyping-agent",
                              "score_patient", {"patient_id": patient_id})
        r1 = self.execute_task(t1.id)
        results["phenotyping"] = r1

        # Step 2: Notes analysis
        t2 = self.create_task("coordinator-agent", "notes-imaging-agent",
                              "analyze_notes", {"patient_id": patient_id})
        r2 = self.execute_task(t2.id)
        results["notes_analysis"] = r2

        # Step 3: LLM summary
        t3 = self.create_task("coordinator-agent", "llm-agent",
                              "summarize", {"patient_id": patient_id})
        r3 = self.execute_task(t3.id)
        results["llm_summary"] = r3

        return {
            "patient_id": patient_id,
            "pipeline_results": results,
            "tasks_executed": 3,
        }


# Singleton
a2a_gateway = A2AGateway()
