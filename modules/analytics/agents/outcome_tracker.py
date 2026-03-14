"""
Eminence HealthOS — Outcome Tracker Agent
Layer 5 (Measurement): Tracks clinical outcomes, treatment effectiveness,
care plan adherence, and generates outcome reports for quality improvement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import json
import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)


class OutcomeTrackerAgent(BaseAgent):
    """Tracks clinical outcomes and treatment effectiveness."""

    name = "outcome_tracker"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Tracks treatment outcomes, adherence, and clinical effectiveness"
    min_confidence = 0.75

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "track")

        if action == "track":
            return await self._track_outcomes(input_data)
        elif action == "adherence":
            return await self._check_adherence(input_data)
        elif action == "effectiveness":
            return await self._assess_effectiveness(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown outcome tracker action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _track_outcomes(self, input_data: AgentInput) -> AgentOutput:
        """Track outcomes for a patient's care plan."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        care_plan = ctx.get("care_plan", {})
        observations = ctx.get("observations", [])

        # Evaluate goal progress
        goals = care_plan.get("goals", [])
        goal_progress = [self._evaluate_goal(g, observations) for g in goals]

        # Calculate adherence
        adherence = self._calculate_adherence(care_plan, observations)

        # Assess overall outcome
        outcome = self._assess_outcome(goal_progress, adherence)

        result = {
            "patient_id": patient_id,
            "outcome_status": outcome["status"],
            "goal_progress": goal_progress,
            "adherence_rate": adherence,
            "outcome_details": outcome,
            "observations_analyzed": len(observations),
            "tracked_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── LLM: generate outcome narrative ──────────────────────────────────
        try:
            prompt = (
                "You are a clinical outcomes analyst. Based on the following patient outcome "
                "tracking data, produce a concise narrative (2-3 paragraphs) explaining "
                "treatment outcomes, goal progress, adherence patterns, and recommendations "
                "for care plan adjustments.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered clinical outcomes analyst for a healthcare platform. "
                    "Provide clear, evidence-based analysis of treatment outcomes and effectiveness."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["outcome_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for track_outcomes; continuing without narrative")
            result["outcome_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82 if goals else 0.65,
            rationale=(
                f"Outcome tracking: {outcome['status']} — "
                f"{len(goal_progress)} goals, adherence {adherence:.0%}"
            ),
        )

    async def _check_adherence(self, input_data: AgentInput) -> AgentOutput:
        """Check care plan adherence for a patient."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        care_plan = ctx.get("care_plan", {})
        observations = ctx.get("observations", [])

        activities = care_plan.get("activities", [])
        adherence = self._calculate_adherence(care_plan, observations)

        activity_details = []
        for a in activities:
            activity_details.append({
                "activity": a.get("name", a.get("description", "")),
                "completed": a.get("completed", False),
                "frequency": a.get("frequency", ""),
            })

        non_adherent = [a for a in activity_details if not a["completed"]]

        result = {
            "patient_id": patient_id,
            "adherence_rate": round(adherence, 3),
            "total_activities": len(activities),
            "completed": sum(1 for a in activities if a.get("completed", False)),
            "activity_details": activity_details,
            "non_adherent_activities": non_adherent,
            "adherence_level": (
                "excellent" if adherence >= 0.9 else
                "good" if adherence >= 0.7 else
                "fair" if adherence >= 0.5 else
                "poor"
            ),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── LLM: generate outcome narrative ──────────────────────────────────
        try:
            prompt = (
                "You are a clinical adherence specialist. Based on the following adherence "
                "data, produce a concise narrative (2-3 paragraphs) explaining adherence "
                "patterns, identifying barriers to compliance, and recommending strategies "
                "to improve adherence.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered clinical outcomes analyst for a healthcare platform. "
                    "Provide clear, evidence-based analysis of treatment outcomes and effectiveness."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["outcome_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for check_adherence; continuing without narrative")
            result["outcome_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Adherence check: {result['adherence_level']} ({adherence:.0%}), {len(non_adherent)} gaps",
        )

    async def _assess_effectiveness(self, input_data: AgentInput) -> AgentOutput:
        """Assess treatment effectiveness across multiple patients."""
        ctx = input_data.context
        treatments = ctx.get("treatments", [])

        assessments = []
        for t in treatments:
            outcomes = t.get("outcomes", [])
            improved = sum(1 for o in outcomes if o.get("improved", False))
            total = len(outcomes)
            rate = improved / max(total, 1)
            assessments.append({
                "treatment": t.get("name", ""),
                "patients": total,
                "improved": improved,
                "effectiveness_rate": round(rate, 3),
                "effective": rate >= 0.6,
            })

        assessments.sort(key=lambda a: a["effectiveness_rate"], reverse=True)

        result = {
            "treatments_analyzed": len(assessments),
            "assessments": assessments,
            "most_effective": assessments[0]["treatment"] if assessments else "none",
            "avg_effectiveness": round(
                sum(a["effectiveness_rate"] for a in assessments) / max(len(assessments), 1), 3
            ),
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── LLM: generate outcome narrative ──────────────────────────────────
        try:
            prompt = (
                "You are a clinical effectiveness researcher. Based on the following "
                "treatment effectiveness data, produce a concise narrative (2-3 paragraphs) "
                "explaining which treatments are most effective, comparative effectiveness "
                "insights, and recommendations for treatment protocol optimization.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered clinical outcomes analyst for a healthcare platform. "
                    "Provide clear, evidence-based analysis of treatment outcomes and effectiveness."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["outcome_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for assess_effectiveness; continuing without narrative")
            result["outcome_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.80,
            rationale=f"Effectiveness assessment: {len(assessments)} treatments, avg rate {result['avg_effectiveness']:.1%}",
        )

    @staticmethod
    def _evaluate_goal(goal: dict, observations: list) -> dict:
        target = goal.get("target_value")
        metric = goal.get("metric")
        description = goal.get("description", "")

        relevant = [o for o in observations if o.get("metric") == metric] if metric else []
        latest = relevant[-1] if relevant else None

        if not target or not latest:
            return {"goal": description, "status": "tracking", "progress": 0}

        current = latest.get("value", 0)
        progress = min(1.0, current / target) if target > 0 else 0

        return {
            "goal": description,
            "status": "met" if progress >= 1.0 else "in_progress",
            "progress": round(progress, 2),
            "current_value": current,
            "target_value": target,
        }

    @staticmethod
    def _calculate_adherence(care_plan: dict, observations: list) -> float:
        activities = care_plan.get("activities", [])
        if not activities:
            return 1.0
        completed = sum(1 for a in activities if a.get("completed", False))
        return completed / len(activities)

    @staticmethod
    def _assess_outcome(goal_progress: list, adherence: float) -> dict:
        goals_met = sum(1 for g in goal_progress if g.get("status") == "met")
        total_goals = len(goal_progress)

        if total_goals == 0:
            status = "no_goals"
        elif goals_met == total_goals:
            status = "excellent"
        elif goals_met / total_goals >= 0.7:
            status = "good"
        elif goals_met / total_goals >= 0.4:
            status = "fair"
        else:
            status = "needs_improvement"

        return {
            "status": status,
            "goals_met": goals_met,
            "total_goals": total_goals,
            "adherence": adherence,
            "trend": "improving" if goals_met > 0 else "stable",
        }
