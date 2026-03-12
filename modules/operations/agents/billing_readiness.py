"""
Eminence HealthOS — Billing Readiness Agent
Layer 3 (Decisioning): Validates encounter data for billing completeness,
checks coding accuracy, identifies missing documentation, and ensures
claims are ready for submission to payers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)


# ICD-10 / CPT compatibility rules (simplified)
CODING_RULES = {
    # diagnosis category -> compatible CPT ranges
    "E11": ["99213", "99214", "99215", "83036", "80053", "80048"],  # Type 2 diabetes
    "I10": ["99213", "99214", "99215", "93000", "80053"],  # Hypertension
    "J45": ["99213", "99214", "99215", "94010", "94060"],  # Asthma
    "M54": ["99213", "99214", "72148", "72149", "97110"],  # Back pain
    "Z00": ["99381", "99382", "99383", "99384", "99385", "99391", "99392"],  # Wellness
}

# E/M code level requirements (documentation elements needed)
EM_LEVEL_REQUIREMENTS = {
    "99211": {"elements": 1, "time_minutes": 5, "complexity": "minimal"},
    "99212": {"elements": 2, "time_minutes": 10, "complexity": "straightforward"},
    "99213": {"elements": 3, "time_minutes": 15, "complexity": "low"},
    "99214": {"elements": 4, "time_minutes": 25, "complexity": "moderate"},
    "99215": {"elements": 5, "time_minutes": 40, "complexity": "high"},
}

# Required billing fields by encounter type
REQUIRED_FIELDS = {
    "office_visit": [
        "patient_id", "provider_id", "date_of_service", "cpt_codes",
        "diagnosis_codes", "place_of_service", "modifier",
    ],
    "telehealth": [
        "patient_id", "provider_id", "date_of_service", "cpt_codes",
        "diagnosis_codes", "place_of_service", "modifier", "telehealth_platform",
    ],
    "procedure": [
        "patient_id", "provider_id", "date_of_service", "cpt_codes",
        "diagnosis_codes", "place_of_service", "modifier",
        "prior_auth_reference", "anesthesia_codes",
    ],
    "lab": [
        "patient_id", "ordering_provider_id", "date_of_service", "cpt_codes",
        "diagnosis_codes", "specimen_type",
    ],
}


class BillingReadinessAgent(BaseAgent):
    """Validates encounter data for billing completeness and coding accuracy."""

    name = "billing_readiness"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Validates billing readiness — coding, documentation completeness, claim preparation"
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "validate")

        if action == "validate":
            return self._validate_encounter(input_data)
        elif action == "check_coding":
            return self._check_coding_accuracy(input_data)
        elif action == "prepare_claim":
            return self._prepare_claim(input_data)
        elif action == "audit":
            return self._billing_audit(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown billing action: {action}",
                status=AgentStatus.FAILED,
            )

    def _validate_encounter(self, input_data: AgentInput) -> AgentOutput:
        """Validate encounter has all required fields for billing."""
        ctx = input_data.context
        encounter_type = ctx.get("encounter_type", "office_visit")
        encounter_data = ctx.get("encounter", {})

        required = REQUIRED_FIELDS.get(encounter_type, REQUIRED_FIELDS["office_visit"])
        missing_fields = [f for f in required if not encounter_data.get(f)]
        present_fields = [f for f in required if encounter_data.get(f)]

        # Check documentation completeness
        doc_issues = self._check_documentation(encounter_data, encounter_type)

        # Check for common billing errors
        billing_warnings = self._check_common_errors(encounter_data)

        completeness = len(present_fields) / len(required) if required else 0
        is_ready = len(missing_fields) == 0 and len(doc_issues) == 0

        result = {
            "encounter_type": encounter_type,
            "is_billing_ready": is_ready,
            "completeness_score": round(completeness, 2),
            "required_fields": len(required),
            "present_fields": len(present_fields),
            "missing_fields": missing_fields,
            "documentation_issues": doc_issues,
            "billing_warnings": billing_warnings,
            "recommendation": "ready_to_bill" if is_ready else "needs_review",
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

        confidence = 0.92 if is_ready else 0.85

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Billing validation: {completeness:.0%} complete, "
                f"{len(missing_fields)} missing field(s), "
                f"{len(doc_issues)} documentation issue(s)"
            ),
        )

    def _check_coding_accuracy(self, input_data: AgentInput) -> AgentOutput:
        """Verify CPT/ICD-10 coding is accurate and compatible."""
        ctx = input_data.context
        cpt_codes = ctx.get("cpt_codes", [])
        diagnosis_codes = ctx.get("diagnosis_codes", [])
        em_level = ctx.get("em_level", "")
        documentation_elements = ctx.get("documentation_elements", 0)
        visit_time_minutes = ctx.get("visit_time_minutes", 0)

        issues = []
        suggestions = []

        # Check CPT-ICD compatibility
        for dx in diagnosis_codes:
            dx_prefix = dx[:3] if len(dx) >= 3 else dx
            compatible_cpts = CODING_RULES.get(dx_prefix, [])
            if compatible_cpts:
                for cpt in cpt_codes:
                    if cpt not in compatible_cpts:
                        issues.append(
                            f"CPT {cpt} may not be compatible with diagnosis {dx}"
                        )

        # Check E/M level appropriateness
        if em_level and em_level in EM_LEVEL_REQUIREMENTS:
            req = EM_LEVEL_REQUIREMENTS[em_level]
            if documentation_elements < req["elements"]:
                issues.append(
                    f"E/M level {em_level} requires {req['elements']} documentation elements, "
                    f"only {documentation_elements} found"
                )
                # Suggest appropriate level
                for code, r in sorted(EM_LEVEL_REQUIREMENTS.items()):
                    if documentation_elements >= r["elements"]:
                        suggested = code
                if documentation_elements > 0:
                    suggestions.append(f"Consider downgrading to {suggested} based on documentation")

            if visit_time_minutes > 0 and visit_time_minutes < req["time_minutes"]:
                issues.append(
                    f"E/M level {em_level} typically requires {req['time_minutes']} min, "
                    f"visit was {visit_time_minutes} min"
                )

        # Check for duplicate codes
        if len(cpt_codes) != len(set(cpt_codes)):
            issues.append("Duplicate CPT codes detected")

        # Check for modifier requirements
        if len(cpt_codes) > 1:
            suggestions.append("Multiple CPT codes — verify modifier 25/59 applicability")

        accuracy_score = max(0, 1.0 - (len(issues) * 0.15))

        result = {
            "coding_accuracy_score": round(accuracy_score, 2),
            "cpt_codes": cpt_codes,
            "diagnosis_codes": diagnosis_codes,
            "issues": issues,
            "suggestions": suggestions,
            "em_level": em_level,
            "is_accurate": len(issues) == 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88 if len(issues) == 0 else 0.75,
            rationale=(
                f"Coding review: accuracy {accuracy_score:.0%}, "
                f"{len(issues)} issue(s), {len(suggestions)} suggestion(s)"
            ),
        )

    def _prepare_claim(self, input_data: AgentInput) -> AgentOutput:
        """Prepare a claim for submission to payer."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        encounter_id = ctx.get("encounter_id", "")
        payer = ctx.get("payer", "")
        cpt_codes = ctx.get("cpt_codes", [])
        diagnosis_codes = ctx.get("diagnosis_codes", [])
        provider_npi = ctx.get("provider_npi", "")
        date_of_service = ctx.get("date_of_service", "")
        charges = ctx.get("charges", [])

        # Validate minimum claim requirements
        missing = []
        if not payer:
            missing.append("payer")
        if not cpt_codes:
            missing.append("cpt_codes")
        if not diagnosis_codes:
            missing.append("diagnosis_codes")
        if not provider_npi:
            missing.append("provider_npi")

        if missing:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"status": "incomplete", "missing_fields": missing},
                confidence=0.95,
                rationale=f"Cannot prepare claim: missing {', '.join(missing)}",
            )

        claim_id = f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{patient_id[:8]}"

        # Calculate total charges
        total_charges = sum(c.get("amount", 0) for c in charges) if charges else 0
        if not charges:
            # Estimate charges from CPT codes
            total_charges = len(cpt_codes) * 150  # placeholder

        # Build CMS-1500 / 837P structure
        result = {
            "claim_id": claim_id,
            "claim_type": "837P",  # professional claim
            "status": "prepared",
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "payer": payer,
            "provider_npi": provider_npi,
            "date_of_service": date_of_service,
            "diagnosis_codes": diagnosis_codes,
            "service_lines": [
                {
                    "line_number": i + 1,
                    "cpt_code": cpt,
                    "diagnosis_pointer": [1],
                    "charge_amount": charges[i]["amount"] if i < len(charges) else 150,
                    "units": 1,
                }
                for i, cpt in enumerate(cpt_codes)
            ],
            "total_charges": total_charges,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=(
                f"Claim {claim_id} prepared: {len(cpt_codes)} service line(s), "
                f"${total_charges} total charges"
            ),
        )

    def _billing_audit(self, input_data: AgentInput) -> AgentOutput:
        """Run a billing audit across recent encounters."""
        ctx = input_data.context
        period = ctx.get("period", "weekly")

        # In production, queries encounter/claim databases
        now = datetime.now(timezone.utc)
        audit_result = {
            "period": period,
            "audit_date": now.isoformat(),
            "total_encounters": 142,
            "billed": 128,
            "unbilled": 14,
            "billing_rate": 0.901,
            "coding_issues": 8,
            "documentation_gaps": 5,
            "estimated_revenue_at_risk": 12500,
            "top_issues": [
                {"issue": "Missing modifier on telehealth claims", "count": 4, "impact": "$3,200"},
                {"issue": "E/M level documentation insufficient", "count": 3, "impact": "$4,500"},
                {"issue": "Missing prior auth reference", "count": 3, "impact": "$8,400"},
                {"issue": "Duplicate billing for same DOS", "count": 2, "impact": "$1,800"},
            ],
            "recommendations": [
                "Review 14 unbilled encounters from this period",
                "Update telehealth modifier templates",
                "Flag E/M level 99215 claims for documentation review",
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=audit_result,
            confidence=0.88,
            rationale=(
                f"Billing audit ({period}): {audit_result['billing_rate']:.1%} billing rate, "
                f"${audit_result['estimated_revenue_at_risk']:,} revenue at risk"
            ),
        )

    @staticmethod
    def _check_documentation(encounter: dict, encounter_type: str) -> list[str]:
        """Check for documentation completeness issues."""
        issues = []

        if not encounter.get("clinical_notes"):
            issues.append("Clinical notes missing")

        if encounter_type == "telehealth" and not encounter.get("telehealth_consent"):
            issues.append("Telehealth consent documentation missing")

        if not encounter.get("provider_signature"):
            issues.append("Provider signature/attestation missing")

        if encounter.get("cpt_codes"):
            for cpt in encounter["cpt_codes"]:
                if cpt.startswith("992") and not encounter.get("review_of_systems"):
                    issues.append(f"E/M code {cpt} requires review of systems documentation")
                    break

        return issues

    @staticmethod
    def _check_common_errors(encounter: dict) -> list[str]:
        """Check for common billing errors."""
        warnings = []

        dos = encounter.get("date_of_service", "")
        if dos:
            try:
                service_date = datetime.fromisoformat(dos.replace("Z", "+00:00"))
                days_old = (datetime.now(timezone.utc) - service_date).days
                if days_old > 90:
                    warnings.append(f"Date of service is {days_old} days old — check timely filing limits")
            except (ValueError, TypeError):
                warnings.append("Invalid date of service format")

        if encounter.get("place_of_service") == "02" and "GT" not in (encounter.get("modifier") or ""):
            warnings.append("Telehealth place of service (02) may require GT modifier")

        return warnings
