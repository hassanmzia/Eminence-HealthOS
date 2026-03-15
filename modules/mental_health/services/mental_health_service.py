"""Mental Health service layer."""

import logging
from typing import Optional

logger = logging.getLogger("healthos.mental_health.mental_health_service")


class MentalHealthService:
    """Business logic for mental health screening, crisis detection, and engagement."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._screenings: list[dict] = []

    async def score_phq9(self, patient_id: str, responses: list[int]) -> dict:
        total = sum(responses)
        if total <= 4:
            severity = "minimal"
        elif total <= 9:
            severity = "mild"
        elif total <= 14:
            severity = "moderate"
        elif total <= 19:
            severity = "moderately_severe"
        else:
            severity = "severe"

        result = {
            "patient_id": patient_id, "instrument": "PHQ-9",
            "total_score": total, "severity": severity,
            "recommendation": "Consider referral" if total >= 10 else "Monitor",
            "risk_flags": ["suicidal_ideation"] if responses[8] > 0 else [],
        }
        self._screenings.append(result)
        return result

    async def score_gad7(self, patient_id: str, responses: list[int]) -> dict:
        total = sum(responses)
        if total <= 4:
            severity = "minimal"
        elif total <= 9:
            severity = "mild"
        elif total <= 14:
            severity = "moderate"
        else:
            severity = "severe"

        result = {
            "patient_id": patient_id, "instrument": "GAD-7",
            "total_score": total, "severity": severity,
            "recommendation": "Consider treatment" if total >= 10 else "Monitor",
            "risk_flags": [],
        }
        self._screenings.append(result)
        return result

    async def assess_crisis(self, patient_id: str, data: dict) -> dict:
        is_high = data.get("suicidal_ideation") or data.get("self_harm")
        return {
            "patient_id": patient_id,
            "risk_level": "high" if is_high else "low",
            "recommended_action": "Immediate intervention" if is_high else "Routine follow-up",
            "safety_plan_needed": is_high,
            "escalate": is_high,
        }

    async def generate_safety_plan(self, patient_id: str) -> dict:
        return {
            "patient_id": patient_id,
            "warning_signs": ["Increased isolation", "Sleep changes", "Hopelessness"],
            "coping_strategies": ["Deep breathing", "Call a friend", "Go for a walk"],
            "crisis_resources": [
                {"name": "988 Suicide & Crisis Lifeline", "phone": "988"},
                {"name": "Crisis Text Line", "phone": "Text HOME to 741741"},
            ],
        }

    async def get_screening_history(self, patient_id: str) -> list[dict]:
        return [s for s in self._screenings if s.get("patient_id") == patient_id]
