"""
Contraindication & Safety Agent — Tier 4 (Action / Intervention).

Performs comprehensive drug safety analysis: drug-drug interactions,
drug-disease contraindications, allergy conflicts, and QT-prolonging
medication checks. Generates safety alerts with intervention recommendations.

Adapted from InHealth contraindication_agent (Tier 4 Intervention).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.contraindication")

# Severity mapping to alert level
SEVERITY_ALERT_MAP = {
    "contraindicated": "EMERGENCY",
    "major": "HIGH",
    "moderate": "MEDIUM",
    "minor": "LOW",
}


class ContraindicationAgent(HealthOSAgent):
    """Drug safety, contraindication, and interaction verification."""

    def __init__(self) -> None:
        super().__init__(
            name="contraindication",
            tier=AgentTier.INTERVENTION,
            description=(
                "Comprehensive drug safety analysis: DDI, drug-disease contraindications, "
                "allergy conflicts, and QT-prolongation risk"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.MEDICATION_CHECK, AgentCapability.COMPLIANCE_CHECK]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        current_meds: list[str] = data.get("current_medications", [])
        proposed_meds: list[str] = data.get("proposed_medications", [])
        current_allergies: list[str] = data.get("allergies", [])
        current_conditions: list[str] = data.get("conditions", [])
        ddi_interactions: list[dict[str, Any]] = data.get("drug_interactions", [])
        drug_disease_contraindications: list[dict[str, Any]] = data.get("drug_disease_contraindications", [])

        all_meds = list(set(current_meds + proposed_meds))

        alerts: list[dict[str, Any]] = []
        severity = "LOW"
        emergency = False

        # 1. Drug-drug interactions
        for interaction in ddi_interactions:
            sev = interaction.get("severity", "minor")
            alert_level = SEVERITY_ALERT_MAP.get(sev, "LOW")
            if sev == "contraindicated":
                emergency = True
                severity = "EMERGENCY"
            alerts.append({
                "severity": alert_level,
                "message": (
                    f"Drug interaction [{sev.upper()}]: "
                    f"{interaction.get('drug1', '')} <-> {interaction.get('drug2', '')}. "
                    f"Effect: {interaction.get('clinical_effect', 'N/A')}. "
                    f"Management: {interaction.get('management', 'Monitor closely')}"
                ),
            })

        # 2. Drug-disease contraindications
        for contra in drug_disease_contraindications:
            sev = contra.get("severity", "major")
            if sev == "absolute":
                emergency = True
                severity = "EMERGENCY"
            alerts.append({
                "severity": "EMERGENCY" if sev == "absolute" else "HIGH",
                "message": (
                    f"Drug-disease contraindication: {contra.get('drug', '')} "
                    f"contraindicated in {contra.get('condition', '')}. "
                    f"Rationale: {contra.get('rationale', 'N/A')}. "
                    f"Alternative: {contra.get('alternative', 'Consult physician')}"
                ),
            })

        # 3. Drug-allergy conflicts
        allergy_conflicts: list[dict[str, str]] = []
        for med in all_meds:
            for allergy in current_allergies:
                if allergy.lower() in med.lower() or med.lower() in allergy.lower():
                    allergy_conflicts.append({"drug": med, "allergy": allergy})
                    emergency = True
                    severity = "EMERGENCY"
                    alerts.append({
                        "severity": "EMERGENCY",
                        "message": (
                            f"ALLERGY CONFLICT: {med} - patient has documented allergy "
                            f"to {allergy}. STOP - do not administer."
                        ),
                    })

        # 4. QT-prolonging medication check
        qt_prolonging = self._check_qt_prolonging(all_meds)
        if len(qt_prolonging) >= 2:
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"Multiple QT-prolonging medications: {', '.join(qt_prolonging)}. "
                    "Risk of Torsades de Pointes. Monitor QTc interval."
                ),
            })

        recommendations = self._generate_recommendations(ddi_interactions, allergy_conflicts)

        # LLM safety narrative
        safety_narrative = None
        try:
            prompt = (
                f"Medication safety analysis:\n\n"
                f"Current medications: {', '.join(current_meds[:20])}\n"
                f"Proposed medications: {', '.join(proposed_meds)}\n"
                f"Allergies: {', '.join(current_allergies) or 'None'}\n"
                f"Conditions: {', '.join(current_conditions[:10])}\n\n"
                f"Drug-drug interactions found: {len(ddi_interactions)}\n"
                f"Drug-disease contraindications: {len(drug_disease_contraindications)}\n"
                f"Allergy conflicts: {len(allergy_conflicts)}\n"
                f"QT-prolonging medications: {qt_prolonging}\n\n"
                "Provide:\n"
                "1. Safety priority list (most dangerous first)\n"
                "2. Specific management for each interaction/contraindication\n"
                "3. Safe alternative medications for contraindicated drugs\n"
                "4. Required monitoring parameters and frequency\n"
                "5. Patient counseling points"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical pharmacology safety narrator. "
                    "Reference FDA drug labels, Micromedex, and Clinical Pharmacology."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            safety_narrative = resp.content
        except Exception:
            logger.warning("LLM contraindication analysis failed; continuing without it")

        ddi_severity_summary: dict[str, int] = {}
        for i in ddi_interactions:
            sev = i.get("severity", "minor")
            ddi_severity_summary[sev] = ddi_severity_summary.get(sev, 0) + 1

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="safety_assessment",
            rationale=(
                f"{len(ddi_interactions)} DDI; {len(drug_disease_contraindications)} drug-disease; "
                f"{len(allergy_conflicts)} allergy conflicts; {len(qt_prolonging)} QT-prolonging meds"
            ),
            confidence=0.90,
            data={
                "severity": severity,
                "ddi_count": len(ddi_interactions),
                "drug_disease_contraindications": len(drug_disease_contraindications),
                "allergy_conflicts": len(allergy_conflicts),
                "qt_prolonging_meds": qt_prolonging,
                "severity_summary": ddi_severity_summary,
                "safety_narrative": safety_narrative,
                "meds_analyzed": len(all_meds),
                "alerts": alerts,
                "recommendations": recommendations,
            },
            requires_hitl=emergency,
            hitl_reason="Critical drug safety issue requires immediate physician review" if emergency else None,
        )

    # -- Medical logic (preserved from source) ------------------------------------

    def _check_qt_prolonging(self, meds: list[str]) -> list[str]:
        qt_known = [
            "azithromycin", "clarithromycin", "erythromycin",
            "haloperidol", "quetiapine", "risperidone", "olanzapine",
            "amiodarone", "sotalol", "dofetilide",
            "methadone", "ondansetron", "hydroxychloroquine",
            "ciprofloxacin", "levofloxacin", "moxifloxacin",
        ]
        return [med for med in meds if any(qt.lower() in med.lower() for qt in qt_known)]

    def _generate_recommendations(
        self,
        interactions: list[dict[str, Any]],
        allergy_conflicts: list[dict[str, str]],
    ) -> list[str]:
        recs: list[str] = []
        if allergy_conflicts:
            recs.append(
                "CRITICAL: Remove allergenic medications from order. "
                "Document allergy reaction type. Select safe alternative."
            )
        contraindicated = [i for i in interactions if i.get("severity") == "contraindicated"]
        if contraindicated:
            pairs = ", ".join([
                f"{i.get('drug1', '')}+{i.get('drug2', '')}" for i in contraindicated[:3]
            ])
            recs.append(
                f"CONTRAINDICATED combination(s) detected: {pairs}. "
                "Discontinue and replace with safe alternatives."
            )
        if not recs:
            recs.append("No critical safety issues identified. Continue current regimen with standard monitoring.")
        return recs
