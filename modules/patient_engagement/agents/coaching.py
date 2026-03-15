"""
Lifestyle Coaching Agent — Tier 4 (Action / Intervention).

Provides personalized, evidence-based lifestyle recommendations adapted to
the patient's health literacy level, preferred language, and chronic conditions.
Includes gamification badges and motivational coaching.

Adapted from InHealth coaching_agent (Tier 4 Intervention).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.coaching")

# Health literacy levels 1-5 (1=very low, 5=high)
LITERACY_PROMPTS = {
    1: "Use very simple words. Short sentences. One idea at a time.",
    2: "Use simple words. Avoid medical terms. Explain everything in plain language.",
    3: "Use everyday language. Briefly explain medical terms when needed.",
    4: "Use standard medical language with some explanation.",
    5: "Use full clinical/medical language appropriate for a healthcare professional.",
}

# Gamification badges
BADGES = {
    "first_steps": {"name": "First Steps", "description": "Completed your first week of daily step tracking"},
    "glucose_champion": {"name": "Glucose Champion", "description": "3 consecutive days of glucose in target range"},
    "medication_master": {"name": "Medication Master", "description": "7-day perfect medication adherence"},
    "blood_pressure_hero": {"name": "BP Hero", "description": "Blood pressure in target range for 1 week"},
    "activity_star": {"name": "Activity Star", "description": "Reached 7,500 steps daily for 5 days"},
    "hydration_hero": {"name": "Hydration Hero", "description": "Met daily water intake goal for 7 days"},
}


class CoachingAgent(HealthOSAgent):
    """Personalized lifestyle coaching with health literacy adaptation and gamification."""

    def __init__(self) -> None:
        super().__init__(
            name="coaching",
            tier=AgentTier.INTERVENTION,
            description=(
                "Provides personalized lifestyle coaching adapted to health literacy level, "
                "with gamification and motivational interviewing principles"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.PATIENT_COMMUNICATION, AgentCapability.CARE_PLAN_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        health_literacy_level: int = data.get("health_literacy_level", 3)
        preferred_language: str = data.get("preferred_language", "english")
        conditions: list[str] = data.get("conditions", [])
        risk_level: str = data.get("risk_level", "MEDIUM")

        # Monitoring data for context
        glucose_tir: float = data.get("glucose_tir_percent", 0)
        today_steps: float = data.get("today_steps", 0)
        weekly_exercise_min: float = data.get("weekly_exercise_minutes", 0)
        systolic_bp: float = data.get("systolic_bp", 0)
        diastolic_bp: float = data.get("diastolic_bp", 0)

        # Badge eligibility
        earned_badges = self._check_badge_eligibility(data)
        next_badges = self._suggest_next_badges(earned_badges)

        # Language adaptation
        language_instruction = ""
        if preferred_language.lower() == "spanish":
            language_instruction = "Respond entirely in Spanish (Espanol). Use culturally appropriate examples."

        literacy_prompt = LITERACY_PROMPTS.get(health_literacy_level, LITERACY_PROMPTS[3])

        # LLM coaching
        coaching_plan = self._fallback_coaching(health_literacy_level, conditions)
        try:
            prompt = (
                f"Lifestyle coaching request:\n\n"
                f"Patient profile:\n"
                f"  Health literacy level: {health_literacy_level}/5 ({literacy_prompt})\n"
                f"  Preferred language: {preferred_language}\n"
                f"  Active conditions: {conditions}\n"
                f"  Overall risk level: {risk_level}\n\n"
                f"Recent data:\n"
                f"  Glucose TIR: {glucose_tir}%\n"
                f"  Daily steps today: {today_steps}\n"
                f"  Weekly exercise: {weekly_exercise_min} min\n"
                f"  Blood pressure: {systolic_bp}/{diastolic_bp} mmHg\n\n"
                f"Instructions: {language_instruction}\n"
                f"Literacy level instruction: {literacy_prompt}\n\n"
                "Create a personalized coaching plan with:\n"
                "1. 3 specific, achievable lifestyle goals for this week (SMART goals)\n"
                "2. One dietary recommendation with a specific meal example\n"
                "3. Activity recommendation tailored to current fitness level\n"
                "4. Stress management and sleep recommendation\n"
                "5. Motivational closing message (positive, encouraging tone)\n"
                "6. Gamification: celebrate earned badges and describe next achievement"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a lifestyle coaching AI. Be warm, encouraging, and specific. "
                    "Incorporate motivational interviewing principles. "
                    "Reference ADA DPP, AHA Life's Essential 8, and CDC chronic disease prevention."
                ),
                temperature=0.5,
                max_tokens=1024,
            ))
            coaching_plan = resp.content
        except Exception:
            logger.warning("LLM coaching generation failed; using fallback")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="coaching_plan",
            rationale=(
                f"Coaching plan generated for literacy level {health_literacy_level}; "
                f"{len(conditions)} conditions; risk {risk_level}"
            ),
            confidence=0.80,
            data={
                "coaching_plan": coaching_plan,
                "health_literacy_level": health_literacy_level,
                "preferred_language": preferred_language,
                "earned_badges": earned_badges,
                "next_badges": next_badges,
                "recommendations": [
                    "ADA 2024: Mediterranean diet reduces HbA1c by 0.47% and CVD risk by 30%.",
                    "AHA 2024: 150 min/week moderate exercise reduces all-cause mortality by 35%.",
                    "CDC: 5-7% body weight loss reduces T2DM progression by 58% (DPP trial).",
                    "Sleep: 7-9 hours/night. Poor sleep increases insulin resistance by 25%.",
                ],
            },
            requires_hitl=False,
        )

    # -- Gamification logic (preserved from source) --------------------------------

    def _check_badge_eligibility(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        earned: list[dict[str, Any]] = []
        if data.get("glucose_tir_percent", 0) >= 70:
            earned.append(BADGES["glucose_champion"])
        if data.get("today_steps", 0) >= 7500:
            earned.append(BADGES["activity_star"])
        return earned

    def _suggest_next_badges(self, earned: list[dict[str, Any]]) -> list[dict[str, Any]]:
        earned_names = [b["name"] for b in earned]
        suggestions: list[dict[str, Any]] = []
        for badge in BADGES.values():
            if badge["name"] not in earned_names:
                suggestions.append(badge)
                if len(suggestions) >= 2:
                    break
        return suggestions

    def _fallback_coaching(self, literacy_level: int, conditions: list[str]) -> str:
        if literacy_level <= 2:
            return (
                "Eat healthy foods. Move your body every day. Take your medicine. "
                "Drink water. Sleep enough. You can do this!"
            )
        return (
            "Today's health goals: (1) Eat a balanced meal with vegetables, lean protein, "
            "and whole grains. (2) Take a 20-minute walk. (3) Take all prescribed medications. "
            "Small steps lead to big improvements in your health!"
        )
