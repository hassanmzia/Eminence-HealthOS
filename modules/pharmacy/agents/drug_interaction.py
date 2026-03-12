"""
Eminence HealthOS — Drug Interaction Agent (#32)
Layer 3 (Decisioning): Checks new prescriptions against patient medications,
allergies, and conditions. FDA Class II (510(k)) safety-critical agent.
"""

from __future__ import annotations

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

# Drug-drug interaction database (simplified)
INTERACTION_DB: list[dict[str, Any]] = [
    {"drug_a": "lisinopril", "drug_b": "losartan", "severity": "major", "description": "Dual RAAS blockade increases risk of hyperkalemia, hypotension, and renal impairment", "clinical_action": "Avoid combination"},
    {"drug_a": "lisinopril", "drug_b": "spironolactone", "severity": "major", "description": "Increased risk of hyperkalemia", "clinical_action": "Monitor potassium closely if combination necessary"},
    {"drug_a": "metformin", "drug_b": "contrast_dye", "severity": "major", "description": "Risk of lactic acidosis with iodinated contrast", "clinical_action": "Hold metformin 48h before and after contrast"},
    {"drug_a": "warfarin", "drug_b": "aspirin", "severity": "major", "description": "Increased risk of bleeding", "clinical_action": "Monitor INR; consider gastroprotection"},
    {"drug_a": "sertraline", "drug_b": "tramadol", "severity": "major", "description": "Risk of serotonin syndrome", "clinical_action": "Avoid combination"},
    {"drug_a": "amlodipine", "drug_b": "simvastatin", "severity": "moderate", "description": "Increased simvastatin levels — myopathy risk", "clinical_action": "Limit simvastatin to 20mg daily"},
    {"drug_a": "metformin", "drug_b": "alcohol", "severity": "moderate", "description": "Increased risk of lactic acidosis", "clinical_action": "Advise limiting alcohol intake"},
    {"drug_a": "gabapentin", "drug_b": "hydrocodone", "severity": "major", "description": "CNS depression; respiratory depression risk", "clinical_action": "Reduce opioid dose; monitor respiratory status"},
    {"drug_a": "omeprazole", "drug_b": "clopidogrel", "severity": "major", "description": "Reduced antiplatelet effect of clopidogrel", "clinical_action": "Switch to pantoprazole if PPI needed"},
    {"drug_a": "fluoxetine", "drug_b": "tramadol", "severity": "major", "description": "Risk of serotonin syndrome and seizures", "clinical_action": "Avoid combination"},
]

# Drug-allergy cross-reactivity classes
ALLERGY_CLASSES: dict[str, list[str]] = {
    "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "penicillin"],
    "sulfa": ["sulfamethoxazole", "sulfasalazine", "dapsone"],
    "nsaid": ["ibuprofen", "naproxen", "aspirin", "celecoxib", "ketorolac"],
    "cephalosporin": ["cephalexin", "ceftriaxone", "cefazolin", "cefdinir"],
}

# Age-based dosing warnings
AGE_WARNINGS: list[dict[str, Any]] = [
    {"drug": "metformin", "age_min": 80, "warning": "Assess renal function before initiating in patients ≥80", "severity": "moderate"},
    {"drug": "gabapentin", "age_min": 65, "warning": "Start at lower dose in elderly; fall risk", "severity": "moderate"},
    {"drug": "hydrocodone", "age_min": 65, "warning": "Increased sensitivity in elderly; start low", "severity": "major"},
    {"drug": "benzodiazepine", "age_min": 65, "warning": "Beers Criteria — avoid in elderly if possible", "severity": "major"},
]


class DrugInteractionAgent(BaseAgent):
    """Checks prescriptions against medications, allergies, and conditions."""

    name = "drug_interaction"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "FDA Class II drug interaction checking — DDI, drug-allergy cross-reactivity, "
        "age-based dosing, and contraindication validation"
    )
    min_confidence = 0.90

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "check_interactions")

        if action == "check_interactions":
            return self._check_interactions(input_data)
        elif action == "check_allergies":
            return self._check_allergies(input_data)
        elif action == "check_contraindications":
            return self._check_contraindications(input_data)
        elif action == "full_safety_check":
            return self._full_safety_check(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown drug interaction action: {action}",
                status=AgentStatus.FAILED,
            )

    def _check_interactions(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        new_drug = ctx.get("new_drug", "").lower()
        current_medications = [m.lower() for m in ctx.get("current_medications", [])]

        interactions: list[dict[str, Any]] = []
        for interaction in INTERACTION_DB:
            a, b = interaction["drug_a"], interaction["drug_b"]
            if (new_drug == a and b in current_medications) or (new_drug == b and a in current_medications):
                interacting_drug = b if new_drug == a else a
                interactions.append({
                    "new_drug": new_drug,
                    "interacting_drug": interacting_drug,
                    "severity": interaction["severity"],
                    "description": interaction["description"],
                    "clinical_action": interaction["clinical_action"],
                })

        has_major = any(i["severity"] == "major" for i in interactions)

        result = {
            "checked_at": now.isoformat(),
            "new_drug": new_drug,
            "medications_checked": len(current_medications),
            "interactions_found": len(interactions),
            "has_major_interaction": has_major,
            "interactions": sorted(interactions, key=lambda i: i["severity"] == "major", reverse=True),
            "safe_to_prescribe": not has_major,
        }

        confidence = 0.95 if not interactions else (0.85 if not has_major else 0.92)

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Drug interaction check for {new_drug}: {len(interactions)} interactions "
                f"({'MAJOR — review required' if has_major else 'no major issues'})"
            ),
        )

    def _check_allergies(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        new_drug = ctx.get("new_drug", "").lower()
        patient_allergies = [a.lower() for a in ctx.get("allergies", [])]

        alerts: list[dict[str, Any]] = []

        # Direct allergy match
        if new_drug in patient_allergies:
            alerts.append({
                "type": "direct_allergy",
                "drug": new_drug,
                "allergen": new_drug,
                "severity": "critical",
                "message": f"Patient has documented allergy to {new_drug}",
            })

        # Cross-reactivity check
        for allergy in patient_allergies:
            for class_name, members in ALLERGY_CLASSES.items():
                if allergy in members and new_drug in members and new_drug != allergy:
                    alerts.append({
                        "type": "cross_reactivity",
                        "drug": new_drug,
                        "allergen": allergy,
                        "drug_class": class_name,
                        "severity": "high",
                        "message": f"Cross-reactivity risk: {new_drug} and {allergy} are in the {class_name} class",
                    })

        result = {
            "checked_at": now.isoformat(),
            "new_drug": new_drug,
            "allergies_checked": patient_allergies,
            "alerts": alerts,
            "has_allergy_conflict": len(alerts) > 0,
            "safe_to_prescribe": len(alerts) == 0,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Allergy check for {new_drug}: {len(alerts)} alert(s)",
        )

    def _check_contraindications(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        new_drug = ctx.get("new_drug", "").lower()
        patient_age = ctx.get("patient_age", 0)
        conditions = [c.lower() for c in ctx.get("conditions", [])]

        warnings: list[dict[str, Any]] = []

        # Age-based warnings
        for aw in AGE_WARNINGS:
            if aw["drug"] == new_drug and patient_age >= aw["age_min"]:
                warnings.append({
                    "type": "age_warning",
                    "drug": new_drug,
                    "patient_age": patient_age,
                    "severity": aw["severity"],
                    "warning": aw["warning"],
                })

        # Condition-based contraindications
        contraindications = {
            "metformin": {"renal_failure": "Contraindicated in severe renal impairment (eGFR < 30)"},
            "lisinopril": {"pregnancy": "Contraindicated in pregnancy — teratogenic"},
            "losartan": {"pregnancy": "Contraindicated in pregnancy — teratogenic"},
            "atorvastatin": {"liver_disease": "Contraindicated in active liver disease"},
        }

        if new_drug in contraindications:
            for condition, message in contraindications[new_drug].items():
                if condition in conditions:
                    warnings.append({
                        "type": "contraindication",
                        "drug": new_drug,
                        "condition": condition,
                        "severity": "critical",
                        "warning": message,
                    })

        result = {
            "checked_at": now.isoformat(),
            "new_drug": new_drug,
            "warnings": warnings,
            "has_contraindication": any(w["severity"] == "critical" for w in warnings),
            "safe_to_prescribe": not any(w["severity"] == "critical" for w in warnings),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Contraindication check for {new_drug}: {len(warnings)} warning(s)",
        )

    def _full_safety_check(self, input_data: AgentInput) -> AgentOutput:
        """Run all safety checks (interactions + allergies + contraindications)."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        new_drug = ctx.get("new_drug", "").lower()

        # Run all checks
        interactions_out = self._check_interactions(input_data)
        allergies_out = self._check_allergies(input_data)
        contraindications_out = self._check_contraindications(input_data)

        interactions = interactions_out.result.get("interactions", [])
        allergy_alerts = allergies_out.result.get("alerts", [])
        warnings = contraindications_out.result.get("warnings", [])

        all_safe = (
            interactions_out.result.get("safe_to_prescribe", True)
            and allergies_out.result.get("safe_to_prescribe", True)
            and contraindications_out.result.get("safe_to_prescribe", True)
        )

        total_issues = len(interactions) + len(allergy_alerts) + len(warnings)

        result = {
            "checked_at": now.isoformat(),
            "new_drug": new_drug,
            "safe_to_prescribe": all_safe,
            "total_issues": total_issues,
            "drug_interactions": interactions,
            "allergy_alerts": allergy_alerts,
            "contraindication_warnings": warnings,
            "recommendation": "Safe to prescribe" if all_safe else "Review required — safety concerns identified",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Full safety check for {new_drug}: {total_issues} issue(s) — {'SAFE' if all_safe else 'REVIEW REQUIRED'}",
        )
