"""
Eminence HealthOS — Claims Optimization Agent (#47)
Layer 3 (Decisioning): Reviews claims before submission, catches coding errors,
suggests corrections, and optimizes for clean claim rate.
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

# Common claim rejection reasons
REJECTION_RULES: list[dict[str, Any]] = [
    {"rule_id": "R001", "category": "missing_info", "description": "Missing patient demographics", "field": "patient_dob"},
    {"rule_id": "R002", "category": "missing_info", "description": "Missing provider NPI", "field": "provider_npi"},
    {"rule_id": "R003", "category": "coding_error", "description": "Primary diagnosis not set", "field": "primary_icd10"},
    {"rule_id": "R004", "category": "coding_error", "description": "ICD-10 and CPT code mismatch", "field": "code_alignment"},
    {"rule_id": "R005", "category": "eligibility", "description": "Insurance eligibility not verified", "field": "eligibility_status"},
    {"rule_id": "R006", "category": "authorization", "description": "Prior authorization required but missing", "field": "prior_auth"},
    {"rule_id": "R007", "category": "duplicate", "description": "Duplicate claim within 30 days", "field": "duplicate_check"},
    {"rule_id": "R008", "category": "timely_filing", "description": "Claim exceeds timely filing limit", "field": "service_date"},
    {"rule_id": "R009", "category": "modifier", "description": "Missing required modifier", "field": "modifiers"},
    {"rule_id": "R010", "category": "bundling", "description": "Services should be bundled per CCI edits", "field": "bundling"},
]


class ClaimsOptimizationAgent(BaseAgent):
    """Reviews and optimizes claims before payer submission."""

    name = "claims_optimization"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Pre-submission claims scrubbing — catches coding errors, validates "
        "completeness, and optimizes for clean claim rate"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "optimize_claim")

        if action == "optimize_claim":
            return self._optimize_claim(input_data)
        elif action == "batch_scrub":
            return self._batch_scrub(input_data)
        elif action == "check_bundling":
            return self._check_bundling(input_data)
        elif action == "clean_claim_rate":
            return self._clean_claim_rate(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown claims optimization action: {action}",
                status=AgentStatus.FAILED,
            )

    def _optimize_claim(self, input_data: AgentInput) -> AgentOutput:
        """Scrub a single claim for errors and optimize before submission."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        claim_id = ctx.get("claim_id", str(uuid.uuid4()))

        claim_data = {
            "patient_dob": ctx.get("patient_dob"),
            "provider_npi": ctx.get("provider_npi"),
            "primary_icd10": ctx.get("primary_icd10"),
            "icd10_codes": ctx.get("icd10_codes", []),
            "cpt_codes": ctx.get("cpt_codes", []),
            "service_date": ctx.get("service_date"),
            "eligibility_status": ctx.get("eligibility_status"),
            "prior_auth": ctx.get("prior_auth"),
            "modifiers": ctx.get("modifiers", []),
        }

        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        suggestions: list[dict[str, Any]] = []

        for rule in REJECTION_RULES:
            field = rule["field"]
            if field in claim_data:
                value = claim_data[field]
                if value is None or value == "" or value == []:
                    if rule["category"] in ("missing_info", "coding_error"):
                        errors.append({
                            "rule_id": rule["rule_id"],
                            "category": rule["category"],
                            "description": rule["description"],
                            "field": field,
                            "severity": "error",
                        })
                    else:
                        warnings.append({
                            "rule_id": rule["rule_id"],
                            "category": rule["category"],
                            "description": rule["description"],
                            "field": field,
                            "severity": "warning",
                        })

        # Check for code alignment
        icd10_codes = claim_data.get("icd10_codes", [])
        cpt_codes = claim_data.get("cpt_codes", [])
        if icd10_codes and cpt_codes:
            suggestions.append({
                "type": "code_review",
                "message": f"Verify alignment between {len(icd10_codes)} ICD-10 and {len(cpt_codes)} CPT codes",
            })

        # Determine if claim is clean
        is_clean = len(errors) == 0
        clean_score = max(0, 100 - (len(errors) * 20) - (len(warnings) * 5))

        result = {
            "claim_id": claim_id,
            "scrubbed_at": now.isoformat(),
            "is_clean": is_clean,
            "clean_score": clean_score,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "ready_to_submit": is_clean,
            "estimated_days_to_payment": 14 if is_clean else 45,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90 if is_clean else 0.75,
            rationale=(
                f"Claim {claim_id}: {'CLEAN' if is_clean else 'NEEDS FIXES'} — "
                f"{len(errors)} errors, {len(warnings)} warnings (score: {clean_score})"
            ),
        )

    def _batch_scrub(self, input_data: AgentInput) -> AgentOutput:
        """Scrub a batch of claims for common issues."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        claims = ctx.get("claims", [])

        results: list[dict[str, Any]] = []
        clean_count = 0

        for claim in claims:
            claim_id = claim.get("claim_id", str(uuid.uuid4()))
            has_npi = bool(claim.get("provider_npi"))
            has_icd10 = bool(claim.get("primary_icd10"))
            has_eligibility = bool(claim.get("eligibility_status"))

            errors = []
            if not has_npi:
                errors.append("Missing provider NPI")
            if not has_icd10:
                errors.append("Missing primary ICD-10")
            if not has_eligibility:
                errors.append("Eligibility not verified")

            is_clean = len(errors) == 0
            if is_clean:
                clean_count += 1

            results.append({
                "claim_id": claim_id,
                "is_clean": is_clean,
                "error_count": len(errors),
                "errors": errors,
            })

        total = len(claims)
        clean_rate = round(clean_count / max(total, 1) * 100, 1)

        result = {
            "scrubbed_at": now.isoformat(),
            "total_claims": total,
            "clean_claims": clean_count,
            "claims_with_errors": total - clean_count,
            "clean_claim_rate": clean_rate,
            "results": results,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Batch scrub: {clean_count}/{total} clean ({clean_rate}%)",
        )

    def _check_bundling(self, input_data: AgentInput) -> AgentOutput:
        """Check for CCI bundling edits on a set of CPT codes."""
        ctx = input_data.context
        cpt_codes = ctx.get("cpt_codes", [])

        # Simplified CCI bundling rules
        bundling_pairs = {
            ("80048", "80053"): "BMP is bundled into CMP — bill CMP only",
            ("36415", "36416"): "Duplicate venipuncture — bill only one",
            ("85025", "85027"): "CBC variants — bill only one",
        }

        bundles_found: list[dict[str, str]] = []
        code_set = {c.get("cpt", c.get("code", c)) if isinstance(c, dict) else c for c in cpt_codes}

        for (code1, code2), message in bundling_pairs.items():
            if code1 in code_set and code2 in code_set:
                bundles_found.append({
                    "code_1": code1,
                    "code_2": code2,
                    "recommendation": message,
                })

        result = {
            "codes_checked": len(cpt_codes),
            "bundles_found": bundles_found,
            "has_bundling_issues": len(bundles_found) > 0,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"Bundling check: {len(bundles_found)} issues in {len(cpt_codes)} codes",
        )

    def _clean_claim_rate(self, input_data: AgentInput) -> AgentOutput:
        """Report clean claim rate metrics over a period."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        total_submitted = ctx.get("total_submitted", 1250)
        clean_first_pass = ctx.get("clean_first_pass", 1088)
        denied = ctx.get("denied", 87)
        pending = ctx.get("pending", 75)

        clean_rate = round(clean_first_pass / max(total_submitted, 1) * 100, 1)
        denial_rate = round(denied / max(total_submitted, 1) * 100, 1)

        result = {
            "period": ctx.get("period", "last_30_days"),
            "report_date": now.isoformat(),
            "total_submitted": total_submitted,
            "clean_first_pass": clean_first_pass,
            "clean_claim_rate": clean_rate,
            "denied": denied,
            "denial_rate": denial_rate,
            "pending": pending,
            "industry_benchmark": 95.0,
            "performance_vs_benchmark": round(clean_rate - 95.0, 1),
            "top_denial_reasons": [
                {"reason": "Missing prior authorization", "count": 28, "pct": 32.2},
                {"reason": "Coding error", "count": 22, "pct": 25.3},
                {"reason": "Eligibility issue", "count": 19, "pct": 21.8},
                {"reason": "Timely filing exceeded", "count": 10, "pct": 11.5},
                {"reason": "Duplicate claim", "count": 8, "pct": 9.2},
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"Clean claim rate: {clean_rate}% ({clean_first_pass}/{total_submitted})",
        )
