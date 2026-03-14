"""
Eminence HealthOS — Consent Management Agent (#69)
Layer 4 (Action): Manages granular patient consent for data sharing, research,
AI processing, and other purposes with full audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import json
import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

# ── Consent Purposes ─────────────────────────────────────────────────────────

CONSENT_PURPOSES: dict[str, dict[str, Any]] = {
    "treatment": {
        "description": "Use of health information for diagnosis, treatment, and care coordination",
        "requires_explicit": False,
        "default_duration_days": 365,
        "regulatory_basis": "45 CFR 164.506 — Treatment, Payment, and Health Care Operations",
    },
    "payment": {
        "description": "Use of health information for billing, claims processing, and insurance verification",
        "requires_explicit": False,
        "default_duration_days": 365,
        "regulatory_basis": "45 CFR 164.506 — Treatment, Payment, and Health Care Operations",
    },
    "operations": {
        "description": "Use of health information for quality assessment, training, and business management",
        "requires_explicit": False,
        "default_duration_days": 365,
        "regulatory_basis": "45 CFR 164.506 — Treatment, Payment, and Health Care Operations",
    },
    "research": {
        "description": "Use of health information for clinical research, studies, and trials",
        "requires_explicit": True,
        "default_duration_days": 730,
        "regulatory_basis": "45 CFR 164.508 — Uses and Disclosures for Which an Authorization Is Required",
    },
    "ai_processing": {
        "description": "Use of health information for AI/ML model training, inference, and analytics",
        "requires_explicit": True,
        "default_duration_days": 365,
        "regulatory_basis": "45 CFR 164.508 — Uses and Disclosures for Which an Authorization Is Required",
    },
    "data_sharing": {
        "description": "Sharing health information with third-party organizations or health information exchanges",
        "requires_explicit": True,
        "default_duration_days": 180,
        "regulatory_basis": "45 CFR 164.508 — Uses and Disclosures for Which an Authorization Is Required",
    },
    "marketing": {
        "description": "Use of health information for marketing communications and promotional materials",
        "requires_explicit": True,
        "default_duration_days": 90,
        "regulatory_basis": "45 CFR 164.508(a)(3) — Marketing Authorization",
    },
}


class ConsentManagementAgent(BaseAgent):
    """Manages granular patient consent for data sharing, research, and AI processing."""

    name = "consent_management"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Granular patient consent management — records, checks, and revokes consent "
        "for treatment, research, AI processing, data sharing, and marketing"
    )
    min_confidence = 0.90

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "check_consent")

        if action == "check_consent":
            return self._check_consent(input_data)
        elif action == "record_consent":
            return self._record_consent(input_data)
        elif action == "revoke_consent":
            return self._revoke_consent(input_data)
        elif action == "consent_summary":
            return self._consent_summary(input_data)
        elif action == "consent_audit":
            return self._consent_audit(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown consent management action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Check Consent ────────────────────────────────────────────────────────

    def _check_consent(self, input_data: AgentInput) -> AgentOutput:
        """Verify patient has valid consent for a specific purpose."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        patient_id = ctx.get("patient_id", str(input_data.patient_id or ""))
        purpose = ctx.get("purpose", "treatment")
        consents = ctx.get("consents", {})

        purpose_config = CONSENT_PURPOSES.get(purpose)
        if not purpose_config:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown consent purpose: {purpose}", "decision": "denied"},
                confidence=0.95,
                rationale=f"Unknown consent purpose: {purpose}",
                status=AgentStatus.FAILED,
            )

        patient_consent = consents.get(purpose, {})
        has_consent = patient_consent.get("granted", False)
        expiry_str = patient_consent.get("expires_at")

        is_expired = False
        expires_at = None
        if expiry_str:
            try:
                expires_at = datetime.fromisoformat(expiry_str).replace(tzinfo=timezone.utc)
                is_expired = now > expires_at
            except (ValueError, TypeError):
                is_expired = True

        # TPO purposes don't require explicit consent
        requires_explicit = purpose_config["requires_explicit"]
        if not requires_explicit and not has_consent:
            # Implied consent for TPO
            decision = "allowed"
            basis = "implied_consent_tpo"
        elif has_consent and not is_expired:
            decision = "allowed"
            basis = "explicit_consent"
        elif has_consent and is_expired:
            decision = "denied"
            basis = "consent_expired"
        else:
            decision = "denied"
            basis = "no_consent_on_file"

        result = {
            "check_type": "consent_check",
            "checked_at": now.isoformat(),
            "patient_id": patient_id,
            "purpose": purpose,
            "purpose_description": purpose_config["description"],
            "decision": decision,
            "basis": basis,
            "requires_explicit_consent": requires_explicit,
            "consent_on_file": has_consent,
            "is_expired": is_expired,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "regulatory_basis": purpose_config["regulatory_basis"],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=(
                f"Consent check for {purpose}: {decision} — "
                f"basis: {basis}, patient: {patient_id}"
            ),
        )

    # ── Record Consent ───────────────────────────────────────────────────────

    def _record_consent(self, input_data: AgentInput) -> AgentOutput:
        """Record new consent with purpose, scope, expiry, and granular permissions."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        patient_id = ctx.get("patient_id", str(input_data.patient_id or ""))
        purpose = ctx.get("purpose", "")
        scope = ctx.get("scope", "all")
        granted_by = ctx.get("granted_by", "patient")
        permissions = ctx.get("permissions", {})

        purpose_config = CONSENT_PURPOSES.get(purpose)
        if not purpose_config:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown consent purpose: {purpose}"},
                confidence=0.95,
                rationale=f"Cannot record consent — unknown purpose: {purpose}",
                status=AgentStatus.FAILED,
            )

        duration_days = ctx.get("duration_days", purpose_config["default_duration_days"])
        expires_at = now + timedelta(days=duration_days)

        consent_record = {
            "consent_id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "purpose": purpose,
            "purpose_description": purpose_config["description"],
            "scope": scope,
            "granted": True,
            "granted_by": granted_by,
            "granted_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "duration_days": duration_days,
            "permissions": permissions or self._default_permissions(purpose),
            "regulatory_basis": purpose_config["regulatory_basis"],
            "requires_explicit": purpose_config["requires_explicit"],
            "version": "1.0",
            "audit_trail": [
                {
                    "action": "consent_granted",
                    "timestamp": now.isoformat(),
                    "actor": granted_by,
                    "details": f"Consent granted for {purpose} with scope: {scope}",
                }
            ],
        }

        result = {
            "action": "record_consent",
            "status": "recorded",
            "consent_record": consent_record,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.97,
            rationale=(
                f"Consent recorded for {purpose} — patient: {patient_id}, "
                f"expires: {expires_at.date().isoformat()}, scope: {scope}"
            ),
        )

    # ── Revoke Consent ───────────────────────────────────────────────────────

    def _revoke_consent(self, input_data: AgentInput) -> AgentOutput:
        """Process consent revocation and trigger downstream access restrictions."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        patient_id = ctx.get("patient_id", str(input_data.patient_id or ""))
        purpose = ctx.get("purpose", "")
        revoked_by = ctx.get("revoked_by", "patient")
        reason = ctx.get("reason", "patient_request")
        consent_id = ctx.get("consent_id", "")

        purpose_config = CONSENT_PURPOSES.get(purpose)
        if not purpose_config:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown consent purpose: {purpose}"},
                confidence=0.95,
                rationale=f"Cannot revoke consent — unknown purpose: {purpose}",
                status=AgentStatus.FAILED,
            )

        downstream_actions = self._revocation_downstream_actions(purpose)

        revocation_record = {
            "revocation_id": str(uuid.uuid4()),
            "consent_id": consent_id,
            "patient_id": patient_id,
            "purpose": purpose,
            "revoked_by": revoked_by,
            "revoked_at": now.isoformat(),
            "reason": reason,
            "effective_immediately": True,
            "downstream_actions": downstream_actions,
            "audit_trail": [
                {
                    "action": "consent_revoked",
                    "timestamp": now.isoformat(),
                    "actor": revoked_by,
                    "details": f"Consent revoked for {purpose} — reason: {reason}",
                }
            ],
        }

        result = {
            "action": "revoke_consent",
            "status": "revoked",
            "revocation_record": revocation_record,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.97,
            rationale=(
                f"Consent revoked for {purpose} — patient: {patient_id}, "
                f"reason: {reason}, {len(downstream_actions)} downstream actions triggered"
            ),
        )

    # ── Consent Summary ──────────────────────────────────────────────────────

    def _consent_summary(self, input_data: AgentInput) -> AgentOutput:
        """Return complete consent profile for a patient across all purposes."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        patient_id = ctx.get("patient_id", str(input_data.patient_id or ""))
        consents = ctx.get("consents", {})

        summary: list[dict[str, Any]] = []
        for purpose, config in CONSENT_PURPOSES.items():
            patient_consent = consents.get(purpose, {})
            has_consent = patient_consent.get("granted", False)
            expiry_str = patient_consent.get("expires_at")

            is_expired = False
            expires_at = None
            if expiry_str:
                try:
                    expires_at = datetime.fromisoformat(expiry_str).replace(tzinfo=timezone.utc)
                    is_expired = now > expires_at
                except (ValueError, TypeError):
                    is_expired = True

            if not config["requires_explicit"] and not has_consent:
                status = "implied_active"
            elif has_consent and not is_expired:
                status = "active"
            elif has_consent and is_expired:
                status = "expired"
            else:
                status = "not_granted"

            summary.append({
                "purpose": purpose,
                "description": config["description"],
                "requires_explicit": config["requires_explicit"],
                "regulatory_basis": config["regulatory_basis"],
                "status": status,
                "granted": has_consent,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "granted_at": patient_consent.get("granted_at"),
                "scope": patient_consent.get("scope", "all" if has_consent else None),
            })

        active_count = sum(1 for s in summary if s["status"] in ("active", "implied_active"))
        expired_count = sum(1 for s in summary if s["status"] == "expired")

        result = {
            "summary_type": "consent_summary",
            "generated_at": now.isoformat(),
            "patient_id": patient_id,
            "total_purposes": len(summary),
            "active_consents": active_count,
            "expired_consents": expired_count,
            "not_granted": sum(1 for s in summary if s["status"] == "not_granted"),
            "consents": summary,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=(
                f"Consent summary for patient {patient_id}: "
                f"{active_count} active, {expired_count} expired across {len(summary)} purposes"
            ),
        )

    # ── Consent Audit ────────────────────────────────────────────────────────

    def _consent_audit(self, input_data: AgentInput) -> AgentOutput:
        """Generate audit trail of all consent changes for compliance reporting."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        patient_id = ctx.get("patient_id", str(input_data.patient_id or ""))
        audit_events = ctx.get("audit_events", [])
        date_from = ctx.get("date_from")
        date_to = ctx.get("date_to")

        # Filter events by date range if specified
        filtered_events = audit_events
        if date_from:
            try:
                from_dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
                filtered_events = [
                    e for e in filtered_events
                    if datetime.fromisoformat(e.get("timestamp", "")).replace(tzinfo=timezone.utc) >= from_dt
                ]
            except (ValueError, TypeError):
                pass

        if date_to:
            try:
                to_dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
                filtered_events = [
                    e for e in filtered_events
                    if datetime.fromisoformat(e.get("timestamp", "")).replace(tzinfo=timezone.utc) <= to_dt
                ]
            except (ValueError, TypeError):
                pass

        # Categorize events
        event_counts: dict[str, int] = {}
        for event in filtered_events:
            action = event.get("action", "unknown")
            event_counts[action] = event_counts.get(action, 0) + 1

        result = {
            "audit_type": "consent_audit",
            "generated_at": now.isoformat(),
            "patient_id": patient_id,
            "date_range": {
                "from": date_from,
                "to": date_to,
            },
            "total_events": len(filtered_events),
            "event_breakdown": event_counts,
            "events": sorted(
                filtered_events,
                key=lambda e: e.get("timestamp", ""),
                reverse=True,
            ),
            "compliance_note": (
                "Audit trail maintained per 45 CFR 164.530(j) — "
                "all consent documentation retained for minimum 6 years"
            ),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=(
                f"Consent audit for patient {patient_id}: "
                f"{len(filtered_events)} events in period"
            ),
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _default_permissions(purpose: str) -> dict[str, bool]:
        """Return default permission set for a consent purpose."""
        base = {"view": True, "store": True}
        if purpose == "treatment":
            return {**base, "share_with_care_team": True, "share_with_specialists": True}
        elif purpose == "research":
            return {**base, "de_identify": True, "aggregate": True, "publish_results": True}
        elif purpose == "ai_processing":
            return {**base, "model_training": True, "inference": True, "analytics": True}
        elif purpose == "data_sharing":
            return {**base, "hie_exchange": True, "third_party": False}
        elif purpose == "marketing":
            return {**base, "email": True, "sms": False, "phone": False}
        return base

    @staticmethod
    def _revocation_downstream_actions(purpose: str) -> list[dict[str, str]]:
        """Determine downstream actions triggered by consent revocation."""
        base = [
            {"action": "update_consent_registry", "description": "Mark consent as revoked in central registry"},
            {"action": "log_audit_event", "description": "Record revocation in compliance audit trail"},
        ]

        purpose_actions: dict[str, list[dict[str, str]]] = {
            "research": [
                {"action": "notify_research_team", "description": "Alert active research studies using this patient's data"},
                {"action": "exclude_from_studies", "description": "Remove patient data from ongoing research datasets"},
            ],
            "ai_processing": [
                {"action": "exclude_from_training", "description": "Exclude patient data from future model training"},
                {"action": "flag_active_models", "description": "Flag models that used this patient's data"},
            ],
            "data_sharing": [
                {"action": "revoke_hie_access", "description": "Remove patient data from health information exchanges"},
                {"action": "notify_third_parties", "description": "Notify third-party recipients of revocation"},
            ],
            "marketing": [
                {"action": "remove_from_lists", "description": "Remove patient from all marketing communication lists"},
                {"action": "suppress_communications", "description": "Suppress any pending marketing communications"},
            ],
        }

        return base + purpose_actions.get(purpose, [])
