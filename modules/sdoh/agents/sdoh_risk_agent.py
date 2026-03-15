"""
Eminence HealthOS — SDOH Risk Agent

Adapted from Inhealth-Capstone-project ``agents/tier3_risk/sdoh_agent.py``.

Responsibilities:
  - Retrieve SDOH assessment data (from service layer or FHIR context)
  - Calculate composite SDOH risk score using weighted domain scoring
  - Match patients with community resources via RAG / vector search
  - Generate social work referral recommendations with LLM planning
  - Produce structured alerts for high-risk and domestic-violence cases
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

logger = structlog.get_logger()

# ── SDOH domains and their clinical impact weights ───────────────────────────
# Preserved from Inhealth sdoh_agent.py

SDOH_DOMAINS: dict[str, dict[str, Any]] = {
    "food_insecurity":      {"weight": 2.0, "loinc": "88122-7"},
    "housing_instability":  {"weight": 2.0, "loinc": "71802-3"},
    "transportation_need":  {"weight": 1.5, "loinc": "93030-5"},
    "financial_strain":     {"weight": 1.5, "loinc": "77594-0"},
    "social_isolation":     {"weight": 1.5, "loinc": "93025-5"},
    "health_literacy_low":  {"weight": 1.0, "loinc": ""},
    "unsafe_neighborhood":  {"weight": 1.0, "loinc": ""},
    "domestic_violence":    {"weight": 2.5, "loinc": "76499-3"},
    "substance_use":        {"weight": 2.0, "loinc": "68517-2"},
    "mental_health_need":   {"weight": 1.5, "loinc": ""},
}

MAX_SDOH_SCORE: float = sum(d["weight"] for d in SDOH_DOMAINS.values())


class SDOHRiskAgent(BaseAgent):
    """Social Determinants of Health risk assessment and resource matching.

    Tier: DECISIONING (risk scoring and policy checks).
    """

    name = "sdoh_risk_agent"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Assesses social, economic, and environmental factors affecting patient "
        "health outcomes. Calculates composite SDOH risk scores and matches "
        "patients with community resources. References NACHC PRAPARE, AHC "
        "Health-Related Social Needs screening, and Healthy People 2030 SDOH framework."
    )
    min_confidence = 0.70

    # ── Core process ─────────────────────────────────────────────────────────

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "assess")

        if action == "assess":
            return await self._assess_patient(input_data)
        elif action == "score":
            return self._score_only(input_data)
        elif action == "recommendations":
            return self._generate_recs(input_data)
        elif action == "screen_parse":
            return self._parse_screening(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown SDOH action: {action}"},
                confidence=0.0,
                rationale=f"Unknown action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Full assessment (main flow) ──────────────────────────────────────────

    async def _assess_patient(self, input_data: AgentInput) -> AgentOutput:
        """Full SDOH assessment pipeline: parse, score, match resources, plan."""
        ctx = input_data.context
        patient_id = str(input_data.patient_id or ctx.get("patient_id", "unknown"))

        # Parse SDOH screening data from context
        observations = ctx.get("observations", [])
        questionnaire_responses = ctx.get("questionnaire_responses", [])

        sdoh_screen = self._parse_sdoh_screen(observations)
        questionnaire_results = self._parse_questionnaire(questionnaire_responses)
        combined_sdoh = {**sdoh_screen, **questionnaire_results}

        # Also accept direct domain flags from context (e.g. from assessment service)
        for domain in SDOH_DOMAINS:
            if ctx.get(domain) is True:
                combined_sdoh[domain] = True

        # Calculate composite SDOH score
        score_result = self._calculate_sdoh_score(combined_sdoh)
        needs_list = score_result["active_needs"]

        # Build alerts
        alerts = self._build_alerts(patient_id, combined_sdoh, score_result)

        # Generate recommendations
        recs = self._generate_static_recommendations(needs_list, score_result)

        # LLM intervention planning prompt (for downstream LLM call)
        needs_formatted = "\n".join(
            [f"  - {n.replace('_', ' ').title()}" for n in needs_list]
        ) or "  No significant SDOH needs identified"

        intervention_prompt = (
            f"Patient {patient_id} SDOH assessment:\n\n"
            f"Identified social needs:\n{needs_formatted}\n\n"
            f"SDOH Risk Score: {score_result['score']:.1f}/{MAX_SDOH_SCORE:.1f} "
            f"({score_result['risk_level']})\n\n"
            f"Provide:\n"
            f"1. Prioritized SDOH intervention plan (highest health impact first)\n"
            f"2. Specific community resource referrals with contact information\n"
            f"3. Trauma-informed, culturally sensitive communication approach\n"
            f"4. Impact of unaddressed SDOH on chronic disease control\n"
            f"5. Social work referral urgency and scope"
        )

        # Attempt LLM-powered intervention planning
        intervention_plan = ""
        try:
            from healthos_platform.ml.llm.router import LLMRequest, llm_router

            llm_result = await llm_router.route(LLMRequest(
                prompt=intervention_prompt,
                system_prompt=(
                    "You are the Social Determinants of Health (SDOH) AI Agent for "
                    "Eminence HealthOS. You assess social, economic, and environmental "
                    "factors affecting patient health outcomes. Calculate composite SDOH "
                    "risk scores and match patients with community resources. Reference "
                    "NACHC PRAPARE assessment tool, AHC Health-Related Social Needs "
                    "screening, and Healthy People 2030 SDOH framework."
                ),
                max_tokens=1024,
                temperature=0.3,
            ))
            intervention_plan = llm_result.content if llm_result else ""
        except Exception as exc:
            logger.warning("sdoh.llm_planning_failed", error=str(exc))

        result = {
            "patient_id": patient_id,
            "sdoh_needs": combined_sdoh,
            "needs_count": len(needs_list),
            "sdoh_score": score_result,
            "intervention_plan": intervention_plan,
            "recommendations": recs,
            "alerts": alerts,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

        confidence = 0.85 if needs_list else 0.90
        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"SDOH assessment complete. Score {score_result['score']:.1f}/"
                f"{MAX_SDOH_SCORE:.1f} ({score_result['risk_level']}). "
                f"{len(needs_list)} active social needs identified."
            ),
        )

    # ── Score-only action ────────────────────────────────────────────────────

    def _score_only(self, input_data: AgentInput) -> AgentOutput:
        """Calculate SDOH score from domain flags in context."""
        ctx = input_data.context
        sdoh_flags = {domain: ctx.get(domain, False) for domain in SDOH_DOMAINS}
        score_result = self._calculate_sdoh_score(sdoh_flags)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"sdoh_score": score_result},
            confidence=0.95,
            rationale=f"SDOH score: {score_result['score']:.1f}/{MAX_SDOH_SCORE:.1f}",
        )

    # ── Recommendations-only action ──────────────────────────────────────────

    def _generate_recs(self, input_data: AgentInput) -> AgentOutput:
        """Generate recommendations from domain flags or a score result."""
        ctx = input_data.context
        sdoh_flags = {domain: ctx.get(domain, False) for domain in SDOH_DOMAINS}
        score_result = self._calculate_sdoh_score(sdoh_flags)
        recs = self._generate_static_recommendations(score_result["active_needs"], score_result)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"recommendations": recs, "sdoh_score": score_result},
            confidence=0.85,
            rationale=f"{len(recs)} recommendations generated for {len(score_result['active_needs'])} needs.",
        )

    # ── Screen parsing action ────────────────────────────────────────────────

    def _parse_screening(self, input_data: AgentInput) -> AgentOutput:
        """Parse raw FHIR observations and questionnaire responses."""
        ctx = input_data.context
        observations = ctx.get("observations", [])
        questionnaire_responses = ctx.get("questionnaire_responses", [])

        sdoh_screen = self._parse_sdoh_screen(observations)
        questionnaire_results = self._parse_questionnaire(questionnaire_responses)
        combined = {**sdoh_screen, **questionnaire_results}

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"sdoh_needs": combined, "needs_count": sum(1 for v in combined.values() if v)},
            confidence=0.90,
            rationale="SDOH screening data parsed.",
        )

    # ── Internal helpers (preserved from Inhealth sdoh_agent.py) ─────────────

    def _parse_sdoh_screen(self, resources: list[dict[str, Any]]) -> dict[str, bool]:
        """Parse FHIR Observation resources for SDOH screening results."""
        screen: dict[str, bool] = {domain: False for domain in SDOH_DOMAINS}
        for r in resources:
            code = r.get("code", "")
            value = r.get("value", "")
            for domain, info in SDOH_DOMAINS.items():
                if code == info.get("loinc") and value in ("positive", "yes", "1", "true"):
                    screen[domain] = True
        return screen

    def _parse_questionnaire(self, resources: list[dict[str, Any]]) -> dict[str, bool]:
        """Parse QuestionnaireResponse for PRAPARE-style SDOH screens."""
        result: dict[str, bool] = {}
        for r in resources:
            meta = r.get("meta", {})
            answers = meta.get("answers", {}) if isinstance(meta, dict) else {}
            for domain in SDOH_DOMAINS:
                if answers.get(domain) in (True, "yes", 1, "positive"):
                    result[domain] = True
        return result

    def _calculate_sdoh_score(self, sdoh: dict[str, bool]) -> dict[str, Any]:
        """Calculate weighted SDOH composite score.

        Preserved from Inhealth ``SDOHAgent._calculate_sdoh_score()``.
        """
        score = 0.0
        active_needs: list[str] = []
        for domain, present in sdoh.items():
            if present and domain in SDOH_DOMAINS:
                weight = SDOH_DOMAINS[domain]["weight"]
                score += weight
                active_needs.append(domain)

        percentage = (score / MAX_SDOH_SCORE) * 100 if MAX_SDOH_SCORE > 0 else 0.0

        if percentage >= 50:
            risk_level = "CRITICAL"
        elif percentage >= 30:
            risk_level = "HIGH"
        elif percentage >= 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "score": round(score, 2),
            "max_score": MAX_SDOH_SCORE,
            "percentage": round(percentage, 1),
            "risk_level": risk_level,
            "active_needs": active_needs,
        }

    def _build_alerts(
        self,
        patient_id: str,
        combined_sdoh: dict[str, bool],
        score_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build alert objects for high-risk conditions."""
        alerts: list[dict[str, Any]] = []

        if score_result["risk_level"] in ("HIGH", "CRITICAL"):
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"High SDOH risk: Score {score_result['score']:.1f}/"
                    f"{MAX_SDOH_SCORE:.1f} ({score_result['risk_level']}). "
                    f"Social work referral recommended."
                ),
                "patient_id": patient_id,
                "domain": "composite",
            })

        if combined_sdoh.get("domestic_violence"):
            alerts.append({
                "severity": "HIGH",
                "message": (
                    "Domestic violence/safety concern identified. Immediate "
                    "social work consultation and safety planning required."
                ),
                "patient_id": patient_id,
                "domain": "domestic_violence",
            })

        if combined_sdoh.get("food_insecurity"):
            alerts.append({
                "severity": "NORMAL",
                "message": (
                    "Food insecurity identified. Link to food assistance programs. "
                    "Consider nutrition counseling. Food insecurity increases HbA1c "
                    "by 0.5-1.0%."
                ),
                "patient_id": patient_id,
                "domain": "food_insecurity",
            })

        return alerts

    def _generate_static_recommendations(
        self,
        needs: list[str],
        score_result: dict[str, Any],
    ) -> list[str]:
        """Generate static intervention recommendations.

        Preserved from Inhealth ``SDOHAgent._generate_recommendations()``.
        """
        recs: list[str] = []
        if "food_insecurity" in needs:
            recs.append(
                "Food insecurity: Refer to local food bank, SNAP enrollment "
                "assistance, and diabetes-appropriate nutrition programs."
            )
        if "housing_instability" in needs:
            recs.append(
                "Housing instability: Social work referral for housing assistance. "
                "Unstable housing is associated with 2x hospital readmission risk."
            )
        if "transportation_need" in needs:
            recs.append(
                "Transportation need: Connect with medical transportation services. "
                "Consider telehealth as alternative for routine visits."
            )
        if "financial_strain" in needs:
            recs.append(
                "Financial strain: Connect with financial assistance programs and "
                "prescription assistance (NeedyMeds.org, RxAssist.org)."
            )
        if "social_isolation" in needs:
            recs.append(
                "Social isolation: Refer to community support groups and senior "
                "services (eldercare.acl.gov, NAMI)."
            )
        if "domestic_violence" in needs:
            recs.append(
                "Domestic violence: Immediate social work consultation. Activate "
                "safety planning protocol. National DV Hotline: 1-800-799-7233."
            )
        if "substance_use" in needs:
            recs.append(
                "Substance use concern: Refer to SAMHSA treatment locator. "
                "Consider integrated behavioral health support."
            )
        if "mental_health_need" in needs:
            recs.append(
                "Mental health need: Screen with PHQ-9/GAD-7. Refer to "
                "behavioral health integration or community mental health center."
            )
        if score_result.get("risk_level") in ("HIGH", "CRITICAL"):
            recs.append(
                "High SDOH burden: Assign dedicated care coordinator. Monthly "
                "social work follow-up. CHW (Community Health Worker) engagement."
            )
        return recs
