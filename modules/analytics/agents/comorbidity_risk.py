"""
Comorbidity Risk Agent — Tier 3 (Decisioning / Risk).

Analyzes co-existing chronic conditions, calculates Charlson Comorbidity Index,
identifies high-risk condition clusters (e.g., cardiorenal-metabolic syndrome),
and prioritizes conditions for management.

Adapted from InHealth comorbidity_agent (Tier 3 Risk).
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

logger = logging.getLogger("healthos.agent.comorbidity_risk")

# Charlson Comorbidity Index weights (Charlson 1987 / Quan 2011 updated)
CCI_WEIGHTS = {
    "myocardial_infarction": 1,
    "congestive_heart_failure": 1,
    "peripheral_vascular_disease": 1,
    "cerebrovascular_disease": 1,
    "dementia": 1,
    "chronic_pulmonary_disease": 1,
    "connective_tissue_disease": 1,
    "peptic_ulcer_disease": 1,
    "mild_liver_disease": 1,
    "diabetes_without_complications": 1,
    "diabetes_with_complications": 2,
    "hemiplegia_paraplegia": 2,
    "renal_disease": 2,
    "solid_tumor": 2,
    "leukemia": 2,
    "lymphoma": 2,
    "moderate_severe_liver_disease": 3,
    "metastatic_solid_tumor": 6,
    "aids_hiv": 6,
}

# SNOMED CT condition codes (simplified)
CONDITION_SNOMED_MAP = {
    "44054006": "diabetes_type2",
    "38341003": "hypertension",
    "73211009": "diabetes_mellitus",
    "46635009": "diabetes_type1",
    "431855005": "chronic_kidney_disease",
    "84114007": "heart_failure",
    "22298006": "myocardial_infarction",
    "230690007": "stroke",
    "13645005": "chronic_pulmonary_disease",
    "363346000": "malignant_tumor",
}


class ComorbidityRiskAgent(HealthOSAgent):
    """Comorbidity risk analysis and Charlson Index calculation."""

    def __init__(self) -> None:
        super().__init__(
            name="comorbidity_risk",
            tier=AgentTier.RISK,
            description=(
                "Analyzes co-existing chronic conditions, calculates Charlson Comorbidity Index, "
                "and identifies high-risk condition clusters"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.RISK_SCORING, AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        # Accept conditions as a list of dicts or strings
        raw_conditions: list = data.get("conditions", [])
        active_conditions = self._parse_conditions(raw_conditions)

        if not active_conditions:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_conditions",
                rationale="No active conditions provided",
                confidence=1.0,
            )

        # Calculate Charlson Comorbidity Index
        cci_result = self._calculate_cci(active_conditions)

        # Identify high-risk condition clusters
        risk_clusters = self._identify_risk_clusters(active_conditions)

        alerts: list[dict[str, Any]] = []
        severity = "LOW"

        if cci_result["score"] >= 6:
            severity = "HIGH"
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"High comorbidity burden: Charlson Index {cci_result['score']} - "
                    f"estimated 10-year survival {cci_result['ten_year_survival']}. "
                    "Comprehensive care planning indicated."
                ),
            })

        for cluster in risk_clusters:
            if cluster.get("risk_level") == "CRITICAL":
                severity = "HIGH"
                alerts.append({
                    "severity": "HIGH",
                    "message": f"High-risk condition cluster: {cluster['name']} - {cluster['description']}",
                })

        recommendations = self._generate_recommendations(cci_result, risk_clusters)

        # LLM prioritization analysis
        prioritization = None
        try:
            cond_lines = "\n".join([
                f"  - {name} (severity: {info.get('severity', 'unknown')})"
                for name, info in active_conditions.items()
            ])
            prompt = (
                f"Patient active conditions:\n{cond_lines}\n\n"
                f"Charlson Comorbidity Index: {cci_result['score']} ({cci_result['risk_category']})\n"
                f"Estimated 10-year survival: {cci_result['ten_year_survival']}\n"
                f"Risk clusters: {json.dumps(risk_clusters, default=str)}\n\n"
                "Provide:\n"
                "1. Prioritized conditions list (highest clinical impact first)\n"
                "2. Synergistic risks requiring coordinated management\n"
                "3. Care coordination recommendations\n"
                "4. Overall prognosis assessment\n"
                "5. Quality-of-life optimization strategies"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical comorbidity management narrator. "
                    "Analyze condition combinations and prioritize management strategies."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            prioritization = resp.content
        except Exception:
            logger.warning("LLM comorbidity analysis failed; continuing without it")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="comorbidity_assessment",
            rationale=f"CCI {cci_result['score']} ({cci_result['risk_category']}); {len(active_conditions)} conditions",
            confidence=0.87,
            data={
                "severity": severity,
                "active_conditions": active_conditions,
                "condition_count": len(active_conditions),
                "charlson_index": cci_result,
                "risk_clusters": risk_clusters,
                "prioritization_analysis": prioritization,
                "alerts": alerts,
                "recommendations": recommendations,
            },
            requires_hitl=cci_result["score"] >= 6,
            hitl_reason="High comorbidity burden (CCI >= 6) requires comprehensive care planning" if cci_result["score"] >= 6 else None,
        )

    # -- Medical logic (preserved from source) ------------------------------------

    def _parse_conditions(self, resources: list) -> dict[str, Any]:
        conditions: dict[str, Any] = {}
        for r in resources:
            if isinstance(r, str):
                if r and r not in conditions:
                    conditions[r] = {"code": "", "severity": "active"}
            elif isinstance(r, dict):
                code = r.get("code", "")
                name = CONDITION_SNOMED_MAP.get(code, r.get("display", code.replace("_", " ").title()))
                if name and name not in conditions:
                    conditions[name] = {
                        "code": code,
                        "onset": r.get("effective_datetime", ""),
                        "severity": r.get("status", "active"),
                    }
        return conditions

    def _calculate_cci(self, conditions: dict[str, Any]) -> dict[str, Any]:
        score = 0
        matched: list[dict[str, Any]] = []
        for cci_name, weight in CCI_WEIGHTS.items():
            condition_key = cci_name.replace("_", " ")
            for patient_condition in conditions.keys():
                if condition_key in patient_condition.lower() or patient_condition.lower() in condition_key:
                    score += weight
                    matched.append({"condition": cci_name, "weight": weight})
                    break

        survival_map = {
            (0, 0): "> 90%",
            (1, 2): "89%",
            (3, 4): "77%",
            (5, 6): "53%",
            (7, 10): "21%",
        }
        survival = "> 20%"
        for (low, high), pct in survival_map.items():
            if low <= score <= high:
                survival = pct
                break

        if score == 0:
            cat = "Low"
        elif score <= 2:
            cat = "Low-Moderate"
        elif score <= 4:
            cat = "Moderate"
        elif score <= 6:
            cat = "High"
        else:
            cat = "Very High"

        return {
            "score": score,
            "risk_category": cat,
            "ten_year_survival": survival,
            "matched_conditions": matched,
        }

    def _identify_risk_clusters(self, conditions: dict[str, Any]) -> list[dict[str, Any]]:
        clusters: list[dict[str, Any]] = []
        names_lower = [k.lower() for k in conditions.keys()]

        has_dm = any("diabet" in n for n in names_lower)
        has_ckd = any("kidney" in n or "renal" in n for n in names_lower)
        has_htn = any("hypertens" in n for n in names_lower)
        has_hf = any("heart fail" in n for n in names_lower)

        if has_dm and has_ckd and has_htn:
            clusters.append({
                "name": "Cardiorenal-Metabolic Syndrome",
                "conditions": ["T2DM", "CKD", "Hypertension"],
                "risk_level": "CRITICAL",
                "description": (
                    "Synergistic cardiovascular and renal risk. 3-5x increased CV mortality. "
                    "Requires integrated management with SGLT2i/GLP-1RA, ACE/ARB, and intensive BP control."
                ),
            })
        if has_hf and has_ckd:
            clusters.append({
                "name": "Cardiorenal Syndrome",
                "conditions": ["Heart Failure", "CKD"],
                "risk_level": "CRITICAL",
                "description": (
                    "Bidirectional cardiac-renal dysfunction. Complex fluid and medication management. "
                    "Cardiology + nephrology co-management essential."
                ),
            })
        return clusters

    def _generate_recommendations(
        self, cci: dict[str, Any], clusters: list[dict[str, Any]],
    ) -> list[str]:
        recs: list[str] = []
        if cci["score"] >= 4:
            recs.append(
                "High comorbidity burden: Establish comprehensive care plan with "
                "primary care + relevant specialists. Advance care planning discussion recommended."
            )
        for cluster in clusters:
            if "Cardiorenal-Metabolic" in cluster.get("name", ""):
                recs.append(
                    "Cardiorenal-metabolic syndrome: SGLT2 inhibitor (empagliflozin/dapagliflozin) "
                    "addresses CV, renal, and metabolic risk simultaneously (EMPA-REG, DAPA-HF, CREDENCE)."
                )
        return recs
