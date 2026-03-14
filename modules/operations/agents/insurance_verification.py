"""
Eminence HealthOS — Insurance Verification Agent
Layer 3 (Decisioning): Verifies patient insurance coverage, eligibility,
benefits, and co-pay information before appointments and procedures.
"""

from __future__ import annotations

import json
import logging
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

logger = logging.getLogger("healthos.agent.insurance_verification")


class InsuranceVerificationAgent(BaseAgent):
    """Verifies patient insurance eligibility and coverage details."""

    name = "insurance_verification"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Verifies insurance coverage, eligibility, benefits, and co-pay details"
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "verify_eligibility")

        if action == "verify_eligibility":
            return await self._verify_eligibility_with_llm(input_data)
        elif action == "check_benefits":
            return await self._check_benefits_with_llm(input_data)
        elif action == "estimate_cost":
            return await self._estimate_cost_with_llm(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown insurance verification action: {action}",
                status=AgentStatus.FAILED,
            )

    def _verify_eligibility(self, input_data: AgentInput) -> AgentOutput:
        """Verify patient insurance eligibility and active coverage."""
        ctx = input_data.context
        member_id = ctx.get("member_id", "")
        group_number = ctx.get("group_number", "")
        payer = ctx.get("payer", "")
        date_of_service = ctx.get("date_of_service", datetime.now(timezone.utc).isoformat())
        subscriber_dob = ctx.get("subscriber_dob", "")

        # Validate required fields
        if not member_id or not payer:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "eligible": False,
                    "status": "incomplete",
                    "missing_fields": [
                        f for f in ["member_id", "payer"]
                        if not ctx.get(f)
                    ],
                },
                confidence=0.95,
                rationale="Cannot verify eligibility: missing required insurance information",
            )

        # In production, this calls X12 270/271 eligibility inquiry
        eligibility = self._simulate_eligibility_check(member_id, group_number, payer)

        result = {
            "eligible": eligibility["active"],
            "payer": payer,
            "member_id": member_id,
            "group_number": group_number,
            "plan_name": eligibility["plan_name"],
            "plan_type": eligibility["plan_type"],
            "effective_date": eligibility["effective_date"],
            "termination_date": eligibility["termination_date"],
            "coverage_status": "active" if eligibility["active"] else "inactive",
            "subscriber_relationship": eligibility["relationship"],
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "date_of_service": date_of_service,
        }

        confidence = 0.92 if eligibility["active"] else 0.88

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Insurance verification for {payer} member {member_id}: "
                f"{'eligible' if eligibility['active'] else 'NOT eligible'} — "
                f"{eligibility['plan_name']}"
            ),
        )

    def _check_benefits(self, input_data: AgentInput) -> AgentOutput:
        """Check specific benefits and coverage details."""
        ctx = input_data.context
        member_id = ctx.get("member_id", "")
        payer = ctx.get("payer", "")
        service_type = ctx.get("service_type", "medical")
        cpt_codes = ctx.get("cpt_codes", [])

        benefits = self._simulate_benefits_check(payer, service_type)

        result = {
            "member_id": member_id,
            "payer": payer,
            "service_type": service_type,
            "benefits": benefits,
            "cpt_codes_checked": cpt_codes,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=(
                f"Benefits check for {service_type}: "
                f"copay ${benefits['copay']}, "
                f"deductible ${benefits['deductible_remaining']} remaining"
            ),
        )

    def _estimate_patient_cost(self, input_data: AgentInput) -> AgentOutput:
        """Estimate patient out-of-pocket costs for a service."""
        ctx = input_data.context
        payer = ctx.get("payer", "")
        cpt_codes = ctx.get("cpt_codes", [])
        estimated_charges = ctx.get("estimated_charges", 0)
        service_type = ctx.get("service_type", "medical")

        benefits = self._simulate_benefits_check(payer, service_type)

        # Calculate patient responsibility
        deductible_applies = min(estimated_charges, benefits["deductible_remaining"])
        after_deductible = estimated_charges - deductible_applies
        coinsurance_amount = after_deductible * (benefits["coinsurance_pct"] / 100)
        copay = benefits["copay"]

        patient_responsibility = min(
            copay + deductible_applies + coinsurance_amount,
            benefits["out_of_pocket_max_remaining"],
        )

        result = {
            "estimated_charges": estimated_charges,
            "deductible_applied": deductible_applies,
            "coinsurance_amount": round(coinsurance_amount, 2),
            "copay": copay,
            "patient_responsibility": round(patient_responsibility, 2),
            "plan_pays": round(estimated_charges - patient_responsibility, 2),
            "out_of_pocket_max_remaining": benefits["out_of_pocket_max_remaining"],
            "note": "Estimate only — actual costs may vary based on final billing",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.75,
            rationale=(
                f"Cost estimate: ${estimated_charges} charges, "
                f"patient responsibility ~${patient_responsibility:.2f}"
            ),
        )

    async def _verify_eligibility_with_llm(self, input_data: AgentInput) -> AgentOutput:
        output = self._verify_eligibility(input_data)
        output = await self._add_verification_summary(output)
        return output

    async def _check_benefits_with_llm(self, input_data: AgentInput) -> AgentOutput:
        output = self._check_benefits(input_data)
        output = await self._add_verification_summary(output)
        return output

    async def _estimate_cost_with_llm(self, input_data: AgentInput) -> AgentOutput:
        output = self._estimate_patient_cost(input_data)
        output = await self._add_verification_summary(output)
        return output

    async def _add_verification_summary(self, output: AgentOutput) -> AgentOutput:
        """Add LLM-generated verification summary to any output."""
        try:
            result_data = output.result if hasattr(output, "result") else {}
            prompt = (
                "You are an insurance verification specialist. "
                "Analyze the following insurance verification results and provide a concise "
                "coverage analysis summary that highlights key findings, coverage status, "
                "patient financial responsibility, and any action items for the front desk staff.\n\n"
                f"Verification results: {json.dumps(result_data, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an insurance verification narrator for a healthcare operations platform. "
                    "Provide clear, actionable summaries of coverage analysis that help front desk "
                    "and billing staff understand patient coverage quickly. Highlight any issues "
                    "that need attention."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if isinstance(result_data, dict):
                result_data["verification_summary"] = resp.content
        except Exception:
            logger.warning("LLM verification_summary generation failed; continuing without it")
        return output

    @staticmethod
    def _simulate_eligibility_check(member_id: str, group_number: str, payer: str) -> dict:
        """Simulate an eligibility response (production: X12 270/271)."""
        return {
            "active": True,
            "plan_name": f"{payer.title()} Standard PPO",
            "plan_type": "PPO",
            "effective_date": "2025-01-01",
            "termination_date": None,
            "relationship": "self",
        }

    @staticmethod
    def _simulate_benefits_check(payer: str, service_type: str) -> dict:
        """Simulate benefits response (production: payer API / X12)."""
        benefits_map = {
            "medical": {
                "copay": 30,
                "deductible_remaining": 750,
                "coinsurance_pct": 20,
                "out_of_pocket_max_remaining": 4500,
                "prior_auth_required": False,
                "in_network": True,
            },
            "specialist": {
                "copay": 50,
                "deductible_remaining": 750,
                "coinsurance_pct": 20,
                "out_of_pocket_max_remaining": 4500,
                "prior_auth_required": False,
                "in_network": True,
            },
            "imaging": {
                "copay": 100,
                "deductible_remaining": 750,
                "coinsurance_pct": 30,
                "out_of_pocket_max_remaining": 4500,
                "prior_auth_required": True,
                "in_network": True,
            },
            "surgical": {
                "copay": 250,
                "deductible_remaining": 750,
                "coinsurance_pct": 20,
                "out_of_pocket_max_remaining": 4500,
                "prior_auth_required": True,
                "in_network": True,
            },
        }
        return benefits_map.get(service_type, benefits_map["medical"])
