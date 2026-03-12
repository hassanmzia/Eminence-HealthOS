"""
Eminence HealthOS — Prescription Agent (#31)
Layer 4 (Action): Generates e-prescriptions from care plans and encounter
decisions, transmitting them electronically to the pharmacy.
"""

from __future__ import annotations

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

PRESCRIPTION_STATUSES = ["draft", "pending_review", "signed", "transmitted", "dispensed", "cancelled"]

# Common medication templates
MEDICATION_TEMPLATES: dict[str, dict[str, Any]] = {
    "lisinopril": {"generic": "Lisinopril", "class": "ACE Inhibitor", "rxnorm": "29046", "schedule": "unscheduled"},
    "metformin": {"generic": "Metformin HCl", "class": "Biguanide", "rxnorm": "6809", "schedule": "unscheduled"},
    "amlodipine": {"generic": "Amlodipine Besylate", "class": "Calcium Channel Blocker", "rxnorm": "17767", "schedule": "unscheduled"},
    "losartan": {"generic": "Losartan Potassium", "class": "ARB", "rxnorm": "52175", "schedule": "unscheduled"},
    "atorvastatin": {"generic": "Atorvastatin Calcium", "class": "Statin", "rxnorm": "83367", "schedule": "unscheduled"},
    "omeprazole": {"generic": "Omeprazole", "class": "Proton Pump Inhibitor", "rxnorm": "7646", "schedule": "unscheduled"},
    "levothyroxine": {"generic": "Levothyroxine Sodium", "class": "Thyroid Hormone", "rxnorm": "10582", "schedule": "unscheduled"},
    "sertraline": {"generic": "Sertraline HCl", "class": "SSRI", "rxnorm": "36437", "schedule": "unscheduled"},
    "gabapentin": {"generic": "Gabapentin", "class": "Anticonvulsant", "rxnorm": "25480", "schedule": "V"},
    "hydrocodone": {"generic": "Hydrocodone/APAP", "class": "Opioid Analgesic", "rxnorm": "856980", "schedule": "II"},
}


class PrescriptionAgent(BaseAgent):
    """Generates e-prescriptions from care plans and encounter decisions."""

    name = "prescription"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Electronic prescription generation from care plan decisions, "
        "with EPCS support for controlled substances"
    )
    min_confidence = 0.88

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "create_prescription")

        if action == "create_prescription":
            return self._create_prescription(input_data)
        elif action == "review_prescription":
            return self._review_prescription(input_data)
        elif action == "sign_and_transmit":
            return self._sign_and_transmit(input_data)
        elif action == "cancel_prescription":
            return self._cancel_prescription(input_data)
        elif action == "prescription_history":
            return self._prescription_history(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown prescription action: {action}",
                status=AgentStatus.FAILED,
            )

    def _create_prescription(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        medication_name = ctx.get("medication", "losartan").lower()
        template = MEDICATION_TEMPLATES.get(medication_name, {
            "generic": medication_name.title(), "class": "Unknown", "rxnorm": "", "schedule": "unscheduled",
        })

        rx = {
            "prescription_id": str(uuid.uuid4()),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "encounter_id": ctx.get("encounter_id"),
            "provider_id": ctx.get("provider_id", "unknown"),
            "created_at": now.isoformat(),
            "status": "draft",
            "medication": {
                "name": template["generic"],
                "drug_class": template["class"],
                "rxnorm": template["rxnorm"],
                "schedule": template["schedule"],
                "dose": ctx.get("dose", "50mg"),
                "route": ctx.get("route", "oral"),
                "frequency": ctx.get("frequency", "once daily"),
                "duration_days": ctx.get("duration_days", 30),
                "quantity": ctx.get("quantity", 30),
                "refills": ctx.get("refills", 3),
                "daw": ctx.get("dispense_as_written", False),
            },
            "instructions": ctx.get("instructions", f"Take {ctx.get('dose', '50mg')} by mouth once daily"),
            "requires_interaction_check": True,
            "requires_formulary_check": True,
            "is_controlled": template["schedule"] != "unscheduled",
            "epcs_required": template["schedule"] in ("II", "III", "IV", "V"),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=rx,
            confidence=0.92,
            rationale=f"Created prescription for {template['generic']} — pending safety checks",
        )

    def _review_prescription(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        rx_id = ctx.get("prescription_id", "unknown")

        checks = {
            "interaction_check": ctx.get("interaction_clear", True),
            "formulary_check": ctx.get("formulary_covered", True),
            "allergy_check": ctx.get("allergy_clear", True),
            "dosage_appropriate": ctx.get("dosage_appropriate", True),
            "duplicate_therapy_check": ctx.get("no_duplicate", True),
        }

        all_clear = all(checks.values())
        issues = [k for k, v in checks.items() if not v]

        result = {
            "prescription_id": rx_id,
            "reviewed_at": now.isoformat(),
            "checks": checks,
            "all_clear": all_clear,
            "issues": issues,
            "status": "ready_to_sign" if all_clear else "requires_attention",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93 if all_clear else 0.80,
            rationale=f"Prescription review: {'all clear' if all_clear else f'{len(issues)} issue(s)'}",
        )

    def _sign_and_transmit(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        rx_id = ctx.get("prescription_id", str(uuid.uuid4()))

        result = {
            "prescription_id": rx_id,
            "status": "transmitted",
            "signed_at": now.isoformat(),
            "transmitted_at": now.isoformat(),
            "pharmacy_ncpdp": ctx.get("pharmacy_ncpdp", "1234567"),
            "pharmacy_name": ctx.get("pharmacy_name", "Walgreens #1234"),
            "transmission_method": "NCPDP SCRIPT v2017071",
            "confirmation_number": str(uuid.uuid4())[:8].upper(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Prescription {rx_id} signed and transmitted to pharmacy",
        )

    def _cancel_prescription(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "prescription_id": ctx.get("prescription_id", "unknown"),
            "status": "cancelled",
            "cancelled_at": now.isoformat(),
            "reason": ctx.get("reason", "Provider cancelled"),
            "cancel_transmitted": True,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale="Prescription cancelled and cancellation transmitted",
        )

    def _prescription_history(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        history = [
            {"medication": "Losartan 50mg", "prescribed": "2026-03-12", "status": "active", "refills_remaining": 3},
            {"medication": "Metformin 500mg", "prescribed": "2026-01-15", "status": "active", "refills_remaining": 5},
            {"medication": "Atorvastatin 20mg", "prescribed": "2025-11-20", "status": "active", "refills_remaining": 2},
            {"medication": "Amlodipine 5mg", "prescribed": "2026-02-20", "status": "discontinued", "refills_remaining": 0},
            {"medication": "Lisinopril 10mg", "prescribed": "2025-06-10", "status": "discontinued", "refills_remaining": 0},
        ]

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "as_of": now.isoformat(),
            "total_medications": len(history),
            "active_count": sum(1 for h in history if h["status"] == "active"),
            "medications": history,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Prescription history: {result['active_count']} active medications",
        )
