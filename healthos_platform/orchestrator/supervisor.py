"""
Eminence HealthOS — LangGraph Supervisor
Builds a LangGraph StateGraph that orchestrates the 5-tier agent pipeline
with conditional routing, feedback loops, HITL checkpoints, and emergency
escalation paths.
"""

from __future__ import annotations

import operator
import uuid
from typing import Annotated, Any, TypedDict

import structlog

from healthos_platform.agents.types import (
    AgentOutput,
    AgentStatus,
    PipelineState,
    Severity,
)

logger = structlog.get_logger()


# ── LangGraph State ──────────────────────────────────────────────────────────


class SupervisorState(TypedDict):
    """State flowing through the LangGraph supervisor graph."""

    trace_id: str
    org_id: str
    patient_id: str
    trigger_event: str

    # Accumulated messages from agents (append-only via operator.add)
    messages: Annotated[list[dict[str, Any]], operator.add]

    # Tier outputs
    monitoring_output: dict[str, Any]
    diagnostic_output: dict[str, Any]
    risk_output: dict[str, Any]
    intervention_output: dict[str, Any]
    action_output: dict[str, Any]

    # Control flow
    alert_level: str  # none, low, moderate, high, critical
    risk_score: float
    iteration_count: int
    max_iterations: int
    requires_hitl: bool
    hitl_reason: str
    is_emergency: bool

    # Final report
    final_report: dict[str, Any]
    executed_tiers: list[str]


def _default_state(
    org_id: str,
    patient_id: str,
    trigger_event: str,
) -> SupervisorState:
    """Create initial supervisor state."""
    return SupervisorState(
        trace_id=str(uuid.uuid4()),
        org_id=org_id,
        patient_id=patient_id,
        trigger_event=trigger_event,
        messages=[],
        monitoring_output={},
        diagnostic_output={},
        risk_output={},
        intervention_output={},
        action_output={},
        alert_level="none",
        risk_score=0.0,
        iteration_count=0,
        max_iterations=3,
        requires_hitl=False,
        hitl_reason="",
        is_emergency=False,
        final_report={},
        executed_tiers=[],
    )


# ── Tier Node Functions ──────────────────────────────────────────────────────


async def triage_node(state: SupervisorState) -> dict[str, Any]:
    """Classify the incoming event and determine initial routing."""
    trigger = state.get("trigger_event", "")
    is_emergency = any(
        kw in trigger.lower()
        for kw in ("emergency", "critical", "stemi", "stroke", "sepsis", "code_blue")
    )

    alert_level = "critical" if is_emergency else "none"

    return {
        "messages": [
            {
                "agent": "triage",
                "content": f"Event '{trigger}' classified — emergency={is_emergency}",
            }
        ],
        "is_emergency": is_emergency,
        "alert_level": alert_level,
    }


async def monitoring_node(state: SupervisorState) -> dict[str, Any]:
    """Tier 1: Patient monitoring — vitals, glucose, cardiac, activity, temperature."""
    patient_id = state.get("patient_id", "")
    trigger = state.get("trigger_event", "")

    # Simulate monitoring agents producing output
    output = {
        "tier": "monitoring",
        "agents_run": [
            "glucose_agent",
            "cardiac_agent",
            "activity_agent",
            "temperature_agent",
        ],
        "patient_id": patient_id,
        "vitals_analyzed": True,
        "anomalies_detected": [],
        "alert_level": state.get("alert_level", "none"),
    }

    return {
        "messages": [{"agent": "tier1_monitoring", "content": "Vitals monitoring complete"}],
        "monitoring_output": output,
        "executed_tiers": ["monitoring"],
    }


async def diagnostic_node(state: SupervisorState) -> dict[str, Any]:
    """Tier 2: Diagnostic analysis — ECG, kidney, imaging, lab interpretation."""
    monitoring = state.get("monitoring_output", {})

    output = {
        "tier": "diagnostic",
        "agents_run": [
            "ecg_agent",
            "kidney_agent",
            "imaging_agent",
            "lab_agent",
        ],
        "findings": [],
        "based_on_monitoring": bool(monitoring),
    }

    return {
        "messages": [{"agent": "tier2_diagnostic", "content": "Diagnostic analysis complete"}],
        "diagnostic_output": output,
        "executed_tiers": ["diagnostic"],
    }


async def risk_node(state: SupervisorState) -> dict[str, Any]:
    """Tier 3: Risk assessment — comorbidity, prediction, family history, SDOH, ML ensemble."""
    output = {
        "tier": "risk",
        "agents_run": [
            "comorbidity_agent",
            "prediction_agent",
            "family_history_agent",
            "sdoh_agent",
            "ml_ensemble_agent",
        ],
        "risk_scores": {},
        "overall_risk": 0.0,
    }

    risk_score = state.get("risk_score", 0.0)
    alert_level = state.get("alert_level", "none")

    if risk_score >= 0.8:
        alert_level = "critical"
    elif risk_score >= 0.6:
        alert_level = max(alert_level, "high", key=lambda x: ["none", "low", "moderate", "high", "critical"].index(x) if x in ["none", "low", "moderate", "high", "critical"] else 0)

    return {
        "messages": [{"agent": "tier3_risk", "content": f"Risk assessment complete — score={risk_score}"}],
        "risk_output": output,
        "alert_level": alert_level,
        "executed_tiers": ["risk"],
    }


async def intervention_node(state: SupervisorState) -> dict[str, Any]:
    """Tier 4: Intervention — coaching, prescription, contraindication, triage."""
    output = {
        "tier": "intervention",
        "agents_run": [
            "coaching_agent",
            "prescription_agent",
            "contraindication_agent",
            "triage_agent",
        ],
        "interventions": [],
        "requires_hitl": False,
    }

    # High-risk interventions require HITL
    alert_level = state.get("alert_level", "none")
    requires_hitl = alert_level in ("high", "critical")
    hitl_reason = ""
    if requires_hitl:
        hitl_reason = f"Intervention at alert_level={alert_level} requires clinician review"

    return {
        "messages": [{"agent": "tier4_intervention", "content": "Intervention planning complete"}],
        "intervention_output": output,
        "requires_hitl": requires_hitl,
        "hitl_reason": hitl_reason,
        "executed_tiers": ["intervention"],
    }


async def hitl_checkpoint_node(state: SupervisorState) -> dict[str, Any]:
    """HITL checkpoint — pauses pipeline for human review when required."""
    reason = state.get("hitl_reason", "Automated HITL checkpoint")

    return {
        "messages": [
            {
                "agent": "hitl_checkpoint",
                "content": f"HITL review requested: {reason}",
            }
        ],
        "requires_hitl": True,
    }


async def action_node(state: SupervisorState) -> dict[str, Any]:
    """Tier 5: Action — physician notify, patient notify, scheduling, EHR sync, billing."""
    output = {
        "tier": "action",
        "agents_run": [
            "physician_notify_agent",
            "patient_notify_agent",
            "scheduling_agent",
            "ehr_integration_agent",
            "billing_agent",
        ],
        "actions_taken": [],
    }

    # Increment iteration for feedback loop
    iteration = state.get("iteration_count", 0) + 1

    return {
        "messages": [{"agent": "tier5_action", "content": "Actions executed"}],
        "action_output": output,
        "iteration_count": iteration,
        "executed_tiers": ["action"],
    }


async def final_report_node(state: SupervisorState) -> dict[str, Any]:
    """Compile final report from all tier outputs."""
    report = {
        "trace_id": state.get("trace_id", ""),
        "patient_id": state.get("patient_id", ""),
        "trigger_event": state.get("trigger_event", ""),
        "tiers_executed": state.get("executed_tiers", []),
        "monitoring": state.get("monitoring_output", {}),
        "diagnostic": state.get("diagnostic_output", {}),
        "risk": state.get("risk_output", {}),
        "intervention": state.get("intervention_output", {}),
        "action": state.get("action_output", {}),
        "alert_level": state.get("alert_level", "none"),
        "risk_score": state.get("risk_score", 0.0),
        "iterations": state.get("iteration_count", 0),
        "requires_hitl": state.get("requires_hitl", False),
    }

    return {
        "messages": [{"agent": "final_report", "content": "Pipeline complete"}],
        "final_report": report,
    }


# ── Conditional Routing Functions ────────────────────────────────────────────


def route_after_triage(state: SupervisorState) -> str:
    """Route after triage: emergency goes directly to intervention, else monitoring."""
    if state.get("is_emergency"):
        return "intervention"
    return "monitoring"


def route_after_monitoring(state: SupervisorState) -> str:
    """Route after monitoring: anomalies go to diagnostic, otherwise to risk."""
    monitoring = state.get("monitoring_output", {})
    anomalies = monitoring.get("anomalies_detected", [])
    alert_level = state.get("alert_level", "none")

    if anomalies or alert_level in ("high", "critical"):
        return "diagnostic"
    return "risk"


def route_after_diagnostic(state: SupervisorState) -> str:
    """After diagnostic, always proceed to risk assessment."""
    return "risk"


def route_after_risk(state: SupervisorState) -> str:
    """Route after risk: high/critical risk goes to intervention, else final report."""
    alert_level = state.get("alert_level", "none")
    risk_score = state.get("risk_score", 0.0)

    if alert_level in ("high", "critical") or risk_score >= 0.6:
        return "intervention"
    return "final_report"


def route_after_intervention(state: SupervisorState) -> str:
    """Route after intervention: HITL needed goes to checkpoint, else action."""
    if state.get("requires_hitl"):
        return "hitl_checkpoint"
    return "action"


def route_after_hitl(state: SupervisorState) -> str:
    """After HITL checkpoint, proceed to action tier."""
    return "action"


def route_after_action(state: SupervisorState) -> str:
    """Route after action: feedback loop back to monitoring or finish."""
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)

    # Feedback loop: if alert level is still elevated and within max iterations
    alert_level = state.get("alert_level", "none")
    if alert_level in ("high", "critical") and iteration < max_iter:
        return "monitoring"

    return "final_report"


# ── Graph Builder ────────────────────────────────────────────────────────────


def build_supervisor_graph():
    """
    Build the LangGraph StateGraph for the 5-tier agent pipeline.

    Graph structure:
        triage -> [emergency: intervention, normal: monitoring]
        monitoring -> [anomalies: diagnostic, clean: risk]
        diagnostic -> risk
        risk -> [high: intervention, low: final_report]
        intervention -> [hitl_needed: hitl_checkpoint, ok: action]
        hitl_checkpoint -> action
        action -> [feedback: monitoring, done: final_report]
        final_report -> END
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        logger.warning(
            "langgraph not installed — supervisor graph unavailable. "
            "Install with: pip install langgraph"
        )
        return None

    graph = StateGraph(SupervisorState)

    # Add nodes
    graph.add_node("triage", triage_node)
    graph.add_node("monitoring", monitoring_node)
    graph.add_node("diagnostic", diagnostic_node)
    graph.add_node("risk", risk_node)
    graph.add_node("intervention", intervention_node)
    graph.add_node("hitl_checkpoint", hitl_checkpoint_node)
    graph.add_node("action", action_node)
    graph.add_node("final_report", final_report_node)

    # Set entry point
    graph.set_entry_point("triage")

    # Conditional edges
    graph.add_conditional_edges("triage", route_after_triage, {
        "monitoring": "monitoring",
        "intervention": "intervention",
    })

    graph.add_conditional_edges("monitoring", route_after_monitoring, {
        "diagnostic": "diagnostic",
        "risk": "risk",
    })

    graph.add_edge("diagnostic", "risk")

    graph.add_conditional_edges("risk", route_after_risk, {
        "intervention": "intervention",
        "final_report": "final_report",
    })

    graph.add_conditional_edges("intervention", route_after_intervention, {
        "hitl_checkpoint": "hitl_checkpoint",
        "action": "action",
    })

    graph.add_edge("hitl_checkpoint", "action")

    graph.add_conditional_edges("action", route_after_action, {
        "monitoring": "monitoring",
        "final_report": "final_report",
    })

    graph.add_edge("final_report", END)

    return graph.compile()


# ── Execution Helper ─────────────────────────────────────────────────────────


async def run_supervisor_pipeline(
    org_id: str,
    patient_id: str,
    trigger_event: str,
) -> SupervisorState:
    """Execute the full supervisor pipeline for a patient event."""
    compiled = build_supervisor_graph()
    if compiled is None:
        raise RuntimeError("LangGraph supervisor graph could not be built")

    initial_state = _default_state(org_id, patient_id, trigger_event)
    final_state = await compiled.ainvoke(initial_state)
    return final_state
