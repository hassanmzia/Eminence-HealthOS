"""
Eminence HealthOS — Guideline Agent
Retrieves and analyzes clinical practice guidelines relevant to a patient's
conditions, identifying care gaps where current treatment deviates from
evidence-based recommendations.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentTier

logger = structlog.get_logger()

# Evidence levels per guideline source
EVIDENCE_LEVELS = {
    "A": "Strong recommendation, high-quality evidence",
    "B": "Moderate recommendation, moderate-quality evidence",
    "C": "Weak recommendation, low-quality evidence",
    "D": "Expert opinion, very low-quality evidence",
}

# Known guideline sources
GUIDELINE_SOURCES = [
    "ADA Standards of Care 2024",
    "ACC/AHA Heart Failure Guidelines",
    "KDIGO CKD Guidelines",
    "GOLD COPD Guidelines",
    "JNC 8 Hypertension Guidelines",
    "ACS Breast Cancer Screening",
    "USPSTF Preventive Services",
]


class GuidelineAgent(BaseAgent):
    """
    Retrieves clinical guidelines relevant to a patient's conditions
    and identifies gaps between current care and guideline recommendations.
    """

    name = "guideline_agent"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Clinical guideline retrieval and care gap analysis"
    min_confidence = 0.75

    async def process(self, input_data: AgentInput) -> AgentOutput:
        context = input_data.context or {}
        conditions = context.get("conditions", [])
        medications = context.get("medications", [])
        vitals = context.get("vitals", {})

        # Retrieve applicable guidelines
        applicable = self._match_guidelines(conditions)

        # Analyze care gaps
        care_gaps = self._analyze_care_gaps(applicable, medications, vitals)

        # Calculate compliance score
        total_recs = sum(len(g.get("recommendations", [])) for g in applicable)
        met_recs = total_recs - len(care_gaps)
        compliance = met_recs / total_recs if total_recs > 0 else 1.0

        confidence = 0.90 if applicable else 0.50

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "applicable_guidelines": applicable,
                "care_gaps": care_gaps,
                "compliance_score": round(compliance, 2),
                "total_recommendations": total_recs,
                "met_recommendations": met_recs,
            },
            confidence=confidence,
            rationale=(
                f"Found {len(applicable)} applicable guidelines with "
                f"{len(care_gaps)} care gap(s) — compliance {compliance:.0%}"
            ),
        )

    def _match_guidelines(self, conditions: list[dict]) -> list[dict[str, Any]]:
        """Match patient conditions to clinical guidelines."""
        guidelines = []

        condition_codes = {c.get("code", "") for c in conditions}
        condition_names = {c.get("display", "").lower() for c in conditions}

        # Type 2 Diabetes
        if any("E11" in c for c in condition_codes) or any("diabetes" in n for n in condition_names):
            guidelines.append({
                "source": "ADA Standards of Care 2024",
                "condition": "Type 2 Diabetes Mellitus",
                "evidence_level": "A",
                "recommendations": [
                    {"rec": "HbA1c testing every 3 months", "code": "LOINC:4548-4"},
                    {"rec": "Annual dilated eye exam", "code": "CPT:92004"},
                    {"rec": "Annual foot exam", "code": "CPT:99213"},
                    {"rec": "Statin therapy if age >= 40", "code": "RxNorm:36567"},
                    {"rec": "ACE inhibitor or ARB if microalbuminuria", "code": "RxNorm:29046"},
                    {"rec": "Blood pressure target < 130/80 mmHg", "code": "BP-TARGET"},
                ],
            })

        # Hypertension
        if any("I10" in c for c in condition_codes) or any("hypertension" in n for n in condition_names):
            guidelines.append({
                "source": "JNC 8 Hypertension Guidelines",
                "condition": "Essential Hypertension",
                "evidence_level": "A",
                "recommendations": [
                    {"rec": "Blood pressure monitoring", "code": "LOINC:85354-9"},
                    {"rec": "Target BP < 140/90 (general) or < 130/80 (diabetes/CKD)", "code": "BP-TARGET"},
                    {"rec": "Lifestyle modifications", "code": "LIFESTYLE"},
                    {"rec": "First-line: thiazide, CCB, ACE-i, or ARB", "code": "RxNorm:ANTIHTN"},
                ],
            })

        # Heart Failure
        if any("I50" in c for c in condition_codes) or any("heart failure" in n for n in condition_names):
            guidelines.append({
                "source": "ACC/AHA Heart Failure Guidelines",
                "condition": "Heart Failure",
                "evidence_level": "A",
                "recommendations": [
                    {"rec": "ACE-i/ARB/ARNI therapy", "code": "RxNorm:RAAS"},
                    {"rec": "Beta-blocker therapy", "code": "RxNorm:BB"},
                    {"rec": "Diuretic for volume overload", "code": "RxNorm:DIURETIC"},
                    {"rec": "Annual influenza vaccination", "code": "CVX:141"},
                    {"rec": "Daily weight monitoring", "code": "LOINC:29463-7"},
                ],
            })

        # CKD
        if any("N18" in c for c in condition_codes) or any("kidney" in n for n in condition_names):
            guidelines.append({
                "source": "KDIGO CKD Guidelines",
                "condition": "Chronic Kidney Disease",
                "evidence_level": "B",
                "recommendations": [
                    {"rec": "eGFR monitoring every 3-6 months", "code": "LOINC:48642-3"},
                    {"rec": "UACR monitoring annually", "code": "LOINC:9318-7"},
                    {"rec": "Blood pressure target < 130/80", "code": "BP-TARGET"},
                    {"rec": "SGLT2 inhibitor consideration", "code": "RxNorm:SGLT2"},
                ],
            })

        # COPD
        if any("J44" in c for c in condition_codes) or any("copd" in n for n in condition_names):
            guidelines.append({
                "source": "GOLD COPD Guidelines",
                "condition": "COPD",
                "evidence_level": "A",
                "recommendations": [
                    {"rec": "Spirometry every 1-2 years", "code": "CPT:94010"},
                    {"rec": "Inhaled bronchodilator therapy", "code": "RxNorm:BRONCHO"},
                    {"rec": "Annual influenza vaccination", "code": "CVX:141"},
                    {"rec": "Pneumococcal vaccination", "code": "CVX:33"},
                    {"rec": "Smoking cessation counseling", "code": "CPT:99407"},
                ],
            })

        return guidelines

    def _analyze_care_gaps(
        self,
        guidelines: list[dict],
        medications: list[dict],
        vitals: dict,
    ) -> list[dict[str, Any]]:
        """Identify care gaps where current care deviates from guidelines."""
        gaps = []
        med_codes = {m.get("rxNormCode", m.get("code", "")) for m in medications}

        for guideline in guidelines:
            for rec in guideline.get("recommendations", []):
                rec_code = rec.get("code", "")

                # Check if recommendation is being met (simplified)
                is_met = any(rec_code in mc for mc in med_codes if mc)

                if not is_met and rec_code not in ("BP-TARGET", "LIFESTYLE"):
                    gaps.append({
                        "guideline": guideline["source"],
                        "condition": guideline["condition"],
                        "recommendation": rec["rec"],
                        "code": rec_code,
                        "evidence_level": guideline["evidence_level"],
                        "priority": "high" if guideline["evidence_level"] == "A" else "moderate",
                    })

        return gaps
