"""
Eminence HealthOS — Behavioral Health Workflow Agent (#77)
Layer 4 (Action): Manages behavioral health referrals, therapy scheduling,
follow-up assessments, treatment plans, and multi-provider care coordination.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger(__name__)


# ── Specialties & Modalities ────────────────────────────────────────────────

SPECIALTIES: dict[str, dict[str, Any]] = {
    "depression": {
        "provider_types": ["psychiatrist", "psychologist", "lcsw", "lpc"],
        "recommended_modalities": ["in_person", "telehealth"],
        "therapies": ["CBT", "IPT", "behavioral_activation"],
        "typical_frequency": "weekly",
        "estimated_wait_days": 7,
    },
    "anxiety": {
        "provider_types": ["psychologist", "lcsw", "lpc", "psychiatrist"],
        "recommended_modalities": ["in_person", "telehealth"],
        "therapies": ["CBT", "exposure_therapy", "ACT"],
        "typical_frequency": "weekly",
        "estimated_wait_days": 7,
    },
    "substance_use": {
        "provider_types": ["addiction_counselor", "psychiatrist", "lcsw"],
        "recommended_modalities": ["in_person", "group"],
        "therapies": ["motivational_interviewing", "CBT", "twelve_step_facilitation"],
        "typical_frequency": "twice_weekly",
        "estimated_wait_days": 3,
    },
    "trauma": {
        "provider_types": ["psychologist", "lcsw", "psychiatrist"],
        "recommended_modalities": ["in_person"],
        "therapies": ["EMDR", "CPT", "prolonged_exposure"],
        "typical_frequency": "weekly",
        "estimated_wait_days": 14,
    },
    "eating_disorder": {
        "provider_types": ["psychologist", "psychiatrist", "dietitian", "lcsw"],
        "recommended_modalities": ["in_person", "group"],
        "therapies": ["CBT-E", "FBT", "DBT"],
        "typical_frequency": "twice_weekly",
        "estimated_wait_days": 10,
    },
}

URGENCY_LEVELS: dict[str, dict[str, Any]] = {
    "routine": {"max_wait_days": 14, "priority": 3},
    "urgent": {"max_wait_days": 3, "priority": 2},
    "emergent": {"max_wait_days": 0, "priority": 1},
}


class BehavioralHealthWorkflowAgent(BaseAgent):
    """Manages behavioral health referrals, scheduling, follow-ups, and care coordination."""

    name = "behavioral_health_workflow"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Orchestrates behavioral health workflows including referrals to specialists, "
        "therapy session scheduling, follow-up monitoring, treatment planning, "
        "and multi-provider care coordination"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "create_referral")

        if action == "create_referral":
            return self._create_referral(input_data)
        elif action == "schedule_session":
            return self._schedule_session(input_data)
        elif action == "follow_up_check":
            return self._follow_up_check(input_data)
        elif action == "treatment_plan":
            return await self._treatment_plan(input_data)
        elif action == "care_coordination":
            return self._care_coordination(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown workflow action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Create Referral ──────────────────────────────────────────────────────

    def _create_referral(self, input_data: AgentInput) -> AgentOutput:
        """Create a referral to a behavioral health specialist based on screening results."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        condition_type = ctx.get("condition_type", "depression")
        screening_scores = ctx.get("screening_scores", {})
        urgency = ctx.get("urgency", "routine")

        if condition_type not in SPECIALTIES:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": f"Unknown condition type: {condition_type}",
                    "supported_types": list(SPECIALTIES.keys()),
                },
                confidence=0.95,
                rationale=f"Unsupported condition type: {condition_type}",
                status=AgentStatus.FAILED,
            )

        spec = SPECIALTIES[condition_type]
        urgency_config = URGENCY_LEVELS.get(urgency, URGENCY_LEVELS["routine"])

        # Auto-escalate urgency based on screening scores
        effective_urgency = urgency
        phq9_score = screening_scores.get("phq9_total", 0)
        if phq9_score >= 20 or screening_scores.get("suicidal_ideation_flag"):
            effective_urgency = "emergent"
        elif phq9_score >= 15:
            effective_urgency = "urgent"

        if effective_urgency != urgency:
            urgency_config = URGENCY_LEVELS[effective_urgency]

        referral_id = str(uuid.uuid4())

        matched_providers = [
            {
                "provider_type": pt,
                "available_modalities": spec["recommended_modalities"],
                "specializes_in": spec["therapies"],
                "next_available_slot": None,  # populated by scheduling system
            }
            for pt in spec["provider_types"]
        ]

        result = {
            "referral_id": referral_id,
            "patient_id": patient_id,
            "condition_type": condition_type,
            "matched_providers": matched_providers,
            "urgency": effective_urgency,
            "priority": urgency_config["priority"],
            "estimated_wait_days": min(spec["estimated_wait_days"], urgency_config["max_wait_days"]),
            "recommended_therapies": spec["therapies"],
            "recommended_frequency": spec["typical_frequency"],
            "screening_scores": screening_scores,
            "auto_escalated": effective_urgency != urgency,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=(
                f"Created referral {referral_id} for {condition_type} — "
                f"urgency: {effective_urgency}, "
                f"matched {len(matched_providers)} provider type(s). "
                f"{'Auto-escalated from ' + urgency + '. ' if effective_urgency != urgency else ''}"
                f"Estimated wait: {result['estimated_wait_days']} days"
            ),
        )

    # ── Schedule Session ─────────────────────────────────────────────────────

    def _schedule_session(self, input_data: AgentInput) -> AgentOutput:
        """Schedule a therapy session with availability matching and patient preferences."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        referral_id = ctx.get("referral_id")
        provider_id = ctx.get("provider_id")
        preferred_modality = ctx.get("preferred_modality", "telehealth")
        preferred_times = ctx.get("preferred_times", [])
        session_type = ctx.get("session_type", "individual")

        if not referral_id and not provider_id:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "Either referral_id or provider_id is required"},
                confidence=0.95,
                rationale="Cannot schedule session without referral or provider reference",
                status=AgentStatus.FAILED,
            )

        valid_modalities = ["in_person", "telehealth", "group"]
        if preferred_modality not in valid_modalities:
            preferred_modality = "telehealth"

        session_id = str(uuid.uuid4())

        result = {
            "session_id": session_id,
            "patient_id": patient_id,
            "referral_id": referral_id,
            "provider_id": provider_id,
            "modality": preferred_modality,
            "session_type": session_type,
            "preferred_times": preferred_times,
            "status": "pending_confirmation",
            "suggested_slots": [],  # populated by scheduling system
            "reminders_enabled": True,
            "pre_session_checklist": [
                "Complete mood check-in",
                "Review previous session notes",
                "Prepare discussion topics",
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=(
                f"Scheduled {preferred_modality} {session_type} session {session_id} "
                f"for patient {patient_id}. Awaiting provider confirmation."
            ),
        )

    # ── Follow-up Check ──────────────────────────────────────────────────────

    def _follow_up_check(self, input_data: AgentInput) -> AgentOutput:
        """Generate follow-up assessment for a patient in behavioral health treatment."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        referral_id = ctx.get("referral_id")
        last_session_date = ctx.get("last_session_date")
        current_scores = ctx.get("current_scores", {})
        previous_scores = ctx.get("previous_scores", {})
        treatment_plan_id = ctx.get("treatment_plan_id")

        # Calculate days since last session
        days_since_session = None
        if last_session_date:
            try:
                last_dt = datetime.fromisoformat(last_session_date)
                days_since_session = (datetime.now(timezone.utc) - last_dt).days
            except (ValueError, TypeError):
                days_since_session = None

        # Compute score changes
        score_changes: dict[str, dict[str, Any]] = {}
        for instrument in ("phq9", "gad7", "audit_c"):
            current = current_scores.get(instrument)
            previous = previous_scores.get(instrument)
            if current is not None and previous is not None:
                change = current - previous
                direction = "improved" if change < 0 else ("worsened" if change > 0 else "stable")
                score_changes[instrument] = {
                    "current": current,
                    "previous": previous,
                    "change": change,
                    "direction": direction,
                }

        # Generate flags
        flags: list[dict[str, str]] = []
        if days_since_session is not None and days_since_session > 21:
            flags.append({
                "type": "overdue_session",
                "message": f"Patient has not had a session in {days_since_session} days",
                "urgency": "moderate",
            })
        if days_since_session is not None and days_since_session > 42:
            flags.append({
                "type": "treatment_disengagement",
                "message": "Patient may be disengaging from treatment — outreach recommended",
                "urgency": "high",
            })

        for instrument, change_data in score_changes.items():
            if change_data["direction"] == "worsened" and abs(change_data["change"]) >= 5:
                flags.append({
                    "type": "significant_worsening",
                    "message": f"{instrument.upper()} score increased by {change_data['change']}",
                    "urgency": "high",
                })

        no_show_count = ctx.get("no_show_count", 0)
        if no_show_count >= 2:
            flags.append({
                "type": "repeated_no_shows",
                "message": f"Patient has {no_show_count} no-shows — engagement intervention recommended",
                "urgency": "moderate",
            })

        result = {
            "patient_id": patient_id,
            "referral_id": referral_id,
            "treatment_plan_id": treatment_plan_id,
            "days_since_last_session": days_since_session,
            "score_changes": score_changes,
            "no_show_count": no_show_count,
            "adherence_flags": flags,
            "recommended_actions": [],
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Determine recommended actions
        if any(f["urgency"] == "high" for f in flags):
            result["recommended_actions"].append("immediate_provider_review")
        if any(f["type"] == "treatment_disengagement" for f in flags):
            result["recommended_actions"].append("outreach_call")
            result["recommended_actions"].append("reassess_treatment_plan")
        if not flags:
            result["recommended_actions"].append("continue_current_plan")

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=(
                f"Follow-up assessment for patient {patient_id}: "
                f"{len(flags)} adherence flag(s) detected. "
                f"Days since last session: {days_since_session or 'unknown'}. "
                f"Score changes tracked for {len(score_changes)} instrument(s)."
            ),
        )

    # ── Treatment Plan ───────────────────────────────────────────────────────

    async def _treatment_plan(self, input_data: AgentInput) -> AgentOutput:
        """Create a structured behavioral health treatment plan."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        condition_types = ctx.get("condition_types", ["depression"])
        screening_scores = ctx.get("screening_scores", {})
        patient_preferences = ctx.get("patient_preferences", {})
        existing_medications = ctx.get("existing_medications", [])

        plan_id = str(uuid.uuid4())

        # Build goals based on conditions
        goals: list[dict[str, Any]] = []
        interventions: list[dict[str, Any]] = []
        outcome_measures: list[str] = []

        for condition in condition_types:
            spec = SPECIALTIES.get(condition, SPECIALTIES["depression"])

            if condition == "depression":
                goals.append({
                    "condition": condition,
                    "description": "Reduce depressive symptoms to PHQ-9 score < 10",
                    "target_score": {"instrument": "PHQ-9", "target": 9},
                    "timeline_weeks": 12,
                })
                outcome_measures.append("PHQ-9")
            elif condition == "anxiety":
                goals.append({
                    "condition": condition,
                    "description": "Reduce anxiety symptoms to GAD-7 score < 10",
                    "target_score": {"instrument": "GAD-7", "target": 9},
                    "timeline_weeks": 12,
                })
                outcome_measures.append("GAD-7")
            elif condition == "substance_use":
                goals.append({
                    "condition": condition,
                    "description": "Achieve and maintain sobriety or reduce harmful use",
                    "target_score": {"instrument": "AUDIT-C", "target": 3},
                    "timeline_weeks": 24,
                })
                outcome_measures.append("AUDIT-C")
            elif condition == "trauma":
                goals.append({
                    "condition": condition,
                    "description": "Process traumatic experiences and reduce PTSD symptoms",
                    "target_score": {"instrument": "PCL-5", "target": 32},
                    "timeline_weeks": 16,
                })
                outcome_measures.append("PCL-5")
            elif condition == "eating_disorder":
                goals.append({
                    "condition": condition,
                    "description": "Normalize eating patterns and reduce disordered behaviors",
                    "target_score": {"instrument": "EDE-Q", "target": 2.5},
                    "timeline_weeks": 24,
                })
                outcome_measures.append("EDE-Q")

            for therapy in spec["therapies"]:
                interventions.append({
                    "type": therapy,
                    "target_condition": condition,
                    "frequency": spec["typical_frequency"],
                    "modality": patient_preferences.get(
                        "modality",
                        spec["recommended_modalities"][0],
                    ),
                })

        # Milestones
        milestones = [
            {"week": 2, "checkpoint": "Initial rapport and treatment engagement assessment"},
            {"week": 4, "checkpoint": "First screening re-assessment and treatment adjustment"},
            {"week": 8, "checkpoint": "Mid-treatment review — progress toward goals"},
            {"week": 12, "checkpoint": "Treatment outcome evaluation and continuation decision"},
        ]

        # ── LLM: generate treatment plan narrative ─────────────────────
        treatment_plan_narrative: str | None = None
        try:
            prompt = (
                f"Patient conditions: {', '.join(condition_types)}.\n"
                f"Screening scores: {screening_scores or 'not available'}.\n"
                f"Treatment goals: {'; '.join(g['description'] for g in goals) or 'none defined'}.\n"
                f"Planned interventions: {', '.join(i['type'] for i in interventions) or 'none'}.\n"
                f"Session frequency: {patient_preferences.get('frequency', 'weekly')}.\n"
                f"Existing medications: {', '.join(str(m) for m in existing_medications) or 'none'}.\n"
                f"Estimated duration: {max(g['timeline_weeks'] for g in goals) if goals else 12} weeks.\n\n"
                "Write a personalized behavioral health treatment plan narrative. "
                "Summarize the clinical rationale, treatment approach, expected milestones, "
                "and how the interventions address the patient's specific conditions. "
                "Include guidance on what the patient can expect during treatment."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a behavioral health treatment planning assistant. "
                    "Produce a clear, professional treatment plan narrative suitable "
                    "for both the clinical record and patient communication. "
                    "Be specific to the patient's conditions and evidence-based interventions."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            treatment_plan_narrative = resp.content
        except Exception:
            logger.warning("LLM unavailable for treatment plan narrative; continuing without it.")

        result = {
            "plan_id": plan_id,
            "patient_id": patient_id,
            "condition_types": condition_types,
            "goals": goals,
            "interventions": interventions,
            "outcome_measures": list(set(outcome_measures)),
            "milestones": milestones,
            "session_frequency": patient_preferences.get("frequency", "weekly"),
            "existing_medications": existing_medications,
            "medication_management": bool(existing_medications),
            "estimated_duration_weeks": max(g["timeline_weeks"] for g in goals) if goals else 12,
            "screening_scores_at_baseline": screening_scores,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if treatment_plan_narrative:
            result["treatment_plan_narrative"] = treatment_plan_narrative

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=(
                f"Created treatment plan {plan_id} for patient {patient_id} — "
                f"conditions: {', '.join(condition_types)}, "
                f"{len(goals)} goal(s), {len(interventions)} intervention(s), "
                f"estimated duration: {result['estimated_duration_weeks']} weeks"
            ),
        )

    # ── Care Coordination ────────────────────────────────────────────────────

    def _care_coordination(self, input_data: AgentInput) -> AgentOutput:
        """Coordinate care between PCP, psychiatrist, therapist, and social worker."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        care_team = ctx.get("care_team", [])
        treatment_plan_id = ctx.get("treatment_plan_id")
        medications = ctx.get("medications", [])
        recent_updates = ctx.get("recent_updates", [])

        coordination_id = str(uuid.uuid4())

        # Build shared care plan updates
        care_plan_updates: list[dict[str, Any]] = []
        for update in recent_updates:
            care_plan_updates.append({
                "source_provider": update.get("provider"),
                "update_type": update.get("type"),
                "summary": update.get("summary"),
                "action_items": update.get("action_items", []),
                "timestamp": update.get("timestamp", datetime.now(timezone.utc).isoformat()),
            })

        # Medication reconciliation
        med_reconciliation = {
            "medications": medications,
            "potential_interactions": [],
            "reconciliation_status": "current" if medications else "no_medications",
            "last_reviewed": datetime.now(timezone.utc).isoformat(),
        }

        # Check for potential psychiatric medication interactions
        psych_meds = [m for m in medications if m.get("category") == "psychiatric"]
        if len(psych_meds) > 2:
            med_reconciliation["potential_interactions"].append({
                "flag": "multiple_psych_medications",
                "message": f"Patient on {len(psych_meds)} psychiatric medications — review recommended",
                "urgency": "moderate",
            })

        # Crisis protocols for the care team
        crisis_protocols = {
            "primary_contact": next(
                (m for m in care_team if m.get("role") == "psychiatrist"),
                next((m for m in care_team if m.get("role") == "pcp"), None),
            ),
            "crisis_line": "988",
            "crisis_text": "Text HOME to 741741",
            "emergency_protocol": "Call 911 for imminent danger",
            "escalation_chain": [
                {"step": 1, "action": "Contact therapist"},
                {"step": 2, "action": "Contact psychiatrist"},
                {"step": 3, "action": "Contact PCP"},
                {"step": 4, "action": "Crisis services / 988"},
                {"step": 5, "action": "Emergency services / 911"},
            ],
        }

        # Communication plan
        communication_plan = {
            "team_updates_frequency": "biweekly",
            "shared_notes_enabled": True,
            "care_conference_schedule": "monthly",
            "notification_preferences": {
                role: "immediate" for role in set(m.get("role", "") for m in care_team)
            },
        }

        result = {
            "coordination_id": coordination_id,
            "patient_id": patient_id,
            "treatment_plan_id": treatment_plan_id,
            "care_team": care_team,
            "care_plan_updates": care_plan_updates,
            "medication_reconciliation": med_reconciliation,
            "crisis_protocols": crisis_protocols,
            "communication_plan": communication_plan,
            "coordinated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=(
                f"Care coordination {coordination_id} for patient {patient_id}: "
                f"{len(care_team)} team member(s), "
                f"{len(care_plan_updates)} recent update(s), "
                f"{len(medications)} medication(s) reconciled"
            ),
        )
