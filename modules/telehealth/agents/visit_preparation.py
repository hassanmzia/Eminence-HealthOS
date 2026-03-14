"""
Eminence HealthOS — Visit Preparation Agent
Layer 3 (Decisioning): Generates pre-visit summaries for providers by
assembling patient history, recent vitals, active conditions, medications,
pending alerts, and prior encounter context into a structured brief.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    PipelineState,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

_NARRATIVE_SYSTEM_PROMPT = (
    "You are a clinical decision support system preparing a provider for an "
    "upcoming patient visit. Generate a concise, actionable pre-visit briefing "
    "from the following patient data."
)


class VisitPreparationAgent(BaseAgent):
    name = "visit_preparation"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Generates pre-visit summaries for providers from patient context"
    min_confidence = 0.75

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        summary = self._build_pre_visit_summary(ctx)

        narrative = await self._generate_provider_narrative(summary)

        result: dict[str, Any] = {"pre_visit_summary": summary}
        if narrative:
            result["provider_narrative"] = narrative

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=self._compute_confidence(summary),
            rationale=self._build_rationale(summary),
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        ctx = state.patient_context or {}
        summary = self._build_pre_visit_summary(ctx)

        narrative = await self._generate_provider_narrative(summary)

        result: dict[str, Any] = {"pre_visit_summary": summary}
        if narrative:
            result["provider_narrative"] = narrative

        state.patient_context["pre_visit_summary"] = summary
        if narrative:
            state.patient_context["provider_narrative"] = narrative
        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result=result,
            confidence=self._compute_confidence(summary),
            rationale=self._build_rationale(summary),
        )
        return state

    def _build_pre_visit_summary(self, ctx: dict[str, Any]) -> dict[str, Any]:
        demographics = ctx.get("demographics", {})
        conditions = ctx.get("conditions", [])
        medications = ctx.get("medications", [])
        allergies = ctx.get("allergies", [])
        recent_vitals = ctx.get("recent_vitals", [])
        risk_assessments = ctx.get("risk_assessments", [])
        active_anomalies = ctx.get("active_anomalies", [])
        encounter_reason = ctx.get("encounter_reason", "")
        chief_complaint = ctx.get("chief_complaint", "")
        symptoms = ctx.get("symptoms", [])

        # Compute key clinical flags
        flags: list[str] = []
        for r in risk_assessments:
            score = r.get("score", 0) if isinstance(r, dict) else 0
            if score >= 0.75:
                flags.append(f"High risk score: {score:.2f}")
        for a in active_anomalies:
            sev = a.get("severity", "") if isinstance(a, dict) else ""
            if sev in ("critical", "high"):
                desc = a.get("description", "Anomaly") if isinstance(a, dict) else "Anomaly"
                flags.append(f"{sev.upper()}: {desc}")

        # Latest vitals snapshot
        vitals_snapshot: dict[str, Any] = {}
        for v in recent_vitals[:10]:
            vtype = v.get("vital_type", "") if isinstance(v, dict) else ""
            if vtype and vtype not in vitals_snapshot:
                vitals_snapshot[vtype] = {
                    "value": v.get("value"),
                    "unit": v.get("unit", ""),
                    "recorded_at": v.get("recorded_at", ""),
                }

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "patient": {
                "name": f"{demographics.get('first_name', '')} {demographics.get('last_name', '')}".strip() or "Unknown",
                "age": demographics.get("age", ""),
                "gender": demographics.get("gender", ""),
            },
            "encounter_reason": encounter_reason or chief_complaint or "Not specified",
            "presenting_symptoms": symptoms,
            "active_conditions": [
                c.get("display", c) if isinstance(c, dict) else str(c)
                for c in conditions
            ],
            "current_medications": [
                f"{m.get('name', m)} {m.get('dosage', '')}" if isinstance(m, dict) else str(m)
                for m in medications
            ],
            "allergies": allergies,
            "latest_vitals": vitals_snapshot,
            "clinical_flags": flags,
            "active_alert_count": len(active_anomalies),
            "risk_summary": {
                "highest_score": max(
                    (r.get("score", 0) if isinstance(r, dict) else 0 for r in risk_assessments),
                    default=0,
                ),
                "risk_level": next(
                    (r.get("risk_level", "low") for r in risk_assessments
                     if isinstance(r, dict) and r.get("score", 0) >= 0.5),
                    "low",
                ),
            },
        }

    async def _generate_provider_narrative(
        self, summary: dict[str, Any]
    ) -> str | None:
        """Use LLM to produce a natural-language pre-visit narrative.

        Returns the narrative string on success or ``None`` if the LLM call
        fails for any reason (network error, timeout, model error, etc.).
        The caller should treat a ``None`` return as a graceful degradation
        and continue with the structured summary alone.
        """
        try:
            patient = summary.get("patient", {})
            prompt_parts: list[str] = [
                "Generate a pre-visit briefing for the following patient:\n",
                f"Patient: {patient.get('name', 'Unknown')}, "
                f"Age: {patient.get('age', 'N/A')}, "
                f"Gender: {patient.get('gender', 'N/A')}",
                f"Encounter reason: {summary.get('encounter_reason', 'N/A')}",
            ]

            if summary.get("presenting_symptoms"):
                prompt_parts.append(
                    f"Presenting symptoms: {', '.join(summary['presenting_symptoms'])}"
                )

            if summary.get("active_conditions"):
                prompt_parts.append(
                    f"Active conditions: {', '.join(summary['active_conditions'])}"
                )

            if summary.get("current_medications"):
                prompt_parts.append(
                    f"Current medications: {', '.join(summary['current_medications'])}"
                )

            if summary.get("allergies"):
                allergies_text = ", ".join(
                    a if isinstance(a, str) else json.dumps(a)
                    for a in summary["allergies"]
                )
                prompt_parts.append(f"Allergies: {allergies_text}")

            if summary.get("latest_vitals"):
                vitals_lines = []
                for vtype, vdata in summary["latest_vitals"].items():
                    vitals_lines.append(
                        f"  {vtype}: {vdata.get('value')} {vdata.get('unit', '')}"
                    )
                prompt_parts.append("Latest vitals:\n" + "\n".join(vitals_lines))

            if summary.get("clinical_flags"):
                prompt_parts.append(
                    f"Clinical flags: {'; '.join(summary['clinical_flags'])}"
                )

            risk = summary.get("risk_summary", {})
            if risk.get("highest_score", 0) > 0:
                prompt_parts.append(
                    f"Risk level: {risk.get('risk_level', 'low')} "
                    f"(highest score: {risk['highest_score']:.2f})"
                )

            prompt = "\n".join(prompt_parts)

            response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=_NARRATIVE_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=2048,
                )
            )
            narrative = response.content.strip() if response and response.content else None
            return narrative or None
        except Exception:
            logger.warning(
                "LLM narrative generation failed; falling back to structured summary only.",
                exc_info=True,
            )
            return None

    @staticmethod
    def _compute_confidence(summary: dict[str, Any]) -> float:
        """Higher confidence when more data is available."""
        scores = []
        scores.append(1.0 if summary.get("patient", {}).get("name", "Unknown") != "Unknown" else 0.3)
        scores.append(1.0 if summary.get("latest_vitals") else 0.3)
        scores.append(1.0 if summary.get("active_conditions") else 0.6)
        scores.append(1.0 if summary.get("current_medications") else 0.6)
        return round(sum(scores) / len(scores), 2)

    @staticmethod
    def _build_rationale(summary: dict[str, Any]) -> str:
        flags = summary.get("clinical_flags", [])
        vitals_count = len(summary.get("latest_vitals", {}))
        cond_count = len(summary.get("active_conditions", []))
        return (
            f"Pre-visit summary: {cond_count} conditions, {vitals_count} vital types, "
            f"{len(flags)} clinical flag(s)"
        )
