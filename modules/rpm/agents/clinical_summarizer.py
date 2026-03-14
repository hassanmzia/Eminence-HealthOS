"""
Clinical Summary Agent — Tier 2 (Diagnostic).

Generates AI-powered clinical summaries from patient data, agent outputs,
and encounter history. Supports different summary types for providers
and patients. Uses LLM for natural-language narrative generation with
graceful fallback to rule-based bullet-point summaries.
"""

import json
import logging
from datetime import datetime, timezone

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.clinical_summarizer")

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_PROVIDER_SYSTEM_PROMPT = (
    "You are a clinical documentation assistant embedded in a remote patient "
    "monitoring platform. Generate a structured, provider-facing clinical "
    "summary from the data provided. Use concise medical language. Organize "
    "the summary into clearly labeled sections: Active Alerts, Risk "
    "Assessment, Active Conditions, Current Medications, and Latest Vitals. "
    "Omit any section for which no data is available. Highlight clinically "
    "significant findings."
)

_PATIENT_SYSTEM_PROMPT = (
    "You are a friendly health assistant. Generate a plain-language health "
    "summary that a patient can easily understand. Avoid medical jargon — "
    "when medical terms are necessary, include a brief parenthetical "
    "explanation. Use an encouraging, supportive tone. Organize the summary "
    "into sections: Your Health Summary, Your Vital Signs, and Your "
    "Medications. Omit any section for which no data is available."
)

_HANDOFF_SYSTEM_PROMPT = (
    "You are a clinical documentation assistant. Generate a clinical handoff "
    "document (SBAR-style) suitable for care-team transitions. Include a "
    "brief Situation overview with counts of active alerts, conditions, and "
    "medications, followed by Background (conditions, medications), "
    "Assessment (vitals, risk level, alerts), and Recommendation sections. "
    "Be concise and precise. Use standard medical terminology."
)


class ClinicalSummarizerAgent(HealthOSAgent):
    """Generates structured clinical summaries from multi-source data."""

    def __init__(self):
        super().__init__(
            name="clinical_summarizer",
            tier=AgentTier.DIAGNOSTIC,
            description="Generates clinical summaries for providers and patients",
            version="0.2.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CLINICAL_SUMMARY]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])
        summary_type = data.get("summary_type", "provider")  # provider, patient, handoff

        # Collect data from various sources
        vitals = data.get("vitals", {})
        conditions = data.get("conditions", [])
        medications = data.get("medications", [])
        alerts = [
            o
            for o in prior_outputs
            if isinstance(o, dict) and "alert" in o.get("decision", "")
        ]
        risk_info = next(
            (
                o
                for o in prior_outputs
                if isinstance(o, dict) and o.get("agent") == "risk_scorer"
            ),
            {},
        )

        # Attempt LLM-powered summary; fall back to rule-based on failure
        try:
            summary = await self._llm_summary(
                summary_type, vitals, conditions, medications, alerts, risk_info,
            )
            generation_method = "llm"
        except Exception:
            logger.warning(
                "LLM summary generation failed — falling back to rule-based summary",
                exc_info=True,
            )
            summary = self._rule_based_summary(
                summary_type, vitals, conditions, medications, alerts, risk_info,
            )
            generation_method = "rule_based"

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="summary_generated",
            rationale=(
                f"Generated {summary_type} summary with "
                f"{len(summary['sections'])} sections ({generation_method})"
            ),
            confidence=0.90 if generation_method == "llm" else 0.80,
            data={
                "summary_type": summary_type,
                "summary": summary,
                "generation_method": generation_method,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            feature_contributions=[
                {"feature": "data_sources", "contribution": 0.4, "value": len(prior_outputs)},
                {"feature": "conditions", "contribution": 0.3, "value": len(conditions)},
                {"feature": "alerts", "contribution": 0.3, "value": len(alerts)},
            ],
        )

    # ------------------------------------------------------------------
    # LLM-powered summaries
    # ------------------------------------------------------------------

    async def _llm_summary(
        self,
        summary_type: str,
        vitals: dict,
        conditions: list,
        medications: list,
        alerts: list,
        risk_info: dict,
    ) -> dict:
        if summary_type == "provider":
            return await self._llm_provider_summary(
                vitals, conditions, medications, alerts, risk_info,
            )
        elif summary_type == "patient":
            return await self._llm_patient_summary(vitals, conditions, medications)
        else:
            return await self._llm_handoff_summary(
                vitals, conditions, medications, alerts, risk_info,
            )

    async def _llm_provider_summary(
        self, vitals, conditions, medications, alerts, risk_info,
    ) -> dict:
        prompt = self._build_data_block(vitals, conditions, medications, alerts, risk_info)
        prompt += (
            "\n\nGenerate a structured provider-facing clinical summary from "
            "the data above. Use labeled sections."
        )
        narrative = await self._call_llm(prompt, _PROVIDER_SYSTEM_PROMPT)
        return {
            "sections": self._narrative_to_sections(narrative),
            "narrative": narrative,
            "type": "provider",
        }

    async def _llm_patient_summary(self, vitals, conditions, medications) -> dict:
        prompt = self._build_data_block(vitals, conditions, medications)
        prompt += (
            "\n\nGenerate a friendly, plain-language health summary for the "
            "patient based on the data above."
        )
        narrative = await self._call_llm(prompt, _PATIENT_SYSTEM_PROMPT)
        return {
            "sections": self._narrative_to_sections(narrative),
            "narrative": narrative,
            "type": "patient",
        }

    async def _llm_handoff_summary(
        self, vitals, conditions, medications, alerts, risk_info,
    ) -> dict:
        prompt = self._build_data_block(vitals, conditions, medications, alerts, risk_info)
        prompt += (
            "\n\nGenerate a clinical handoff document (SBAR-style) from the "
            "data above. Include Situation, Background, Assessment, and "
            "Recommendation sections."
        )
        narrative = await self._call_llm(prompt, _HANDOFF_SYSTEM_PROMPT)
        return {
            "sections": self._narrative_to_sections(narrative),
            "narrative": narrative,
            "type": "handoff",
        }

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _call_llm(prompt: str, system: str) -> str:
        """Send a request to the LLM router and return the response text."""
        response = await llm_router.complete(
            LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=system,
                temperature=0.3,
                max_tokens=2048,
            ),
        )
        return response.content

    @staticmethod
    def _build_data_block(
        vitals: dict,
        conditions: list,
        medications: list,
        alerts: list | None = None,
        risk_info: dict | None = None,
    ) -> str:
        """Serialise the clinical data into a text block for the LLM prompt."""
        parts: list[str] = []

        if vitals:
            filtered = {k: v for k, v in vitals.items() if not k.startswith("_")}
            parts.append(f"Vitals:\n{json.dumps(filtered, indent=2)}")

        if conditions:
            parts.append("Active Conditions:\n" + "\n".join(f"- {c}" for c in conditions))

        if medications:
            parts.append("Current Medications:\n" + "\n".join(f"- {m}" for m in medications))

        if alerts:
            alert_lines = []
            for a in alerts:
                severity = a.get("data", {}).get("severity", "UNKNOWN")
                rationale = a.get("rationale", "")
                alert_lines.append(f"- [{severity}] {rationale}")
            parts.append("Active Alerts:\n" + "\n".join(alert_lines))

        if risk_info:
            risk_data = risk_info.get("data", {})
            parts.append(
                "Risk Assessment:\n"
                f"  Risk Level: {risk_data.get('risk_level', 'Unknown')}\n"
                f"  NEWS2 Score: {risk_data.get('news2_score', 'N/A')}"
            )

        return "\n\n".join(parts) if parts else "No clinical data available."

    @staticmethod
    def _narrative_to_sections(narrative: str) -> list[dict]:
        """Parse an LLM narrative into a list of {title, content} sections.

        Splits on lines that look like Markdown headings (## or **Title**) or
        all-caps labels followed by a colon. Falls back to a single section if
        no headings are detected.
        """
        import re

        sections: list[dict] = []
        current_title: str | None = None
        current_lines: list[str] = []

        for line in narrative.splitlines():
            stripped = line.strip()
            # Detect section headings
            heading_match = re.match(
                r"^(?:#{1,3}\s+(.+)|(?:\*\*(.+?)\*\*)\s*:?|([A-Z][A-Z /&]+):)\s*$",
                stripped,
            )
            if heading_match:
                # Save previous section
                if current_title is not None and current_lines:
                    sections.append({"title": current_title, "content": current_lines})
                current_title = (
                    heading_match.group(1)
                    or heading_match.group(2)
                    or heading_match.group(3).title()
                )
                current_lines = []
            elif stripped:
                current_lines.append(stripped)

        # Append final section
        if current_title is not None and current_lines:
            sections.append({"title": current_title, "content": current_lines})

        # Fallback: if no headings were detected, wrap entire text as one section
        if not sections:
            sections.append({
                "title": "Summary",
                "content": [l.strip() for l in narrative.splitlines() if l.strip()],
            })

        return sections

    # ------------------------------------------------------------------
    # Rule-based fallback (original implementation)
    # ------------------------------------------------------------------

    def _rule_based_summary(
        self,
        summary_type: str,
        vitals: dict,
        conditions: list,
        medications: list,
        alerts: list,
        risk_info: dict,
    ) -> dict:
        if summary_type == "provider":
            return self._provider_summary(vitals, conditions, medications, alerts, risk_info)
        elif summary_type == "patient":
            return self._patient_summary(vitals, conditions, medications)
        else:
            return self._handoff_summary(vitals, conditions, medications, alerts, risk_info)

    def _provider_summary(self, vitals, conditions, medications, alerts, risk_info) -> dict:
        sections = []

        if alerts:
            sections.append({
                "title": "Active Alerts",
                "content": [
                    f"- [{a.get('data', {}).get('severity', 'UNKNOWN')}] {a.get('rationale', '')}"
                    for a in alerts
                ],
            })

        if risk_info:
            risk_data = risk_info.get("data", {})
            sections.append({
                "title": "Risk Assessment",
                "content": [
                    f"Risk Level: {risk_data.get('risk_level', 'Unknown')}",
                    f"NEWS2 Score: {risk_data.get('news2_score', 'N/A')}",
                ],
            })

        if conditions:
            sections.append({
                "title": "Active Conditions",
                "content": [f"- {c}" for c in conditions],
            })

        if medications:
            sections.append({
                "title": "Current Medications",
                "content": [f"- {m}" for m in medications],
            })

        if vitals:
            sections.append({
                "title": "Latest Vitals",
                "content": [
                    f"- {k}: {v}"
                    for k, v in vitals.items()
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
                    f"- {k}: {v}"
                    for k, v in vitals.items()
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
