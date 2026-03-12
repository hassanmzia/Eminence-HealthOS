"""
Eminence HealthOS — Charge Capture Agent (#46)
Layer 4 (Action): Identifies billable services from encounters, procedures,
and care activities, producing charge entries for the billing pipeline.
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

# Fee schedule (simplified national average RVU-based)
FEE_SCHEDULE: dict[str, dict[str, Any]] = {
    "99211": {"rvu": 0.70, "description": "Office visit, minimal"},
    "99212": {"rvu": 1.58, "description": "Office visit, straightforward"},
    "99213": {"rvu": 2.45, "description": "Office visit, low complexity"},
    "99214": {"rvu": 3.62, "description": "Office visit, moderate complexity"},
    "99215": {"rvu": 4.98, "description": "Office visit, high complexity"},
    "80048": {"rvu": 1.42, "description": "Basic metabolic panel"},
    "80053": {"rvu": 1.57, "description": "Comprehensive metabolic panel"},
    "80069": {"rvu": 1.56, "description": "Renal function panel"},
    "85025": {"rvu": 0.88, "description": "CBC with differential"},
    "93000": {"rvu": 1.32, "description": "ECG with interpretation"},
    "36415": {"rvu": 0.17, "description": "Venipuncture"},
    "99441": {"rvu": 1.30, "description": "Telephone E&M, 5-10 min"},
    "99442": {"rvu": 2.45, "description": "Telephone E&M, 11-20 min"},
    "99443": {"rvu": 3.62, "description": "Telephone E&M, 21-30 min"},
}

CONVERSION_FACTOR = 33.89  # 2024 Medicare conversion factor


class ChargeCaptureAgent(BaseAgent):
    """Identifies billable services and produces charge entries."""

    name = "charge_capture"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Automated charge capture — identifies billable services from encounters "
        "and care activities, producing charge entries with RVU-based pricing"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "capture_charges")

        if action == "capture_charges":
            return self._capture_charges(input_data)
        elif action == "review_encounter":
            return self._review_encounter(input_data)
        elif action == "estimate_reimbursement":
            return self._estimate_reimbursement(input_data)
        elif action == "missed_charge_scan":
            return self._missed_charge_scan(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown charge capture action: {action}",
                status=AgentStatus.FAILED,
            )

    def _capture_charges(self, input_data: AgentInput) -> AgentOutput:
        """Capture all billable charges from an encounter."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        encounter_id = ctx.get("encounter_id", str(uuid.uuid4()))

        em_code = ctx.get("em_code", {})
        cpt_codes = ctx.get("cpt_codes", [])
        icd10_codes = ctx.get("icd10_codes", [])

        charges: list[dict[str, Any]] = []
        total_rvu = 0.0

        # E&M charge
        if em_code:
            code = em_code.get("code", "99213")
            fee_info = FEE_SCHEDULE.get(code, {"rvu": 2.45, "description": "Office visit"})
            rvu = fee_info["rvu"]
            total_rvu += rvu
            charges.append({
                "charge_id": str(uuid.uuid4()),
                "code": code,
                "code_type": "E&M",
                "description": fee_info["description"],
                "rvu": rvu,
                "estimated_amount": round(rvu * CONVERSION_FACTOR, 2),
                "icd10_pointers": [c.get("code", "") for c in (icd10_codes or [])[:4]],
                "units": 1,
            })

        # Procedure charges
        for proc in cpt_codes:
            code = proc.get("cpt", proc.get("code", ""))
            fee_info = FEE_SCHEDULE.get(code, {"rvu": 1.0, "description": proc.get("description", "")})
            rvu = fee_info["rvu"]
            total_rvu += rvu
            charges.append({
                "charge_id": str(uuid.uuid4()),
                "code": code,
                "code_type": "CPT",
                "description": fee_info.get("description", proc.get("description", "")),
                "rvu": rvu,
                "estimated_amount": round(rvu * CONVERSION_FACTOR, 2),
                "icd10_pointers": [c.get("code", "") for c in (icd10_codes or [])[:4]],
                "units": proc.get("units", 1),
            })

        total_estimated = round(total_rvu * CONVERSION_FACTOR, 2)

        result = {
            "capture_id": str(uuid.uuid4()),
            "encounter_id": encounter_id,
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "captured_at": now.isoformat(),
            "charges": charges,
            "total_charges": len(charges),
            "total_rvu": round(total_rvu, 2),
            "total_estimated_amount": total_estimated,
            "conversion_factor": CONVERSION_FACTOR,
            "status": "ready_for_claim",
            "diagnosis_codes": [c.get("code", "") for c in (icd10_codes or [])],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=(
                f"Captured {len(charges)} charges for encounter {encounter_id} — "
                f"total estimated ${total_estimated}"
            ),
        )

    def _review_encounter(self, input_data: AgentInput) -> AgentOutput:
        """Review an encounter for billable services that may have been missed."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        encounter_id = ctx.get("encounter_id", "unknown")

        services_found = ctx.get("services", [])
        existing_charges = ctx.get("existing_charges", [])
        existing_codes = {c.get("code") for c in existing_charges}

        missed: list[dict[str, Any]] = []
        for svc in services_found:
            code = svc.get("code", "")
            if code and code not in existing_codes:
                fee_info = FEE_SCHEDULE.get(code, {"rvu": 1.0, "description": svc.get("description", "")})
                missed.append({
                    "code": code,
                    "description": fee_info.get("description", ""),
                    "estimated_amount": round(fee_info["rvu"] * CONVERSION_FACTOR, 2),
                    "reason": svc.get("reason", "Service identified in encounter documentation"),
                })

        result = {
            "encounter_id": encounter_id,
            "reviewed_at": now.isoformat(),
            "existing_charges": len(existing_charges),
            "missed_charges": missed,
            "potential_revenue_recovery": round(sum(m["estimated_amount"] for m in missed), 2),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Review found {len(missed)} missed charges for encounter {encounter_id}",
        )

    def _estimate_reimbursement(self, input_data: AgentInput) -> AgentOutput:
        """Estimate reimbursement for a set of codes by payer type."""
        ctx = input_data.context
        codes = ctx.get("codes", [])
        payer_type = ctx.get("payer_type", "medicare")

        # Payer-specific multipliers
        multipliers = {
            "medicare": 1.0,
            "medicaid": 0.72,
            "commercial": 1.45,
            "self_pay": 2.5,
        }
        multiplier = multipliers.get(payer_type, 1.0)

        estimates = []
        total = 0.0
        for code in codes:
            code_str = code.get("code", code) if isinstance(code, dict) else code
            fee_info = FEE_SCHEDULE.get(code_str, {"rvu": 1.0, "description": ""})
            amount = round(fee_info["rvu"] * CONVERSION_FACTOR * multiplier, 2)
            total += amount
            estimates.append({
                "code": code_str,
                "description": fee_info.get("description", ""),
                "medicare_amount": round(fee_info["rvu"] * CONVERSION_FACTOR, 2),
                "payer_amount": amount,
            })

        result = {
            "payer_type": payer_type,
            "multiplier": multiplier,
            "estimates": estimates,
            "total_estimated": round(total, 2),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Estimated ${round(total, 2)} reimbursement for {len(codes)} codes ({payer_type})",
        )

    def _missed_charge_scan(self, input_data: AgentInput) -> AgentOutput:
        """Scan a batch of encounters for potentially missed charges."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        encounters = ctx.get("encounters", [])

        findings: list[dict[str, Any]] = []
        total_recovery = 0.0

        for enc in encounters:
            enc_id = enc.get("encounter_id", "unknown")
            has_em = enc.get("has_em_code", True)
            has_labs = enc.get("labs_ordered", False)
            has_lab_charge = enc.get("lab_charge_captured", False)

            if has_labs and not has_lab_charge:
                amount = round(1.42 * CONVERSION_FACTOR, 2)
                total_recovery += amount
                findings.append({
                    "encounter_id": enc_id,
                    "issue": "Lab ordered but no lab charge captured",
                    "suggested_code": "80048",
                    "estimated_amount": amount,
                })

            if not has_em:
                amount = round(2.45 * CONVERSION_FACTOR, 2)
                total_recovery += amount
                findings.append({
                    "encounter_id": enc_id,
                    "issue": "No E&M code captured for encounter",
                    "suggested_code": "99213",
                    "estimated_amount": amount,
                })

        result = {
            "scanned_at": now.isoformat(),
            "encounters_scanned": len(encounters),
            "findings": findings,
            "total_potential_recovery": round(total_recovery, 2),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.83,
            rationale=f"Scanned {len(encounters)} encounters — {len(findings)} missed charges (${round(total_recovery, 2)})",
        )
