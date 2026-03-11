"""
Visit Summarizer Agent — generates structured visit documentation.

Creates SOAP notes, visit summaries, and after-visit summaries (AVS)
from telehealth session data, agent outputs, and clinical context.
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

logger = logging.getLogger("healthos.agent.visit_summarizer")


class VisitSummarizerAgent(HealthOSAgent):
    """Generates structured visit documentation from telehealth sessions."""

    def __init__(self):
        super().__init__(
            name="visit_summarizer",
            tier=AgentTier.DIAGNOSTIC,
            description="Generates SOAP notes and visit summaries from telehealth sessions",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])

        session_data = data.get("session", {})
        symptoms = data.get("symptoms", [])
        vitals = data.get("vitals", {})
        assessment = data.get("assessment", "")
        plan = data.get("plan", [])
        medications = data.get("medications", [])

        # Generate SOAP note
        soap = self._generate_soap(symptoms, vitals, assessment, plan, prior_outputs)

        # Generate after-visit summary for patient
        avs = self._generate_avs(symptoms, plan, medications)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="visit_documented",
            rationale=f"Generated SOAP note and AVS for visit with {len(symptoms)} presenting symptoms",
            confidence=0.80,
            data={
                "soap_note": soap,
                "after_visit_summary": avs,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "session_id": session_data.get("session_id"),
            },
            feature_contributions=[
                {"feature": "symptoms", "contribution": 0.3, "value": len(symptoms)},
                {"feature": "vitals", "contribution": 0.2, "value": len(vitals)},
                {"feature": "assessment", "contribution": 0.3, "value": bool(assessment)},
                {"feature": "plan", "contribution": 0.2, "value": len(plan)},
            ],
            requires_hitl=True,  # Provider must review/sign documentation
        )

    def _generate_soap(self, symptoms, vitals, assessment, plan, prior_outputs) -> dict:
        # Subjective
        subjective = {
            "chief_complaint": symptoms[0] if symptoms else "Not specified",
            "hpi": f"Patient presents with: {', '.join(symptoms)}" if symptoms else "No symptoms reported",
            "review_of_systems": self._group_symptoms_by_system(symptoms),
        }

        # Objective
        objective = {
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
        }

        # Assessment
        assessment_section = {
            "clinical_impression": assessment or "Pending provider assessment",
            "differential": [],
        }

        # Plan
        plan_section = {
            "items": plan or ["Pending provider plan"],
            "follow_up": "As clinically indicated",
        }

        return {
            "subjective": subjective,
            "objective": objective,
            "assessment": assessment_section,
            "plan": plan_section,
        }

    def _generate_avs(self, symptoms, plan, medications) -> dict:
        return {
            "visit_reason": ", ".join(symptoms[:3]) if symptoms else "Follow-up visit",
            "what_we_discussed": f"We discussed your symptoms ({', '.join(symptoms[:3])})" if symptoms else "General health review",
            "your_plan": plan or ["Follow up as scheduled"],
            "medications": [
                {"name": m, "instructions": "Take as directed"} for m in medications
            ],
            "when_to_seek_care": [
                "Symptoms worsen significantly",
                "New concerning symptoms develop",
                "Fever above 101°F (38.3°C)",
            ],
            "follow_up": "Please schedule a follow-up as recommended by your provider",
        }

    def _group_symptoms_by_system(self, symptoms: list) -> dict:
        system_map = {}
        for s in symptoms:
            key = s.lower().replace(" ", "_")
            system = SYMPTOM_SYSTEMS.get(key, "general")
            system_map.setdefault(system, []).append(s)
        return system_map


# Import for the system mapping
SYMPTOM_SYSTEMS = {
    "headache": "neurological", "chest_pain": "cardiovascular",
    "shortness_of_breath": "respiratory", "cough": "respiratory",
    "fever": "systemic", "fatigue": "systemic",
    "nausea": "gastrointestinal", "abdominal_pain": "gastrointestinal",
    "dizziness": "neurological", "palpitations": "cardiovascular",
    "joint_pain": "musculoskeletal", "rash": "dermatological",
}
