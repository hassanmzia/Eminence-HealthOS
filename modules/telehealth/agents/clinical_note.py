"""
Eminence HealthOS — Clinical Note Agent
Layer 4 (Action): Generates structured clinical documentation from
telehealth encounters. Produces SOAP notes, assessment summaries, and
ICD-10 coding suggestions. Designed for LLM-powered documentation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import json as json_mod

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = structlog.get_logger()

# Common symptom → ICD-10 suggestion mapping
SYMPTOM_ICD10: dict[str, dict[str, str]] = {
    "chest_pain": {"code": "R07.9", "display": "Chest pain, unspecified"},
    "shortness_of_breath": {"code": "R06.00", "display": "Dyspnea, unspecified"},
    "headache": {"code": "R51.9", "display": "Headache, unspecified"},
    "fever": {"code": "R50.9", "display": "Fever, unspecified"},
    "cough": {"code": "R05.9", "display": "Cough, unspecified"},
    "fatigue": {"code": "R53.83", "display": "Other fatigue"},
    "nausea": {"code": "R11.0", "display": "Nausea"},
    "abdominal_pain": {"code": "R10.9", "display": "Unspecified abdominal pain"},
    "dizziness": {"code": "R42", "display": "Dizziness and giddiness"},
    "palpitations": {"code": "R00.2", "display": "Palpitations"},
    "back_pain": {"code": "M54.9", "display": "Dorsalgia, unspecified"},
    "joint_pain": {"code": "M25.50", "display": "Pain in unspecified joint"},
    "anxiety": {"code": "F41.9", "display": "Anxiety disorder, unspecified"},
    "insomnia": {"code": "G47.00", "display": "Insomnia, unspecified"},
    "rash": {"code": "R21", "display": "Rash and other nonspecific skin eruption"},
    "sore_throat": {"code": "J02.9", "display": "Acute pharyngitis, unspecified"},
}


class ClinicalNoteAgent(BaseAgent):
    name = "clinical_note"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "LLM-powered clinical documentation: SOAP notes, assessments, ICD-10 suggestions"
    requires_hitl = True  # Provider must review and sign notes
    min_confidence = 0.7

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context

        symptoms: list[str] = ctx.get("symptoms", [])
        vitals: dict[str, Any] = ctx.get("vitals", {})
        assessment_text: str = ctx.get("assessment", "")
        plan_items: list[str] = ctx.get("plan", [])
        prior_outputs: list[dict[str, Any]] = ctx.get("prior_outputs", [])
        encounter_type: str = ctx.get("encounter_type", "telehealth")
        medications: list[str] = ctx.get("medications", [])

        # Build structured SOAP note (rule-based)
        soap = self._build_soap(symptoms, vitals, assessment_text, plan_items, prior_outputs)

        # Enhance with LLM-generated narrative
        llm_narrative = None
        try:
            prompt = (
                f"Generate a complete clinical SOAP note for a {encounter_type} encounter.\n\n"
                f"Patient symptoms: {', '.join(symptoms) if symptoms else 'None reported'}\n"
                f"Vital signs: {json_mod.dumps(vitals) if vitals else 'Not recorded'}\n"
                f"Current medications: {', '.join(medications) if medications else 'None'}\n"
                f"Provider assessment: {assessment_text or 'Pending'}\n"
                f"Plan items: {', '.join(plan_items) if plan_items else 'Pending'}\n"
                f"AI agent findings: {json_mod.dumps([o.get('rationale', '') for o in prior_outputs if isinstance(o, dict)])}\n\n"
                f"Generate a professional clinical note with Subjective, Objective, Assessment, and Plan sections."
            )
            llm_resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical documentation specialist generating SOAP notes for "
                    "telehealth encounters. Write concise, medically accurate documentation "
                    "suitable for the electronic health record. Use standard medical terminology."
                ),
                temperature=0.3,
                max_tokens=2048,
            ))
            llm_narrative = llm_resp.content
        except Exception as exc:
            logger.warning("clinical_note.llm_failed", error=str(exc))

        # Suggest ICD-10 codes
        icd_suggestions = self._suggest_icd10(symptoms)

        # Suggest billing codes
        billing = self._suggest_billing(encounter_type, len(symptoms), bool(vitals))

        note = {
            "soap_note": soap,
            "icd10_suggestions": icd_suggestions,
            "billing_suggestions": billing,
            "medications_reviewed": medications,
            "note_status": "draft",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if llm_narrative:
            note["llm_narrative"] = llm_narrative

        confidence = 0.85 if llm_narrative else 0.75

        return self.build_output(
            trace_id=input_data.trace_id,
            result=note,
            confidence=confidence,
            rationale=(
                f"Clinical note generated: {len(symptoms)} symptoms, "
                f"{len(icd_suggestions)} ICD-10 suggestions, "
                f"billing level {billing.get('suggested_level', 'N/A')}"
                f"{' (LLM-enhanced)' if llm_narrative else ''}"
            ),
        )

    def _build_soap(
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
                "history_of_present_illness": (
                    f"Patient reports: {', '.join(symptoms)}." if symptoms else "No acute complaints."
                ),
                "review_of_systems": self._build_ros(symptoms),
            },
            "objective": {
                "vital_signs": vitals,
                "physical_exam": "Telehealth encounter — limited to visual assessment",
                "ai_agent_findings": [
                    {"agent": o.get("agent_name", ""), "finding": o.get("rationale", "")}
                    for o in prior_outputs
                    if isinstance(o, dict)
                ],
            },
            "assessment": {
                "clinical_impression": assessment or "Awaiting provider assessment",
                "differential_diagnoses": [],
            },
            "plan": {
                "treatment": plan or ["Pending provider plan"],
                "follow_up": "As clinically indicated",
                "patient_education": "Provided via after-visit summary",
            },
        }

    @staticmethod
    def _build_ros(symptoms: list[str]) -> dict[str, str]:
        """Build review of systems from symptom list."""
        ros: dict[str, str] = {}
        for s in symptoms:
            key = s.lower().replace(" ", "_")
            from modules.telehealth.agents.symptom_checker import SYMPTOM_SYSTEMS
            system = SYMPTOM_SYSTEMS.get(key, "general")
            ros[system] = ros.get(system, "") + (", " if system in ros else "") + s
        return ros

    @staticmethod
    def _suggest_icd10(symptoms: list[str]) -> list[dict[str, str]]:
        suggestions = []
        for s in symptoms:
            key = s.lower().replace(" ", "_")
            if key in SYMPTOM_ICD10:
                suggestions.append(SYMPTOM_ICD10[key])
        return suggestions

    @staticmethod
    def _suggest_billing(encounter_type: str, symptom_count: int, has_vitals: bool) -> dict[str, str]:
        """Suggest E/M billing level based on encounter complexity."""
        if encounter_type == "telehealth":
            if symptom_count >= 5 or (symptom_count >= 3 and has_vitals):
                return {"code": "99214", "suggested_level": "Moderate", "modifier": "95"}
            elif symptom_count >= 2:
                return {"code": "99213", "suggested_level": "Low", "modifier": "95"}
            else:
                return {"code": "99212", "suggested_level": "Straightforward", "modifier": "95"}
        return {"code": "99213", "suggested_level": "Low", "modifier": ""}
