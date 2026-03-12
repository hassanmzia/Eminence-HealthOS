"""
Eminence HealthOS — Master Orchestrator Agent
Layer 3 (Decisioning): Decides which domain agents should run and in what
sequence for a given event.  Classifies incoming events, builds an execution
graph based on patient acuity and event type, and returns an ordered agent
execution plan that the ExecutionEngine can follow.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    PipelineState,
    Severity,
)
from healthos_platform.orchestrator.router import ROUTING_TABLE

logger = structlog.get_logger()


# ── Event Classification ──────────────────────────────────────────────────────

EVENT_PRIORITY: dict[str, int] = {
    "emergency": 0,
    "critical": 1,
    "high": 2,
    "routine": 3,
    "scheduled": 4,
}

# Keyword patterns → priority classification
PRIORITY_KEYWORDS: list[tuple[str, str]] = [
    ("critical", "critical"),
    ("emergency", "emergency"),
    ("escalation", "high"),
    ("alert", "high"),
    ("pipeline", "scheduled"),
    ("scheduled", "scheduled"),
]

# Control agents injected around domain agents
CONTROL_PREFIX: list[str] = ["context_assembly"]
CONTROL_SUFFIX: list[str] = ["policy_rules", "quality_confidence", "audit_trace"]


class MasterOrchestratorAgent(BaseAgent):
    """
    Classifies events, resolves the domain agent sequence from the routing
    table, and wraps it with the appropriate control agents (context assembly,
    policy checks, quality scoring, audit logging).

    The output ``execution_plan`` is stored on the pipeline state so the
    engine (or a future graph executor) can follow it.
    """

    name = "master_orchestrator"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Classifies events and builds ordered agent execution plans"
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Build an execution plan from standalone input."""
        event_type = input_data.trigger or ""
        context = input_data.context or {}

        priority = self._classify_priority(event_type, context)
        domain_agents = self._resolve_domain_agents(event_type)
        plan = self._build_execution_plan(domain_agents, priority, context)

        confidence = 0.95 if domain_agents else 0.50

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "event_type": event_type,
                "priority": priority,
                "domain_agents": domain_agents,
                "execution_plan": plan,
            },
            confidence=confidence,
            rationale=self._build_rationale(event_type, priority, plan),
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Classify the trigger event and attach the execution plan."""
        event_type = state.trigger_event
        context_hints = self._acuity_hints(state)

        priority = self._classify_priority(event_type, context_hints)
        domain_agents = self._resolve_domain_agents(event_type)
        plan = self._build_execution_plan(domain_agents, priority, context_hints)

        # Store the plan on the patient context for downstream consumers
        state.patient_context["execution_plan"] = plan
        state.patient_context["event_priority"] = priority

        confidence = 0.95 if domain_agents else 0.50

        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result={
                "event_type": event_type,
                "priority": priority,
                "domain_agents": domain_agents,
                "execution_plan": plan,
            },
            confidence=confidence,
            rationale=self._build_rationale(event_type, priority, plan),
        )

        return state

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _classify_priority(self, event_type: str, context: dict[str, Any]) -> str:
        """Classify event priority from event name and context signals."""
        # Check explicit context override
        if "priority" in context:
            return str(context["priority"])

        # Check high-acuity patient signals
        if context.get("has_critical_anomalies") or context.get("has_critical_risk"):
            return "critical"

        # Keyword matching on the event type
        event_lower = event_type.lower()
        for keyword, priority in PRIORITY_KEYWORDS:
            if keyword in event_lower:
                return priority

        return "routine"

    def _resolve_domain_agents(self, event_type: str) -> list[str]:
        """Look up the domain agents for the event in the routing table."""
        return list(ROUTING_TABLE.get(event_type, []))

    def _build_execution_plan(
        self,
        domain_agents: list[str],
        priority: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build the full ordered execution plan wrapping domain agents with
        control agents (prefix + suffix).
        """
        plan: list[dict[str, Any]] = []
        order = 0

        # 1. Control prefix (context assembly, etc.)
        for agent_name in CONTROL_PREFIX:
            if agent_name not in domain_agents:
                plan.append(self._plan_entry(agent_name, order, "control_prefix"))
                order += 1

        # 2. Domain agents in routing-table order
        for agent_name in domain_agents:
            plan.append(self._plan_entry(agent_name, order, "domain"))
            order += 1

        # 3. Control suffix (policy, quality, audit)
        for agent_name in CONTROL_SUFFIX:
            if agent_name not in domain_agents:
                plan.append(self._plan_entry(agent_name, order, "control_suffix"))
                order += 1

        # 4. Add HITL checkpoint for critical/emergency events
        if priority in ("critical", "emergency"):
            plan.append(self._plan_entry("hitl", order, "control_checkpoint"))
            order += 1

        return plan

    @staticmethod
    def _plan_entry(agent_name: str, order: int, phase: str) -> dict[str, Any]:
        return {"agent": agent_name, "order": order, "phase": phase}

    def _acuity_hints(self, state: PipelineState) -> dict[str, Any]:
        """Extract acuity-relevant signals from the pipeline state."""
        hints: dict[str, Any] = {}

        if state.anomalies:
            hints["has_critical_anomalies"] = any(
                a.severity == Severity.CRITICAL for a in state.anomalies
            )

        if state.risk_assessments:
            hints["has_critical_risk"] = any(
                r.score >= 0.75 for r in state.risk_assessments
            )

        return hints

    def _build_rationale(
        self, event_type: str, priority: str, plan: list[dict[str, Any]]
    ) -> str:
        agent_names = [p["agent"] for p in plan]
        return (
            f"Event '{event_type}' classified as {priority} priority — "
            f"execution plan: {', '.join(agent_names)} ({len(plan)} steps)"
        )
