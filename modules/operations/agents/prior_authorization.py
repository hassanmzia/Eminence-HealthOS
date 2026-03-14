"""
Eminence HealthOS — Prior Authorization Agent
Layer 4 (Action): Automates prior authorization requests by evaluating
clinical necessity, checking payer rules, assembling documentation,
and tracking authorization status through completion.
"""

from __future__ import annotations

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

logger = logging.getLogger(__name__)


# Common CPT codes requiring prior auth
PRIOR_AUTH_REQUIRED_CATEGORIES = {
    "advanced_imaging": ["70553", "74177", "74178", "71260", "72148"],
    "surgical_procedures": ["27447", "27130", "63030", "29881"],
    "specialty_drugs": ["J0897", "J9035", "J9271", "J2505"],
    "durable_medical_equipment": ["E0601", "E0470", "K0823", "E1390"],
    "genetic_testing": ["81479", "81455", "81432"],
    "behavioral_health": ["90837", "90847", "H0031"],
}

# Payer-specific auto-approval criteria
PAYER_AUTO_APPROVE_RULES = {
    "default": {"max_cost": 500, "routine_procedures": True},
    "medicare": {"max_cost": 0, "routine_procedures": False},
    "medicaid": {"max_cost": 0, "routine_procedures": False},
}


class PriorAuthorizationAgent(BaseAgent):
    """Automates prior authorization submission and tracking."""

    name = "prior_authorization"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Evaluates clinical necessity and manages prior authorization workflows"
    min_confidence = 0.80
    requires_hitl = False  # escalates to HITL when clinical review needed

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "evaluate")

        if action == "evaluate":
            return self._evaluate_auth_requirement(input_data)
        elif action == "submit":
            return await self._submit_authorization(input_data)
        elif action == "check_status":
            return self._check_status(input_data)
        elif action == "appeal":
            return self._initiate_appeal(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown prior auth action: {action}",
                status=AgentStatus.FAILED,
            )

    def _evaluate_auth_requirement(self, input_data: AgentInput) -> AgentOutput:
        """Evaluate whether a procedure/service requires prior authorization."""
        ctx = input_data.context
        cpt_codes = ctx.get("cpt_codes", [])
        diagnosis_codes = ctx.get("diagnosis_codes", [])
        payer = ctx.get("payer", "default").lower()
        estimated_cost = ctx.get("estimated_cost", 0)
        procedure_description = ctx.get("procedure_description", "")

        requires_auth = False
        auth_reasons = []
        matching_category = None

        # Check if any CPT codes require prior auth
        for category, codes in PRIOR_AUTH_REQUIRED_CATEGORIES.items():
            for code in cpt_codes:
                if code in codes:
                    requires_auth = True
                    matching_category = category
                    auth_reasons.append(
                        f"CPT {code} in category '{category}' requires prior authorization"
                    )

        # Check payer-specific rules
        payer_rules = PAYER_AUTO_APPROVE_RULES.get(payer, PAYER_AUTO_APPROVE_RULES["default"])
        if estimated_cost > payer_rules["max_cost"] and payer_rules["max_cost"] > 0:
            requires_auth = True
            auth_reasons.append(
                f"Estimated cost ${estimated_cost} exceeds payer auto-approve threshold"
            )

        # Clinical necessity scoring
        necessity_score = self._score_clinical_necessity(
            diagnosis_codes, cpt_codes, ctx.get("clinical_notes", "")
        )

        # Build documentation checklist
        required_docs = self._get_required_documents(matching_category, payer)

        result = {
            "requires_prior_auth": requires_auth,
            "auth_reasons": auth_reasons,
            "clinical_necessity_score": necessity_score,
            "matching_category": matching_category,
            "payer": payer,
            "estimated_cost": estimated_cost,
            "required_documents": required_docs,
            "recommendation": "submit_auth" if requires_auth else "proceed_without_auth",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        confidence = 0.92 if cpt_codes else 0.70

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Prior auth {'required' if requires_auth else 'not required'} — "
                f"{len(auth_reasons)} rule(s) triggered, "
                f"clinical necessity score: {necessity_score:.2f}"
            ),
        )

    async def _submit_authorization(self, input_data: AgentInput) -> AgentOutput:
        """Submit a prior authorization request to payer."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        payer = ctx.get("payer", "unknown")
        cpt_codes = ctx.get("cpt_codes", [])
        diagnosis_codes = ctx.get("diagnosis_codes", [])
        clinical_summary = ctx.get("clinical_summary", "")
        supporting_docs = ctx.get("supporting_documents", [])

        # Validate required fields
        missing = []
        if not cpt_codes:
            missing.append("cpt_codes")
        if not diagnosis_codes:
            missing.append("diagnosis_codes")
        if not clinical_summary:
            missing.append("clinical_summary")

        if missing:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "status": "incomplete",
                    "missing_fields": missing,
                },
                confidence=0.95,
                rationale=f"Cannot submit: missing required fields: {', '.join(missing)}",
            )

        # In production, this would call payer API / X12 278 transaction
        auth_reference = f"PA-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{patient_id[:8]}"

        # --- LLM: generate authorization narrative with clinical justification ---
        authorization_narrative = None
        try:
            procedure_description = ctx.get("procedure_description", "not specified")
            clinical_notes = ctx.get("clinical_notes", "")
            prompt = (
                f"Prior authorization request to {payer}.\n"
                f"CPT codes: {', '.join(cpt_codes)}\n"
                f"Diagnosis codes: {', '.join(diagnosis_codes)}\n"
                f"Procedure: {procedure_description}\n"
                f"Clinical summary: {clinical_summary}\n"
                f"Additional clinical notes: {clinical_notes or 'none'}\n"
                f"Supporting documents attached: {len(supporting_docs)}\n\n"
                f"Write a clinical justification narrative for this prior authorization "
                f"request. Explain the medical necessity, how the proposed treatment "
                f"relates to the diagnosis, and why alternative treatments may be "
                f"insufficient. Use language appropriate for payer medical reviewers."
            )
            llm_response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=(
                        "You are a clinical documentation specialist writing prior "
                        "authorization justifications. Craft compelling, evidence-based "
                        "narratives that demonstrate medical necessity. Reference "
                        "diagnosis codes, procedure codes, and clinical evidence. "
                        "Use clear, professional medical language that satisfies "
                        "payer utilization review criteria. Be thorough but concise."
                    ),
                    temperature=0.3,
                    max_tokens=1024,
                )
            )
            authorization_narrative = llm_response.content
        except Exception:
            logger.warning(
                "LLM authorization narrative generation failed; "
                "submitting without narrative justification",
                exc_info=True,
            )

        result = {
            "auth_reference": auth_reference,
            "status": "submitted",
            "payer": payer,
            "cpt_codes": cpt_codes,
            "diagnosis_codes": diagnosis_codes,
            "documents_attached": len(supporting_docs),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "expected_response_hours": 48 if payer != "medicare" else 72,
        }
        if authorization_narrative is not None:
            result["authorization_narrative"] = authorization_narrative

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Prior auth {auth_reference} submitted to {payer} for CPT {', '.join(cpt_codes)}",
        )

    def _check_status(self, input_data: AgentInput) -> AgentOutput:
        """Check status of an existing prior authorization."""
        ctx = input_data.context
        auth_reference = ctx.get("auth_reference", "")

        # In production, queries payer status API
        result = {
            "auth_reference": auth_reference,
            "status": "pending_review",
            "payer_response": None,
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "estimated_completion": "24-48 hours",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Status check for {auth_reference}: pending payer review",
        )

    def _initiate_appeal(self, input_data: AgentInput) -> AgentOutput:
        """Initiate appeal for a denied prior authorization."""
        ctx = input_data.context
        auth_reference = ctx.get("auth_reference", "")
        denial_reason = ctx.get("denial_reason", "")
        additional_evidence = ctx.get("additional_evidence", [])

        result = {
            "auth_reference": auth_reference,
            "appeal_status": "initiated",
            "denial_reason": denial_reason,
            "additional_evidence_count": len(additional_evidence),
            "appeal_type": "peer_to_peer" if denial_reason else "written",
            "initiated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Appeal initiated for {auth_reference} — {result['appeal_type']} review",
            status=AgentStatus.WAITING_HITL,
        )

    @staticmethod
    def _score_clinical_necessity(
        diagnosis_codes: list[str], cpt_codes: list[str], notes: str
    ) -> float:
        """Score clinical necessity based on available evidence."""
        score = 0.5  # baseline
        if diagnosis_codes:
            score += 0.2
        if len(diagnosis_codes) > 1:
            score += 0.1
        if cpt_codes:
            score += 0.1
        if notes and len(notes) > 50:
            score += 0.1
        return min(score, 1.0)

    @staticmethod
    def _get_required_documents(category: str | None, payer: str) -> list[str]:
        """Return list of documents needed for prior auth submission."""
        base_docs = [
            "Clinical summary / letter of medical necessity",
            "Relevant diagnosis codes (ICD-10)",
            "Procedure codes (CPT/HCPCS)",
            "Patient demographics and insurance info",
        ]

        category_docs = {
            "advanced_imaging": ["Prior imaging results", "Conservative treatment history"],
            "surgical_procedures": ["Operative report / surgical plan", "Failed conservative treatment documentation"],
            "specialty_drugs": ["Medication history", "Step therapy documentation"],
            "durable_medical_equipment": ["Prescription / order form", "Functional limitation documentation"],
            "genetic_testing": ["Family history documentation", "Genetic counseling referral"],
            "behavioral_health": ["Treatment plan", "Assessment / evaluation report"],
        }

        if category and category in category_docs:
            base_docs.extend(category_docs[category])

        return base_docs
