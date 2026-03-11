"""
Eminence HealthOS — Symptom Checker Agent
Layer 2 (Interpretation): AI-powered pre-visit symptom assessment.
Guides patients through symptom collection, detects red flags, and
generates structured chief complaints for provider review.
"""

from __future__ import annotations

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

# Symptom → body system mapping
SYMPTOM_SYSTEMS: dict[str, str] = {
    "headache": "neurological",
    "chest_pain": "cardiovascular",
    "shortness_of_breath": "respiratory",
    "cough": "respiratory",
    "fever": "systemic",
    "fatigue": "systemic",
    "nausea": "gastrointestinal",
    "abdominal_pain": "gastrointestinal",
    "dizziness": "neurological",
    "palpitations": "cardiovascular",
    "joint_pain": "musculoskeletal",
    "rash": "dermatological",
    "sore_throat": "ent",
    "back_pain": "musculoskeletal",
    "anxiety": "psychiatric",
    "insomnia": "psychiatric",
    "urinary_frequency": "genitourinary",
    "blurred_vision": "ophthalmological",
}

# Red flag symptoms requiring urgent evaluation
RED_FLAGS = {
    "chest_pain", "shortness_of_breath", "sudden_severe_headache",
    "loss_of_consciousness", "severe_bleeding", "seizure",
    "sudden_weakness", "slurred_speech", "suicidal_ideation",
}


class SymptomCheckerAgent(BaseAgent):
    name = "symptom_checker"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Pre-visit symptom assessment with urgency classification and red-flag detection"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        data = input_data.context
        symptoms: list[str] = data.get("symptoms", [])
        duration = data.get("duration", "unknown")
        severity_rating = data.get("severity_rating", 5)

        if not symptoms:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"assessment": "no_symptoms"},
                confidence=1.0,
                rationale="No symptoms reported",
            )

        # Check for red flags
        red_flags_found = [
            s for s in symptoms if s.lower().replace(" ", "_") in RED_FLAGS
        ]

        # Classify body systems
        systems_affected: set[str] = set()
        for s in symptoms:
            key = s.lower().replace(" ", "_")
            if key in SYMPTOM_SYSTEMS:
                systems_affected.add(SYMPTOM_SYSTEMS[key])

        # Determine urgency
        urgency = self._determine_urgency(red_flags_found, severity_rating, len(symptoms))

        assessment = {
            "chief_complaint": symptoms[0] if symptoms else "unspecified",
            "symptoms": symptoms,
            "duration": duration,
            "patient_severity_rating": severity_rating,
            "systems_affected": sorted(systems_affected),
            "red_flags": red_flags_found,
            "urgency": urgency,
            "recommended_visit_type": self._recommend_visit_type(urgency),
        }

        is_emergency = urgency == "emergency"

        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            status=AgentStatus.WAITING_HITL if is_emergency else AgentStatus.COMPLETED,
            confidence=0.75,
            result=assessment,
            rationale=(
                f"Symptom assessment: {len(symptoms)} symptom(s) across "
                f"{len(systems_affected)} system(s). Urgency: {urgency}. "
                f"Red flags: {len(red_flags_found)}."
            ),
            requires_hitl=is_emergency,
            hitl_reason="Emergency red flags detected — immediate provider review required" if is_emergency else None,
        )

    @staticmethod
    def _determine_urgency(red_flags: list, severity: int, symptom_count: int) -> str:
        if red_flags:
            return "emergency"
        if severity >= 8:
            return "urgent"
        if severity >= 6 or symptom_count >= 4:
            return "same_day"
        return "routine"

    @staticmethod
    def _recommend_visit_type(urgency: str) -> str:
        return {
            "emergency": "emergency_department",
            "urgent": "urgent_telehealth",
            "same_day": "same_day_telehealth",
            "routine": "scheduled_telehealth",
        }.get(urgency, "scheduled_telehealth")
