"""
Clinical Summary Agent — Tier 2 (Diagnostic).

Generates AI-powered clinical summaries from patient data, agent outputs,
and encounter history. Supports different summary types for providers
and patients.
"""

import logging
from datetime import datetime, timezone

from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.clinical_summarizer")


class ClinicalSummarizerAgent(HealthOSAgent):
    """Generates structured clinical summaries from multi-source data."""

    def __init__(self):
        super().__init__(
            name="clinical_summarizer",
            tier=AgentTier.DIAGNOSTIC,
            description="Generates clinical summaries for providers and patients",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])
        summary_type = data.get("summary_type", "provider")  # provider, patient, handoff

        # Collect data from various sources
        vitals = data.get("vitals", {})
        conditions = data.get("conditions", [])
        medications = data.get("medications", [])
        alerts = [o for o in prior_outputs if isinstance(o, dict) and "alert" in o.get("decision", "")]
        risk_info = next(
            (o for o in prior_outputs if isinstance(o, dict) and o.get("agent") == "risk_scorer"),
            {},
        )

        # Generate summary based on type
        if summary_type == "provider":
            summary = self._provider_summary(vitals, conditions, medications, alerts, risk_info)
        elif summary_type == "patient":
            summary = self._patient_summary(vitals, conditions, medications)
        else:
            summary = self._handoff_summary(vitals, conditions, medications, alerts, risk_info)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="summary_generated",
            rationale=f"Generated {summary_type} summary with {len(summary['sections'])} sections",
            confidence=0.80,
            data={
                "summary_type": summary_type,
                "summary": summary,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            feature_contributions=[
                {"feature": "data_sources", "contribution": 0.4, "value": len(prior_outputs)},
                {"feature": "conditions", "contribution": 0.3, "value": len(conditions)},
                {"feature": "alerts", "contribution": 0.3, "value": len(alerts)},
            ],
        )

    def _provider_summary(self, vitals, conditions, medications, alerts, risk_info) -> dict:
        sections = []

        # Active alerts
        if alerts:
            sections.append({
                "title": "Active Alerts",
                "content": [
                    f"- [{a.get('data', {}).get('severity', 'UNKNOWN')}] {a.get('rationale', '')}"
                    for a in alerts
                ],
            })

        # Risk assessment
        if risk_info:
            risk_data = risk_info.get("data", {})
            sections.append({
                "title": "Risk Assessment",
                "content": [
                    f"Risk Level: {risk_data.get('risk_level', 'Unknown')}",
                    f"NEWS2 Score: {risk_data.get('news2_score', 'N/A')}",
                ],
            })

        # Active conditions
        if conditions:
            sections.append({
                "title": "Active Conditions",
                "content": [f"- {c}" for c in conditions],
            })

        # Current medications
        if medications:
            sections.append({
                "title": "Current Medications",
                "content": [f"- {m}" for m in medications],
            })

        # Latest vitals
        if vitals:
            sections.append({
                "title": "Latest Vitals",
                "content": [
                    f"- {k}: {v}" for k, v in vitals.items()
                    if not k.startswith("_")
                ],
            })

        return {"sections": sections, "type": "provider"}

    def _patient_summary(self, vitals, conditions, medications) -> dict:
        sections = []

        sections.append({
            "title": "Your Health Summary",
            "content": ["Here is an overview of your current health status."],
        })

        if vitals:
            sections.append({
                "title": "Your Vital Signs",
                "content": [
                    f"- {k}: {v}" for k, v in vitals.items()
                    if not k.startswith("_")
                ],
            })

        if medications:
            sections.append({
                "title": "Your Medications",
                "content": [f"- {m}" for m in medications],
            })

        return {"sections": sections, "type": "patient"}

    def _handoff_summary(self, vitals, conditions, medications, alerts, risk_info) -> dict:
        summary = self._provider_summary(vitals, conditions, medications, alerts, risk_info)
        summary["type"] = "handoff"
        summary["sections"].insert(0, {
            "title": "Clinical Handoff",
            "content": [
                f"Active Alerts: {len(alerts)}",
                f"Active Conditions: {len(conditions)}",
                f"Current Medications: {len(medications)}",
            ],
        })
        return summary
