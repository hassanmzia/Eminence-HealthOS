"""
Eminence HealthOS — Crisis Detection Agent (#78)
Layer 1 (Sensing): Detects suicidal ideation, self-harm risk, and crisis
indicators from patient interactions, screening scores, and clinical data.

SAFETY: This agent uses a lower confidence threshold (0.6) to flag more
aggressively and ALWAYS requires human-in-the-loop review for moderate+
risk levels.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)


# ── Crisis Indicators ────────────────────────────────────────────────────────

CRISIS_INDICATORS: dict[str, list[dict[str, Any]]] = {
    "suicidal_ideation": [
        {"phrase": "want to die", "severity": 0.9},
        {"phrase": "wish i was dead", "severity": 0.9},
        {"phrase": "better off dead", "severity": 0.9},
        {"phrase": "kill myself", "severity": 1.0},
        {"phrase": "end my life", "severity": 1.0},
        {"phrase": "no reason to live", "severity": 0.85},
        {"phrase": "don't want to be here", "severity": 0.7},
        {"phrase": "can't go on", "severity": 0.7},
        {"phrase": "want it to be over", "severity": 0.75},
        {"phrase": "suicidal", "severity": 0.95},
        {"phrase": "end it all", "severity": 0.95},
    ],
    "self_harm": [
        {"phrase": "cut myself", "severity": 0.85},
        {"phrase": "hurt myself", "severity": 0.8},
        {"phrase": "self-harm", "severity": 0.85},
        {"phrase": "burning myself", "severity": 0.85},
        {"phrase": "hitting myself", "severity": 0.75},
        {"phrase": "scratching myself", "severity": 0.7},
        {"phrase": "punishing myself", "severity": 0.7},
    ],
    "hopelessness": [
        {"phrase": "no hope", "severity": 0.65},
        {"phrase": "hopeless", "severity": 0.65},
        {"phrase": "nothing will get better", "severity": 0.7},
        {"phrase": "never going to change", "severity": 0.6},
        {"phrase": "pointless", "severity": 0.55},
        {"phrase": "give up", "severity": 0.6},
        {"phrase": "can't take it anymore", "severity": 0.7},
        {"phrase": "trapped", "severity": 0.6},
        {"phrase": "burden to everyone", "severity": 0.75},
        {"phrase": "no way out", "severity": 0.75},
    ],
    "plan_or_means": [
        {"phrase": "have a plan", "severity": 1.0},
        {"phrase": "know how i would", "severity": 0.95},
        {"phrase": "bought a gun", "severity": 1.0},
        {"phrase": "stockpiling pills", "severity": 1.0},
        {"phrase": "wrote a note", "severity": 0.95},
        {"phrase": "giving away", "severity": 0.7},
        {"phrase": "saying goodbye", "severity": 0.8},
        {"phrase": "put my affairs in order", "severity": 0.85},
        {"phrase": "access to firearms", "severity": 0.8},
    ],
    "substance_crisis": [
        {"phrase": "overdose", "severity": 0.9},
        {"phrase": "can't stop drinking", "severity": 0.7},
        {"phrase": "relapsed", "severity": 0.65},
        {"phrase": "blacked out", "severity": 0.7},
        {"phrase": "withdrawal", "severity": 0.75},
        {"phrase": "using again", "severity": 0.65},
        {"phrase": "need a fix", "severity": 0.7},
    ],
}

# ── Risk Level Definitions ──────────────────────────────────────────────────

RISK_LEVELS: dict[str, dict[str, Any]] = {
    "none": {"score_range": (0.0, 0.1), "requires_hitl": False},
    "low": {"score_range": (0.1, 0.3), "requires_hitl": False},
    "moderate": {"score_range": (0.3, 0.6), "requires_hitl": True},
    "high": {"score_range": (0.6, 0.85), "requires_hitl": True},
    "imminent": {"score_range": (0.85, 1.0), "requires_hitl": True},
}

ESCALATION_PATHS: dict[str, dict[str, Any]] = {
    "none": {
        "action": "document_only",
        "description": "No crisis indicators detected — document in chart",
        "timeline": "next_scheduled_visit",
    },
    "low": {
        "action": "flag_for_next_visit",
        "description": "Flag for discussion at next scheduled visit",
        "timeline": "next_visit",
        "notifications": ["therapist"],
    },
    "moderate": {
        "action": "same_day_callback",
        "description": "Same-day callback from behavioral health provider",
        "timeline": "within_4_hours",
        "notifications": ["therapist", "psychiatrist", "care_coordinator"],
    },
    "high": {
        "action": "immediate_outreach",
        "description": "Immediate outreach by crisis-trained clinician",
        "timeline": "within_1_hour",
        "notifications": ["therapist", "psychiatrist", "pcp", "crisis_team"],
    },
    "imminent": {
        "action": "emergency_services",
        "description": "Activate emergency services — imminent risk to life",
        "timeline": "immediate",
        "notifications": ["crisis_team", "emergency_services", "pcp", "psychiatrist"],
    },
}

CRISIS_RESOURCES = {
    "suicide_crisis_lifeline": {"number": "988", "name": "988 Suicide & Crisis Lifeline"},
    "crisis_text_line": {"number": "741741", "name": "Crisis Text Line (text HOME)"},
    "emergency_services": {"number": "911", "name": "Emergency Services"},
    "samhsa_helpline": {"number": "1-800-662-4357", "name": "SAMHSA National Helpline"},
    "veterans_crisis_line": {"number": "988 (press 1)", "name": "Veterans Crisis Line"},
}


class CrisisDetectionAgent(BaseAgent):
    """Detects suicidal ideation, self-harm risk, and crisis indicators from patient data."""

    name = "crisis_detection"
    tier = AgentTier.SENSING
    version = "1.0.0"
    description = (
        "Monitors patient interactions, screening scores, and clinical notes for "
        "crisis indicators including suicidal ideation, self-harm, and substance crises. "
        "Always requires human-in-the-loop review for moderate or higher risk."
    )
    min_confidence = 0.60  # Lower threshold — flag more aggressively for safety
    requires_hitl = True  # ALWAYS require human review for crisis detection

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "assess_risk")

        if action == "assess_risk":
            return self._assess_risk(input_data)
        elif action == "screen_text":
            return self._screen_text(input_data)
        elif action == "evaluate_indicators":
            return self._evaluate_indicators(input_data)
        elif action == "safety_plan":
            return self._safety_plan(input_data)
        elif action == "escalation_protocol":
            return self._escalation_protocol(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown crisis detection action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Assess Risk ──────────────────────────────────────────────────────────

    def _assess_risk(self, input_data: AgentInput) -> AgentOutput:
        """Assess crisis risk from PHQ-9 item 9, screening scores, and clinical flags."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        phq9_item9 = ctx.get("phq9_item9", 0)
        screening_scores = ctx.get("screening_scores", {})
        clinical_flags = ctx.get("clinical_flags", [])
        social_risk_factors = ctx.get("social_risk_factors", [])

        contributing_factors: list[dict[str, Any]] = []
        risk_score = 0.0

        # PHQ-9 item 9 (suicidal ideation) — heavily weighted
        if phq9_item9 >= 3:
            risk_score += 0.45
            contributing_factors.append({
                "source": "PHQ-9 item 9",
                "value": phq9_item9,
                "weight": 0.45,
                "note": "Nearly every day thoughts of self-harm or being better off dead",
            })
        elif phq9_item9 == 2:
            risk_score += 0.30
            contributing_factors.append({
                "source": "PHQ-9 item 9",
                "value": phq9_item9,
                "weight": 0.30,
                "note": "More than half the days — thoughts of self-harm",
            })
        elif phq9_item9 == 1:
            risk_score += 0.15
            contributing_factors.append({
                "source": "PHQ-9 item 9",
                "value": phq9_item9,
                "weight": 0.15,
                "note": "Several days — thoughts of self-harm",
            })

        # PHQ-9 total score contribution
        phq9_total = screening_scores.get("phq9_total", 0)
        if phq9_total >= 20:
            risk_score += 0.20
            contributing_factors.append({
                "source": "PHQ-9 total",
                "value": phq9_total,
                "weight": 0.20,
                "note": "Severe depression",
            })
        elif phq9_total >= 15:
            risk_score += 0.10
            contributing_factors.append({
                "source": "PHQ-9 total",
                "value": phq9_total,
                "weight": 0.10,
                "note": "Moderately severe depression",
            })

        # Clinical flags
        for flag in clinical_flags:
            flag_type = flag.get("type", "")
            if flag_type in ("suicidal_ideation", "self_harm", "prior_attempt"):
                weight = 0.25
                risk_score += weight
                contributing_factors.append({
                    "source": "clinical_flag",
                    "value": flag_type,
                    "weight": weight,
                    "note": flag.get("description", flag_type),
                })

        # Social risk factors
        social_weights = {
            "recent_loss": 0.10,
            "social_isolation": 0.10,
            "housing_instability": 0.08,
            "financial_crisis": 0.08,
            "relationship_breakdown": 0.08,
            "chronic_pain": 0.08,
            "prior_suicide_attempt": 0.20,
            "family_history_suicide": 0.10,
            "access_to_means": 0.15,
        }
        for factor in social_risk_factors:
            factor_name = factor if isinstance(factor, str) else factor.get("type", "")
            weight = social_weights.get(factor_name, 0.05)
            risk_score += weight
            contributing_factors.append({
                "source": "social_risk_factor",
                "value": factor_name,
                "weight": weight,
                "note": f"Social risk: {factor_name}",
            })

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine risk level
        risk_level = "none"
        for level, config in RISK_LEVELS.items():
            low, high = config["score_range"]
            if low <= risk_score < high:
                risk_level = level
                break
        if risk_score >= 0.85:
            risk_level = "imminent"

        # Determine recommended actions
        escalation = ESCALATION_PATHS[risk_level]
        recommended_actions = [escalation["action"]]
        if risk_level in ("high", "imminent"):
            recommended_actions.append("activate_safety_plan")
            recommended_actions.append("provide_crisis_resources")

        # Determine HITL status
        needs_hitl = risk_level in ("moderate", "high", "imminent")
        status = AgentStatus.WAITING_HITL if needs_hitl else AgentStatus.COMPLETED

        result = {
            "patient_id": patient_id,
            "risk_level": risk_level,
            "risk_score": round(risk_score, 3),
            "contributing_factors": contributing_factors,
            "recommended_actions": recommended_actions,
            "escalation": escalation,
            "requires_hitl": True,  # Always True for crisis detection
            "crisis_resources": CRISIS_RESOURCES,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=max(0.60, min(0.95, 0.60 + len(contributing_factors) * 0.05)),
            rationale=(
                f"Crisis risk assessment for patient {patient_id}: "
                f"risk level = {risk_level} (score: {risk_score:.3f}). "
                f"{len(contributing_factors)} contributing factor(s). "
                f"Escalation: {escalation['action']}."
            ),
            status=status,
        )

    # ── Screen Text ──────────────────────────────────────────────────────────

    def _screen_text(self, input_data: AgentInput) -> AgentOutput:
        """Scan free-text input for crisis keywords and phrases."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        text = ctx.get("text", "")
        source = ctx.get("source", "patient_message")

        if not text:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No text provided for screening"},
                confidence=0.95,
                rationale="No text provided for crisis screening",
                status=AgentStatus.FAILED,
            )

        text_lower = text.lower()
        detections: list[dict[str, Any]] = []
        max_severity = 0.0

        for category, indicators in CRISIS_INDICATORS.items():
            for indicator in indicators:
                phrase = indicator["phrase"]
                # Use word-boundary-aware matching
                pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
                if pattern.search(text_lower):
                    severity = indicator["severity"]
                    max_severity = max(max_severity, severity)
                    detections.append({
                        "category": category,
                        "phrase": phrase,
                        "severity": severity,
                        "context_snippet": self._extract_snippet(text, phrase),
                    })

        # Determine overall risk from text screening
        if max_severity >= 0.85:
            risk_level = "imminent"
        elif max_severity >= 0.6:
            risk_level = "high"
        elif max_severity >= 0.3:
            risk_level = "moderate"
        elif detections:
            risk_level = "low"
        else:
            risk_level = "none"

        needs_hitl = risk_level in ("moderate", "high", "imminent")
        status = AgentStatus.WAITING_HITL if needs_hitl else AgentStatus.COMPLETED

        result = {
            "patient_id": patient_id,
            "source": source,
            "text_length": len(text),
            "detections": sorted(detections, key=lambda d: d["severity"], reverse=True),
            "detection_count": len(detections),
            "max_severity": round(max_severity, 2),
            "risk_level": risk_level,
            "categories_detected": list(set(d["category"] for d in detections)),
            "requires_hitl": True,
            "crisis_resources": CRISIS_RESOURCES,
            "screened_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=max(0.60, min(0.95, 0.70 + len(detections) * 0.03)),
            rationale=(
                f"Text screening for patient {patient_id}: "
                f"{len(detections)} crisis indicator(s) detected in {source}. "
                f"Max severity: {max_severity:.2f}. Risk level: {risk_level}."
            ),
            status=status,
        )

    # ── Evaluate Indicators ──────────────────────────────────────────────────

    def _evaluate_indicators(self, input_data: AgentInput) -> AgentOutput:
        """Combine multiple data sources into a composite risk score with temporal weighting."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        screenings = ctx.get("screenings", [])
        encounters = ctx.get("encounters", [])
        medications = ctx.get("medications", [])
        social_factors = ctx.get("social_factors", [])

        components: list[dict[str, Any]] = []
        weighted_score = 0.0
        total_weight = 0.0

        # Process screening data with temporal weighting
        now = datetime.now(timezone.utc)
        for screening in screenings:
            base_risk = 0.0
            instrument = screening.get("instrument", "")
            score = screening.get("score", 0)
            max_score = screening.get("max_score", 1)

            if instrument == "PHQ-9":
                base_risk = score / max_score
            elif instrument == "GAD-7":
                base_risk = (score / max_score) * 0.7
            elif instrument == "AUDIT-C":
                base_risk = (score / max_score) * 0.5

            # Temporal decay — recent results weighted higher
            days_ago = screening.get("days_ago", 0)
            temporal_weight = max(0.3, 1.0 - (days_ago / 90.0))

            weighted = base_risk * temporal_weight
            weighted_score += weighted
            total_weight += temporal_weight
            components.append({
                "source": f"screening_{instrument}",
                "base_risk": round(base_risk, 3),
                "temporal_weight": round(temporal_weight, 3),
                "weighted_contribution": round(weighted, 3),
                "days_ago": days_ago,
            })

        # Process encounter history
        for encounter in encounters:
            enc_type = encounter.get("type", "")
            days_ago = encounter.get("days_ago", 0)
            temporal_weight = max(0.2, 1.0 - (days_ago / 60.0))

            enc_risk = 0.0
            if enc_type == "crisis_visit":
                enc_risk = 0.8
            elif enc_type == "psychiatric_emergency":
                enc_risk = 0.9
            elif enc_type == "no_show":
                enc_risk = 0.2

            if enc_risk > 0:
                weighted = enc_risk * temporal_weight
                weighted_score += weighted
                total_weight += temporal_weight
                components.append({
                    "source": f"encounter_{enc_type}",
                    "base_risk": round(enc_risk, 3),
                    "temporal_weight": round(temporal_weight, 3),
                    "weighted_contribution": round(weighted, 3),
                    "days_ago": days_ago,
                })

        # Process medication signals
        high_risk_meds = {"lithium", "clozapine", "naltrexone", "buprenorphine", "methadone"}
        for med in medications:
            med_name = med.get("name", "").lower()
            if any(hrm in med_name for hrm in high_risk_meds):
                # Indicates treatment for serious condition — not a risk factor per se
                # but discontinuation is a risk
                if med.get("status") == "discontinued":
                    risk = 0.3
                    weighted_score += risk
                    total_weight += 1.0
                    components.append({
                        "source": f"medication_discontinued_{med_name}",
                        "base_risk": risk,
                        "temporal_weight": 1.0,
                        "weighted_contribution": risk,
                        "note": "High-risk medication recently discontinued",
                    })

        # Social factors
        for factor in social_factors:
            factor_name = factor.get("type", "") if isinstance(factor, dict) else str(factor)
            risk = 0.15
            weighted_score += risk
            total_weight += 0.5
            components.append({
                "source": f"social_{factor_name}",
                "base_risk": risk,
                "temporal_weight": 0.5,
                "weighted_contribution": risk * 0.5,
            })

        # Normalize composite score
        composite_score = (weighted_score / total_weight) if total_weight > 0 else 0.0
        composite_score = min(composite_score, 1.0)

        # Determine risk level
        risk_level = "none"
        for level, config in RISK_LEVELS.items():
            low, high = config["score_range"]
            if low <= composite_score < high:
                risk_level = level
                break
        if composite_score >= 0.85:
            risk_level = "imminent"

        needs_hitl = risk_level in ("moderate", "high", "imminent")
        status = AgentStatus.WAITING_HITL if needs_hitl else AgentStatus.COMPLETED

        result = {
            "patient_id": patient_id,
            "composite_risk_score": round(composite_score, 3),
            "risk_level": risk_level,
            "components": components,
            "data_sources_evaluated": {
                "screenings": len(screenings),
                "encounters": len(encounters),
                "medications": len(medications),
                "social_factors": len(social_factors),
            },
            "requires_hitl": True,
            "crisis_resources": CRISIS_RESOURCES,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=max(0.60, min(0.90, 0.55 + total_weight * 0.05)),
            rationale=(
                f"Composite risk evaluation for patient {patient_id}: "
                f"score = {composite_score:.3f}, risk level = {risk_level}. "
                f"Evaluated {len(components)} component(s) across "
                f"{len(screenings)} screening(s), {len(encounters)} encounter(s), "
                f"{len(medications)} medication(s), {len(social_factors)} social factor(s)."
            ),
            status=status,
        )

    # ── Safety Plan ──────────────────────────────────────────────────────────

    def _safety_plan(self, input_data: AgentInput) -> AgentOutput:
        """Generate a personalized safety plan template."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        patient_name = ctx.get("patient_name", "Patient")
        warning_signs = ctx.get("warning_signs", [])
        coping_strategies = ctx.get("coping_strategies", [])
        support_contacts = ctx.get("support_contacts", [])
        provider_contacts = ctx.get("provider_contacts", [])
        risk_level = ctx.get("risk_level", "moderate")

        # Build personalized safety plan
        default_warning_signs = [
            "Increased feelings of hopelessness or helplessness",
            "Withdrawal from social activities",
            "Increased alcohol or substance use",
            "Difficulty sleeping or sleeping too much",
            "Giving away possessions",
            "Talking about being a burden",
        ]

        default_coping_strategies = [
            "Deep breathing exercises (4-7-8 technique)",
            "Go for a walk or engage in physical activity",
            "Write in a journal",
            "Listen to calming music",
            "Practice grounding (5-4-3-2-1 technique)",
            "Call a friend or family member",
        ]

        safety_plan = {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "step_1_warning_signs": warning_signs or default_warning_signs,
            "step_2_internal_coping": coping_strategies[:3] if coping_strategies else default_coping_strategies[:3],
            "step_3_social_distractions": [
                "Visit a public place (coffee shop, library, park)",
                "Call a friend to talk about something other than the crisis",
                "Attend a support group or community event",
            ],
            "step_4_support_contacts": support_contacts or [
                {"name": "Trusted friend or family member", "phone": "(to be filled in)"},
            ],
            "step_5_professional_contacts": provider_contacts or [
                {"name": "Therapist", "phone": "(to be filled in)"},
                {"name": "Psychiatrist", "phone": "(to be filled in)"},
            ],
            "step_6_emergency_resources": [
                {"name": "988 Suicide & Crisis Lifeline", "contact": "Call or text 988"},
                {"name": "Crisis Text Line", "contact": "Text HOME to 741741"},
                {"name": "Emergency Services", "contact": "Call 911"},
                {"name": "SAMHSA National Helpline", "contact": "1-800-662-4357"},
                {"name": "Veterans Crisis Line", "contact": "Call 988, press 1"},
            ],
            "environment_safety": {
                "instructions": "Remove or secure access to means of self-harm",
                "items_to_secure": [
                    "Firearms — store with a trusted person or use a gun lock",
                    "Medications — have someone else hold excess supply",
                    "Sharp objects — secure or remove from immediate access",
                ],
            },
            "reasons_for_living": ctx.get("reasons_for_living", [
                "(to be filled in with patient)",
            ]),
            "risk_level_at_creation": risk_level,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "review_date": None,  # to be set by clinician
        }

        result = {
            "safety_plan": safety_plan,
            "requires_hitl": True,
            "crisis_resources": CRISIS_RESOURCES,
            "instructions": (
                "This safety plan template must be reviewed and personalized "
                "with the patient by a licensed clinician before use."
            ),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.80,
            rationale=(
                f"Generated safety plan template for patient {patient_id} "
                f"at risk level {risk_level}. Requires clinician review and personalization."
            ),
            status=AgentStatus.WAITING_HITL,
        )

    # ── Escalation Protocol ──────────────────────────────────────────────────

    def _escalation_protocol(self, input_data: AgentInput) -> AgentOutput:
        """Determine and execute the escalation path based on risk level."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or "unknown")
        risk_level = ctx.get("risk_level", "moderate")
        risk_score = ctx.get("risk_score", 0.5)
        source = ctx.get("source", "manual_assessment")

        if risk_level not in ESCALATION_PATHS:
            risk_level = "moderate"  # default to moderate for safety

        escalation = ESCALATION_PATHS[risk_level]

        # Build notification list
        notifications: list[dict[str, Any]] = []
        for recipient in escalation.get("notifications", []):
            notifications.append({
                "recipient_role": recipient,
                "notification_type": "urgent" if risk_level in ("high", "imminent") else "standard",
                "message": (
                    f"Crisis escalation for patient {patient_id}: "
                    f"risk level {risk_level} detected via {source}. "
                    f"Action required: {escalation['description']}"
                ),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            })

        # Documentation requirements
        documentation = {
            "required_notes": [
                "Document risk assessment findings",
                "Record patient's current mental status",
                "Note any protective factors identified",
                "Document actions taken and rationale",
            ],
            "follow_up_required": risk_level in ("moderate", "high", "imminent"),
            "follow_up_timeline": escalation["timeline"],
            "supervisor_notification_required": risk_level in ("high", "imminent"),
        }

        result = {
            "patient_id": patient_id,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "escalation_action": escalation["action"],
            "escalation_description": escalation["description"],
            "timeline": escalation["timeline"],
            "notifications": notifications,
            "documentation": documentation,
            "requires_hitl": True,
            "crisis_resources": CRISIS_RESOURCES,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=(
                f"Escalation protocol activated for patient {patient_id}: "
                f"risk level {risk_level}, action = {escalation['action']}, "
                f"timeline = {escalation['timeline']}. "
                f"{len(notifications)} notification(s) queued."
            ),
            status=AgentStatus.WAITING_HITL,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_snippet(text: str, phrase: str, window: int = 50) -> str:
        """Extract a text snippet around a matched phrase for context."""
        lower_text = text.lower()
        idx = lower_text.find(phrase.lower())
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(phrase) + window)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet
