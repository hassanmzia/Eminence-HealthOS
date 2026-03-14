"""
Eminence HealthOS — Pharmacogenomics Agent (#74)
Layer 3 (Decisioning): Matches medications to patient's genetic profile
for precision medicine, drug metabolism prediction, and adverse effect risk.
"""

from __future__ import annotations

import json
import logging
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
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

# Gene-drug interactions (CPIC guidelines)
GENE_DRUG_INTERACTIONS: dict[str, dict[str, Any]] = {
    "CYP2D6": {
        "gene_name": "Cytochrome P450 2D6",
        "drugs_affected": ["codeine", "tramadol", "tamoxifen", "metoprolol", "fluoxetine", "paroxetine"],
        "phenotypes": {
            "poor_metabolizer": {"prevalence": 0.07, "effect": "Reduced drug activation, increased toxicity risk", "action": "Use alternative or reduce dose"},
            "intermediate_metabolizer": {"prevalence": 0.12, "effect": "Reduced metabolism", "action": "Consider dose adjustment"},
            "normal_metabolizer": {"prevalence": 0.70, "effect": "Standard metabolism", "action": "Standard dosing"},
            "ultra_rapid_metabolizer": {"prevalence": 0.11, "effect": "Rapid drug activation, reduced efficacy", "action": "Use alternative or increase dose"},
        },
    },
    "CYP2C19": {
        "gene_name": "Cytochrome P450 2C19",
        "drugs_affected": ["clopidogrel", "omeprazole", "escitalopram", "voriconazole"],
        "phenotypes": {
            "poor_metabolizer": {"prevalence": 0.03, "effect": "Reduced clopidogrel activation", "action": "Use alternative antiplatelet (e.g., prasugrel)"},
            "intermediate_metabolizer": {"prevalence": 0.25, "effect": "Decreased activation", "action": "Consider alternative or higher dose"},
            "normal_metabolizer": {"prevalence": 0.60, "effect": "Standard metabolism", "action": "Standard dosing"},
            "rapid_metabolizer": {"prevalence": 0.12, "effect": "Increased metabolism", "action": "Consider dose adjustment for PPIs"},
        },
    },
    "VKORC1": {
        "gene_name": "Vitamin K Epoxide Reductase Complex 1",
        "drugs_affected": ["warfarin"],
        "phenotypes": {
            "high_sensitivity": {"prevalence": 0.15, "effect": "High warfarin sensitivity, bleeding risk", "action": "Start at lower dose (1-2mg)"},
            "normal_sensitivity": {"prevalence": 0.55, "effect": "Standard warfarin response", "action": "Standard dosing (5mg)"},
            "low_sensitivity": {"prevalence": 0.30, "effect": "Warfarin resistance", "action": "May require higher doses (7-10mg)"},
        },
    },
    "HLA-B*5701": {
        "gene_name": "HLA-B*5701 Allele",
        "drugs_affected": ["abacavir"],
        "phenotypes": {
            "positive": {"prevalence": 0.06, "effect": "High risk of hypersensitivity reaction", "action": "CONTRAINDICATED — do not prescribe abacavir"},
            "negative": {"prevalence": 0.94, "effect": "No increased hypersensitivity risk", "action": "Abacavir can be used"},
        },
    },
    "SLCO1B1": {
        "gene_name": "Solute Carrier Organic Anion Transporter 1B1",
        "drugs_affected": ["simvastatin", "atorvastatin", "rosuvastatin"],
        "phenotypes": {
            "poor_function": {"prevalence": 0.08, "effect": "Increased statin exposure, myopathy risk", "action": "Use lower statin dose or alternative (rosuvastatin preferred)"},
            "decreased_function": {"prevalence": 0.22, "effect": "Moderately increased exposure", "action": "Avoid simvastatin > 20mg"},
            "normal_function": {"prevalence": 0.70, "effect": "Standard statin metabolism", "action": "Standard dosing"},
        },
    },
}


class PharmacogenomicsAgent(BaseAgent):
    """Matches medications to patient's genetic profile for precision medicine."""

    name = "pharmacogenomics"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Pharmacogenomic-guided prescribing — CPIC guideline-based drug-gene "
        "interaction analysis, metabolizer phenotyping, and dose optimization"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "check_drug_gene")

        if action == "check_drug_gene":
            return await self._check_drug_gene(input_data)
        elif action == "patient_profile":
            return self._patient_profile(input_data)
        elif action == "dose_recommendation":
            return self._dose_recommendation(input_data)
        elif action == "panel_summary":
            return self._panel_summary(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown pharmacogenomics action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _check_drug_gene(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        medication = ctx.get("medication", "").lower()
        genotype = ctx.get("genotype", {})

        interactions: list[dict[str, Any]] = []
        for gene, info in GENE_DRUG_INTERACTIONS.items():
            if medication in info["drugs_affected"]:
                patient_phenotype = genotype.get(gene, "normal_metabolizer")
                if patient_phenotype not in info["phenotypes"]:
                    patient_phenotype = list(info["phenotypes"].keys())[2] if len(info["phenotypes"]) > 2 else list(info["phenotypes"].keys())[0]

                phenotype_info = info["phenotypes"][patient_phenotype]
                interactions.append({
                    "gene": gene,
                    "gene_name": info["gene_name"],
                    "medication": medication,
                    "patient_phenotype": patient_phenotype,
                    "effect": phenotype_info["effect"],
                    "recommended_action": phenotype_info["action"],
                    "population_prevalence": phenotype_info["prevalence"],
                    "clinical_significance": "high" if "CONTRAINDICATED" in phenotype_info["action"] or "alternative" in phenotype_info["action"].lower() else "moderate",
                })

        # --- LLM-generated PGx recommendation ---
        pgx_recommendation = None
        try:
            pgx_payload = {
                "medication": medication,
                "interactions": interactions,
                "patient_genotype": genotype,
                "current_medications": ctx.get("current_medications", []),
            }
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Explain how these genetic variants affect drug metabolism "
                    f"and dosing for this patient.\n\n"
                    f"Pharmacogenomic details:\n{json.dumps(pgx_payload, indent=2)}"
                )}],
                system=(
                    "You are a pharmacogenomics specialist AI with expertise in "
                    "CPIC guidelines. Explain in clinician-friendly language how "
                    "the patient's genetic variants affect metabolism of the "
                    "prescribed medication. Include specific dosing recommendations, "
                    "alternative drug suggestions where appropriate, monitoring "
                    "recommendations, and the strength of evidence (CPIC level). "
                    "Be concise and clinically actionable."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if llm_response and llm_response.content:
                pgx_recommendation = llm_response.content
        except Exception:
            logger.warning(
                "LLM call failed for PGx recommendation on %s; skipping",
                medication,
                exc_info=True,
            )

        result = {
            "checked_at": now.isoformat(),
            "medication": medication,
            "interactions": interactions,
            "total_interactions": len(interactions),
            "requires_action": any(i["clinical_significance"] == "high" for i in interactions),
            "pgx_recommendation": pgx_recommendation,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"PGx check for {medication}: {len(interactions)} gene interactions",
        )

    def _patient_profile(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        genotype = ctx.get("genotype", {
            "CYP2D6": "normal_metabolizer",
            "CYP2C19": "intermediate_metabolizer",
            "VKORC1": "normal_sensitivity",
            "HLA-B*5701": "negative",
            "SLCO1B1": "normal_function",
        })

        profile: list[dict[str, Any]] = []
        for gene, phenotype in genotype.items():
            info = GENE_DRUG_INTERACTIONS.get(gene, {})
            phenotype_data = info.get("phenotypes", {}).get(phenotype, {})
            profile.append({
                "gene": gene,
                "gene_name": info.get("gene_name", gene),
                "phenotype": phenotype,
                "drugs_affected": info.get("drugs_affected", []),
                "clinical_implication": phenotype_data.get("effect", "Unknown"),
            })

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "profiled_at": now.isoformat(),
            "genetic_profile": profile,
            "total_genes_tested": len(profile),
            "actionable_findings": sum(1 for p in profile if p["phenotype"] not in ("normal_metabolizer", "normal_sensitivity", "normal_function", "negative")),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"PGx profile: {result['total_genes_tested']} genes, {result['actionable_findings']} actionable",
        )

    def _dose_recommendation(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        medication = ctx.get("medication", "warfarin")
        phenotype = ctx.get("phenotype", "normal_sensitivity")

        dose_adjustments = {
            ("warfarin", "high_sensitivity"): {"standard_dose": "5mg", "recommended_dose": "1-2mg", "adjustment": "75% reduction"},
            ("warfarin", "normal_sensitivity"): {"standard_dose": "5mg", "recommended_dose": "5mg", "adjustment": "none"},
            ("warfarin", "low_sensitivity"): {"standard_dose": "5mg", "recommended_dose": "7-10mg", "adjustment": "40-100% increase"},
            ("clopidogrel", "poor_metabolizer"): {"standard_dose": "75mg", "recommended_dose": "N/A — use prasugrel 10mg", "adjustment": "alternative drug"},
            ("codeine", "ultra_rapid_metabolizer"): {"standard_dose": "30-60mg", "recommended_dose": "N/A — use morphine alternative", "adjustment": "alternative drug"},
        }

        key = (medication.lower(), phenotype)
        dose = dose_adjustments.get(key, {"standard_dose": "standard", "recommended_dose": "standard", "adjustment": "none"})

        result = {
            "recommended_at": now.isoformat(),
            "medication": medication,
            "phenotype": phenotype,
            **dose,
            "evidence_level": "CPIC Level A",
            "guideline_source": "CPIC (Clinical Pharmacogenetics Implementation Consortium)",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"PGx dose recommendation: {medication} — {dose['adjustment']}",
        )

    def _panel_summary(self, input_data: AgentInput) -> AgentOutput:
        now = datetime.now(timezone.utc)

        result = {
            "summary_at": now.isoformat(),
            "genes_in_panel": list(GENE_DRUG_INTERACTIONS.keys()),
            "total_genes": len(GENE_DRUG_INTERACTIONS),
            "total_drugs_covered": sum(len(info["drugs_affected"]) for info in GENE_DRUG_INTERACTIONS.values()),
            "guideline_source": "CPIC (Clinical Pharmacogenetics Implementation Consortium)",
            "gene_details": [
                {"gene": gene, "gene_name": info["gene_name"], "drugs_count": len(info["drugs_affected"]), "drugs": info["drugs_affected"]}
                for gene, info in GENE_DRUG_INTERACTIONS.items()
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.99,
            rationale=f"PGx panel: {result['total_genes']} genes, {result['total_drugs_covered']} drugs",
        )
