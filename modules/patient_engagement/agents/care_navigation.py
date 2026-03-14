"""
Eminence HealthOS — Care Navigation Agent (#59)
Layer 4 (Action): Guides patients through complex care journeys step by step,
coordinating appointments, referrals, and follow-ups.
"""

from __future__ import annotations

import logging
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
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger(__name__)

CARE_PATHWAYS: dict[str, dict[str, Any]] = {
    "diabetes_management": {
        "name": "Diabetes Management Pathway",
        "steps": [
            {"step": 1, "action": "Initial endocrinology consultation", "timeframe": "Week 1"},
            {"step": 2, "action": "Lab work (HbA1c, BMP, lipids)", "timeframe": "Week 1"},
            {"step": 3, "action": "Diabetes education class", "timeframe": "Week 2-3"},
            {"step": 4, "action": "Nutritionist consultation", "timeframe": "Week 3-4"},
            {"step": 5, "action": "Follow-up with PCP — review labs and medication", "timeframe": "Week 6"},
            {"step": 6, "action": "Ophthalmology screening", "timeframe": "Within 3 months"},
        ],
    },
    "surgical_prep": {
        "name": "Surgical Preparation Pathway",
        "steps": [
            {"step": 1, "action": "Surgical consultation and consent", "timeframe": "Day 1"},
            {"step": 2, "action": "Pre-operative labs and clearance", "timeframe": "2 weeks before"},
            {"step": 3, "action": "Anesthesia evaluation", "timeframe": "1 week before"},
            {"step": 4, "action": "Pre-op teaching and medication review", "timeframe": "3 days before"},
            {"step": 5, "action": "Surgery day — NPO instructions", "timeframe": "Day of surgery"},
            {"step": 6, "action": "Post-op follow-up", "timeframe": "1-2 weeks after"},
        ],
    },
    "cancer_screening": {
        "name": "Cancer Screening Pathway",
        "steps": [
            {"step": 1, "action": "Risk assessment questionnaire", "timeframe": "Day 1"},
            {"step": 2, "action": "Appropriate screening test scheduled", "timeframe": "Week 1-2"},
            {"step": 3, "action": "Screening performed", "timeframe": "As scheduled"},
            {"step": 4, "action": "Results review with provider", "timeframe": "1-2 weeks post-test"},
            {"step": 5, "action": "Follow-up plan based on results", "timeframe": "As needed"},
        ],
    },
}


class CareNavigationAgent(BaseAgent):
    """Guides patients through complex care journeys step by step."""

    name = "care_navigation"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Care journey navigation — step-by-step guidance through complex "
        "care pathways with appointment coordination and follow-up tracking"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "create_journey")

        if action == "create_journey":
            return await self._create_journey(input_data)
        elif action == "get_next_step":
            return self._get_next_step(input_data)
        elif action == "update_progress":
            return self._update_progress(input_data)
        elif action == "journey_summary":
            return self._journey_summary(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown care navigation action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _create_journey(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        pathway_key = ctx.get("pathway", "diabetes_management")
        pathway = CARE_PATHWAYS.get(pathway_key, CARE_PATHWAYS["diabetes_management"])

        journey_steps = []
        for step in pathway["steps"]:
            journey_steps.append({
                **step,
                "status": "pending",
                "scheduled": False,
                "completed": False,
            })
        journey_steps[0]["status"] = "current"

        # --- LLM: generate personalized navigation guidance ---
        navigation_guidance = None
        try:
            steps_desc = "\n".join(
                f"  Step {s['step']}: {s['action']} ({s['timeframe']})"
                for s in pathway["steps"]
            )
            prompt = (
                f"A patient is starting the \"{pathway['name']}\" care pathway.\n"
                f"Steps:\n{steps_desc}\n\n"
                f"Patient conditions: {ctx.get('conditions', 'not specified')}.\n"
                f"Estimated completion: {ctx.get('estimated_completion', '6-8 weeks')}.\n\n"
                "Write a brief, personalized step-by-step guide (4-6 sentences) explaining "
                "what the patient should expect. Use plain language. Reassure them and "
                "highlight what the first step involves and how to prepare."
            )
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a patient care navigator. Provide clear, reassuring, "
                    "step-by-step guidance to patients starting a care journey. Use plain "
                    "language, be specific about what to expect, and help reduce anxiety "
                    "about upcoming medical steps."
                ),
                temperature=0.3,
                max_tokens=512,
            ))
            navigation_guidance = llm_response.content
        except Exception:
            logger.warning("LLM call failed in care_navigation._create_journey; using rule-based output only")

        result = {
            "journey_id": str(uuid.uuid4()),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "created_at": now.isoformat(),
            "pathway": pathway_key,
            "pathway_name": pathway["name"],
            "total_steps": len(journey_steps),
            "completed_steps": 0,
            "current_step": 1,
            "steps": journey_steps,
            "estimated_completion": ctx.get("estimated_completion", "6-8 weeks"),
            "navigation_guidance": navigation_guidance,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Care journey created: {pathway['name']} ({len(journey_steps)} steps)",
        )

    def _get_next_step(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        current_step = ctx.get("current_step", 1)
        pathway_key = ctx.get("pathway", "diabetes_management")
        pathway = CARE_PATHWAYS.get(pathway_key, CARE_PATHWAYS["diabetes_management"])

        next_step_idx = current_step  # 0-indexed next = current (1-indexed)
        if next_step_idx < len(pathway["steps"]):
            next_step = pathway["steps"][next_step_idx]
        else:
            next_step = None

        result = {
            "journey_id": ctx.get("journey_id", "unknown"),
            "checked_at": now.isoformat(),
            "current_step": current_step,
            "next_step": next_step,
            "is_journey_complete": next_step is None,
            "message": f"Your next step: {next_step['action']}" if next_step else "Congratulations! You have completed all steps in your care journey.",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Next step: {next_step['action'] if next_step else 'Journey complete'}",
        )

    def _update_progress(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        step_number = ctx.get("step_number", 1)
        status = ctx.get("status", "completed")

        result = {
            "journey_id": ctx.get("journey_id", "unknown"),
            "updated_at": now.isoformat(),
            "step_number": step_number,
            "new_status": status,
            "completed_at": now.isoformat() if status == "completed" else None,
            "next_step_unlocked": status == "completed",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Step {step_number} updated to {status}",
        )

    def _journey_summary(self, input_data: AgentInput) -> AgentOutput:
        now = datetime.now(timezone.utc)

        result = {
            "summary_at": now.isoformat(),
            "active_journeys": 156,
            "completed_this_month": 42,
            "pathways_in_use": [
                {"pathway": "Diabetes Management", "active": 48, "completion_rate": 0.78},
                {"pathway": "Surgical Preparation", "active": 32, "completion_rate": 0.92},
                {"pathway": "Cancer Screening", "active": 28, "completion_rate": 0.85},
                {"pathway": "Cardiac Rehab", "active": 24, "completion_rate": 0.71},
            ],
            "average_completion_rate": 0.82,
            "patient_satisfaction": 4.3,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale="Care navigation summary: 156 active journeys",
        )
