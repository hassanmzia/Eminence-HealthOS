"""
Eminence HealthOS — Event-to-Agent Router
Routes incoming events to the appropriate agent pipeline based on event type.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.types import AgentTier

logger = structlog.get_logger()


# Event type → ordered list of agents to invoke
ROUTING_TABLE: dict[str, list[str]] = {
    # RPM vital sign events
    "vitals.ingested": [
        "device_ingestion",
        "vitals_normalization",
        "anomaly_detection",
        "risk_scoring",
        "trend_analysis",
        "adherence_monitoring",
    ],
    # Single vital anomaly detected
    "anomaly.detected": [
        "risk_scoring",
        "trend_analysis",
    ],
    # Risk threshold crossed
    "risk.elevated": [
        "context_assembly",
        "policy_rules",
    ],
    # Alert generated, needs action
    "alert.generated": [
        "context_assembly",
        "policy_rules",
    ],
    # Scheduled patient check
    "patient.scheduled_check": [
        "context_assembly",
        "trend_analysis",
        "risk_scoring",
        "adherence_monitoring",
    ],
    # ── Telehealth Events ──────────────────────────────────────────────────
    # Pre-visit preparation
    "telehealth.visit.prepare": [
        "context_assembly",
        "visit_preparation",
        "medication_review",
    ],
    # Visit started
    "telehealth.visit.started": [
        "context_assembly",
        "symptom_checker",
        "visit_preparation",
    ],
    # Visit completed — documentation workflow
    "telehealth.visit.completed": [
        "clinical_note",
        "visit_summarizer",
        "follow_up_plan",
        "scheduling",
        "patient_communication",
    ],
    # Escalation needed
    "telehealth.escalation": [
        "context_assembly",
        "policy_rules",
        "escalation_routing",
    ],
    # Symptom check (pre-visit)
    "telehealth.symptom_check": [
        "symptom_checker",
    ],
    # ── Operations Events ──────────────────────────────────────────────────
    # Prior authorization evaluation
    "operations.prior_auth.evaluate": [
        "context_assembly",
        "insurance_verification",
        "prior_authorization",
    ],
    # Prior auth submission
    "operations.prior_auth.submit": [
        "prior_authorization",
        "task_orchestration",
    ],
    # Insurance verification
    "operations.insurance.verify": [
        "insurance_verification",
    ],
    # Referral creation
    "operations.referral.create": [
        "insurance_verification",
        "referral_coordination",
        "task_orchestration",
    ],
    # Task / workflow management
    "operations.workflow.create": [
        "task_orchestration",
    ],
    # SLA monitoring
    "operations.sla.check": [
        "task_orchestration",
    ],
    # ── Billing Events ─────────────────────────────────────────────────────
    # Encounter billing validation
    "billing.encounter.validate": [
        "billing_readiness",
    ],
    # Claim preparation
    "billing.claim.prepare": [
        "insurance_verification",
        "billing_readiness",
    ],
    # Post-encounter billing workflow
    "billing.post_encounter": [
        "billing_readiness",
        "prior_authorization",
        "task_orchestration",
    ],
}


class EventRouter:
    """
    Routes events to the correct agent pipeline.
    Uses a static routing table augmented with dynamic rules.
    """

    def __init__(self) -> None:
        self._custom_routes: dict[str, list[str]] = {}

    def resolve(self, event_type: str) -> list[str]:
        """
        Resolve an event type to an ordered list of agent names.
        Custom routes take priority over the static routing table.
        """
        # Check custom routes first
        if event_type in self._custom_routes:
            return self._custom_routes[event_type]

        # Fall back to static routing table
        agents = ROUTING_TABLE.get(event_type, [])

        if not agents:
            logger.warning("router.no_route", event_type=event_type)

        return agents

    def add_route(self, event_type: str, agent_names: list[str]) -> None:
        """Add a custom route for a specific event type."""
        self._custom_routes[event_type] = agent_names
        logger.info("router.custom_route_added", event_type=event_type, agents=agent_names)

    def list_routes(self) -> dict[str, list[str]]:
        """Return all active routes."""
        routes = dict(ROUTING_TABLE)
        routes.update(self._custom_routes)
        return routes
