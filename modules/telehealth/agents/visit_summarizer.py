"""
Eminence HealthOS — Visit Summarizer Agent
Layer 4 (Action): Generates structured visit documentation — SOAP notes,
visit summaries, and after-visit summaries (AVS) from telehealth session
data, agent outputs, and clinical context.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger(__name__)

# Symptom → body system mapping for ROS grouping
SYMPTOM_SYSTEMS: dict[str, str] = {
    "headache": "neurological", "chest_pain": "cardiovascular",
    "shortness_of_breath": "respiratory", "cough": "respiratory",
    "fever": "systemic", "fatigue": "systemic",
    "nausea": "gastrointestinal", "abdominal_pain": "gastrointestinal",
    "dizziness": "neurological", "palpitations": "cardiovascular",
    "joint_pain": "musculoskeletal", "rash": "dermatological",
}


class VisitSummarizerAgent(BaseAgent):
    name = "visit_summarizer"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Generates SOAP notes and visit summaries from telehealth sessions"
    requires_hitl = True  # Provider must review/sign documentation

    async def process(self, input_data: AgentInput) -> AgentOutput:
        data = input_data.context
        prior_outputs = data.get("prior_outputs", [])

        symptoms: list[str] = data.get("symptoms", [])
        vitals: dict[str, Any] = data.get("vitals", {})
        assessment: str = data.get("assessment", "")
        plan: list[str] = data.get("plan", [])
        medications: list[str] = data.get("medications", [])
        session_data: dict[str, Any] = data.get("session", {})

        soap = self._generate_soap(symptoms, vitals, assessment, plan, prior_outputs)
        avs = self._generate_avs(symptoms, plan, medications)

        # ── LLM: generate visit summary narrative ─────────────────────
        visit_summary_narrative: str | None = None
        try:
            prompt = (
                f"Symptoms: {', '.join(symptoms) or 'none reported'}.\n"
                f"Vital signs: {vitals or 'not recorded'}.\n"
                f"Assessment: {assessment or 'pending'}.\n"
                f"Plan: {'; '.join(plan) or 'pending'}.\n"
                f"Medications: {', '.join(medications) or 'none'}.\n"
                f"Prior agent findings: {len(prior_outputs)} output(s).\n\n"
                "Write a concise clinical narrative summarizing this telehealth encounter. "
                "Include chief complaint, key findings, clinical impression, and plan of care."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a medical documentation assistant in a telehealth platform. "
                    "Produce a clear, professional visit summary narrative suitable for "
                    "the patient's medical record. Use standard clinical documentation style."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            visit_summary_narrative = resp.content
        except Exception:
            logger.warning("LLM unavailable for visit summary narrative; continuing without it.")

        result: dict[str, Any] = {
            "soap_note": soap,
            "after_visit_summary": avs,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session_data.get("session_id"),
        }
        if visit_summary_narrative:
            result["visit_summary_narrative"] = visit_summary_narrative

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.80,
            rationale=f"Generated SOAP note and AVS for visit with {len(symptoms)} presenting symptoms",
        )

    def _generate_soap(
        self,
        symptoms: list[str],
        vitals: dict[str, Any],
        assessment: str,
        plan: list[str],
        prior_outputs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "subjective": {
                "chief_complaint": symptoms[0] if symptoms else "Not specified",
                "hpi": f"Patient presents with: {', '.join(symptoms)}" if symptoms else "No symptoms reported",
                "review_of_systems": self._group_symptoms_by_system(symptoms),
            },
            "objective": {
                "vital_signs": vitals,
                "agent_findings": [
                    {
                        "agent": o.get("agent", "unknown"),
                        "finding": o.get("decision", ""),
                        "confidence": o.get("confidence", 0),
                    }
                    for o in prior_outputs
                    if isinstance(o, dict) and o.get("decision")
                ],
            },
            "assessment": {
                "clinical_impression": assessment or "Pending provider assessment",
                "differential": [],
            },
            "plan": {
                "items": plan or ["Pending provider plan"],
                "follow_up": "As clinically indicated",
            },
        }

    @staticmethod
    def _generate_avs(
        symptoms: list[str],
        plan: list[str],
        medications: list[str],
    ) -> dict[str, Any]:
        return {
            "visit_reason": ", ".join(symptoms[:3]) if symptoms else "Follow-up visit",
            "what_we_discussed": (
                f"We discussed your symptoms ({', '.join(symptoms[:3])})"
                if symptoms else "General health review"
            ),
            "your_plan": plan or ["Follow up as scheduled"],
            "medications": [
                {"name": m, "instructions": "Take as directed"} for m in medications
            ],
            "when_to_seek_care": [
                "Symptoms worsen significantly",
                "New concerning symptoms develop",
                "Fever above 101\u00b0F (38.3\u00b0C)",
            ],
            "follow_up": "Please schedule a follow-up as recommended by your provider",
        }

    @staticmethod
    def _group_symptoms_by_system(symptoms: list[str]) -> dict[str, list[str]]:
        system_map: dict[str, list[str]] = {}
        for s in symptoms:
            key = s.lower().replace(" ", "_")
            system = SYMPTOM_SYSTEMS.get(key, "general")
            system_map.setdefault(system, []).append(s)
        return system_map
