"""
Eminence HealthOS — Visit Preparation Agent
Layer 3 (Decisioning): Generates pre-visit summaries for providers by
assembling patient history, recent vitals, active conditions, medications,
pending alerts, and prior encounter context into a structured brief.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    PipelineState,
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

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"pre_visit_summary": summary},
            confidence=self._compute_confidence(summary),
            rationale=self._build_rationale(summary),
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        ctx = state.patient_context or {}
        summary = self._build_pre_visit_summary(ctx)

        state.patient_context["pre_visit_summary"] = summary
        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result={"pre_visit_summary": summary},
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
