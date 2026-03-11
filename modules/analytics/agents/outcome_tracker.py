"""
Outcome Tracker Agent — tracks clinical outcomes and treatment effectiveness.

Monitors treatment outcomes, readmission rates, care plan adherence,
and generates effectiveness reports for quality improvement.
"""

import logging
from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.outcome_tracker")


class OutcomeTrackerAgent(HealthOSAgent):
    """Tracks clinical outcomes and treatment effectiveness."""

    def __init__(self):
        super().__init__(
            name="outcome_tracker",
            tier=AgentTier.DIAGNOSTIC,
            description="Tracks treatment outcomes, adherence, and clinical effectiveness",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CLINICAL_SUMMARY, AgentCapability.RISK_SCORING]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        patient_id = agent_input.patient_id
        care_plan = data.get("care_plan", {})
        observations = data.get("observations", [])
        interventions = data.get("interventions", [])

        # Evaluate goal progress
        goals = care_plan.get("goals", [])
        goal_progress = []
        for goal in goals:
            progress = self._evaluate_goal(goal, observations)
            goal_progress.append(progress)

        # Calculate adherence
        adherence = self._calculate_adherence(care_plan, observations)

        # Assess overall outcome
        outcome = self._assess_outcome(goal_progress, adherence)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=f"outcome_{outcome['status']}",
            rationale=f"Outcome tracking: {outcome['status']} — "
                      f"{len(goal_progress)} goals tracked, adherence {adherence:.0%}",
            confidence=0.80,
            data={
                "outcome_status": outcome["status"],
                "goal_progress": goal_progress,
                "adherence_rate": adherence,
                "outcome_details": outcome,
                "observations_analyzed": len(observations),
            },
            feature_contributions=[
                {"feature": "goal_completion", "contribution": 0.4, "value": outcome.get("goals_met", 0)},
                {"feature": "adherence", "contribution": 0.35, "value": adherence},
                {"feature": "trend", "contribution": 0.25, "value": outcome.get("trend", "stable")},
            ],
        )

    def _evaluate_goal(self, goal: dict, observations: list) -> dict:
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

    def _calculate_adherence(self, care_plan: dict, observations: list) -> float:
        activities = care_plan.get("activities", [])
        if not activities:
            return 1.0

        completed = sum(1 for a in activities if a.get("completed", False))
        return completed / len(activities)

    def _assess_outcome(self, goal_progress: list, adherence: float) -> dict:
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
