"""
Eminence HealthOS — Referral Coordination Agent
Layer 4 (Action): Manages the full referral lifecycle — creation, specialist
matching, tracking, and outcome capture for inter-provider care coordination.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
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


# Specialty-to-urgency default turnaround days
SPECIALTY_TURNAROUND = {
    "cardiology": 7,
    "oncology": 3,
    "orthopedics": 14,
    "neurology": 10,
    "dermatology": 21,
    "psychiatry": 14,
    "endocrinology": 14,
    "gastroenterology": 14,
    "pulmonology": 10,
    "nephrology": 14,
    "default": 14,
}


class ReferralCoordinationAgent(BaseAgent):
    """Manages referral creation, specialist matching, and tracking."""

    name = "referral_coordination"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Coordinates referrals — specialist matching, tracking, and outcome capture"
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "create")

        if action == "create":
            return await self._create_referral(input_data)
        elif action == "match_specialist":
            return self._match_specialist(input_data)
        elif action == "track":
            return self._track_referral(input_data)
        elif action == "close":
            return self._close_referral(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown referral action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _create_referral(self, input_data: AgentInput) -> AgentOutput:
        """Create a new referral with clinical context."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        specialty = ctx.get("specialty", "").lower()
        urgency = ctx.get("urgency", "routine")
        reason = ctx.get("reason", "")
        diagnosis_codes = ctx.get("diagnosis_codes", [])
        referring_provider = ctx.get("referring_provider", "")
        clinical_notes = ctx.get("clinical_notes", "")
        insurance_verified = ctx.get("insurance_verified", False)

        # Validate required fields
        missing = []
        if not specialty:
            missing.append("specialty")
        if not reason:
            missing.append("reason")
        if missing:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"status": "incomplete", "missing_fields": missing},
                confidence=0.95,
                rationale=f"Cannot create referral: missing {', '.join(missing)}",
            )

        # Calculate expected turnaround
        base_days = SPECIALTY_TURNAROUND.get(specialty, SPECIALTY_TURNAROUND["default"])
        urgency_multiplier = {"emergency": 0.1, "urgent": 0.3, "soon": 0.6, "routine": 1.0}
        target_days = max(1, int(base_days * urgency_multiplier.get(urgency, 1.0)))
        target_date = datetime.now(timezone.utc) + timedelta(days=target_days)

        referral_id = f"REF-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{patient_id[:8]}"

        # --- LLM: generate referral summary for receiving specialist ---
        referral_summary = None
        try:
            dx_desc = ", ".join(diagnosis_codes) if diagnosis_codes else "not specified"
            prompt = (
                f"Referral to {specialty} specialist.\n"
                f"Urgency: {urgency}\n"
                f"Reason for referral: {reason}\n"
                f"Diagnosis codes: {dx_desc}\n"
                f"Referring provider: {referring_provider or 'not specified'}\n"
                f"Clinical notes: {clinical_notes or 'none provided'}\n\n"
                f"Write a concise clinical summary for the receiving specialist that "
                f"includes relevant clinical context, reason for referral, pertinent "
                f"history, and what the referring provider is requesting."
            )
            llm_response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=(
                        "You are a clinical referral coordinator. Write professional, "
                        "concise referral summaries for receiving specialists. Include "
                        "relevant clinical context, the specific reason for referral, "
                        "and what evaluation or management is being requested. Use "
                        "clear medical language appropriate for specialist communication."
                    ),
                    temperature=0.3,
                    max_tokens=1024,
                )
            )
            referral_summary = llm_response.content
        except Exception:
            logger.warning(
                "LLM referral summary generation failed; "
                "returning referral without narrative summary",
                exc_info=True,
            )

        result = {
            "referral_id": referral_id,
            "patient_id": patient_id,
            "specialty": specialty,
            "urgency": urgency,
            "reason": reason,
            "diagnosis_codes": diagnosis_codes,
            "referring_provider": referring_provider,
            "status": "created",
            "target_appointment_date": target_date.isoformat(),
            "target_days": target_days,
            "insurance_verified": insurance_verified,
            "insurance_warning": not insurance_verified,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "next_steps": self._get_next_steps(insurance_verified, urgency),
        }
        if referral_summary is not None:
            result["referral_summary"] = referral_summary

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=(
                f"Referral {referral_id} created for {specialty} — "
                f"{urgency} priority, target within {target_days} days"
            ),
        )

    def _match_specialist(self, input_data: AgentInput) -> AgentOutput:
        """Match patient to appropriate specialist based on clinical needs."""
        ctx = input_data.context
        specialty = ctx.get("specialty", "").lower()
        urgency = ctx.get("urgency", "routine")
        insurance_network = ctx.get("insurance_network", "")
        location_preference = ctx.get("location_preference", "")
        language_preference = ctx.get("language_preference", "")

        # In production, queries provider directory API
        matches = self._simulate_specialist_search(
            specialty, urgency, insurance_network
        )

        result = {
            "specialty": specialty,
            "matches_found": len(matches),
            "specialists": matches,
            "filters_applied": {
                "insurance_network": insurance_network or "any",
                "location": location_preference or "any",
                "language": language_preference or "any",
            },
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85 if matches else 0.60,
            rationale=f"Found {len(matches)} {specialty} specialist(s) matching criteria",
        )

    def _track_referral(self, input_data: AgentInput) -> AgentOutput:
        """Track status of an existing referral."""
        ctx = input_data.context
        referral_id = ctx.get("referral_id", "")

        # In production, queries referral tracking system
        result = {
            "referral_id": referral_id,
            "status": "pending_scheduling",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "timeline": [
                {"event": "created", "timestamp": "2026-03-10T10:00:00Z"},
                {"event": "sent_to_specialist", "timestamp": "2026-03-10T10:05:00Z"},
                {"event": "acknowledged", "timestamp": "2026-03-10T14:30:00Z"},
            ],
            "overdue": False,
            "days_open": 2,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Referral {referral_id}: pending scheduling, {result['days_open']} days open",
        )

    def _close_referral(self, input_data: AgentInput) -> AgentOutput:
        """Close a referral with outcome data."""
        ctx = input_data.context
        referral_id = ctx.get("referral_id", "")
        outcome = ctx.get("outcome", "completed")
        specialist_notes = ctx.get("specialist_notes", "")
        follow_up_needed = ctx.get("follow_up_needed", False)

        result = {
            "referral_id": referral_id,
            "status": "closed",
            "outcome": outcome,
            "specialist_notes_received": bool(specialist_notes),
            "follow_up_needed": follow_up_needed,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"Referral {referral_id} closed — outcome: {outcome}",
        )

    @staticmethod
    def _get_next_steps(insurance_verified: bool, urgency: str) -> list[str]:
        steps = []
        if not insurance_verified:
            steps.append("Verify patient insurance coverage for specialist visit")
        if urgency in ("emergency", "urgent"):
            steps.append("Contact specialist office directly for expedited scheduling")
        steps.append("Send referral documentation to specialist")
        steps.append("Schedule patient appointment with specialist")
        steps.append("Notify patient of referral details")
        return steps

    @staticmethod
    def _simulate_specialist_search(
        specialty: str, urgency: str, network: str
    ) -> list[dict[str, Any]]:
        """Simulate specialist directory search (production: provider directory API)."""
        base_availability = {
            "emergency": 1,
            "urgent": 3,
            "soon": 7,
            "routine": 14,
        }
        days = base_availability.get(urgency, 14)
        next_avail = datetime.now(timezone.utc) + timedelta(days=days)

        return [
            {
                "provider_id": f"PROV-{specialty[:3].upper()}-001",
                "name": f"Dr. Smith ({specialty.title()})",
                "specialty": specialty,
                "in_network": True,
                "accepting_patients": True,
                "next_available": next_avail.isoformat(),
                "distance_miles": 3.2,
                "rating": 4.8,
            },
            {
                "provider_id": f"PROV-{specialty[:3].upper()}-002",
                "name": f"Dr. Johnson ({specialty.title()})",
                "specialty": specialty,
                "in_network": True,
                "accepting_patients": True,
                "next_available": (next_avail + timedelta(days=2)).isoformat(),
                "distance_miles": 5.7,
                "rating": 4.6,
            },
        ]
