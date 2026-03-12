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
    # ── Analytics Events ──────────────────────────────────────────────────
    # Population health analysis
    "analytics.population_health": [
        "population_health",
    ],
    # Risk stratification
    "analytics.risk_stratification": [
        "population_health",
        "cohort_segmentation",
    ],
    # Quality metrics
    "analytics.quality_metrics": [
        "population_health",
    ],
    # Outcome tracking
    "analytics.outcome.track": [
        "outcome_tracker",
    ],
    # Readmission risk prediction
    "analytics.readmission.predict": [
        "readmission_risk",
    ],
    # Batch readmission risk
    "analytics.readmission.batch": [
        "readmission_risk",
    ],
    # Cohort creation & analysis
    "analytics.cohort.create": [
        "cohort_segmentation",
    ],
    # Cost analysis
    "analytics.cost.analyze": [
        "cost_analyzer",
    ],
    # Discharge triggers readmission risk assessment
    "analytics.discharge.assess": [
        "readmission_risk",
        "outcome_tracker",
        "cohort_segmentation",
    ],
    # ── Executive Intelligence Events ─────────────────────────────────────
    # Cost/risk insight analysis
    "analytics.cost_risk.analyze": [
        "cost_risk_insight",
    ],
    # Intervention impact modeling
    "analytics.cost_risk.intervention": [
        "cost_risk_insight",
    ],
    # Executive summary generation
    "analytics.executive.summary": [
        "cost_risk_insight",
        "executive_insight",
    ],
    # KPI scorecard
    "analytics.executive.scorecard": [
        "executive_insight",
    ],
    # Strategic briefing
    "analytics.executive.brief": [
        "executive_insight",
    ],
    # Scheduled analytics pipeline (periodic)
    "analytics.pipeline.scheduled": [
        "population_health",
        "readmission_risk",
        "cost_risk_insight",
        "executive_insight",
    ],
    # ── Ambient AI Documentation Events ───────────────────────────────────
    # Start recording session
    "ambient.session.start": [
        "ambient_listening",
    ],
    # Transcription complete — diarize and generate SOAP
    "ambient.transcription.complete": [
        "speaker_diarization",
        "soap_note_generator",
    ],
    # SOAP note generated — auto-code and submit for attestation
    "ambient.soap.generated": [
        "auto_coding",
        "provider_attestation",
    ],
    # Full ambient documentation pipeline
    "ambient.encounter.complete": [
        "ambient_listening",
        "speaker_diarization",
        "soap_note_generator",
        "auto_coding",
        "provider_attestation",
    ],
    # Provider attestation approved — hand off to RCM
    "ambient.attestation.approved": [
        "charge_capture",
        "claims_optimization",
    ],
    # ── Revenue Cycle Management Events ───────────────────────────────────
    # Charge capture from encounter
    "rcm.charges.capture": [
        "charge_capture",
    ],
    # Pre-submission claim scrub
    "rcm.claim.scrub": [
        "claims_optimization",
    ],
    # Full claim submission pipeline
    "rcm.claim.submit": [
        "revenue_integrity",
        "claims_optimization",
        "charge_capture",
    ],
    # Denial received — analyze and appeal
    "rcm.denial.received": [
        "denial_management",
    ],
    # Payment received — post and reconcile
    "rcm.payment.received": [
        "payment_posting",
    ],
    # ERA/835 reconciliation
    "rcm.era.received": [
        "payment_posting",
    ],
    # Revenue integrity scan
    "rcm.integrity.scan": [
        "revenue_integrity",
    ],
    # End-to-end RCM pipeline (scheduled)
    "rcm.pipeline.scheduled": [
        "revenue_integrity",
        "claims_optimization",
        "denial_management",
        "payment_posting",
    ],
    # ── Pharmacy Events ─────────────────────────────────────────────────
    # New prescription created
    "pharmacy.prescription.create": [
        "drug_interaction",
        "formulary",
        "prescription",
    ],
    # Prescription transmitted to pharmacy
    "pharmacy.prescription.transmit": [
        "prescription",
        "pharmacy_routing",
    ],
    # Drug interaction check
    "pharmacy.interaction.check": [
        "drug_interaction",
    ],
    # Formulary coverage check
    "pharmacy.formulary.check": [
        "formulary",
    ],
    # Refill requested
    "pharmacy.refill.requested": [
        "refill_automation",
        "drug_interaction",
    ],
    # Refill automation (scheduled)
    "pharmacy.refill.scheduled": [
        "refill_automation",
        "medication_adherence",
    ],
    # Adherence monitoring
    "pharmacy.adherence.monitor": [
        "medication_adherence",
    ],
    # Full pharmacy pipeline (new Rx)
    "pharmacy.pipeline.new_rx": [
        "drug_interaction",
        "formulary",
        "prescription",
        "pharmacy_routing",
        "medication_adherence",
    ],
    # ── Labs Events ─────────────────────────────────────────────────────
    # New lab order
    "labs.order.create": [
        "lab_order",
    ],
    # Lab results received
    "labs.results.received": [
        "lab_results",
        "critical_value_alert",
        "lab_trend",
    ],
    # Critical value detected
    "labs.critical.detected": [
        "critical_value_alert",
    ],
    # Lab trend analysis
    "labs.trend.analyze": [
        "lab_trend",
    ],
    # Full lab pipeline (results ingestion)
    "labs.pipeline.ingest": [
        "lab_results",
        "critical_value_alert",
        "lab_trend",
    ],
    # Lab panel suggestion
    "labs.order.suggest": [
        "lab_order",
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
