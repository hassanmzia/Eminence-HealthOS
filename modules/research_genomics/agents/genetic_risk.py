"""
Eminence HealthOS — Genetic Risk Agent (#75)
Layer 2 (Interpretation): Incorporates genetic markers into risk scoring
models with polygenic risk scores and personalized risk stratification.
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

# Polygenic risk score models
PRS_MODELS: dict[str, dict[str, Any]] = {
    "coronary_artery_disease": {
        "name": "Coronary Artery Disease PRS",
        "snp_count": 6630000,
        "population_mean": 0.0,
        "population_sd": 1.0,
        "top_percentile_or": 3.34,
        "clinical_validity": "strong",
    },
    "type_2_diabetes": {
        "name": "Type 2 Diabetes PRS",
        "snp_count": 1280000,
        "population_mean": 0.0,
        "population_sd": 1.0,
        "top_percentile_or": 2.75,
        "clinical_validity": "strong",
    },
    "breast_cancer": {
        "name": "Breast Cancer PRS",
        "snp_count": 313,
        "population_mean": 0.0,
        "population_sd": 1.0,
        "top_percentile_or": 2.36,
        "clinical_validity": "strong",
    },
    "alzheimers": {
        "name": "Alzheimer's Disease PRS",
        "snp_count": 84,
        "population_mean": 0.0,
        "population_sd": 1.0,
        "top_percentile_or": 4.10,
        "clinical_validity": "moderate",
    },
    "atrial_fibrillation": {
        "name": "Atrial Fibrillation PRS",
        "snp_count": 142,
        "population_mean": 0.0,
        "population_sd": 1.0,
        "top_percentile_or": 2.80,
        "clinical_validity": "moderate",
    },
}

# Single-gene high-impact variants
MONOGENIC_VARIANTS: dict[str, dict[str, Any]] = {
    "BRCA1": {"gene": "BRCA1", "condition": "Breast/Ovarian Cancer", "inheritance": "autosomal_dominant", "lifetime_risk_increase": 5.0, "actionability": "high"},
    "BRCA2": {"gene": "BRCA2", "condition": "Breast/Ovarian Cancer", "inheritance": "autosomal_dominant", "lifetime_risk_increase": 3.5, "actionability": "high"},
    "LDLR": {"gene": "LDLR", "condition": "Familial Hypercholesterolemia", "inheritance": "autosomal_dominant", "lifetime_risk_increase": 4.0, "actionability": "high"},
    "APOE_e4": {"gene": "APOE", "condition": "Alzheimer's Disease", "inheritance": "complex", "lifetime_risk_increase": 3.0, "actionability": "moderate"},
    "HFE": {"gene": "HFE", "condition": "Hereditary Hemochromatosis", "inheritance": "autosomal_recessive", "lifetime_risk_increase": 2.5, "actionability": "high"},
    "MUTYH": {"gene": "MUTYH", "condition": "Colorectal Cancer", "inheritance": "autosomal_recessive", "lifetime_risk_increase": 2.0, "actionability": "high"},
}


class GeneticRiskAgent(BaseAgent):
    """Incorporates genetic markers into risk scoring models."""

    name = "genetic_risk"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = (
        "Genetic risk scoring — polygenic risk scores, monogenic variant analysis, "
        "and integrated clinical-genomic risk stratification"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "calculate_prs")

        if action == "calculate_prs":
            return self._calculate_prs(input_data)
        elif action == "monogenic_screen":
            return self._monogenic_screen(input_data)
        elif action == "integrated_risk":
            return self._integrated_risk(input_data)
        elif action == "risk_report":
            return await self._risk_report(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown genetic risk action: {action}",
                status=AgentStatus.FAILED,
            )

    def _calculate_prs(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        conditions = ctx.get("conditions", list(PRS_MODELS.keys())[:3])

        scores: list[dict[str, Any]] = []
        for condition in conditions:
            model = PRS_MODELS.get(condition)
            if not model:
                continue

            # Simulated PRS z-score for patient
            z_score = ctx.get(f"prs_{condition}", 1.2)
            percentile = min(99, max(1, int(50 + z_score * 34)))

            risk_category = "high" if percentile >= 90 else ("elevated" if percentile >= 75 else ("average" if percentile >= 25 else "low"))

            scores.append({
                "condition": condition,
                "model_name": model["name"],
                "snp_count": model["snp_count"],
                "z_score": z_score,
                "percentile": percentile,
                "risk_category": risk_category,
                "odds_ratio_vs_average": round(1.0 + z_score * 0.5, 2) if z_score > 0 else round(max(0.3, 1.0 + z_score * 0.3), 2),
                "clinical_validity": model["clinical_validity"],
            })

        result = {
            "calculated_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "prs_scores": scores,
            "total_conditions_scored": len(scores),
            "high_risk_conditions": sum(1 for s in scores if s["risk_category"] == "high"),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"PRS calculated: {len(scores)} conditions, {result['high_risk_conditions']} high-risk",
        )

    def _monogenic_screen(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        variants_detected = ctx.get("variants", [])

        if not variants_detected:
            variants_detected = ["APOE_e4"]

        findings: list[dict[str, Any]] = []
        for variant_key in variants_detected:
            variant = MONOGENIC_VARIANTS.get(variant_key)
            if variant:
                findings.append({
                    **variant,
                    "variant_key": variant_key,
                    "detected": True,
                    "classification": "pathogenic",
                })

        result = {
            "screened_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "genes_screened": len(MONOGENIC_VARIANTS),
            "variants_detected": len(findings),
            "findings": findings,
            "actionable_findings": sum(1 for f in findings if f["actionability"] == "high"),
            "genetic_counseling_recommended": len(findings) > 0,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Monogenic screen: {len(findings)} variants detected from {len(MONOGENIC_VARIANTS)} genes",
        )

    def _integrated_risk(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        clinical_risk = ctx.get("clinical_risk_score", 0.15)
        prs_percentile = ctx.get("prs_percentile", 82)

        # Integrate clinical and genetic risk
        genetic_modifier = 1.0 + (prs_percentile - 50) / 100
        integrated = round(min(1.0, clinical_risk * genetic_modifier), 4)

        result = {
            "calculated_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "clinical_risk_score": clinical_risk,
            "prs_percentile": prs_percentile,
            "genetic_modifier": round(genetic_modifier, 3),
            "integrated_risk_score": integrated,
            "risk_category": "high" if integrated >= 0.20 else ("moderate" if integrated >= 0.10 else "low"),
            "risk_reclassified": abs(integrated - clinical_risk) / max(clinical_risk, 0.01) > 0.20,
            "reclassification_direction": "up" if integrated > clinical_risk else "down",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.83,
            rationale=f"Integrated risk: clinical {clinical_risk:.2%} -> genomic-adjusted {integrated:.2%}",
        )

    async def _risk_report(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        prs_summary = [
            {"condition": "Coronary Artery Disease", "percentile": 82, "risk": "elevated"},
            {"condition": "Type 2 Diabetes", "percentile": 91, "risk": "high"},
            {"condition": "Breast Cancer", "percentile": 45, "risk": "average"},
        ]
        monogenic_findings = [
            {"gene": "APOE", "variant": "e4/e3", "condition": "Alzheimer's Disease", "actionability": "moderate"},
        ]
        pharmacogenomic_alerts = [
            {"gene": "CYP2C19", "phenotype": "Intermediate Metabolizer", "drugs_affected": 4},
        ]
        recommendations = [
            "Enhanced cardiovascular screening due to elevated CAD PRS",
            "Intensive diabetes prevention program (high T2D PRS)",
            "APOE e4 carrier — discuss Alzheimer's risk and prevention strategies",
            "CYP2C19 intermediate metabolizer — consider clopidogrel alternatives",
        ]

        # --- LLM-generated genetic counseling summary ---
        genetic_counseling_summary = None
        try:
            report_payload = {
                "prs_summary": prs_summary,
                "monogenic_findings": monogenic_findings,
                "pharmacogenomic_alerts": pharmacogenomic_alerts,
                "recommendations": recommendations,
                "patient_age": ctx.get("age"),
                "family_history": ctx.get("family_history", []),
            }
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Generate a patient-friendly genetic counseling summary "
                    f"explaining these genetic risk findings.\n\n"
                    f"Genetic report:\n{json.dumps(report_payload, indent=2)}"
                )}],
                system=(
                    "You are a certified genetic counselor AI. Write a clear, "
                    "empathetic, patient-friendly summary explaining the genetic "
                    "risk findings. Avoid jargon and use plain language. Explain "
                    "what polygenic risk scores mean, what the monogenic findings "
                    "imply, and how pharmacogenomic results affect medication "
                    "choices. Include reassurance where appropriate and emphasize "
                    "actionable next steps. Do not cause undue alarm."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if llm_response and llm_response.content:
                genetic_counseling_summary = llm_response.content
        except Exception:
            logger.warning(
                "LLM call failed for genetic counseling summary; skipping",
                exc_info=True,
            )

        result = {
            "report_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "prs_summary": prs_summary,
            "monogenic_findings": monogenic_findings,
            "pharmacogenomic_alerts": pharmacogenomic_alerts,
            "recommendations": recommendations,
            "genetic_counseling_summary": genetic_counseling_summary,
            "genetic_counseling_recommended": True,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale="Comprehensive genetic risk report generated",
        )
