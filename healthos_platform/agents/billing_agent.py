"""
Eminence HealthOS — Billing Agent
Tier 5 (Action): Automated CPT code selection for RPM billing,
claim preparation, and submission per CMS 2024 guidelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentTier

logger = structlog.get_logger()

# ── RPM CPT Codes (CMS 2024) ────────────────────────────────────────────────

RPM_CPT_CODES = {
    "99453": {
        "description": "Remote physiologic monitoring setup (one-time)",
        "requirements": {"device_setup": True},
        "reimbursement_estimate": 19.32,
    },
    "99454": {
        "description": "Remote physiologic monitoring device supply (monthly)",
        "requirements": {"monitoring_days": 16},
        "reimbursement_estimate": 55.72,
    },
    "99457": {
        "description": "Remote physiologic monitoring treatment management (first 20 min)",
        "requirements": {"clinical_time_minutes": 20, "interactive_communication": True},
        "reimbursement_estimate": 50.94,
    },
    "99458": {
        "description": "Remote physiologic monitoring treatment management (additional 20 min)",
        "requirements": {"clinical_time_minutes": 40},
        "reimbursement_estimate": 41.17,
    },
}

# ── E/M CPT Codes ───────────────────────────────────────────────────────────

EM_CPT_CODES = {
    "99213": {
        "description": "Office visit, established patient, low complexity",
        "level": "low",
        "reimbursement_estimate": 92.00,
    },
    "99214": {
        "description": "Office visit, established patient, moderate complexity",
        "level": "moderate",
        "reimbursement_estimate": 130.00,
    },
    "99215": {
        "description": "Office visit, established patient, high complexity",
        "level": "high",
        "reimbursement_estimate": 175.00,
    },
    "99241": {
        "description": "Telehealth visit, low complexity",
        "level": "low",
        "reimbursement_estimate": 85.00,
    },
    "99242": {
        "description": "Telehealth visit, moderate complexity",
        "level": "moderate",
        "reimbursement_estimate": 120.00,
    },
}


class BillingAgent(BaseAgent):
    """
    Automated CPT code generation and claim preparation for RPM billing.
    Evaluates monitoring data, clinical time, and patient encounters to
    select appropriate CPT codes per CMS 2024 guidelines.
    """

    name = "billing_agent"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = "Automated CPT code selection and RPM claim preparation"
    min_confidence = 0.85
    requires_hitl = True  # Always require review for billing

    async def process(self, input_data: AgentInput) -> AgentOutput:
        context = input_data.context or {}
        patient_id = str(input_data.patient_id or "")

        # Extract RPM episode data
        monitoring_days = context.get("monitoring_days", 0)
        clinical_time_minutes = context.get("clinical_time_minutes", 0)
        device_setup_complete = context.get("device_setup_complete", False)
        interactive_communication = context.get("interactive_communication", False)
        encounter_type = context.get("encounter_type", "")
        encounter_complexity = context.get("encounter_complexity", "low")
        session_count = context.get("session_count", 0)

        # Determine eligible CPT codes
        eligible_codes = self._evaluate_rpm_eligibility(
            monitoring_days=monitoring_days,
            clinical_time_minutes=clinical_time_minutes,
            device_setup_complete=device_setup_complete,
            interactive_communication=interactive_communication,
        )

        # Add E/M codes if encounter-based
        if encounter_type:
            em_code = self._select_em_code(encounter_type, encounter_complexity)
            if em_code:
                eligible_codes.append(em_code)

        # Calculate estimated reimbursement
        total_reimbursement = sum(c.get("reimbursement_estimate", 0) for c in eligible_codes)

        # Build claim
        claim = self._build_claim(
            patient_id=patient_id,
            codes=eligible_codes,
            total_reimbursement=total_reimbursement,
        )

        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            confidence=0.90 if eligible_codes else 0.50,
            result={
                "patient_id": patient_id,
                "eligible_cpt_codes": eligible_codes,
                "total_estimated_reimbursement": round(total_reimbursement, 2),
                "claim": claim,
                "qualification_summary": {
                    "monitoring_days": monitoring_days,
                    "clinical_time_minutes": clinical_time_minutes,
                    "device_setup": device_setup_complete,
                    "interactive_communication": interactive_communication,
                    "session_count": session_count,
                },
            },
            rationale=(
                f"Identified {len(eligible_codes)} eligible CPT codes — "
                f"estimated reimbursement ${total_reimbursement:.2f}"
            ),
            requires_hitl=True,
            hitl_reason="Billing codes require clinician review before submission",
        )

    def _evaluate_rpm_eligibility(
        self,
        monitoring_days: int,
        clinical_time_minutes: int,
        device_setup_complete: bool,
        interactive_communication: bool,
    ) -> list[dict[str, Any]]:
        """Evaluate RPM CPT code eligibility per CMS 2024 guidelines."""
        codes: list[dict[str, Any]] = []

        # 99453: Device setup (one-time)
        if device_setup_complete:
            codes.append({
                "cpt_code": "99453",
                **RPM_CPT_CODES["99453"],
                "qualified": True,
                "qualification_reason": "Device setup completed",
            })

        # 99454: Monthly device supply (requires >= 16 monitoring days)
        if monitoring_days >= 16:
            codes.append({
                "cpt_code": "99454",
                **RPM_CPT_CODES["99454"],
                "qualified": True,
                "qualification_reason": f"{monitoring_days} monitoring days (min: 16)",
            })

        # 99457: First 20 min of clinical time
        if clinical_time_minutes >= 20 and interactive_communication:
            codes.append({
                "cpt_code": "99457",
                **RPM_CPT_CODES["99457"],
                "qualified": True,
                "qualification_reason": (
                    f"{clinical_time_minutes} min clinical time with "
                    f"interactive communication"
                ),
            })

        # 99458: Additional 20 min (requires 99457 and >= 40 min total)
        if clinical_time_minutes >= 40 and interactive_communication:
            codes.append({
                "cpt_code": "99458",
                **RPM_CPT_CODES["99458"],
                "qualified": True,
                "qualification_reason": (
                    f"{clinical_time_minutes} min total clinical time "
                    f"(additional 20 min block)"
                ),
            })

        return codes

    def _select_em_code(
        self, encounter_type: str, complexity: str
    ) -> dict[str, Any] | None:
        """Select the appropriate E/M CPT code based on encounter type and complexity."""
        if encounter_type == "telehealth":
            code_map = {"low": "99241", "moderate": "99242"}
        else:
            code_map = {"low": "99213", "moderate": "99214", "high": "99215"}

        code = code_map.get(complexity)
        if code and code in EM_CPT_CODES:
            return {
                "cpt_code": code,
                **EM_CPT_CODES[code],
                "qualified": True,
                "qualification_reason": f"{encounter_type} encounter, {complexity} complexity",
            }
        return None

    def _build_claim(
        self,
        patient_id: str,
        codes: list[dict[str, Any]],
        total_reimbursement: float,
    ) -> dict[str, Any]:
        """Build a structured claim for submission."""
        return {
            "patient_id": patient_id,
            "claim_type": "CMS-1500",
            "service_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "cpt_codes": [c["cpt_code"] for c in codes],
            "total_charges": round(total_reimbursement, 2),
            "status": "draft",
            "requires_pre_authorization": any(
                c["cpt_code"] in ("99457", "99458") for c in codes
            ),
            "line_items": [
                {
                    "cpt_code": c["cpt_code"],
                    "description": c["description"],
                    "charge": c.get("reimbursement_estimate", 0),
                    "units": 1,
                }
                for c in codes
            ],
        }
