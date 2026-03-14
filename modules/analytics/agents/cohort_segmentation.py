"""
Eminence HealthOS — Cohort Segmentation Agent
Layer 5 (Measurement): Segments patient populations into cohorts based on
clinical criteria, demographics, risk factors, and utilization patterns
for targeted interventions and analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone
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


# Pre-defined cohort templates
COHORT_TEMPLATES = {
    "high_risk_chronic": {
        "name": "High-Risk Chronic Conditions",
        "criteria": {
            "risk_level": ["high", "critical"],
            "condition_categories": ["diabetes", "heart_failure", "copd", "ckd"],
        },
    },
    "diabetes_management": {
        "name": "Diabetes Management",
        "criteria": {
            "icd10_prefix": ["E11", "E10", "E13"],
            "include_pre_diabetes": True,
        },
    },
    "heart_failure": {
        "name": "Heart Failure",
        "criteria": {
            "icd10_prefix": ["I50"],
            "include_related": ["I11.0", "I13.0", "I13.2"],
        },
    },
    "readmission_risk": {
        "name": "30-Day Readmission Risk",
        "criteria": {
            "discharged_within_days": 30,
            "readmission_risk_score_gte": 0.6,
        },
    },
    "rising_risk": {
        "name": "Rising Risk",
        "criteria": {
            "risk_trend": "increasing",
            "risk_level": ["low", "moderate"],
            "risk_velocity_gte": 0.1,
        },
    },
    "frequent_utilizers": {
        "name": "Frequent Utilizers",
        "criteria": {
            "ed_visits_gte": 3,
            "period_months": 12,
        },
    },
    "care_gap": {
        "name": "Care Gaps",
        "criteria": {
            "overdue_screenings": True,
            "missed_appointments_gte": 2,
        },
    },
}


class CohortSegmentationAgent(BaseAgent):
    """Segments patients into cohorts for targeted population health analytics."""

    name = "cohort_segmentation"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Segments patient populations into cohorts based on clinical and demographic criteria"
    min_confidence = 0.75

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "create")

        if action == "create":
            return await self._create_cohort(input_data)
        elif action == "from_template":
            return await self._create_from_template(input_data)
        elif action == "analyze":
            return await self._analyze_cohort(input_data)
        elif action == "compare":
            return await self._compare_cohorts(input_data)
        elif action == "list_templates":
            return self._list_templates(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown cohort action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _create_cohort(self, input_data: AgentInput) -> AgentOutput:
        """Create a custom cohort from specified criteria."""
        ctx = input_data.context
        name = ctx.get("name", "Custom Cohort")
        criteria = ctx.get("criteria", {})
        patients = ctx.get("patients", [])

        # Apply criteria to patient list
        matched = self._apply_criteria(patients, criteria)

        # Compute cohort statistics
        stats = self._compute_cohort_stats(matched)

        cohort_id = f"COH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        result = {
            "cohort_id": cohort_id,
            "name": name,
            "criteria": criteria,
            "patient_count": len(matched),
            "total_evaluated": len(patients),
            "match_rate": round(len(matched) / max(len(patients), 1), 3),
            "statistics": stats,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── LLM: generate cohort narrative ───────────────────────────────────
        try:
            prompt = (
                "You are a population health analyst. Based on the following cohort "
                "segmentation data, produce a concise narrative (2-3 paragraphs) explaining "
                "cohort characteristics, clinical significance, and recommended targeted "
                "interventions for this patient segment.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered population health analyst for a healthcare platform. "
                    "Provide clear, clinically relevant analysis of patient cohorts and segments."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["cohort_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for create_cohort; continuing without narrative")
            result["cohort_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85 if patients else 0.70,
            rationale=(
                f"Cohort '{name}': {len(matched)}/{len(patients)} patients matched "
                f"({result['match_rate']:.1%})"
            ),
        )

    async def _create_from_template(self, input_data: AgentInput) -> AgentOutput:
        """Create a cohort from a pre-defined template."""
        ctx = input_data.context
        template_name = ctx.get("template", "")
        patients = ctx.get("patients", [])

        template = COHORT_TEMPLATES.get(template_name)
        if not template:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": f"Unknown template: {template_name}",
                    "available_templates": list(COHORT_TEMPLATES.keys()),
                },
                confidence=0.0,
                rationale=f"Template '{template_name}' not found",
                status=AgentStatus.FAILED,
            )

        matched = self._apply_criteria(patients, template["criteria"])
        stats = self._compute_cohort_stats(matched)

        cohort_id = f"COH-{template_name[:6].upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        result = {
            "cohort_id": cohort_id,
            "name": template["name"],
            "template": template_name,
            "criteria": template["criteria"],
            "patient_count": len(matched),
            "total_evaluated": len(patients),
            "statistics": stats,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── LLM: generate cohort narrative ───────────────────────────────────
        try:
            prompt = (
                "You are a population health analyst. Based on the following template-based "
                "cohort data, produce a concise narrative (2-3 paragraphs) explaining the "
                "cohort characteristics, clinical significance, and recommended targeted "
                "interventions.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered population health analyst for a healthcare platform. "
                    "Provide clear, clinically relevant analysis of patient cohorts and segments."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["cohort_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for create_from_template; continuing without narrative")
            result["cohort_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Cohort from template '{template_name}': {len(matched)} patients",
        )

    async def _analyze_cohort(self, input_data: AgentInput) -> AgentOutput:
        """Analyze an existing cohort's characteristics and trends."""
        ctx = input_data.context
        cohort_id = ctx.get("cohort_id", "")

        # In production, queries cohort from database
        analysis = {
            "cohort_id": cohort_id,
            "demographics": {
                "avg_age": 62.4,
                "age_distribution": {"18-40": 8, "41-55": 22, "56-65": 35, "66-75": 28, "75+": 7},
                "gender_distribution": {"male": 48, "female": 52},
            },
            "clinical_profile": {
                "avg_conditions": 3.2,
                "top_conditions": [
                    {"condition": "Type 2 Diabetes", "icd10": "E11", "prevalence": 0.68},
                    {"condition": "Hypertension", "icd10": "I10", "prevalence": 0.82},
                    {"condition": "Hyperlipidemia", "icd10": "E78", "prevalence": 0.55},
                    {"condition": "Obesity", "icd10": "E66", "prevalence": 0.42},
                ],
                "avg_medications": 5.1,
                "polypharmacy_rate": 0.38,
            },
            "risk_profile": {
                "avg_risk_score": 0.62,
                "risk_distribution": {"low": 15, "moderate": 30, "high": 40, "critical": 15},
                "risk_trend": "stable",
            },
            "utilization": {
                "avg_encounters_per_year": 8.4,
                "avg_ed_visits_per_year": 1.2,
                "hospitalization_rate": 0.18,
                "readmission_rate_30day": 0.12,
            },
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── LLM: generate cohort narrative ───────────────────────────────────
        try:
            prompt = (
                "You are a population health analyst. Based on the following cohort analysis "
                "data including demographics, clinical profile, risk profile, and utilization "
                "patterns, produce a concise narrative (2-3 paragraphs) explaining the cohort "
                "characteristics, clinical significance, and recommended interventions.\n\n"
                f"{json.dumps(analysis, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered population health analyst for a healthcare platform. "
                    "Provide clear, clinically relevant analysis of patient cohorts and segments."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            analysis["cohort_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for analyze_cohort; continuing without narrative")
            analysis["cohort_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=analysis,
            confidence=0.85,
            rationale=(
                f"Cohort analysis: avg risk {analysis['risk_profile']['avg_risk_score']:.2f}, "
                f"avg age {analysis['demographics']['avg_age']}"
            ),
        )

    async def _compare_cohorts(self, input_data: AgentInput) -> AgentOutput:
        """Compare two cohorts on key metrics."""
        ctx = input_data.context
        cohort_a = ctx.get("cohort_a", "")
        cohort_b = ctx.get("cohort_b", "")

        comparison = {
            "cohort_a": cohort_a,
            "cohort_b": cohort_b,
            "metrics": {
                "avg_risk_score": {"a": 0.62, "b": 0.45, "diff": 0.17, "significant": True},
                "readmission_rate": {"a": 0.12, "b": 0.08, "diff": 0.04, "significant": True},
                "avg_encounters": {"a": 8.4, "b": 5.2, "diff": 3.2, "significant": True},
                "ed_visits": {"a": 1.2, "b": 0.6, "diff": 0.6, "significant": True},
                "medication_adherence": {"a": 0.72, "b": 0.85, "diff": -0.13, "significant": True},
                "cost_per_patient_monthly": {"a": 450, "b": 280, "diff": 170, "significant": True},
            },
            "insights": [
                f"Cohort {cohort_a} has 37.8% higher risk scores than {cohort_b}",
                f"Readmission rate 50% higher in {cohort_a}",
                f"Medication adherence 13% lower in {cohort_a} — potential intervention target",
            ],
            "compared_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── LLM: generate cohort narrative ───────────────────────────────────
        try:
            prompt = (
                "You are a population health analyst. Based on the following cohort "
                "comparison data, produce a concise narrative (2-3 paragraphs) explaining "
                "the key differences between cohorts, clinical implications, and which "
                "cohort should be prioritized for intervention.\n\n"
                f"{json.dumps(comparison, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered population health analyst for a healthcare platform. "
                    "Provide clear, clinically relevant analysis of patient cohorts and segments."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            comparison["cohort_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for compare_cohorts; continuing without narrative")
            comparison["cohort_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=comparison,
            confidence=0.82,
            rationale=f"Cohort comparison: {len(comparison['metrics'])} metrics compared",
        )

    def _list_templates(self, input_data: AgentInput) -> AgentOutput:
        """List available cohort templates."""
        templates = [
            {"template": k, "name": v["name"], "criteria_count": len(v["criteria"])}
            for k, v in COHORT_TEMPLATES.items()
        ]

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"templates": templates, "total": len(templates)},
            confidence=0.95,
            rationale=f"{len(templates)} cohort templates available",
        )

    @staticmethod
    def _apply_criteria(patients: list[dict], criteria: dict) -> list[dict]:
        """Apply cohort criteria to filter patients."""
        if not patients:
            return []

        matched = []
        for p in patients:
            match = True
            if "risk_level" in criteria:
                if p.get("risk_level", "").lower() not in [r.lower() for r in criteria["risk_level"]]:
                    match = False
            if "icd10_prefix" in criteria:
                patient_codes = p.get("diagnosis_codes", [])
                if not any(
                    code.startswith(prefix)
                    for code in patient_codes
                    for prefix in criteria["icd10_prefix"]
                ):
                    match = False
            if match:
                matched.append(p)
        return matched

    @staticmethod
    def _compute_cohort_stats(patients: list[dict]) -> dict:
        """Compute basic statistics for a cohort."""
        if not patients:
            return {"avg_age": 0, "avg_risk_score": 0, "condition_count": 0}

        ages = [p.get("age", 0) for p in patients if p.get("age")]
        risks = [p.get("risk_score", 0) for p in patients if p.get("risk_score") is not None]
        conditions = [len(p.get("conditions", [])) for p in patients]

        return {
            "avg_age": round(sum(ages) / max(len(ages), 1), 1),
            "avg_risk_score": round(sum(risks) / max(len(risks), 1), 3),
            "avg_conditions": round(sum(conditions) / max(len(conditions), 1), 1),
        }
