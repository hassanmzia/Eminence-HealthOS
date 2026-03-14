"""
Eminence HealthOS — Formulary Agent (#33)
Layer 3 (Decisioning): Verifies insurance formulary coverage for prescribed
medications and suggests covered alternatives when needed.
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
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

# Formulary tier definitions
FORMULARY_TIERS: dict[int, dict[str, Any]] = {
    1: {"name": "Preferred Generic", "copay_range": "$0-$10", "requires_pa": False},
    2: {"name": "Non-Preferred Generic", "copay_range": "$10-$25", "requires_pa": False},
    3: {"name": "Preferred Brand", "copay_range": "$25-$50", "requires_pa": False},
    4: {"name": "Non-Preferred Brand", "copay_range": "$50-$100", "requires_pa": True},
    5: {"name": "Specialty", "copay_range": "$100-$500+", "requires_pa": True},
}

# Sample formulary database
FORMULARY_DB: dict[str, dict[str, Any]] = {
    "losartan": {"tier": 1, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "lisinopril": {"tier": 1, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "metformin": {"tier": 1, "covered": True, "quantity_limit": 180, "step_therapy": False},
    "atorvastatin": {"tier": 1, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "amlodipine": {"tier": 1, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "omeprazole": {"tier": 1, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "sertraline": {"tier": 1, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "gabapentin": {"tier": 2, "covered": True, "quantity_limit": 270, "step_therapy": False},
    "levothyroxine": {"tier": 1, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "rosuvastatin": {"tier": 2, "covered": True, "quantity_limit": 90, "step_therapy": False},
    "valsartan": {"tier": 2, "covered": True, "quantity_limit": 90, "step_therapy": True},
    "jardiance": {"tier": 3, "covered": True, "quantity_limit": 30, "step_therapy": True},
    "eliquis": {"tier": 3, "covered": True, "quantity_limit": 60, "step_therapy": False},
    "humira": {"tier": 5, "covered": True, "quantity_limit": 2, "step_therapy": True},
    "ozempic": {"tier": 4, "covered": True, "quantity_limit": 4, "step_therapy": True},
    "brand_only_drug": {"tier": 4, "covered": False, "quantity_limit": 0, "step_therapy": False},
}

# Therapeutic alternatives
ALTERNATIVES: dict[str, list[dict[str, Any]]] = {
    "valsartan": [
        {"drug": "losartan", "tier": 1, "reason": "Same class ARB, preferred generic"},
        {"drug": "lisinopril", "tier": 1, "reason": "ACE inhibitor alternative"},
    ],
    "ozempic": [
        {"drug": "jardiance", "tier": 3, "reason": "SGLT2 inhibitor with cardiovascular benefit"},
        {"drug": "metformin", "tier": 1, "reason": "First-line diabetes therapy"},
    ],
    "humira": [
        {"drug": "biosimilar_adalimumab", "tier": 3, "reason": "Biosimilar with equivalent efficacy"},
    ],
}


class FormularyAgent(BaseAgent):
    """Verifies insurance formulary coverage and suggests alternatives."""

    name = "formulary"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Insurance formulary verification, tier assignment, copay estimation, "
        "and therapeutic alternative suggestions for non-covered medications"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "check_coverage")

        if action == "check_coverage":
            return self._check_coverage(input_data)
        elif action == "suggest_alternatives":
            return await self._suggest_alternatives(input_data)
        elif action == "check_step_therapy":
            return self._check_step_therapy(input_data)
        elif action == "estimate_cost":
            return self._estimate_cost(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown formulary action: {action}",
                status=AgentStatus.FAILED,
            )

    def _check_coverage(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        drug = ctx.get("drug", "").lower()
        payer = ctx.get("payer", "BlueCross")

        entry = FORMULARY_DB.get(drug)

        if entry:
            tier_info = FORMULARY_TIERS.get(entry["tier"], {})
            result = {
                "drug": drug,
                "payer": payer,
                "checked_at": now.isoformat(),
                "is_covered": entry["covered"],
                "formulary_tier": entry["tier"],
                "tier_name": tier_info.get("name", "Unknown"),
                "estimated_copay": tier_info.get("copay_range", "Unknown"),
                "quantity_limit": entry["quantity_limit"],
                "requires_prior_auth": tier_info.get("requires_pa", False),
                "step_therapy_required": entry["step_therapy"],
                "alternatives_available": drug in ALTERNATIVES,
            }
        else:
            result = {
                "drug": drug,
                "payer": payer,
                "checked_at": now.isoformat(),
                "is_covered": False,
                "formulary_tier": None,
                "tier_name": "Not on formulary",
                "estimated_copay": "N/A",
                "quantity_limit": 0,
                "requires_prior_auth": True,
                "step_therapy_required": False,
                "alternatives_available": True,
            }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Formulary check: {drug} — {'covered' if result['is_covered'] else 'NOT covered'} (Tier {result['formulary_tier'] or 'N/A'})",
        )

    async def _suggest_alternatives(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        drug = ctx.get("drug", "").lower()

        alts = ALTERNATIVES.get(drug, [])

        # Enrich with formulary data
        enriched = []
        for alt in alts:
            alt_drug = alt["drug"]
            entry = FORMULARY_DB.get(alt_drug, {})
            tier = entry.get("tier", 3)
            tier_info = FORMULARY_TIERS.get(tier, {})
            enriched.append({
                "drug": alt_drug,
                "tier": tier,
                "tier_name": tier_info.get("name", "Unknown"),
                "estimated_copay": tier_info.get("copay_range", "Unknown"),
                "reason": alt["reason"],
                "covered": entry.get("covered", True),
            })

        # --- LLM-generated formulary guidance narrative ---
        formulary_guidance = (
            f"No alternatives found for {drug}."
            if not enriched
            else f"{len(enriched)} therapeutic alternative(s) available for {drug}."
        )
        try:
            guidance_payload = {
                "original_drug": drug,
                "alternatives": enriched,
                "patient_conditions": ctx.get("conditions", []),
            }
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Explain the therapeutic alternatives for {drug} based on the "
                    f"following formulary data. Include clinical rationale for each "
                    f"alternative and a recommendation.\n\n"
                    f"Formulary data:\n{json.dumps(guidance_payload, indent=2)}"
                )}],
                system=(
                    "You are a clinical pharmacist AI specializing in formulary management. "
                    "Explain therapeutic alternatives in plain clinical language, comparing "
                    "efficacy, cost tiers, and any step-therapy considerations. Provide a "
                    "clear recommendation for the best alternative."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if llm_response and llm_response.content:
                formulary_guidance = llm_response.content
        except Exception:
            logger.warning(
                "LLM call failed for formulary guidance on %s; using fallback narrative",
                drug,
                exc_info=True,
            )

        result = {
            "original_drug": drug,
            "checked_at": now.isoformat(),
            "alternatives": enriched,
            "total_alternatives": len(enriched),
            "formulary_guidance": formulary_guidance,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.87,
            rationale=f"Found {len(enriched)} alternatives for {drug}",
        )

    def _check_step_therapy(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        drug = ctx.get("drug", "").lower()
        medication_history = ctx.get("medication_history", [])

        entry = FORMULARY_DB.get(drug, {})
        requires_step = entry.get("step_therapy", False)

        step_met = False
        if requires_step:
            required_steps = ALTERNATIVES.get(drug, [])
            tried_drugs = {m.lower() for m in medication_history}
            step_met = any(alt["drug"] in tried_drugs for alt in required_steps)

        result = {
            "drug": drug,
            "checked_at": now.isoformat(),
            "step_therapy_required": requires_step,
            "step_therapy_met": step_met if requires_step else True,
            "required_prior_trials": [a["drug"] for a in ALTERNATIVES.get(drug, [])],
            "patient_history_checked": len(medication_history),
            "approved": not requires_step or step_met,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Step therapy for {drug}: {'met' if result['approved'] else 'NOT met — prior trial required'}",
        )

    def _estimate_cost(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        drug = ctx.get("drug", "").lower()
        quantity = ctx.get("quantity", 30)

        entry = FORMULARY_DB.get(drug, {})
        tier = entry.get("tier", 3)
        tier_info = FORMULARY_TIERS.get(tier, {})

        # Estimate cost per fill
        cost_map = {1: 5, 2: 15, 3: 35, 4: 75, 5: 250}
        copay = cost_map.get(tier, 50)
        annual_cost = copay * 12

        result = {
            "drug": drug,
            "estimated_at": now.isoformat(),
            "tier": tier,
            "tier_name": tier_info.get("name", "Unknown"),
            "copay_per_fill": copay,
            "quantity_per_fill": quantity,
            "fills_per_year": 12,
            "estimated_annual_cost": annual_cost,
            "deductible_applies": tier >= 4,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82,
            rationale=f"Cost estimate for {drug}: ${copay}/fill, ${annual_cost}/year",
        )
