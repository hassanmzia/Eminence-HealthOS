"""
Eminence HealthOS — Context Assembly Agent
Layer 3 (Decisioning): Assembles comprehensive patient context from the
feature store, recent vitals, anomalies, medications, and conditions for
downstream agents that need a full clinical picture.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    PipelineState,
)

logger = structlog.get_logger()

# Default feature groups to assemble
DEFAULT_FEATURE_GROUPS = [
    "vitals",
    "labs",
    "risk",
    "medications",
    "demographics",
    "utilization",
    "devices",
    "questionnaires",
]

# Maximum recent items to include per category
MAX_RECENT_VITALS = 50
MAX_RECENT_ANOMALIES = 20
MAX_RECENT_RISK_SCORES = 10
MAX_RECENT_QUESTIONNAIRES = 10


class ContextAssemblyAgent(BaseAgent):
    """
    Assembles a comprehensive patient context snapshot for downstream agents.

    Gathers data from:
    - Pipeline state (current vitals, anomalies, risk scores)
    - Feature store (cached patient features)
    - Patient record (demographics, conditions, medications, care team)

    Outputs a unified patient_context dict on the pipeline state.
    """

    name = "context_assembly"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Assembles comprehensive patient context from multiple data sources"
    min_confidence = 0.8

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Assemble context from input data (standalone mode)."""
        context = input_data.context or {}
        assembled = self._assemble_from_dict(context)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"patient_context": assembled},
            confidence=self._compute_completeness(assembled),
            rationale=self._build_rationale(assembled),
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Assemble full patient context into pipeline state."""
        context: dict[str, Any] = {}

        # 1. Demographics & static data from existing patient_context
        existing = state.patient_context or {}
        context["demographics"] = existing.get("demographics", {})
        context["conditions"] = existing.get("conditions", [])
        context["medications"] = existing.get("medications", [])
        context["care_team"] = existing.get("care_team", [])
        context["allergies"] = existing.get("allergies", [])

        # 2. Current vitals from pipeline
        context["recent_vitals"] = [
            {
                "vital_type": v.vital_type.value if hasattr(v.vital_type, "value") else str(v.vital_type),
                "value": v.value,
                "unit": v.unit,
                "recorded_at": v.recorded_at.isoformat() if hasattr(v.recorded_at, "isoformat") else str(v.recorded_at),
                "quality_score": v.quality_score,
                "source": v.source,
            }
            for v in state.normalized_vitals[:MAX_RECENT_VITALS]
        ]

        # 3. Active anomalies from pipeline
        context["active_anomalies"] = [
            {
                "anomaly_type": a.anomaly_type,
                "vital_type": a.vital_type.value if hasattr(a.vital_type, "value") else str(a.vital_type),
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "description": a.description,
                "confidence_score": a.confidence_score,
            }
            for a in state.anomalies[:MAX_RECENT_ANOMALIES]
        ]

        # 4. Risk assessments from pipeline
        context["risk_assessments"] = [
            {
                "score_type": r.score_type,
                "score": r.score,
                "risk_level": r.risk_level.value if hasattr(r.risk_level, "value") else str(r.risk_level),
                "recommendations": r.recommendations,
                "contributing_factors": r.contributing_factors,
            }
            for r in state.risk_assessments[:MAX_RECENT_RISK_SCORES]
        ]

        # 5. Patient-submitted questionnaires (pre-visit, ROS, HPI)
        context["questionnaire_responses"] = existing.get("questionnaire_responses", [])

        # If questionnaire data not already in context, try to extract
        # structured clinical data from submitted questionnaires for agents
        if context["questionnaire_responses"]:
            extracted = self._extract_clinical_from_questionnaires(context["questionnaire_responses"])
            # Populate clinical note fields from questionnaire answers
            if extracted.get("chief_complaint") and not context.get("chief_complaint"):
                context["chief_complaint"] = extracted["chief_complaint"]
            if extracted.get("history_present_illness") and not context.get("history_present_illness"):
                context["history_present_illness"] = extracted["history_present_illness"]
            if extracted.get("review_of_systems") and not context.get("review_of_systems"):
                context["review_of_systems"] = extracted["review_of_systems"]
            if extracted.get("social_history"):
                context.setdefault("social_history", {}).update(extracted["social_history"])
            if extracted.get("patient_reported_symptoms"):
                context["patient_reported_symptoms"] = extracted["patient_reported_symptoms"]

        # 6. Compute summary statistics
        context["summary"] = self._compute_summary(context)

        # 7. Merge assembled context into pipeline state
        state.patient_context = context

        # Track execution
        state.executed_agents.append(self.name)

        completeness = self._compute_completeness(context)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result={"patient_context": context},
            confidence=completeness,
            rationale=self._build_rationale(context),
        )

        return state

    def _assemble_from_dict(self, context: dict[str, Any]) -> dict[str, Any]:
        """Assemble context from raw dict data (standalone mode)."""
        assembled: dict[str, Any] = {
            "demographics": context.get("demographics", {}),
            "conditions": context.get("conditions", []),
            "medications": context.get("medications", []),
            "care_team": context.get("care_team", []),
            "allergies": context.get("allergies", []),
            "recent_vitals": context.get("normalized_vitals", [])[:MAX_RECENT_VITALS],
            "active_anomalies": context.get("anomalies", [])[:MAX_RECENT_ANOMALIES],
            "risk_assessments": context.get("risk_assessments", [])[:MAX_RECENT_RISK_SCORES],
            "questionnaire_responses": context.get("questionnaire_responses", [])[:MAX_RECENT_QUESTIONNAIRES],
        }
        assembled["summary"] = self._compute_summary(assembled)
        return assembled

    def _extract_clinical_from_questionnaires(
        self, questionnaires: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Extract structured clinical data from patient-submitted questionnaires
        (InhealthUSA-style ROS, HPI, pre-visit forms) into fields agents can use.
        """
        extracted: dict[str, Any] = {}
        symptoms: list[str] = []

        for q in questionnaires:
            q_type = q.get("questionnaire_type", "")
            responses = q.get("responses", {})
            if not responses:
                continue

            if q_type == "history_presenting_illness":
                if responses.get("chief_complaint"):
                    extracted["chief_complaint"] = responses["chief_complaint"]
                hpi_parts = []
                for key in ["onset", "location", "duration", "characteristics",
                            "severity", "aggravating_factors", "relieving_factors",
                            "associated_symptoms", "prior_treatments", "context"]:
                    val = responses.get(key)
                    if val:
                        hpi_parts.append(f"{key.replace('_', ' ').title()}: {val}")
                if hpi_parts:
                    extracted["history_present_illness"] = "\n".join(hpi_parts)

            elif q_type == "review_of_systems":
                ros: dict[str, Any] = {}
                for key, val in responses.items():
                    if val is True:
                        # e.g. "cardio_chest_pain" → system="cardio", symptom="chest pain"
                        parts = key.split("_", 1)
                        system = parts[0] if len(parts) > 1 else "general"
                        symptom = parts[1].replace("_", " ") if len(parts) > 1 else key
                        ros.setdefault(system, []).append(symptom)
                        symptoms.append(symptom)
                    elif isinstance(val, str) and val.strip() and key.endswith("_notes"):
                        system = key.rsplit("_notes", 1)[0]
                        ros.setdefault(system, []).append(f"Notes: {val}")
                if ros:
                    extracted["review_of_systems"] = ros

            elif q_type == "pre_visit":
                if responses.get("visit_reason"):
                    extracted.setdefault("chief_complaint", responses["visit_reason"])

                social: dict[str, Any] = {}
                for key in ["smoking_status", "alcohol_use", "exercise", "sleep_quality"]:
                    if responses.get(key):
                        social[key] = responses[key]
                if social:
                    extracted["social_history"] = social

                # Mental health screening (PHQ-2/GAD-2 items)
                mental_items = ["feeling_down", "little_interest", "feeling_nervous", "worry_control"]
                for item in mental_items:
                    if responses.get(item) and responses[item] != "Not at all":
                        symptoms.append(f"{item.replace('_', ' ')}: {responses[item]}")

                if responses.get("pain_level") and responses["pain_level"] not in ("0", ""):
                    symptoms.append(f"pain level {responses['pain_level']}/10")
                if responses.get("current_medications"):
                    extracted.setdefault("patient_reported_medications", responses["current_medications"])

        if symptoms:
            extracted["patient_reported_symptoms"] = symptoms

        return extracted

    def _compute_summary(self, context: dict[str, Any]) -> dict[str, Any]:
        """Compute summary statistics for the assembled context."""
        anomalies = context.get("active_anomalies", [])
        risk_assessments = context.get("risk_assessments", [])

        # Count anomalies by severity
        severity_counts: dict[str, int] = {}
        for a in anomalies:
            sev = a.get("severity", "unknown") if isinstance(a, dict) else "unknown"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # Highest risk score
        max_risk = 0.0
        max_risk_type = "none"
        for r in risk_assessments:
            score = r.get("score", 0.0) if isinstance(r, dict) else 0.0
            if score > max_risk:
                max_risk = score
                max_risk_type = r.get("score_type", "unknown") if isinstance(r, dict) else "unknown"

        return {
            "total_vitals": len(context.get("recent_vitals", [])),
            "total_anomalies": len(anomalies),
            "anomaly_severity_counts": severity_counts,
            "total_conditions": len(context.get("conditions", [])),
            "total_medications": len(context.get("medications", [])),
            "highest_risk_score": round(max_risk, 4),
            "highest_risk_type": max_risk_type,
            "has_care_team": len(context.get("care_team", [])) > 0,
            "total_questionnaires": len(context.get("questionnaire_responses", [])),
            "has_patient_reported_symptoms": len(context.get("patient_reported_symptoms", [])) > 0,
        }

    def _compute_completeness(self, context: dict[str, Any]) -> float:
        """Compute a confidence score based on data completeness."""
        scores = []

        # Demographics present?
        scores.append(1.0 if context.get("demographics") else 0.3)

        # Has recent vitals?
        vitals_count = len(context.get("recent_vitals", []))
        scores.append(min(1.0, vitals_count / 5) if vitals_count > 0 else 0.2)

        # Has conditions list?
        scores.append(1.0 if context.get("conditions") is not None else 0.5)

        # Has medications list?
        scores.append(1.0 if context.get("medications") is not None else 0.5)

        # Has questionnaire data? (boosts completeness)
        questionnaires = context.get("questionnaire_responses", [])
        if questionnaires:
            scores.append(1.0)
        elif context.get("chief_complaint") or context.get("review_of_systems"):
            scores.append(0.7)  # partial — clinical notes but no questionnaire
        else:
            scores.append(0.3)

        return round(sum(scores) / len(scores), 2) if scores else 0.5

    def _build_rationale(self, context: dict[str, Any]) -> str:
        """Build a human-readable rationale for the assembled context."""
        summary = context.get("summary", {})
        parts = [
            f"Assembled patient context with {summary.get('total_vitals', 0)} vitals",
            f"{summary.get('total_anomalies', 0)} anomalies",
            f"{summary.get('total_conditions', 0)} conditions",
            f"{summary.get('total_medications', 0)} medications",
        ]
        if summary.get("highest_risk_score", 0) > 0:
            parts.append(
                f"highest risk {summary['highest_risk_score']:.2f} ({summary.get('highest_risk_type', 'unknown')})"
            )
        q_count = summary.get("total_questionnaires", 0)
        if q_count > 0:
            parts.append(f"{q_count} patient questionnaire(s)")
        return ", ".join(parts)
