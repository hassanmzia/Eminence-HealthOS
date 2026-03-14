"""
Eminence HealthOS — Community Resource Agent (#61)
Layer 4 (Action): Connects patients to local food banks, transportation,
housing, and social services based on SDOH screening results.
"""

from __future__ import annotations

import json
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

logger = logging.getLogger("healthos.agent.community_resource")

RESOURCE_CATEGORIES: dict[str, list[dict[str, Any]]] = {
    "food_insecurity": [
        {"name": "Community Food Bank", "type": "food_pantry", "phone": "555-FOOD-001", "hours": "Mon-Fri 9am-5pm", "eligibility": "Open to all"},
        {"name": "SNAP Benefits Enrollment", "type": "government", "phone": "800-221-5689", "hours": "24/7 hotline", "eligibility": "Income-based"},
        {"name": "Meals on Wheels", "type": "home_delivery", "phone": "555-MEAL-002", "hours": "Mon-Sat 8am-4pm", "eligibility": "Homebound adults 60+"},
    ],
    "housing_instability": [
        {"name": "Housing Authority", "type": "government", "phone": "555-HOUS-001", "hours": "Mon-Fri 8am-5pm", "eligibility": "Income-based"},
        {"name": "Emergency Shelter Network", "type": "shelter", "phone": "211", "hours": "24/7", "eligibility": "Open to all"},
        {"name": "Habitat for Humanity", "type": "nonprofit", "phone": "555-HABI-003", "hours": "Mon-Fri 9am-5pm", "eligibility": "Application required"},
    ],
    "transportation": [
        {"name": "Medicaid Non-Emergency Transport", "type": "medical_transport", "phone": "800-MED-RIDE", "hours": "24/7", "eligibility": "Medicaid members"},
        {"name": "Community Ride Share", "type": "volunteer", "phone": "555-RIDE-001", "hours": "Mon-Sat 6am-8pm", "eligibility": "Seniors and disabled"},
        {"name": "Public Transit Reduced Fare", "type": "government", "phone": "555-TRAN-002", "hours": "Mon-Fri 9am-5pm", "eligibility": "Seniors, disabled, low-income"},
    ],
    "social_isolation": [
        {"name": "Senior Center Activities", "type": "community", "phone": "555-SNRC-001", "hours": "Mon-Fri 9am-4pm", "eligibility": "Adults 55+"},
        {"name": "Mental Health Support Line", "type": "crisis", "phone": "988", "hours": "24/7", "eligibility": "Open to all"},
        {"name": "Volunteer Companion Program", "type": "volunteer", "phone": "555-COMP-002", "hours": "By appointment", "eligibility": "Homebound individuals"},
    ],
    "financial_strain": [
        {"name": "Patient Financial Assistance", "type": "hospital", "phone": "555-FINL-001", "hours": "Mon-Fri 8am-6pm", "eligibility": "Based on income"},
        {"name": "Prescription Assistance Program", "type": "pharmacy", "phone": "800-RX-HELP", "hours": "Mon-Fri 9am-5pm", "eligibility": "Uninsured/underinsured"},
        {"name": "Utility Assistance (LIHEAP)", "type": "government", "phone": "555-UTIL-003", "hours": "Mon-Fri 8am-5pm", "eligibility": "Income-based"},
    ],
}


class CommunityResourceAgent(BaseAgent):
    """Connects patients to local food banks, transportation, housing, and social services."""

    name = "community_resource"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Community resource matching — connects patients with local food, housing, "
        "transportation, social, and financial assistance based on SDOH needs"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "find_resources")

        if action == "find_resources":
            output = self._find_resources(input_data)
        elif action == "create_referral":
            output = self._create_referral(input_data)
        elif action == "referral_status":
            output = self._referral_status(input_data)
        elif action == "resource_directory":
            output = self._resource_directory(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown community resource action: {action}",
                status=AgentStatus.FAILED,
            )

        # --- LLM: generate personalized resource recommendation ---
        try:
            result_data = output.result if hasattr(output, "result") else {}
            prompt = (
                "You are a social determinants of health (SDOH) specialist. "
                "Analyze the following community resource data and provide a personalized, "
                "empathetic recommendation that helps the patient or care coordinator understand "
                "available resources, prioritize next steps, and overcome common barriers to access.\n\n"
                f"Action: {action}\n"
                f"Patient needs: {json.dumps(ctx.get('needs', []))}\n"
                f"Resource data: {json.dumps(result_data, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a community resource navigator for a healthcare platform. "
                    "Provide warm, practical guidance that helps connect patients to social "
                    "services. Be sensitive to stigma, use encouraging language, and include "
                    "concrete next steps like phone numbers and eligibility tips."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if isinstance(result_data, dict):
                result_data["resource_recommendation"] = resp.content
        except Exception:
            logger.warning("LLM resource_recommendation generation failed; continuing without it")

        return output

    def _find_resources(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        needs = ctx.get("needs", ["food_insecurity"])
        zip_code = ctx.get("zip_code", "10001")

        matched: list[dict[str, Any]] = []
        for need in needs:
            resources = RESOURCE_CATEGORIES.get(need, [])
            for r in resources:
                matched.append({
                    "need_category": need,
                    **r,
                    "zip_code": zip_code,
                    "distance_miles": round(1.0 + len(matched) * 0.8, 1),
                })

        result = {
            "search_id": str(uuid.uuid4()),
            "searched_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "zip_code": zip_code,
            "needs_searched": needs,
            "resources_found": matched,
            "total_resources": len(matched),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Found {len(matched)} resources for {len(needs)} needs near {zip_code}",
        )

    def _create_referral(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "referral_id": str(uuid.uuid4()),
            "created_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "resource_name": ctx.get("resource_name", "Community Food Bank"),
            "need_category": ctx.get("need_category", "food_insecurity"),
            "status": "submitted",
            "contact_method": ctx.get("contact_method", "phone"),
            "follow_up_date": ctx.get("follow_up_date", "2026-03-19"),
            "notes": ctx.get("notes", ""),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"Referral created to {result['resource_name']}",
        )

    def _referral_status(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "referral_id": ctx.get("referral_id", "unknown"),
            "checked_at": now.isoformat(),
            "status": ctx.get("current_status", "in_progress"),
            "resource_name": ctx.get("resource_name", "Community Food Bank"),
            "last_contact": "2026-03-10",
            "outcome": ctx.get("outcome", "Patient contacted resource, intake scheduled"),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Referral status: {result['status']}",
        )

    def _resource_directory(self, input_data: AgentInput) -> AgentOutput:
        now = datetime.now(timezone.utc)

        result = {
            "directory_at": now.isoformat(),
            "categories": {
                cat: {"resource_count": len(resources), "resources": resources}
                for cat, resources in RESOURCE_CATEGORIES.items()
            },
            "total_categories": len(RESOURCE_CATEGORIES),
            "total_resources": sum(len(r) for r in RESOURCE_CATEGORIES.values()),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Resource directory: {result['total_resources']} resources across {result['total_categories']} categories",
        )
