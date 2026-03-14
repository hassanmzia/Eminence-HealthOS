"""
Eminence HealthOS — Clinical Trial Matching Agent (#71)
Layer 3 (Decisioning): Matches patients to eligible clinical trials
based on conditions, demographics, labs, and inclusion/exclusion criteria.
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

# Sample trial registry
TRIAL_REGISTRY: list[dict[str, Any]] = [
    {
        "nct_id": "NCT05001234",
        "title": "SGLT2 Inhibitor for CKD Stage 3-4 with Type 2 Diabetes",
        "phase": "Phase III",
        "status": "Recruiting",
        "sponsor": "Eminence Research Institute",
        "conditions": ["type_2_diabetes", "ckd"],
        "inclusion": {"age_min": 40, "age_max": 80, "egfr_min": 20, "egfr_max": 60, "hba1c_min": 7.0, "hba1c_max": 11.0},
        "exclusion": {"conditions": ["esrd", "dialysis", "pregnancy"], "medications": ["other_sglt2"]},
        "sites": 24,
        "target_enrollment": 500,
        "current_enrollment": 312,
    },
    {
        "nct_id": "NCT05005678",
        "title": "GLP-1 Receptor Agonist for Obesity and Cardiovascular Risk Reduction",
        "phase": "Phase III",
        "status": "Recruiting",
        "sponsor": "CardioMetabolic Research Group",
        "conditions": ["obesity", "cardiovascular_risk"],
        "inclusion": {"age_min": 30, "age_max": 75, "bmi_min": 30},
        "exclusion": {"conditions": ["medullary_thyroid_carcinoma", "men2", "pancreatitis"]},
        "sites": 40,
        "target_enrollment": 1000,
        "current_enrollment": 678,
    },
    {
        "nct_id": "NCT05009012",
        "title": "AI-Assisted Diabetic Retinopathy Screening in Primary Care",
        "phase": "Phase II",
        "status": "Recruiting",
        "sponsor": "Digital Health Research Consortium",
        "conditions": ["type_2_diabetes", "diabetic_retinopathy"],
        "inclusion": {"age_min": 18, "age_max": 85, "diabetes_duration_years_min": 5},
        "exclusion": {"conditions": ["blindness", "prior_vitrectomy"]},
        "sites": 15,
        "target_enrollment": 300,
        "current_enrollment": 142,
    },
    {
        "nct_id": "NCT05012345",
        "title": "Pharmacogenomic-Guided Warfarin Dosing",
        "phase": "Phase IV",
        "status": "Recruiting",
        "sponsor": "Precision Medicine Alliance",
        "conditions": ["atrial_fibrillation", "anticoagulation"],
        "inclusion": {"age_min": 21, "age_max": 90, "requires_anticoagulation": True},
        "exclusion": {"conditions": ["active_bleeding", "thrombocytopenia"]},
        "sites": 10,
        "target_enrollment": 200,
        "current_enrollment": 87,
    },
]


class ClinicalTrialMatchingAgent(BaseAgent):
    """Matches patients to eligible clinical trials based on clinical criteria."""

    name = "clinical_trial_matching"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Clinical trial matching — automated eligibility assessment against "
        "inclusion/exclusion criteria with trial registry integration"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "match_trials")

        if action == "match_trials":
            return self._match_trials(input_data)
        elif action == "check_eligibility":
            return await self._check_eligibility(input_data)
        elif action == "trial_details":
            return self._trial_details(input_data)
        elif action == "enrollment_status":
            return self._enrollment_status(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown clinical trial matching action: {action}",
                status=AgentStatus.FAILED,
            )

    def _match_trials(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        conditions = [c.lower() for c in ctx.get("conditions", ["type_2_diabetes"])]
        age = ctx.get("age", 55)
        labs = ctx.get("labs", {})

        matches: list[dict[str, Any]] = []
        for trial in TRIAL_REGISTRY:
            if trial["status"] != "Recruiting":
                continue

            condition_match = any(c in conditions for c in trial["conditions"])
            if not condition_match:
                continue

            inclusion = trial["inclusion"]
            age_ok = inclusion.get("age_min", 0) <= age <= inclusion.get("age_max", 999)
            if not age_ok:
                continue

            exclusion = trial["exclusion"]
            excluded = any(c in conditions for c in exclusion.get("conditions", []))
            if excluded:
                continue

            match_score = 0.7 + (0.1 if len(set(conditions) & set(trial["conditions"])) > 1 else 0)

            egfr = labs.get("egfr")
            if egfr and "egfr_min" in inclusion:
                if inclusion["egfr_min"] <= egfr <= inclusion.get("egfr_max", 999):
                    match_score += 0.1

            hba1c = labs.get("hba1c")
            if hba1c and "hba1c_min" in inclusion:
                if inclusion["hba1c_min"] <= hba1c <= inclusion.get("hba1c_max", 999):
                    match_score += 0.1

            matches.append({
                "nct_id": trial["nct_id"],
                "title": trial["title"],
                "phase": trial["phase"],
                "sponsor": trial["sponsor"],
                "match_score": round(min(match_score, 1.0), 2),
                "enrollment_remaining": trial["target_enrollment"] - trial["current_enrollment"],
                "sites": trial["sites"],
            })

        matches.sort(key=lambda m: m["match_score"], reverse=True)

        result = {
            "matched_at": now.isoformat(),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "conditions_evaluated": conditions,
            "total_trials_screened": len(TRIAL_REGISTRY),
            "matches_found": len(matches),
            "matches": matches,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Trial matching: {len(matches)} eligible trials from {len(TRIAL_REGISTRY)} screened",
        )

    async def _check_eligibility(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        nct_id = ctx.get("nct_id", "NCT05001234")
        trial = next((t for t in TRIAL_REGISTRY if t["nct_id"] == nct_id), TRIAL_REGISTRY[0])

        conditions = [c.lower() for c in ctx.get("conditions", [])]
        age = ctx.get("age", 55)

        criteria_checks = [
            {"criterion": "Age range", "met": trial["inclusion"].get("age_min", 0) <= age <= trial["inclusion"].get("age_max", 999)},
            {"criterion": "Condition match", "met": any(c in conditions for c in trial["conditions"])},
            {"criterion": "No exclusion conditions", "met": not any(c in conditions for c in trial["exclusion"].get("conditions", []))},
            {"criterion": "Enrollment open", "met": trial["current_enrollment"] < trial["target_enrollment"]},
        ]

        all_met = all(c["met"] for c in criteria_checks)

        # --- LLM-generated eligibility narrative ---
        eligibility_narrative = None
        try:
            eligibility_payload = {
                "nct_id": nct_id,
                "trial_title": trial["title"],
                "trial_phase": trial["phase"],
                "inclusion_criteria": trial["inclusion"],
                "exclusion_criteria": trial["exclusion"],
                "patient_conditions": conditions,
                "patient_age": age,
                "patient_labs": ctx.get("labs", {}),
                "criteria_checks": criteria_checks,
                "eligible": all_met,
            }
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Explain why this patient does or does not match the "
                    f"eligibility criteria for this clinical trial.\n\n"
                    f"Details:\n{json.dumps(eligibility_payload, indent=2)}"
                )}],
                system=(
                    "You are a clinical research coordinator AI. Generate a clear, "
                    "patient-friendly narrative explaining how the patient's clinical "
                    "profile aligns with the trial's inclusion and exclusion criteria. "
                    "For each criterion, explain whether it is met and why. If the "
                    "patient is not eligible, explain what would need to change. "
                    "If eligible, highlight the strongest match factors and next steps."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if llm_response and llm_response.content:
                eligibility_narrative = llm_response.content
        except Exception:
            logger.warning(
                "LLM call failed for eligibility narrative on trial %s; skipping",
                nct_id,
                exc_info=True,
            )

        result = {
            "checked_at": now.isoformat(),
            "nct_id": nct_id,
            "trial_title": trial["title"],
            "eligible": all_met,
            "criteria_checks": criteria_checks,
            "criteria_met": sum(1 for c in criteria_checks if c["met"]),
            "total_criteria": len(criteria_checks),
            "eligibility_narrative": eligibility_narrative,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Eligibility check for {nct_id}: {'eligible' if all_met else 'not eligible'}",
        )

    def _trial_details(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        nct_id = ctx.get("nct_id", "NCT05001234")
        trial = next((t for t in TRIAL_REGISTRY if t["nct_id"] == nct_id), TRIAL_REGISTRY[0])

        result = {
            "trial": trial,
            "enrollment_pct": round(trial["current_enrollment"] / max(trial["target_enrollment"], 1) * 100, 1),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Trial details: {nct_id}",
        )

    def _enrollment_status(self, input_data: AgentInput) -> AgentOutput:
        now = datetime.now(timezone.utc)

        summary = []
        for trial in TRIAL_REGISTRY:
            summary.append({
                "nct_id": trial["nct_id"],
                "title": trial["title"],
                "status": trial["status"],
                "enrolled": trial["current_enrollment"],
                "target": trial["target_enrollment"],
                "pct_enrolled": round(trial["current_enrollment"] / max(trial["target_enrollment"], 1) * 100, 1),
            })

        result = {
            "checked_at": now.isoformat(),
            "total_trials": len(summary),
            "actively_recruiting": sum(1 for t in summary if t["status"] == "Recruiting"),
            "trials": summary,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Enrollment status: {result['actively_recruiting']} recruiting trials",
        )
