"""
Eminence HealthOS — Provider Attestation Agent (#45)
Layer 4 (Action): Routes AI-generated SOAP notes and codes to the provider
for review, edit, and digital signature before finalizing the clinical record.
"""

from __future__ import annotations

import hashlib
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

ATTESTATION_STATUSES = ["pending_review", "in_review", "approved", "rejected", "amended", "expired"]


class ProviderAttestationAgent(BaseAgent):
    """Routes AI-generated notes to provider for review and digital signature."""

    name = "provider_attestation"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Human-in-the-loop workflow for provider review, edit, and digital "
        "signature of AI-generated clinical documentation and billing codes"
    )
    min_confidence = 0.90

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "submit_for_review")

        if action == "submit_for_review":
            return self._submit_for_review(input_data)
        elif action == "get_review_status":
            return self._get_review_status(input_data)
        elif action == "approve":
            return self._approve(input_data)
        elif action == "reject":
            return self._reject(input_data)
        elif action == "request_amendment":
            return self._request_amendment(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown attestation action: {action}",
                status=AgentStatus.FAILED,
            )

    def _submit_for_review(self, input_data: AgentInput) -> AgentOutput:
        """Submit an AI-generated note and codes for provider review."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        note_id = ctx.get("note_id", str(uuid.uuid4()))
        encounter_id = ctx.get("encounter_id", "unknown")
        provider_id = ctx.get("provider_id", "unknown")
        soap = ctx.get("soap", {})
        coding = ctx.get("coding", {})

        # Generate document hash for integrity verification
        doc_content = str(soap) + str(coding)
        doc_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]

        attestation = {
            "attestation_id": str(uuid.uuid4()),
            "note_id": note_id,
            "encounter_id": encounter_id,
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "provider_id": provider_id,
            "status": "pending_review",
            "submitted_at": now.isoformat(),
            "review_deadline": "48 hours",
            "document_hash": doc_hash,
            "components_for_review": {
                "soap_note": bool(soap),
                "icd10_codes": bool(coding.get("icd10_codes")),
                "cpt_codes": bool(coding.get("cpt_codes")),
                "em_level": bool(coding.get("em_code")),
            },
            "ai_confidence": coding.get("coding_confidence", 0.87),
            "flagged_items": self._flag_items(soap, coding),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=attestation,
            confidence=0.95,
            rationale=(
                f"Note {note_id} submitted for provider review — "
                f"{len(attestation['flagged_items'])} items flagged for attention"
            ),
        )

    def _get_review_status(self, input_data: AgentInput) -> AgentOutput:
        """Check the current status of an attestation request."""
        ctx = input_data.context
        attestation_id = ctx.get("attestation_id", "unknown")

        result = {
            "attestation_id": attestation_id,
            "status": ctx.get("current_status", "pending_review"),
            "provider_viewed": ctx.get("provider_viewed", False),
            "time_in_queue_hours": ctx.get("time_in_queue_hours", 2.5),
            "reminder_sent": ctx.get("time_in_queue_hours", 0) > 24,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Attestation {attestation_id}: {result['status']}",
        )

    def _approve(self, input_data: AgentInput) -> AgentOutput:
        """Provider approves and signs the clinical documentation."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        attestation_id = ctx.get("attestation_id", str(uuid.uuid4()))
        provider_id = ctx.get("provider_id", "unknown")
        note_id = ctx.get("note_id", "unknown")

        # Generate digital signature
        sig_content = f"{attestation_id}:{provider_id}:{now.isoformat()}"
        signature = hashlib.sha256(sig_content.encode()).hexdigest()

        result = {
            "attestation_id": attestation_id,
            "note_id": note_id,
            "status": "approved",
            "approved_at": now.isoformat(),
            "provider_id": provider_id,
            "digital_signature": signature,
            "attestation_statement": (
                f"I, Provider {provider_id}, have reviewed and approve this AI-generated "
                "clinical documentation as an accurate representation of the encounter. "
                "I accept responsibility for this record."
            ),
            "finalized": True,
            "ready_for_billing": True,
            "next_steps": ["Submit to RCM for charge capture", "File in patient EHR"],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.98,
            rationale=f"Provider {provider_id} approved note {note_id} — ready for billing",
        )

    def _reject(self, input_data: AgentInput) -> AgentOutput:
        """Provider rejects the AI-generated documentation."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        attestation_id = ctx.get("attestation_id", str(uuid.uuid4()))
        reason = ctx.get("rejection_reason", "Requires significant corrections")

        result = {
            "attestation_id": attestation_id,
            "status": "rejected",
            "rejected_at": now.isoformat(),
            "reason": reason,
            "requires_regeneration": True,
            "next_steps": [
                "Provider may create manual note",
                "Re-run SOAP generator with corrections",
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Note rejected: {reason}",
        )

    def _request_amendment(self, input_data: AgentInput) -> AgentOutput:
        """Provider requests specific amendments to the AI-generated note."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        attestation_id = ctx.get("attestation_id", str(uuid.uuid4()))
        amendments = ctx.get("amendments", [])

        result = {
            "attestation_id": attestation_id,
            "status": "amendment_requested",
            "requested_at": now.isoformat(),
            "amendments": [
                {
                    "section": a.get("section", "unknown"),
                    "description": a.get("description", ""),
                    "original_text": a.get("original_text", ""),
                    "corrected_text": a.get("corrected_text", ""),
                }
                for a in amendments
            ],
            "total_amendments": len(amendments),
            "requires_re_review": True,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Amendment requested: {len(amendments)} changes for attestation {attestation_id}",
        )

    @staticmethod
    def _flag_items(soap: dict[str, Any], coding: dict[str, Any]) -> list[dict[str, str]]:
        """Identify items that need special provider attention."""
        flags: list[dict[str, str]] = []

        # Flag probable diagnoses
        for dx in coding.get("icd10_codes", []):
            if dx.get("certainty") == "probable":
                flags.append({
                    "type": "uncertain_diagnosis",
                    "item": f"{dx.get('code')} — {dx.get('description')}",
                    "message": "AI-suggested diagnosis with probable certainty — please confirm or remove",
                })

        # Flag high E&M level
        em = coding.get("em_code", {})
        if em.get("level", 0) >= 4:
            flags.append({
                "type": "high_em_level",
                "item": f"E&M {em.get('code')}",
                "message": "High-complexity visit level — ensure documentation supports MDM",
            })

        # Flag medication changes
        plan = soap.get("plan", {})
        for item in plan.get("items", []):
            if item.get("category") == "medication":
                flags.append({
                    "type": "medication_change",
                    "item": item.get("description", ""),
                    "message": "Medication change documented — verify dosage and instructions",
                })

        return flags
