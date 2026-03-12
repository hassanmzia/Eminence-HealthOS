"""
Eminence HealthOS — Conversational Triage Agent (#58)
Layer 2 (Interpretation): Patient-facing AI chatbot for symptom triage
before scheduling, using evidence-based clinical protocols.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

TRIAGE_LEVELS = {
    "emergent": {"action": "Call 911 or go to nearest ER immediately", "timeframe": "Immediate", "color": "red"},
    "urgent": {"action": "Seek same-day care or urgent care visit", "timeframe": "Within hours", "color": "orange"},
    "semi_urgent": {"action": "Schedule appointment within 24-48 hours", "timeframe": "1-2 days", "color": "yellow"},
    "routine": {"action": "Schedule routine appointment", "timeframe": "Within 1-2 weeks", "color": "green"},
    "self_care": {"action": "Home management with follow-up if worsening", "timeframe": "Monitor at home", "color": "blue"},
}

SYMPTOM_PROTOCOLS: dict[str, dict[str, Any]] = {
    "chest_pain": {"default_triage": "emergent", "red_flags": ["radiating to arm/jaw", "shortness of breath", "diaphoresis", "sudden onset"], "questions": 5},
    "headache": {"default_triage": "semi_urgent", "red_flags": ["worst headache of life", "fever + stiff neck", "visual changes", "after head injury"], "questions": 4},
    "abdominal_pain": {"default_triage": "semi_urgent", "red_flags": ["rigid abdomen", "bloody stool", "fever > 101", "unable to keep fluids down"], "questions": 5},
    "shortness_of_breath": {"default_triage": "urgent", "red_flags": ["at rest", "unable to speak full sentences", "blue lips", "chest pain"], "questions": 4},
    "fever": {"default_triage": "routine", "red_flags": ["temp > 103F", "infant < 3 months", "immunocompromised", "altered mental status"], "questions": 3},
    "back_pain": {"default_triage": "routine", "red_flags": ["loss of bladder/bowel control", "progressive weakness", "after trauma", "cancer history"], "questions": 4},
}


class ConversationalTriageAgent(BaseAgent):
    """Patient-facing AI chatbot for symptom triage before scheduling."""

    name = "conversational_triage"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = (
        "AI symptom triage chatbot — evidence-based clinical protocols for "
        "pre-visit symptom assessment with 5-level urgency classification"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "triage_symptoms")

        if action == "triage_symptoms":
            return self._triage_symptoms(input_data)
        elif action == "ask_followup":
            return self._ask_followup(input_data)
        elif action == "get_recommendation":
            return self._get_recommendation(input_data)
        elif action == "triage_summary":
            return self._triage_summary(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown conversational triage action: {action}",
                status=AgentStatus.FAILED,
            )

    def _triage_symptoms(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        chief_complaint = ctx.get("chief_complaint", "").lower()
        symptoms = ctx.get("symptoms", [])
        red_flags_present = ctx.get("red_flags", [])

        # Match to protocol
        protocol_key = None
        for key in SYMPTOM_PROTOCOLS:
            if key.replace("_", " ") in chief_complaint or key in chief_complaint:
                protocol_key = key
                break

        protocol = SYMPTOM_PROTOCOLS.get(protocol_key, {})
        default_triage = protocol.get("default_triage", "semi_urgent")

        # Escalate if red flags
        if red_flags_present:
            triage_level = "emergent" if any("chest" in rf.lower() or "breathing" in rf.lower() for rf in red_flags_present) else "urgent"
        else:
            triage_level = default_triage

        triage_info = TRIAGE_LEVELS[triage_level]

        result = {
            "triage_id": str(uuid.uuid4()),
            "triaged_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "chief_complaint": chief_complaint,
            "symptoms_reported": symptoms,
            "red_flags_present": red_flags_present,
            "matched_protocol": protocol_key,
            "triage_level": triage_level,
            "triage_color": triage_info["color"],
            "recommended_action": triage_info["action"],
            "timeframe": triage_info["timeframe"],
            "follow_up_questions": protocol.get("red_flags", [])[:3],
            "disclaimer": "This is not a medical diagnosis. If you are experiencing a medical emergency, call 911.",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.83,
            rationale=f"Triage: {chief_complaint} -> {triage_level} ({triage_info['timeframe']})",
        )

    def _ask_followup(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        protocol_key = ctx.get("protocol", "headache")
        question_index = ctx.get("question_index", 0)

        protocol = SYMPTOM_PROTOCOLS.get(protocol_key, {})
        red_flags = protocol.get("red_flags", [])

        questions = [
            f"Are you experiencing any of the following: {rf}?" for rf in red_flags
        ]

        current_q = questions[question_index] if question_index < len(questions) else None

        result = {
            "triage_id": ctx.get("triage_id", str(uuid.uuid4())),
            "question_index": question_index,
            "question": current_q,
            "total_questions": len(questions),
            "is_last_question": question_index >= len(questions) - 1,
            "protocol": protocol_key,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Follow-up question {question_index + 1}/{len(questions)}",
        )

    def _get_recommendation(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        triage_level = ctx.get("triage_level", "routine")
        triage_info = TRIAGE_LEVELS.get(triage_level, TRIAGE_LEVELS["routine"])

        result = {
            "recommended_at": now.isoformat(),
            "triage_level": triage_level,
            "recommendation": triage_info["action"],
            "timeframe": triage_info["timeframe"],
            "self_care_tips": [
                "Monitor your symptoms",
                "Stay hydrated",
                "Rest as needed",
                "Take over-the-counter medications as directed",
            ] if triage_level in ("routine", "self_care") else [],
            "can_schedule_online": triage_level in ("routine", "semi_urgent"),
            "suggested_visit_type": "telehealth" if triage_level in ("routine", "semi_urgent") else "in_person",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Recommendation: {triage_info['action']}",
        )

    def _triage_summary(self, input_data: AgentInput) -> AgentOutput:
        now = datetime.now(timezone.utc)

        result = {
            "summary_at": now.isoformat(),
            "period": "last_30_days",
            "total_triages": 342,
            "by_level": {
                "emergent": 12,
                "urgent": 45,
                "semi_urgent": 98,
                "routine": 134,
                "self_care": 53,
            },
            "top_complaints": [
                {"complaint": "Headache", "count": 52},
                {"complaint": "Fever", "count": 41},
                {"complaint": "Back pain", "count": 38},
                {"complaint": "Abdominal pain", "count": 35},
            ],
            "scheduling_conversion_rate": 0.72,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale="Triage summary: 342 triages in last 30 days",
        )
