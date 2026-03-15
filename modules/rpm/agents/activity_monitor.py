"""
Activity Monitor Agent — Tier 1 (Monitoring).

Analyzes physical activity data including steps, exercise minutes, and
sedentary time. Detects prolonged inactivity and provides personalized
coaching recommendations per AHA 2024 guidelines.

Adapted from InHealth activity_agent (Tier 1 Monitoring).
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

logger = logging.getLogger("healthos.agent.activity_monitor")

# LOINC codes
LOINC_STEPS = "55423-8"
LOINC_SEDENTARY_MINUTES = "82291-6"
LOINC_EXERCISE_MINUTES = "55411-3"

# Targets (AHA 2024)
DAILY_STEPS_TARGET = 7500
MODERATE_EXERCISE_TARGET_MIN = 150  # per week
SEDENTARY_ALERT_HOURS = 4


class ActivityMonitorAgent(HealthOSAgent):
    """Physical activity monitoring and coaching."""

    def __init__(self) -> None:
        super().__init__(
            name="activity_monitor",
            tier=AgentTier.MONITORING,
            description=(
                "Monitors physical activity (steps, exercise, sedentary time), "
                "detects prolonged inactivity, and provides coaching (AHA 2024)"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.VITAL_MONITORING, AgentCapability.PATIENT_COMMUNICATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        today_steps: float = data.get("today_steps", 0)
        steps_7d: list[float] = data.get("steps_7d", [])
        sedentary_minutes_today: float = data.get("sedentary_minutes_today", 0)
        weekly_exercise_min: float = data.get("weekly_exercise_minutes", 0)
        patient_conditions: list[str] = data.get("conditions", [])

        avg_steps = sum(steps_7d) / len(steps_7d) if steps_7d else today_steps
        step_achievement_pct = (today_steps / DAILY_STEPS_TARGET * 100) if DAILY_STEPS_TARGET > 0 else 0

        alerts: list[dict[str, Any]] = []
        severity = "LOW"

        # Prolonged inactivity
        if sedentary_minutes_today >= SEDENTARY_ALERT_HOURS * 60:
            severity = "MEDIUM"
            alerts.append({
                "severity": "MEDIUM",
                "message": (
                    f"Prolonged inactivity: {sedentary_minutes_today:.0f} minutes sedentary today. "
                    "Recommend movement break."
                ),
            })

        # Low weekly exercise
        if weekly_exercise_min < MODERATE_EXERCISE_TARGET_MIN:
            alerts.append({
                "severity": "LOW",
                "message": (
                    f"Below AHA physical activity target: {weekly_exercise_min:.0f} min/week "
                    f"(target: {MODERATE_EXERCISE_TARGET_MIN} min/week)."
                ),
            })

        # LLM coaching
        coaching_message = None
        try:
            prompt = (
                f"Physical activity data (7-day summary):\n"
                f"  Today's steps: {today_steps:.0f} (target: {DAILY_STEPS_TARGET})\n"
                f"  7-day average steps: {avg_steps:.0f}\n"
                f"  Step goal achievement: {step_achievement_pct:.1f}%\n"
                f"  Today's sedentary time: {sedentary_minutes_today:.0f} minutes\n"
                f"  Weekly exercise minutes: {weekly_exercise_min:.0f} (AHA target: {MODERATE_EXERCISE_TARGET_MIN})\n"
                f"  Patient conditions: {patient_conditions}\n\n"
                "Provide:\n"
                "1. Personalized, encouraging activity coaching message\n"
                "2. Specific, achievable activity goals for this week\n"
                "3. Safety considerations given chronic conditions\n"
                "4. Gamification suggestion (badge or achievement)"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical activity coach. Be encouraging and specific. "
                    "Adapt recommendations to the patient's chronic conditions. "
                    "Reference AHA physical activity guidelines (2024)."
                ),
                temperature=0.4,
                max_tokens=768,
            ))
            coaching_message = resp.content
        except Exception:
            logger.warning("LLM activity coaching failed; using fallback")
            coaching_message = self._default_coaching(today_steps, weekly_exercise_min)

        rationale_parts = [f"Steps: {today_steps:.0f}/{DAILY_STEPS_TARGET}"]
        if weekly_exercise_min < MODERATE_EXERCISE_TARGET_MIN:
            rationale_parts.append(f"Exercise: {weekly_exercise_min:.0f}/{MODERATE_EXERCISE_TARGET_MIN} min/wk")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="activity_assessment",
            rationale="; ".join(rationale_parts),
            confidence=0.85,
            data={
                "severity": severity,
                "today_steps": today_steps,
                "avg_daily_steps_7d": round(avg_steps, 0),
                "step_goal_percent": round(step_achievement_pct, 1),
                "sedentary_minutes_today": sedentary_minutes_today,
                "weekly_exercise_minutes": weekly_exercise_min,
                "aha_exercise_target_met": weekly_exercise_min >= MODERATE_EXERCISE_TARGET_MIN,
                "coaching_message": coaching_message,
                "alerts": alerts,
                "recommendations": [
                    "Aim for 7,500+ steps daily (AHA 2024 - 40-53% lower CVD mortality).",
                    "150+ minutes moderate aerobic exercise per week reduces HbA1c by ~0.7%.",
                    "Break sitting time every 30 minutes with 2-3 minutes of light movement.",
                    "Resistance training 2x/week improves insulin sensitivity by 25-30%.",
                ],
            },
            requires_hitl=False,
        )

    def _default_coaching(self, steps: float, exercise_min: float) -> str:
        if steps >= DAILY_STEPS_TARGET:
            return f"Great job! You've reached your daily step goal of {DAILY_STEPS_TARGET:,} steps. Keep it up!"
        deficit = DAILY_STEPS_TARGET - steps
        return (
            f"You're {deficit:,.0f} steps away from your daily goal. "
            f"A short 10-minute walk adds ~1,000 steps. You can do this!"
        )
