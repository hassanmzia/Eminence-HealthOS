"""
Eminence HealthOS — Medication Review Agent
Layer 2 (Interpretation): Reviews patient medication lists for potential
drug-drug interactions, contraindications against active conditions,
duplicate therapies, and dosage concerns.
"""

from __future__ import annotations

from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    Severity,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger(__name__)

# Known high-risk drug interaction pairs (simplified clinical reference)
INTERACTION_DB: list[dict[str, Any]] = [
    {"drug_a": "warfarin", "drug_b": "aspirin", "severity": "high", "description": "Increased bleeding risk"},
    {"drug_a": "warfarin", "drug_b": "ibuprofen", "severity": "high", "description": "Increased bleeding risk with NSAIDs"},
    {"drug_a": "metformin", "drug_b": "contrast_dye", "severity": "high", "description": "Risk of lactic acidosis"},
    {"drug_a": "lisinopril", "drug_b": "potassium", "severity": "moderate", "description": "Hyperkalemia risk with ACE inhibitors"},
    {"drug_a": "lisinopril", "drug_b": "spironolactone", "severity": "moderate", "description": "Hyperkalemia risk"},
    {"drug_a": "simvastatin", "drug_b": "amiodarone", "severity": "high", "description": "Increased myopathy risk"},
    {"drug_a": "fluoxetine", "drug_b": "tramadol", "severity": "high", "description": "Serotonin syndrome risk"},
    {"drug_a": "metoprolol", "drug_b": "verapamil", "severity": "high", "description": "Risk of severe bradycardia"},
    {"drug_a": "digoxin", "drug_b": "amiodarone", "severity": "high", "description": "Digoxin toxicity risk"},
    {"drug_a": "ciprofloxacin", "drug_b": "theophylline", "severity": "moderate", "description": "Theophylline toxicity risk"},
]

# Condition → contraindicated drug classes
CONTRAINDICATIONS: dict[str, list[str]] = {
    "chronic_kidney_disease": ["nsaids", "metformin", "lithium"],
    "heart_failure": ["nsaids", "thiazolidinediones", "verapamil", "diltiazem"],
    "asthma": ["beta_blockers", "aspirin"],
    "peptic_ulcer": ["nsaids", "aspirin", "corticosteroids"],
    "liver_disease": ["acetaminophen_high_dose", "statins", "methotrexate"],
}


class MedicationReviewAgent(BaseAgent):
    name = "medication_review"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Drug interaction checks, contraindication screening, and medication safety review"
    min_confidence = 0.8

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context

        medications: list[Any] = ctx.get("medications", [])
        conditions: list[Any] = ctx.get("conditions", [])

        # Normalize medication names
        med_names = [self._normalize_med(m) for m in medications]

        # Check drug-drug interactions
        interactions = self._check_interactions(med_names)

        # Check condition contraindications
        contraindication_warnings = self._check_contraindications(med_names, conditions)

        # Check for duplicate therapies
        duplicates = self._check_duplicates(med_names)

        all_findings = interactions + contraindication_warnings + duplicates
        has_critical = any(f["severity"] == "high" for f in all_findings)

        # ── LLM: generate medication review narrative ─────────────────
        medication_review_narrative: str | None = None
        try:
            prompt = (
                f"Medications: {', '.join(med_names) or 'none'}.\n"
                f"Conditions: {', '.join(str(c) for c in conditions) or 'none reported'}.\n"
                f"Interactions found: {len(interactions)} — "
                f"{'; '.join(i['description'] for i in interactions) or 'none'}.\n"
                f"Contraindications found: {len(contraindication_warnings)} — "
                f"{'; '.join(c['description'] for c in contraindication_warnings) or 'none'}.\n"
                f"Duplicate therapies: {len(duplicates)} — "
                f"{'; '.join(d['description'] for d in duplicates) or 'none'}.\n\n"
                "Provide a concise medication review narrative analyzing the appropriateness "
                "of this medication regimen. Highlight any safety concerns, recommend "
                "monitoring parameters, and suggest potential optimizations."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical pharmacist reviewing a patient's medication list "
                    "in a telehealth platform. Provide a professional medication review "
                    "narrative suitable for provider decision-support. Focus on safety, "
                    "efficacy, and actionable recommendations."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            medication_review_narrative = resp.content
        except Exception:
            logger.warning("LLM unavailable for medication review narrative; continuing without it.")

        result = {
            "medications_reviewed": med_names,
            "interactions": interactions,
            "contraindications": contraindication_warnings,
            "duplicates": duplicates,
            "total_findings": len(all_findings),
            "has_critical_findings": has_critical,
        }
        if medication_review_narrative:
            result["medication_review_narrative"] = medication_review_narrative

        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            status=AgentStatus.WAITING_HITL if has_critical else AgentStatus.COMPLETED,
            confidence=0.85,
            result=result,
            rationale=(
                f"Reviewed {len(med_names)} medications: "
                f"{len(interactions)} interaction(s), "
                f"{len(contraindication_warnings)} contraindication(s), "
                f"{len(duplicates)} duplicate(s)"
            ),
            requires_hitl=has_critical,
            hitl_reason="Critical drug interaction or contraindication found" if has_critical else None,
        )

    def _check_interactions(self, meds: list[str]) -> list[dict[str, Any]]:
        findings = []
        for i, med_a in enumerate(meds):
            for med_b in meds[i + 1:]:
                for interaction in INTERACTION_DB:
                    a, b = interaction["drug_a"], interaction["drug_b"]
                    if (med_a == a and med_b == b) or (med_a == b and med_b == a):
                        findings.append({
                            "type": "drug_interaction",
                            "drug_a": med_a,
                            "drug_b": med_b,
                            "severity": interaction["severity"],
                            "description": interaction["description"],
                        })
        return findings

    def _check_contraindications(
        self, meds: list[str], conditions: list[Any]
    ) -> list[dict[str, Any]]:
        findings = []
        for c in conditions:
            cond_key = (c.get("display", c) if isinstance(c, dict) else str(c)).lower().replace(" ", "_")
            contraindicated = CONTRAINDICATIONS.get(cond_key, [])
            for drug_class in contraindicated:
                for med in meds:
                    if drug_class in med or med in drug_class:
                        findings.append({
                            "type": "contraindication",
                            "medication": med,
                            "condition": cond_key,
                            "drug_class": drug_class,
                            "severity": "high",
                            "description": f"{med} may be contraindicated with {cond_key}",
                        })
        return findings

    @staticmethod
    def _check_duplicates(meds: list[str]) -> list[dict[str, Any]]:
        """Check for duplicate therapeutic classes (simplified)."""
        findings = []
        seen: dict[str, str] = {}
        # Simple duplicate check by drug name stem
        for med in meds:
            stem = med[:4]  # crude stem matching
            if stem in seen and seen[stem] != med:
                findings.append({
                    "type": "duplicate_therapy",
                    "drug_a": seen[stem],
                    "drug_b": med,
                    "severity": "moderate",
                    "description": f"Possible duplicate therapy: {seen[stem]} and {med}",
                })
            seen[stem] = med
        return findings

    @staticmethod
    def _normalize_med(med: Any) -> str:
        """Normalize medication entry to lowercase drug name."""
        if isinstance(med, dict):
            return med.get("name", "").lower().split()[0] if med.get("name") else "unknown"
        return str(med).lower().split()[0]
