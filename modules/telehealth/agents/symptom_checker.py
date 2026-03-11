"""
Symptom Checker Agent — AI-powered pre-visit symptom assessment.

Guides patients through symptom collection before telehealth visits,
generating structured chief complaints and preliminary assessments
for provider review.
"""

import logging
from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.symptom_checker")

# Symptom → body system mapping
SYMPTOM_SYSTEMS = {
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


class SymptomCheckerAgent(HealthOSAgent):
    """Pre-visit symptom assessment with urgency classification."""

    def __init__(self):
        super().__init__(
            name="symptom_checker",
            tier=AgentTier.DIAGNOSTIC,
            description="AI-powered symptom assessment for pre-visit triage",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.TRIAGE, AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        symptoms = data.get("symptoms", [])
        duration = data.get("duration", "unknown")
        severity_rating = data.get("severity_rating", 5)  # 1-10 patient-reported
        additional_notes = data.get("additional_notes", "")

        if not symptoms:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_symptoms",
                rationale="No symptoms reported",
                confidence=1.0,
            )

        # Check for red flags
        red_flags_found = [s for s in symptoms if s.lower().replace(" ", "_") in RED_FLAGS]

        # Classify body systems
        systems_affected = set()
        for s in symptoms:
            key = s.lower().replace(" ", "_")
            if key in SYMPTOM_SYSTEMS:
                systems_affected.add(SYMPTOM_SYSTEMS[key])

        # Determine urgency
        urgency = self._determine_urgency(red_flags_found, severity_rating, len(symptoms))

        # Generate structured assessment
        assessment = {
            "chief_complaint": symptoms[0] if symptoms else "unspecified",
            "symptoms": symptoms,
            "duration": duration,
            "patient_severity_rating": severity_rating,
            "systems_affected": list(systems_affected),
            "red_flags": red_flags_found,
            "urgency": urgency,
            "recommended_visit_type": self._recommend_visit_type(urgency),
        }

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=f"assessment_{urgency}",
            rationale=f"Symptom assessment: {len(symptoms)} symptom(s) across {len(systems_affected)} system(s). "
                      f"Urgency: {urgency}. Red flags: {len(red_flags_found)}.",
            confidence=0.75,
            data=assessment,
            feature_contributions=[
                {"feature": "red_flags", "contribution": 0.4, "value": len(red_flags_found)},
                {"feature": "severity_rating", "contribution": 0.3, "value": severity_rating},
                {"feature": "symptom_count", "contribution": 0.2, "value": len(symptoms)},
                {"feature": "duration", "contribution": 0.1, "value": duration},
            ],
            requires_hitl=urgency == "emergency",
            safety_flags=[f"red_flag_{rf}" for rf in red_flags_found],
            risk_level=urgency,
            downstream_agents=["triage_agent"] if urgency in ("emergency", "urgent") else [],
        )

    def _determine_urgency(self, red_flags: list, severity: int, symptom_count: int) -> str:
        if red_flags:
            return "emergency"
        if severity >= 8:
            return "urgent"
        if severity >= 6 or symptom_count >= 4:
            return "same_day"
        return "routine"

    def _recommend_visit_type(self, urgency: str) -> str:
        return {
            "emergency": "emergency_department",
            "urgent": "urgent_telehealth",
            "same_day": "same_day_telehealth",
            "routine": "scheduled_telehealth",
        }.get(urgency, "scheduled_telehealth")
