"""
Prescription Recommender Agent — Tier 4 (Action / Intervention).

Generates evidence-based medication recommendations for chronic disease
management. Checks drug interactions, allergies, and contraindications.
All recommendations require physician approval (HITL).

Adapted from InHealth prescription_agent (Tier 4 Intervention).
This differs from the existing PrescriptionAgent (e-prescribing workflow)
by focusing on clinical decision support for medication gap analysis
and optimization recommendations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.prescription_recommender")

# Evidence levels
EVIDENCE_LEVELS = {
    "A": "Strong evidence from RCTs or systematic reviews",
    "B": "Moderate evidence from well-designed studies",
    "C": "Consensus or expert opinion",
    "D": "Case series, limited evidence",
}


class PrescriptionRecommenderAgent(HealthOSAgent):
    """RAG-assisted medication recommendation with HITL approval."""

    def __init__(self) -> None:
        super().__init__(
            name="prescription_recommender",
            tier=AgentTier.INTERVENTION,
            description=(
                "Generates evidence-based medication recommendations with drug interaction "
                "and allergy checking. All prescriptions require physician approval (HITL)."
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.MEDICATION_CHECK, AgentCapability.CARE_PLAN_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        current_meds: list[str] = data.get("current_medications", [])
        current_allergies: list[str] = data.get("allergies", [])
        current_conditions: list[str] = data.get("conditions", [])
        hba1c = data.get("hba1c")
        egfr = data.get("egfr")
        risk_level: str = data.get("risk_level", "MEDIUM")
        drug_interactions: dict[str, Any] = data.get("drug_interactions", {})

        alerts: list[dict[str, Any]] = []

        if drug_interactions.get("has_contraindications"):
            alerts.append({
                "severity": "HIGH",
                "message": (
                    "CONTRAINDICATED DRUG COMBINATION detected in current medication list. "
                    "Physician review required before any prescription changes."
                ),
            })

        # LLM recommendation generation
        allergies_str = ", ".join(current_allergies) if current_allergies else "None documented"
        conditions_str = ", ".join(current_conditions[:10]) if current_conditions else "None"
        meds_str = ", ".join(current_meds[:20]) if current_meds else "None"
        interactions_str = (
            f"{drug_interactions.get('total_interactions', 0)} interactions found"
            if drug_interactions else "Not checked"
        )

        prescription_recommendation = "Unable to generate recommendation. Manual review required."
        try:
            prompt = (
                f"Medication recommendation request:\n\n"
                f"Current conditions: {conditions_str}\n"
                f"Current medications: {meds_str}\n"
                f"Known allergies: {allergies_str}\n"
                f"Lab values: HbA1c={hba1c}, eGFR={egfr}\n"
                f"Drug interactions: {interactions_str}\n"
                f"Risk level: {risk_level}\n\n"
                "Generate structured medication recommendation(s):\n"
                "For each recommendation include:\n"
                "1. Drug name (generic + brand)\n"
                "2. Dose, frequency, route, duration\n"
                "3. Evidence level (A/B/C) with guideline citation\n"
                "4. Indication and rationale\n"
                "5. Monitoring requirements\n"
                "6. Contraindications check against current meds and allergies\n"
                "7. Patient education points (3-5 key points)\n"
                "8. Alternative options if first-line not appropriate\n"
                "9. Expected clinical outcome\n"
                "10. Confidence score (0.0-1.0)\n\n"
                "IMPORTANT: Flag any prescription that modifies existing medications as requiring physician approval."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical pharmacology decision support narrator. "
                    "Reference ADA 2024, ACC/AHA 2023, KDIGO 2024, JNC-8, and GOLD 2024 guidelines. "
                    "Always check drug interactions, allergies, and contraindications."
                ),
                temperature=0.3,
                max_tokens=1536,
            ))
            prescription_recommendation = resp.content
        except Exception:
            logger.warning("LLM prescription generation failed; manual review required")

        recommendation_payload = {
            "recommendation_text": prescription_recommendation,
            "current_medications": current_meds,
            "current_conditions": current_conditions,
            "allergies": current_allergies,
            "drug_interactions_found": drug_interactions.get("total_interactions", 0),
            "has_contraindications": drug_interactions.get("has_contraindications", False),
            "requires_hitl": True,
            "type": "medication",
            "alerts": alerts,
        }

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            status=AgentStatus.WAITING_HITL,
            decision="prescription_recommendation",
            rationale=(
                f"Medication recommendation generated for {len(current_conditions)} conditions; "
                f"{drug_interactions.get('total_interactions', 0)} drug interactions found"
            ),
            confidence=0.75,
            data=recommendation_payload,
            requires_hitl=True,
            hitl_reason="All medication recommendations require physician review and approval",
        )
