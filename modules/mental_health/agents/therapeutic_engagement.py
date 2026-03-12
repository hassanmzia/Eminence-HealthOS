"""
Eminence HealthOS — Therapeutic Engagement Agent (#79)
Layer 4 (Action): Manages between-session therapeutic engagement including
mood check-ins, CBT exercises, mindfulness prompts, progress tracking,
and personalized engagement plans.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)


# ── CBT Exercises ────────────────────────────────────────────────────────────

CBT_EXERCISES: dict[str, dict[str, Any]] = {
    "thought_record": {
        "name": "Thought Record",
        "description": "Identify and challenge negative automatic thoughts",
        "target_symptoms": ["depression", "anxiety", "rumination"],
        "difficulty": "beginner",
        "estimated_minutes": 15,
        "instructions": [
            "Describe the situation that triggered your negative feelings",
            "Write down the automatic thought that came to mind",
            "Identify the emotion you felt and rate its intensity (0-100)",
            "List evidence that supports this thought",
            "List evidence that contradicts this thought",
            "Create a balanced alternative thought",
            "Re-rate the intensity of the original emotion (0-100)",
        ],
        "worksheet": {
            "situation": "",
            "automatic_thought": "",
            "emotion": "",
            "emotion_intensity_before": 0,
            "supporting_evidence": "",
            "contradicting_evidence": "",
            "balanced_thought": "",
            "emotion_intensity_after": 0,
        },
    },
    "behavioral_activation": {
        "name": "Behavioral Activation — Activity Scheduling",
        "description": "Schedule pleasurable and mastery activities to combat depression",
        "target_symptoms": ["depression", "low_motivation", "withdrawal"],
        "difficulty": "beginner",
        "estimated_minutes": 10,
        "instructions": [
            "List 3 activities that used to bring you pleasure",
            "List 3 activities that give you a sense of accomplishment",
            "Rate each activity on anticipated pleasure (0-10) and mastery (0-10)",
            "Schedule at least one activity for today or tomorrow",
            "After completing the activity, rate actual pleasure and mastery",
            "Notice any differences between anticipated and actual ratings",
        ],
        "worksheet": {
            "pleasure_activities": [],
            "mastery_activities": [],
            "scheduled_activity": "",
            "scheduled_time": "",
            "anticipated_pleasure": 0,
            "anticipated_mastery": 0,
            "actual_pleasure": 0,
            "actual_mastery": 0,
        },
    },
    "cognitive_restructuring": {
        "name": "Cognitive Restructuring",
        "description": "Identify cognitive distortions and reframe unhelpful thinking patterns",
        "target_symptoms": ["depression", "anxiety", "low_self_esteem"],
        "difficulty": "intermediate",
        "estimated_minutes": 20,
        "instructions": [
            "Write down a negative thought that is bothering you",
            "Identify which cognitive distortion(s) apply (all-or-nothing, catastrophizing, "
            "mind reading, fortune telling, emotional reasoning, labeling, etc.)",
            "Rate how strongly you believe the thought (0-100%)",
            "Ask yourself: What would I tell a friend who had this thought?",
            "Create a more realistic and balanced version of the thought",
            "Rate how strongly you believe the new thought (0-100%)",
            "Re-rate your belief in the original thought (0-100%)",
        ],
        "worksheet": {
            "negative_thought": "",
            "distortions_identified": [],
            "belief_rating_before": 0,
            "friend_advice": "",
            "balanced_thought": "",
            "belief_rating_balanced": 0,
            "belief_rating_original_after": 0,
        },
    },
    "exposure_hierarchy": {
        "name": "Exposure Hierarchy",
        "description": "Gradually face feared situations in a structured way",
        "target_symptoms": ["anxiety", "phobia", "avoidance"],
        "difficulty": "intermediate",
        "estimated_minutes": 15,
        "instructions": [
            "Identify the situation or object you are avoiding",
            "List 8-10 related situations from least to most anxiety-provoking",
            "Rate each situation on a scale of 0-100 (SUDS — Subjective Units of Distress)",
            "Start with the lowest-rated item that still causes some anxiety",
            "Practice staying in the situation until anxiety decreases by at least 50%",
            "Record your peak SUDS and ending SUDS for each exposure",
            "Move to the next item when the current one no longer causes significant distress",
        ],
        "worksheet": {
            "fear_target": "",
            "hierarchy": [],
            "current_step": 0,
            "exposure_log": [],
        },
    },
    "problem_solving": {
        "name": "Structured Problem Solving",
        "description": "Work through problems systematically to reduce overwhelm",
        "target_symptoms": ["anxiety", "stress", "overwhelm", "depression"],
        "difficulty": "beginner",
        "estimated_minutes": 15,
        "instructions": [
            "Define the problem clearly in one or two sentences",
            "Brainstorm at least 5 possible solutions (no judgment yet)",
            "List pros and cons for each potential solution",
            "Rate each solution on feasibility (0-10) and effectiveness (0-10)",
            "Choose the best solution based on your ratings",
            "Create a specific action plan with steps and timeline",
            "After implementing, evaluate the outcome and adjust if needed",
        ],
        "worksheet": {
            "problem_statement": "",
            "solutions": [],
            "chosen_solution": "",
            "action_plan": [],
            "outcome": "",
        },
    },
}


# ── Mindfulness Exercises ────────────────────────────────────────────────────

MINDFULNESS_EXERCISES: dict[str, dict[str, Any]] = {
    "breathing_4_7_8": {
        "name": "4-7-8 Breathing",
        "description": "Calming breath technique to activate the parasympathetic nervous system",
        "target_level": "moderate",
        "estimated_minutes": 5,
        "instructions": [
            "Sit comfortably and close your eyes",
            "Exhale completely through your mouth",
            "Inhale quietly through your nose for 4 seconds",
            "Hold your breath for 7 seconds",
            "Exhale completely through your mouth for 8 seconds",
            "Repeat the cycle 3-4 times",
            "Notice how your body feels after completing the exercise",
        ],
    },
    "box_breathing": {
        "name": "Box Breathing",
        "description": "Equal-ratio breathing technique used to regain calm and focus",
        "target_level": "mild",
        "estimated_minutes": 5,
        "instructions": [
            "Sit upright in a comfortable position",
            "Slowly exhale all air from your lungs",
            "Inhale through your nose for 4 seconds",
            "Hold your breath for 4 seconds",
            "Exhale through your mouth for 4 seconds",
            "Hold the empty breath for 4 seconds",
            "Repeat for 4-5 cycles",
            "Return to normal breathing and notice any changes",
        ],
    },
    "body_scan": {
        "name": "Progressive Body Scan",
        "description": "Systematically notice sensations through the body to reduce tension",
        "target_level": "moderate",
        "estimated_minutes": 15,
        "instructions": [
            "Lie down or sit comfortably — close your eyes",
            "Take 3 deep breaths to settle in",
            "Bring your attention to your feet — notice any sensations",
            "Slowly move your attention up through your legs, hips, abdomen",
            "Continue through your chest, shoulders, arms, and hands",
            "Move to your neck, jaw, face, and top of your head",
            "If you notice tension, breathe into that area and release",
            "After scanning your whole body, take a moment to notice how you feel overall",
        ],
    },
    "progressive_muscle_relaxation": {
        "name": "Progressive Muscle Relaxation",
        "description": "Tense and release muscle groups to reduce physical tension and anxiety",
        "target_level": "high",
        "estimated_minutes": 15,
        "instructions": [
            "Find a quiet, comfortable place to sit or lie down",
            "Starting with your feet, tense the muscles as tightly as you can for 5 seconds",
            "Release the tension suddenly and notice the feeling of relaxation for 10 seconds",
            "Move to your calves and repeat: tense for 5 seconds, release for 10",
            "Continue through each muscle group: thighs, abdomen, chest, hands, arms, "
            "shoulders, neck, face",
            "After completing all muscle groups, lie still and enjoy the relaxation",
            "Take 3 deep breaths before opening your eyes",
        ],
    },
    "grounding_5_4_3_2_1": {
        "name": "5-4-3-2-1 Grounding",
        "description": "Sensory grounding technique for acute anxiety or dissociation",
        "target_level": "high",
        "estimated_minutes": 5,
        "instructions": [
            "Pause and take a slow, deep breath",
            "Name 5 things you can SEE around you",
            "Name 4 things you can TOUCH or feel",
            "Name 3 things you can HEAR",
            "Name 2 things you can SMELL",
            "Name 1 thing you can TASTE",
            "Take another deep breath and notice how you feel",
            "Repeat if needed until you feel more grounded",
        ],
    },
}

# Map anxiety/stress levels to exercise selection
ANXIETY_LEVEL_MAP: dict[str, list[str]] = {
    "mild": ["box_breathing", "body_scan"],
    "moderate": ["breathing_4_7_8", "body_scan", "box_breathing"],
    "high": ["grounding_5_4_3_2_1", "progressive_muscle_relaxation", "breathing_4_7_8"],
    "severe": ["grounding_5_4_3_2_1", "progressive_muscle_relaxation"],
}


class TherapeuticEngagementAgent(BaseAgent):
    """Manages between-session check-ins, CBT exercises, mood tracking, and engagement."""

    name = "therapeutic_engagement"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Provides between-session therapeutic engagement including structured mood "
        "check-ins, evidence-based CBT exercises, contextual mindfulness prompts, "
        "progress summaries, and personalized engagement plans"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "mood_check_in")

        if action == "mood_check_in":
            return self._mood_check_in(input_data)
        elif action == "cbt_exercise":
            return self._cbt_exercise(input_data)
        elif action == "mindfulness_prompt":
            return self._mindfulness_prompt(input_data)
        elif action == "progress_summary":
            return self._progress_summary(input_data)
        elif action == "engagement_plan":
            return self._engagement_plan(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown engagement action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Mood Check-in ────────────────────────────────────────────────────────

    def _mood_check_in(self, input_data: AgentInput) -> AgentOutput:
        """Generate structured mood check-in and provide personalized response."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        mood_score = ctx.get("mood_score")  # 1-10
        sleep_quality = ctx.get("sleep_quality")  # 1-10
        energy_level = ctx.get("energy_level")  # 1-10
        anxiety_level = ctx.get("anxiety_level")  # 1-10
        free_text = ctx.get("free_text", "")

        # If no data provided, return the check-in template
        if mood_score is None:
            result = {
                "type": "check_in_template",
                "patient_id": patient_id,
                "questions": [
                    {"id": "mood_score", "question": "How would you rate your mood today?", "scale": "1-10", "anchors": {"1": "Very low", "10": "Excellent"}},
                    {"id": "sleep_quality", "question": "How well did you sleep last night?", "scale": "1-10", "anchors": {"1": "Very poorly", "10": "Excellent"}},
                    {"id": "energy_level", "question": "What is your energy level right now?", "scale": "1-10", "anchors": {"1": "No energy", "10": "Very energized"}},
                    {"id": "anxiety_level", "question": "How anxious or stressed do you feel?", "scale": "1-10", "anchors": {"1": "Not at all", "10": "Extremely"}},
                    {"id": "free_text", "question": "Is there anything else you would like to share?", "type": "text", "optional": True},
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            return self.build_output(
                trace_id=input_data.trace_id,
                result=result,
                confidence=0.90,
                rationale=f"Generated mood check-in template for patient {patient_id}",
            )

        # Process the check-in response
        mood_score = max(1, min(10, int(mood_score)))
        sleep_quality = max(1, min(10, int(sleep_quality or 5)))
        energy_level = max(1, min(10, int(energy_level or 5)))
        anxiety_level = max(1, min(10, int(anxiety_level or 5)))

        # Generate personalized response
        response_message = self._generate_mood_response(
            mood_score, sleep_quality, energy_level, anxiety_level
        )

        # Identify concerns
        concerns: list[dict[str, Any]] = []
        if mood_score <= 3:
            concerns.append({
                "type": "low_mood",
                "severity": "high" if mood_score == 1 else "moderate",
                "message": "Patient reporting very low mood",
            })
        if sleep_quality <= 3:
            concerns.append({
                "type": "poor_sleep",
                "severity": "moderate",
                "message": "Patient reporting poor sleep quality",
            })
        if anxiety_level >= 8:
            concerns.append({
                "type": "high_anxiety",
                "severity": "high" if anxiety_level >= 9 else "moderate",
                "message": "Patient reporting high anxiety levels",
            })
        if energy_level <= 2:
            concerns.append({
                "type": "very_low_energy",
                "severity": "moderate",
                "message": "Patient reporting very low energy",
            })

        # Suggest exercises based on check-in
        suggestions: list[str] = []
        if anxiety_level >= 7:
            suggestions.append("mindfulness_prompt")
        if mood_score <= 4:
            suggestions.append("behavioral_activation")
        if mood_score <= 3 or anxiety_level >= 8:
            suggestions.append("thought_record")

        result = {
            "patient_id": patient_id,
            "check_in": {
                "mood_score": mood_score,
                "sleep_quality": sleep_quality,
                "energy_level": energy_level,
                "anxiety_level": anxiety_level,
                "free_text": free_text,
            },
            "response_message": response_message,
            "concerns": concerns,
            "suggested_exercises": suggestions,
            "requires_provider_attention": any(c["severity"] == "high" for c in concerns),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=(
                f"Mood check-in for patient {patient_id}: "
                f"mood={mood_score}, sleep={sleep_quality}, energy={energy_level}, "
                f"anxiety={anxiety_level}. {len(concerns)} concern(s) identified."
            ),
        )

    # ── CBT Exercise ─────────────────────────────────────────────────────────

    def _cbt_exercise(self, input_data: AgentInput) -> AgentOutput:
        """Select and deliver an appropriate CBT exercise based on current symptoms."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        target_symptom = ctx.get("target_symptom", "depression")
        preferred_exercise = ctx.get("preferred_exercise")
        difficulty = ctx.get("difficulty", "beginner")
        completed_exercises = ctx.get("completed_exercises", [])

        # Select exercise
        if preferred_exercise and preferred_exercise in CBT_EXERCISES:
            exercise_key = preferred_exercise
        else:
            # Match based on target symptom and difficulty
            matching = []
            for key, ex in CBT_EXERCISES.items():
                if target_symptom in ex["target_symptoms"]:
                    if ex["difficulty"] == difficulty or difficulty == "any":
                        matching.append(key)
                    else:
                        matching.append(key)  # include anyway, prefer symptom match

            # Prefer exercises not recently completed
            not_recent = [k for k in matching if k not in completed_exercises]
            candidates = not_recent if not_recent else matching

            if not candidates:
                candidates = list(CBT_EXERCISES.keys())

            exercise_key = candidates[0]

        exercise = CBT_EXERCISES[exercise_key]

        result = {
            "patient_id": patient_id,
            "exercise_key": exercise_key,
            "exercise": {
                "name": exercise["name"],
                "description": exercise["description"],
                "target_symptoms": exercise["target_symptoms"],
                "difficulty": exercise["difficulty"],
                "estimated_minutes": exercise["estimated_minutes"],
                "instructions": exercise["instructions"],
                "worksheet": exercise["worksheet"],
            },
            "target_symptom": target_symptom,
            "tracking": {
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "completed": False,
                "completion_time": None,
                "patient_rating": None,
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=(
                f"Selected CBT exercise '{exercise['name']}' for patient {patient_id} "
                f"targeting {target_symptom} (difficulty: {exercise['difficulty']}, "
                f"~{exercise['estimated_minutes']} min)"
            ),
        )

    # ── Mindfulness Prompt ───────────────────────────────────────────────────

    def _mindfulness_prompt(self, input_data: AgentInput) -> AgentOutput:
        """Generate a contextual mindfulness exercise based on anxiety/stress level."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        anxiety_level = ctx.get("anxiety_level", 5)
        stress_level = ctx.get("stress_level", anxiety_level)
        preferred_type = ctx.get("preferred_type")

        # Determine level category
        effective_level = max(anxiety_level, stress_level)
        if effective_level >= 8:
            level_category = "severe"
        elif effective_level >= 6:
            level_category = "high"
        elif effective_level >= 4:
            level_category = "moderate"
        else:
            level_category = "mild"

        # Select exercise
        if preferred_type and preferred_type in MINDFULNESS_EXERCISES:
            exercise_key = preferred_type
        else:
            candidates = ANXIETY_LEVEL_MAP.get(level_category, ["box_breathing"])
            exercise_key = candidates[0]

        exercise = MINDFULNESS_EXERCISES[exercise_key]

        result = {
            "patient_id": patient_id,
            "exercise_key": exercise_key,
            "exercise": {
                "name": exercise["name"],
                "description": exercise["description"],
                "estimated_minutes": exercise["estimated_minutes"],
                "instructions": exercise["instructions"],
            },
            "selected_for_level": level_category,
            "anxiety_level": anxiety_level,
            "stress_level": stress_level,
            "tracking": {
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "completed": False,
                "pre_exercise_rating": effective_level,
                "post_exercise_rating": None,
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=(
                f"Selected mindfulness exercise '{exercise['name']}' for patient {patient_id} "
                f"at {level_category} anxiety/stress level ({effective_level}/10)"
            ),
        )

    # ── Progress Summary ─────────────────────────────────────────────────────

    def _progress_summary(self, input_data: AgentInput) -> AgentOutput:
        """Aggregate mood trends, exercise completion, and screening changes over a period."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        period_days = ctx.get("period_days", 30)
        mood_entries = ctx.get("mood_entries", [])
        exercises_assigned = ctx.get("exercises_assigned", 0)
        exercises_completed = ctx.get("exercises_completed", 0)
        sessions_scheduled = ctx.get("sessions_scheduled", 0)
        sessions_attended = ctx.get("sessions_attended", 0)
        screening_scores = ctx.get("screening_scores", {})

        # Compute mood trends
        mood_trend = self._compute_trend(mood_entries, "mood_score")
        sleep_trend = self._compute_trend(mood_entries, "sleep_quality")
        anxiety_trend = self._compute_trend(mood_entries, "anxiety_level")
        energy_trend = self._compute_trend(mood_entries, "energy_level")

        # Exercise completion rate
        exercise_completion_rate = (
            round(exercises_completed / exercises_assigned, 2)
            if exercises_assigned > 0 else 0.0
        )

        # Session attendance rate
        session_attendance_rate = (
            round(sessions_attended / sessions_scheduled, 2)
            if sessions_scheduled > 0 else 0.0
        )

        # Screening score changes
        score_changes: dict[str, dict[str, Any]] = {}
        for instrument, scores in screening_scores.items():
            if isinstance(scores, dict) and "start" in scores and "end" in scores:
                change = scores["end"] - scores["start"]
                score_changes[instrument] = {
                    "start_score": scores["start"],
                    "end_score": scores["end"],
                    "change": change,
                    "direction": "improved" if change < 0 else ("worsened" if change > 0 else "stable"),
                }

        # Overall engagement assessment
        engagement_level = "high"
        if exercise_completion_rate < 0.3 or session_attendance_rate < 0.5:
            engagement_level = "low"
        elif exercise_completion_rate < 0.6 or session_attendance_rate < 0.75:
            engagement_level = "moderate"

        result = {
            "patient_id": patient_id,
            "period_days": period_days,
            "trends": {
                "mood": mood_trend,
                "sleep": sleep_trend,
                "anxiety": anxiety_trend,
                "energy": energy_trend,
            },
            "exercise_stats": {
                "assigned": exercises_assigned,
                "completed": exercises_completed,
                "completion_rate": exercise_completion_rate,
            },
            "session_stats": {
                "scheduled": sessions_scheduled,
                "attended": sessions_attended,
                "attendance_rate": session_attendance_rate,
            },
            "screening_score_changes": score_changes,
            "engagement_level": engagement_level,
            "summary_generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=(
                f"Progress summary for patient {patient_id} over {period_days} days: "
                f"engagement = {engagement_level}, "
                f"exercise completion = {exercise_completion_rate:.0%}, "
                f"session attendance = {session_attendance_rate:.0%}. "
                f"Mood trend: {mood_trend.get('direction', 'insufficient_data')}."
            ),
        )

    # ── Engagement Plan ──────────────────────────────────────────────────────

    def _engagement_plan(self, input_data: AgentInput) -> AgentOutput:
        """Create a personalized engagement schedule for between-session activities."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        condition_types = ctx.get("condition_types", ["depression"])
        session_frequency = ctx.get("session_frequency", "weekly")
        patient_preferences = ctx.get("patient_preferences", {})
        current_engagement_level = ctx.get("current_engagement_level", "moderate")

        # Daily check-in schedule
        check_in_time = patient_preferences.get("preferred_check_in_time", "09:00")
        check_in_frequency = "daily"

        # Select exercises based on conditions
        recommended_exercises: list[dict[str, Any]] = []
        for condition in condition_types:
            for key, exercise in CBT_EXERCISES.items():
                if condition in exercise["target_symptoms"]:
                    recommended_exercises.append({
                        "exercise_key": key,
                        "name": exercise["name"],
                        "frequency": "2x_weekly" if current_engagement_level == "low" else "3x_weekly",
                        "target_condition": condition,
                        "estimated_minutes": exercise["estimated_minutes"],
                    })

        # Deduplicate by exercise key
        seen_keys: set[str] = set()
        unique_exercises: list[dict[str, Any]] = []
        for ex in recommended_exercises:
            if ex["exercise_key"] not in seen_keys:
                seen_keys.add(ex["exercise_key"])
                unique_exercises.append(ex)

        # Mindfulness schedule
        mindfulness_schedule = {
            "frequency": "daily",
            "preferred_time": patient_preferences.get("preferred_mindfulness_time", "evening"),
            "exercise_rotation": list(MINDFULNESS_EXERCISES.keys()),
        }

        # Session reminders
        reminder_schedule = {
            "session_reminder_24h": True,
            "session_reminder_1h": True,
            "pre_session_checklist_24h": True,
            "post_session_reflection_prompt": True,
        }

        # Milestone rewards
        milestones = [
            {"target": "7_day_streak", "description": "Complete 7 consecutive daily check-ins", "reward": "Unlock advanced exercises"},
            {"target": "10_exercises", "description": "Complete 10 CBT exercises", "reward": "Progress badge"},
            {"target": "30_day_engagement", "description": "Maintain engagement for 30 days", "reward": "Provider progress note"},
            {"target": "score_improvement", "description": "Screening score improvement of 5+ points", "reward": "Clinical milestone acknowledgment"},
        ]

        result = {
            "patient_id": patient_id,
            "plan": {
                "daily_check_in": {
                    "enabled": True,
                    "frequency": check_in_frequency,
                    "time": check_in_time,
                },
                "cbt_exercises": unique_exercises,
                "mindfulness": mindfulness_schedule,
                "session_reminders": reminder_schedule,
                "milestones": milestones,
            },
            "conditions_addressed": condition_types,
            "session_frequency": session_frequency,
            "engagement_level_target": (
                "moderate" if current_engagement_level == "low" else "high"
            ),
            "plan_created_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=(
                f"Created engagement plan for patient {patient_id}: "
                f"daily check-ins, {len(unique_exercises)} CBT exercise(s), "
                f"daily mindfulness, {len(milestones)} milestone(s). "
                f"Targeting {condition_types}."
            ),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_mood_response(
        mood: int, sleep: int, energy: int, anxiety: int
    ) -> str:
        """Generate a personalized response message based on mood check-in data."""
        parts = []

        if mood <= 3:
            parts.append(
                "Thank you for sharing that you are having a difficult time. "
                "It takes courage to check in when things feel hard."
            )
        elif mood <= 5:
            parts.append(
                "Thank you for checking in. It sounds like today is a mixed day."
            )
        elif mood <= 7:
            parts.append(
                "Good to hear from you. It sounds like things are going reasonably well today."
            )
        else:
            parts.append(
                "Great to hear you are doing well today. Keep up the positive momentum."
            )

        if sleep <= 3:
            parts.append(
                "Poor sleep can significantly affect how we feel. "
                "Consider trying a relaxation exercise before bed tonight."
            )
        if anxiety >= 7:
            parts.append(
                "Your anxiety level is elevated. A grounding or breathing exercise "
                "might help bring it down."
            )
        if energy <= 3:
            parts.append(
                "Low energy can make everything feel harder. Even a short walk or "
                "gentle stretching can help boost your energy."
            )

        if mood <= 2:
            parts.append(
                "If you are having thoughts of hurting yourself, please reach out to "
                "the 988 Suicide & Crisis Lifeline by calling or texting 988."
            )

        return " ".join(parts)

    @staticmethod
    def _compute_trend(
        entries: list[dict[str, Any]], field: str
    ) -> dict[str, Any]:
        """Compute a simple trend from a list of entries."""
        values = [e.get(field) for e in entries if e.get(field) is not None]
        if len(values) < 2:
            return {
                "direction": "insufficient_data",
                "data_points": len(values),
                "average": round(sum(values) / len(values), 1) if values else None,
            }

        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        change = avg_second - avg_first

        if field == "anxiety_level":
            # For anxiety, decreasing is improvement
            direction = "improved" if change < -0.5 else ("worsened" if change > 0.5 else "stable")
        else:
            # For mood, sleep, energy — increasing is improvement
            direction = "improved" if change > 0.5 else ("worsened" if change < -0.5 else "stable")

        return {
            "direction": direction,
            "data_points": len(values),
            "average": round(sum(values) / len(values), 1),
            "first_half_avg": round(avg_first, 1),
            "second_half_avg": round(avg_second, 1),
            "change": round(change, 1),
        }
