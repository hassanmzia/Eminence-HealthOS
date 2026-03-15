"""
Billing Agent — Tier 5 (Action / Measurement).

Generates CPT codes for encounters, calculates RPM billing metrics,
selects appropriate codes (99453/99454/99457/99458), performs
pre-authorization checks, and builds billing claims.

Adapted from InHealth billing_agent (Tier 5 Action).
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.billing")

# RPM CPT codes
RPM_CPT_CODES = {
    "99453": {
        "description": "Remote monitoring - initial device setup and patient education",
        "billing_period": "one_time",
        "requirements": "First time patient enrolled in RPM. Device setup and education required.",
        "reimbursement_approx_usd": 19.0,
    },
    "99454": {
        "description": "Remote monitoring - device supply with daily recordings or alerts",
        "billing_period": "monthly",
        "requirements": ">=16 days of monitoring data in 30-day period.",
        "reimbursement_approx_usd": 50.0,
    },
    "99457": {
        "description": "Remote physiologic monitoring treatment management - first 20 minutes",
        "billing_period": "monthly",
        "requirements": ">=20 minutes interactive communication with clinical staff per month.",
        "reimbursement_approx_usd": 50.0,
    },
    "99458": {
        "description": "Remote physiologic monitoring treatment management - each additional 20 minutes",
        "billing_period": "monthly",
        "requirements": "Each additional 20-min block beyond first (99457). Max 2 add-ons per month.",
        "reimbursement_approx_usd": 43.0,
    },
}

# Common E&M CPT codes
EM_CPT_CODES = {
    "99213": "Office visit - established patient, moderate complexity, 20-29 min",
    "99214": "Office visit - established patient, moderate-high complexity, 30-39 min",
    "99215": "Office visit - established patient, high complexity, 40-54 min",
    "99241": "Telehealth - established patient, low complexity",
    "99242": "Telehealth - established patient, moderate complexity",
}


class BillingAgent(HealthOSAgent):
    """Automated CPT coding and RPM billing claim generation."""

    def __init__(self) -> None:
        super().__init__(
            name="billing",
            tier=AgentTier.ACTION,
            description=(
                "Generates CPT codes for RPM and E&M encounters, calculates billing metrics, "
                "and builds claims for submission"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.COMPLIANCE_CHECK, AgentCapability.RESOURCE_OPTIMIZATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        tenant_id = str(agent_input.org_id) if agent_input.org_id else data.get("tenant_id", "")
        patient_id = str(agent_input.patient_id or data.get("patient_id", ""))
        timestamp = datetime.now(timezone.utc).isoformat()

        monitoring: dict[str, Any] = data.get("monitoring_results", {})
        actions_taken: list[dict[str, Any]] = data.get("actions_taken", [])
        risk_level: str = data.get("risk_level", "MEDIUM")
        first_enrollment: bool = data.get("first_enrollment", False)

        # Calculate RPM metrics
        rpm_metrics = self._calculate_rpm_metrics(monitoring, actions_taken)

        # Select CPT codes
        cpt_codes = self._select_cpt_codes(rpm_metrics, risk_level, first_enrollment)

        # Estimated reimbursement
        estimated_reimbursement = sum(
            RPM_CPT_CODES.get(code, {}).get("reimbursement_approx_usd", 0)
            for code in cpt_codes
            if code in RPM_CPT_CODES
        )

        # Pre-authorization check
        auth_result = await self._check_preauthorization(patient_id, cpt_codes, tenant_id)

        # Build claim
        claim = self._build_billing_claim(
            patient_id, tenant_id, cpt_codes, rpm_metrics, auth_result, timestamp,
        )

        # Submit claim
        submission_result = await self._submit_claim(claim)

        # LLM billing summary
        billing_summary = self._fallback_billing_summary(cpt_codes, estimated_reimbursement)
        try:
            prompt = (
                f"Generate a billing summary for patient {patient_id}:\n\n"
                f"RPM metrics this month:\n"
                f"  Monitoring days: {rpm_metrics.get('monitoring_days', 0)}\n"
                f"  Clinical staff time (minutes): {rpm_metrics.get('clinical_time_minutes', 0)}\n"
                f"  Interactive sessions: {rpm_metrics.get('interactive_sessions', 0)}\n\n"
                f"CPT codes selected: {', '.join(cpt_codes)}\n"
                f"Estimated reimbursement: ${estimated_reimbursement:.2f}\n"
                f"Pre-authorization required: {auth_result.get('required', False)}\n"
                f"Authorization status: {auth_result.get('status', 'pending')}\n\n"
                "Verify code selection and provide:\n"
                "1. Justification for each CPT code with documentation requirements\n"
                "2. Missing documentation that could jeopardize reimbursement\n"
                "3. Compliance checklist for CMS RPM requirements\n"
                "4. Estimated revenue cycle timeline"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a healthcare billing compliance narrator. "
                    "Reference CMS 2024 RPM billing guidelines and AMA CPT coding guidelines."
                ),
                temperature=0.3,
                max_tokens=768,
            ))
            billing_summary = resp.content
        except Exception:
            logger.warning("LLM billing summary failed; using fallback")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="billing_claim",
            rationale=(
                f"CPT codes: {', '.join(cpt_codes)}; "
                f"Est. reimbursement: ${estimated_reimbursement:.2f}; "
                f"Submission: {submission_result.get('status', 'pending')}"
            ),
            confidence=0.85,
            data={
                "cpt_codes": cpt_codes,
                "rpm_metrics": rpm_metrics,
                "estimated_reimbursement_usd": round(estimated_reimbursement, 2),
                "preauth_required": auth_result.get("required", False),
                "preauth_status": auth_result.get("status", "not_required"),
                "claim_id": claim.get("claim_id"),
                "submission_status": submission_result.get("status", "pending"),
                "billing_summary": billing_summary,
                "recommendations": [
                    f"RPM billing: {len(cpt_codes)} CPT codes generated. Est. reimbursement: ${estimated_reimbursement:.2f}.",
                    "Ensure >=16 days monitoring data in billing period for 99454.",
                    "Document interactive communication time for 99457/99458 compliance.",
                ],
            },
            requires_hitl=False,
        )

    # -- Billing logic (preserved from source) -------------------------------------

    def _calculate_rpm_metrics(
        self, monitoring: dict[str, Any], actions_taken: list[dict[str, Any]],
    ) -> dict[str, Any]:
        monitoring_days = 0
        for agent_name, agent_data in monitoring.items():
            if isinstance(agent_data, dict) and agent_data.get("status") == "completed":
                monitoring_days = max(monitoring_days, agent_data.get("readings_analyzed", 0) // 12)

        clinical_time_minutes = 0
        interactive_sessions = 0
        for action in actions_taken:
            if action.get("type") in ("notification_sent", "physician_contacted"):
                clinical_time_minutes += 5
                interactive_sessions += 1

        return {
            "monitoring_days": min(monitoring_days, 31),
            "clinical_time_minutes": clinical_time_minutes,
            "interactive_sessions": interactive_sessions,
            "qualifies_99454": monitoring_days >= 16,
            "qualifies_99457": clinical_time_minutes >= 20,
            "additional_20min_blocks": max(0, (clinical_time_minutes - 20) // 20),
        }

    def _select_cpt_codes(
        self, metrics: dict[str, Any], risk_level: str, first_enrollment: bool,
    ) -> list[str]:
        codes: list[str] = []
        if metrics.get("qualifies_99454"):
            codes.append("99454")
        if metrics.get("qualifies_99457"):
            codes.append("99457")
            additional = min(metrics.get("additional_20min_blocks", 0), 2)
            for _ in range(additional):
                codes.append("99458")
        if first_enrollment:
            codes.insert(0, "99453")
        if not codes:
            if risk_level in ("CRITICAL", "HIGH"):
                codes.append("99215")
            else:
                codes.append("99214")
        return list(dict.fromkeys(codes))

    async def _check_preauthorization(
        self, patient_id: str, cpt_codes: list[str], tenant_id: str,
    ) -> dict[str, Any]:
        try:
            api_url = os.getenv("HEALTHOS_API_URL", "http://backend:8000")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{api_url}/api/billing/preauth-check/",
                    json={
                        "patient_id": patient_id,
                        "cpt_codes": cpt_codes,
                        "tenant_id": tenant_id,
                    },
                    headers={"X-Internal-Token": os.getenv("INTERNAL_API_TOKEN", "")},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.debug("Pre-auth check failed: %s", exc)
        return {"required": False, "status": "not_checked", "message": "Pre-auth check unavailable"}

    def _build_billing_claim(
        self,
        patient_id: str,
        tenant_id: str,
        cpt_codes: list[str],
        rpm_metrics: dict,
        auth_result: dict,
        timestamp: str,
    ) -> dict[str, Any]:
        return {
            "claim_id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "tenant_id": tenant_id,
            "service_date": timestamp[:10],
            "claim_type": "RPM" if "99454" in cpt_codes else "ENCOUNTER",
            "cpt_codes": cpt_codes,
            "rpm_monitoring_days": rpm_metrics.get("monitoring_days", 0),
            "rpm_clinical_time_minutes": rpm_metrics.get("clinical_time_minutes", 0),
            "preauth_number": auth_result.get("auth_number", ""),
            "status": "draft",
            "created_at": timestamp,
            "generated_by": "billing_agent",
        }

    async def _submit_claim(self, claim: dict[str, Any]) -> dict[str, Any]:
        try:
            api_url = os.getenv("HEALTHOS_API_URL", "http://backend:8000")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{api_url}/api/billing/claims/",
                    json=claim,
                    headers={"X-Internal-Token": os.getenv("INTERNAL_API_TOKEN", "")},
                )
                if resp.status_code in (200, 201):
                    return {"status": "submitted", "claim_id": resp.json().get("id")}
                return {"status": "failed", "http_status": resp.status_code}
        except Exception as exc:
            logger.warning("Claim submission failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def _fallback_billing_summary(self, codes: list[str], revenue: float) -> str:
        code_list = ", ".join(codes) if codes else "None"
        return (
            f"CPT codes generated: {code_list}. "
            f"Estimated reimbursement: ${revenue:.2f}. "
            f"Review documentation requirements before submission."
        )
