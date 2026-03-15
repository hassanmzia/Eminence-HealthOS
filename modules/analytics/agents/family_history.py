"""
Family History Risk Agent — Tier 3 (Decisioning / Risk).

Analyzes patient family history data, approximates polygenic risk scores,
maps high-penetrance gene-disease associations (BRCA1, APOE, etc.),
and generates genetic counseling recommendations.

Adapted from InHealth family_history_agent (Tier 3 Risk).
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

logger = logging.getLogger("healthos.agent.family_history")

# Gene-disease high-penetrance associations
GENE_DISEASE_ASSOCIATIONS = {
    "BRCA1": {"diseases": ["breast_cancer", "ovarian_cancer"], "lifetime_risk": "50-85%", "action": "Oncology referral, enhanced screening"},
    "BRCA2": {"diseases": ["breast_cancer", "pancreatic_cancer"], "lifetime_risk": "45-70%", "action": "Oncology referral"},
    "APOE_E4": {"diseases": ["alzheimers_disease"], "lifetime_risk": "3x increased", "action": "Neurology referral, cognitive monitoring"},
    "LDLR": {"diseases": ["familial_hypercholesterolemia"], "lifetime_risk": "High", "action": "Lipid specialist referral, high-intensity statin"},
    "MTHFR": {"diseases": ["cardiovascular_disease", "thrombophilia"], "lifetime_risk": "Moderate", "action": "Folate supplementation, homocysteine monitoring"},
    "HBB": {"diseases": ["sickle_cell_disease", "thalassemia"], "lifetime_risk": "Autosomal recessive", "action": "Hematology referral if symptomatic"},
    "MLH1": {"diseases": ["colorectal_cancer", "endometrial_cancer"], "lifetime_risk": "Lynch syndrome: 70-80%", "action": "Colonoscopy q1-2y starting age 20-25"},
}

# Heritability of common conditions (approximate %)
HERITABILITY = {
    "type2_diabetes": 0.50,
    "hypertension": 0.57,
    "coronary_artery_disease": 0.55,
    "colorectal_cancer": 0.35,
    "breast_cancer": 0.31,
    "alzheimers_disease": 0.60,
    "atrial_fibrillation": 0.42,
    "obesity": 0.71,
    "depression": 0.37,
    "asthma": 0.60,
}


class FamilyHistoryAgent(HealthOSAgent):
    """Family history risk assessment and genetic counseling."""

    def __init__(self) -> None:
        super().__init__(
            name="family_history",
            tier=AgentTier.RISK,
            description=(
                "Analyzes family history, approximates polygenic risk, identifies "
                "high-penetrance gene-disease associations, and generates genetic counseling recommendations"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.RISK_SCORING]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        family_conditions: list[dict[str, Any]] = data.get("family_conditions", [])
        genomic_variants: list[dict[str, Any]] = data.get("genomic_variants", [])

        # Calculate polygenic risk score approximation
        prs_approximation = self._approximate_prs(family_conditions)

        # Map genomic variants to gene-disease associations
        high_penetrance_findings: list[dict[str, Any]] = []
        for variant in genomic_variants:
            gene = variant.get("gene", "")
            if gene in GENE_DISEASE_ASSOCIATIONS:
                assoc = GENE_DISEASE_ASSOCIATIONS[gene]
                high_penetrance_findings.append({
                    "gene": gene,
                    "variant": variant.get("variant", ""),
                    "diseases": assoc["diseases"],
                    "lifetime_risk": assoc["lifetime_risk"],
                    "recommended_action": assoc["action"],
                })

        # Early-onset disease flags
        early_onset_flags = self._check_early_onset(family_conditions)

        alerts: list[dict[str, Any]] = []
        severity = "LOW"

        for finding in high_penetrance_findings:
            severity = "HIGH"
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"High-penetrance genetic finding: {finding['gene']} variant - "
                    f"lifetime risk {finding['lifetime_risk']} for {', '.join(finding['diseases'])}. "
                    f"{finding['recommended_action']}"
                ),
            })

        for flag in early_onset_flags:
            alerts.append({
                "severity": "MEDIUM",
                "message": (
                    f"Early-onset family history: {flag['condition']} in first-degree "
                    f"relative age {flag['age']}. Enhanced screening recommended."
                ),
            })

        recommendations = self._generate_recommendations(high_penetrance_findings, prs_approximation)

        # LLM analysis
        genetic_report = None
        try:
            family_summary = "\n".join([
                f"  {fc.get('relationship', 'relative')}: {fc.get('condition', 'unknown')} (age {fc.get('age_at_diagnosis', '?')})"
                for fc in family_conditions[:15]
            ])
            prs_lines = "\n".join([
                f"  {k}: {v['risk_level']} (heritability-adjusted)"
                for k, v in prs_approximation.items()
            ])
            prompt = (
                f"Family history and genetic risk:\n\n"
                f"Family conditions:\n{family_summary}\n\n"
                f"Polygenic risk approximation:\n{prs_lines}\n\n"
                f"High-penetrance findings: {json.dumps(high_penetrance_findings, default=str)}\n"
                f"Early-onset flags: {json.dumps(early_onset_flags, default=str)}\n\n"
                "Provide:\n"
                "1. Overall hereditary risk assessment with quantified estimates\n"
                "2. Specific genetic testing recommendations (USPSTF/NCCN)\n"
                "3. Enhanced screening protocols based on family history\n"
                "4. Cascade testing recommendations for at-risk family members\n"
                "5. Genetic counseling referral urgency"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a genetic counseling decision support narrator. "
                    "Reference USPSTF genetic testing guidelines, NCCN hereditary cancer guidelines, "
                    "and AHA/ACC familial risk guidelines."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            genetic_report = resp.content
        except Exception:
            logger.warning("LLM family history analysis failed; continuing without it")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="family_history_assessment",
            rationale=(
                f"{len(family_conditions)} family conditions; "
                f"{len(high_penetrance_findings)} high-penetrance findings; "
                f"{len(early_onset_flags)} early-onset flags"
            ),
            confidence=0.80,
            data={
                "severity": severity,
                "family_conditions": family_conditions[:20],
                "polygenic_risk_approximation": prs_approximation,
                "high_penetrance_findings": high_penetrance_findings,
                "early_onset_flags": early_onset_flags,
                "genomic_variants": genomic_variants,
                "genetic_counseling_report": genetic_report,
                "alerts": alerts,
                "recommendations": recommendations,
            },
            requires_hitl=bool(high_penetrance_findings),
            hitl_reason="High-penetrance genetic findings require genetic counselor review" if high_penetrance_findings else None,
        )

    # -- Medical logic (preserved from source) ------------------------------------

    def _approximate_prs(self, family_data: list[dict[str, Any]]) -> dict[str, Any]:
        condition_counts: dict[str, int] = {}
        first_degree: dict[str, int] = {}
        for fc in family_data:
            condition = fc.get("condition", "").lower().replace(" ", "_")
            relationship = fc.get("relationship", "").lower()
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
            if relationship in ("parent", "sibling", "child"):
                first_degree[condition] = first_degree.get(condition, 0) + 1

        prs: dict[str, Any] = {}
        for condition, heritability in HERITABILITY.items():
            count = first_degree.get(condition, 0)
            if count >= 2:
                prs[condition] = {
                    "risk_level": "HIGH",
                    "risk_multiplier": 3.0,
                    "first_degree_affected": count,
                    "condition_heritability": heritability,
                }
            elif count == 1:
                prs[condition] = {
                    "risk_level": "MODERATE",
                    "risk_multiplier": round(1.5 + heritability, 2),
                    "first_degree_affected": count,
                    "condition_heritability": heritability,
                }
        return prs

    def _check_early_onset(self, family_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flags: list[dict[str, Any]] = []
        early_onset_thresholds = {
            "heart disease": 55,
            "breast cancer": 50,
            "colon cancer": 50,
            "diabetes": 40,
            "stroke": 55,
        }
        for fc in family_data:
            relationship = fc.get("relationship", "").lower()
            if relationship not in ("parent", "sibling", "child", "father", "mother", "brother", "sister"):
                continue
            condition = fc.get("condition", "").lower()
            age_raw = fc.get("age_at_diagnosis", "")
            try:
                age = int(str(age_raw).split()[0])
            except (ValueError, TypeError):
                continue
            for cond_key, threshold in early_onset_thresholds.items():
                if cond_key in condition and age < threshold:
                    flags.append({
                        "condition": condition,
                        "relationship": relationship,
                        "age": age,
                        "threshold": threshold,
                    })
        return flags

    def _generate_recommendations(
        self, high_penetrance: list[dict[str, Any]], prs: dict[str, Any],
    ) -> list[str]:
        recs: list[str] = []
        if high_penetrance:
            recs.append(
                "Genetic counseling referral: High-penetrance variant(s) identified. "
                "Patient and first-degree relatives should receive genetic counseling."
            )
        for finding in high_penetrance:
            if "BRCA" in finding.get("gene", ""):
                recs.append(
                    "BRCA variant: Annual breast MRI + mammogram (NCCN Category 1). "
                    "Consider risk-reducing surgery discussion with oncologist."
                )
        if any(v.get("risk_level") == "HIGH" for v in prs.values()):
            recs.append(
                "High polygenic risk in first-degree relatives: Enhanced screening protocol "
                "with earlier initiation and shorter intervals."
            )
        return recs
