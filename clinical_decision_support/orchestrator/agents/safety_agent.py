"""
Safety Agent
Checks for drug interactions, allergies, contraindications, and clinical safety concerns.
Acts as a guardrail before treatments are recommended.
"""

import os
from typing import List, Optional, Dict, Any
from .base_agent import (
    BaseAgent, PatientContext, AgentOutput, AgentCapability,
    ClinicalFinding, TreatmentRecommendation
)


# Common drug-drug interactions database (simplified)
DRUG_INTERACTIONS = {
    ("warfarin", "aspirin"): {
        "severity": "major",
        "effect": "Increased bleeding risk",
        "recommendation": "Monitor INR closely; consider alternative antiplatelet if possible"
    },
    ("lisinopril", "potassium"): {
        "severity": "major",
        "effect": "Hyperkalemia risk",
        "recommendation": "Monitor potassium levels; avoid potassium supplements"
    },
    ("lisinopril", "spironolactone"): {
        "severity": "major",
        "effect": "Hyperkalemia risk",
        "recommendation": "Monitor potassium closely; may need dose adjustment"
    },
    ("metformin", "contrast"): {
        "severity": "major",
        "effect": "Lactic acidosis risk",
        "recommendation": "Hold metformin 48h before and after contrast administration"
    },
    ("simvastatin", "amiodarone"): {
        "severity": "major",
        "effect": "Myopathy/rhabdomyolysis risk",
        "recommendation": "Limit simvastatin to 20mg daily or use alternative statin"
    },
    ("clopidogrel", "omeprazole"): {
        "severity": "moderate",
        "effect": "Reduced clopidogrel efficacy",
        "recommendation": "Consider pantoprazole as alternative PPI"
    },
    ("fluoxetine", "tramadol"): {
        "severity": "major",
        "effect": "Serotonin syndrome risk",
        "recommendation": "Avoid combination; use alternative analgesic"
    },
    ("methotrexate", "nsaids"): {
        "severity": "major",
        "effect": "Methotrexate toxicity",
        "recommendation": "Avoid NSAIDs or use lowest dose for shortest duration"
    },
}

# Drug class mappings for interaction checking
DRUG_CLASSES = {
    "ace_inhibitors": ["lisinopril", "enalapril", "ramipril", "benazepril", "captopril"],
    "arbs": ["losartan", "valsartan", "irbesartan", "candesartan"],
    "beta_blockers": ["metoprolol", "carvedilol", "atenolol", "propranolol", "bisoprolol"],
    "nsaids": ["ibuprofen", "naproxen", "diclofenac", "indomethacin", "meloxicam", "celecoxib"],
    "anticoagulants": ["warfarin", "heparin", "enoxaparin", "rivaroxaban", "apixaban", "dabigatran"],
    "antiplatelets": ["aspirin", "clopidogrel", "ticagrelor", "prasugrel"],
    "statins": ["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin"],
    "ssris": ["fluoxetine", "sertraline", "paroxetine", "citalopram", "escitalopram"],
    "ppis": ["omeprazole", "pantoprazole", "esomeprazole", "lansoprazole"],
}

# Allergy cross-reactivity
ALLERGY_CROSS_REACTIVITY = {
    "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "nafcillin"],
    "sulfa": ["sulfamethoxazole", "sulfasalazine", "some thiazide diuretics"],
    "cephalosporins": ["cephalexin", "ceftriaxone", "cefazolin", "cefepime"],
    "nsaids": ["ibuprofen", "naproxen", "aspirin", "diclofenac"],
}


class SafetyAgent(BaseAgent):
    """
    Clinical Safety Agent
    - Checks drug-drug interactions
    - Validates against patient allergies
    - Identifies contraindications
    - Provides safety warnings
    """

    def __init__(self):
        super().__init__(
            agent_id="safety",
            name="Clinical Safety Officer",
            description="Validates treatment safety, checks interactions and allergies",
            version="1.0.0"
        )
        self.specialties = ["pharmacology", "patient_safety"]

    def _setup_capabilities(self):
        self.capabilities = [
            AgentCapability(
                name="check_drug_interactions",
                description="Check for drug-drug interactions",
                input_schema={"current_meds": "list", "new_meds": "list"},
                output_schema={"interactions": "list", "severity": "string"}
            ),
            AgentCapability(
                name="check_allergies",
                description="Check if treatments conflict with patient allergies",
                input_schema={"allergies": "list", "treatments": "list"},
                output_schema={"conflicts": "list", "safe": "bool"}
            ),
            AgentCapability(
                name="validate_treatment_plan",
                description="Comprehensive safety check of treatment plan",
                input_schema={"treatments": "list", "context": "PatientContext"},
                output_schema={"approved": "list", "rejected": "list", "warnings": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Run safety checks on proposed treatments"""
        reasoning_steps = []
        warnings = []
        findings = []

        # Get treatments to check from task
        treatments = task.get("treatments", []) if task else []

        # Step 1: Check drug-drug interactions
        reasoning_steps.append("Step 1: Checking drug-drug interactions...")
        current_meds = [m.get("medication_name", "").lower() for m in (context.medications or []) if m and isinstance(m, dict)]
        new_meds = self._extract_medications(treatments)

        interactions = self._check_interactions(current_meds, new_meds)
        for interaction in interactions:
            if interaction["severity"] == "major":
                findings.append(ClinicalFinding(
                    type="safety",
                    name="Drug Interaction",
                    value=f"{interaction['drug1']} + {interaction['drug2']}",
                    status="critical",
                    interpretation=interaction["effect"],
                    source="Safety Agent"
                ))
                warnings.append(f"MAJOR INTERACTION: {interaction['drug1']} + {interaction['drug2']}: {interaction['effect']}")
            elif interaction["severity"] == "moderate":
                warnings.append(f"Moderate interaction: {interaction['drug1']} + {interaction['drug2']}: {interaction['recommendation']}")

        # Step 2: Check allergies
        reasoning_steps.append("Step 2: Checking allergy cross-reactivity...")
        allergies = [a.get("substance", "").lower() for a in (context.allergies or []) if a and isinstance(a, dict)]
        allergy_conflicts = self._check_allergy_cross_reactivity(allergies, new_meds)

        for conflict in allergy_conflicts:
            findings.append(ClinicalFinding(
                type="safety",
                name="Allergy Concern",
                value=conflict["medication"],
                status="critical",
                interpretation=f"Patient allergic to {conflict['allergy']}; {conflict['medication']} may cross-react",
                source="Safety Agent"
            ))
            warnings.append(f"ALLERGY RISK: {conflict['medication']} - patient has {conflict['allergy']} allergy")

        # Step 3: Check contraindications based on conditions
        reasoning_steps.append("Step 3: Checking contraindications...")
        contraindications = self._check_contraindications(context, treatments)

        for ci in contraindications:
            findings.append(ClinicalFinding(
                type="safety",
                name="Contraindication",
                value=ci["treatment"],
                status="abnormal",
                interpretation=ci["reason"],
                source="Safety Agent"
            ))
            warnings.append(f"Contraindication: {ci['treatment']} - {ci['reason']}")

        # Step 4: Age-based checks
        reasoning_steps.append("Step 4: Checking age-appropriate dosing...")
        if context.age:
            age_warnings = self._check_age_considerations(context.age, treatments)
            warnings.extend(age_warnings)

        # Determine review requirements
        requires_review = len(findings) > 0 or any("MAJOR" in w for w in warnings)
        review_reason = None
        if requires_review:
            review_reason = f"{len(findings)} safety concern(s) identified"

        return self._create_output(
            findings=findings,
            confidence=0.95,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    def _extract_medications(self, treatments: List) -> List[str]:
        """Extract medication names from treatments"""
        meds = []
        for t in treatments:
            if isinstance(t, dict):
                desc = t.get("description", "").lower()
            elif hasattr(t, "description"):
                desc = t.description.lower()
            else:
                continue

            # Extract medication names from common patterns
            for drug_class, drugs in DRUG_CLASSES.items():
                for drug in drugs:
                    if drug in desc:
                        meds.append(drug)

        return list(set(meds))

    def _check_interactions(self, current_meds: List[str], new_meds: List[str]) -> List[Dict]:
        """Check for drug-drug interactions"""
        interactions = []

        all_meds = current_meds + new_meds

        for (drug1, drug2), info in DRUG_INTERACTIONS.items():
            if drug1 in all_meds and drug2 in all_meds:
                interactions.append({
                    "drug1": drug1,
                    "drug2": drug2,
                    **info
                })

            # Check by drug class
            for class_name, class_drugs in DRUG_CLASSES.items():
                if drug1 == class_name:
                    for d1 in class_drugs:
                        if d1 in all_meds and drug2 in all_meds:
                            interactions.append({
                                "drug1": d1,
                                "drug2": drug2,
                                **info
                            })

        return interactions

    def _check_allergy_cross_reactivity(self, allergies: List[str], medications: List[str]) -> List[Dict]:
        """Check for allergy cross-reactivity"""
        conflicts = []

        for allergy in allergies:
            # Direct match
            if allergy in medications:
                conflicts.append({
                    "allergy": allergy,
                    "medication": allergy,
                    "type": "direct"
                })

            # Cross-reactivity
            if allergy in ALLERGY_CROSS_REACTIVITY:
                for related_drug in ALLERGY_CROSS_REACTIVITY[allergy]:
                    if related_drug.lower() in medications:
                        conflicts.append({
                            "allergy": allergy,
                            "medication": related_drug,
                            "type": "cross_reactivity"
                        })

        return conflicts

    def _check_contraindications(self, context: PatientContext, treatments: List) -> List[Dict]:
        """Check treatments against patient conditions"""
        contraindications = []
        conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]

        for t in treatments:
            if isinstance(t, dict):
                desc = t.get("description", "").lower()
                ci_list = t.get("contraindications", [])
            elif hasattr(t, "description"):
                desc = t.description.lower()
                ci_list = getattr(t, "contraindications", [])
            else:
                continue

            # ACE inhibitor contraindications
            if any(ace in desc for ace in ["lisinopril", "enalapril", "ace inhibitor"]):
                if "pregnancy" in " ".join(conditions):
                    contraindications.append({
                        "treatment": desc[:50],
                        "reason": "ACE inhibitors contraindicated in pregnancy"
                    })
                if "angioedema" in " ".join(conditions):
                    contraindications.append({
                        "treatment": desc[:50],
                        "reason": "History of angioedema - ACE inhibitor contraindicated"
                    })

            # Metformin contraindications
            if "metformin" in desc:
                if any(x in " ".join(conditions) for x in ["ckd stage 4", "ckd stage 5", "egfr < 30"]):
                    contraindications.append({
                        "treatment": desc[:50],
                        "reason": "Metformin contraindicated in severe renal impairment"
                    })

            # Beta-blocker contraindications
            if any(bb in desc for bb in ["metoprolol", "carvedilol", "beta blocker"]):
                if "severe bradycardia" in " ".join(conditions):
                    contraindications.append({
                        "treatment": desc[:50],
                        "reason": "Beta-blocker contraindicated with severe bradycardia"
                    })

        return contraindications

    def _check_age_considerations(self, age: int, treatments: List) -> List[str]:
        """Check for age-appropriate dosing concerns"""
        warnings = []

        for t in treatments:
            if isinstance(t, dict):
                desc = t.get("description", "").lower()
            elif hasattr(t, "description"):
                desc = t.description.lower()
            else:
                continue

            # Elderly considerations
            if age >= 65:
                if "nsaid" in desc or any(nsaid in desc for nsaid in ["ibuprofen", "naproxen"]):
                    warnings.append("Elderly patient: NSAIDs increase GI bleeding and renal risk")
                if "benzodiazepine" in desc or any(benzo in desc for benzo in ["lorazepam", "diazepam", "alprazolam"]):
                    warnings.append("Elderly patient: Benzodiazepines increase fall risk")

            # Pediatric considerations
            if age < 18:
                if "aspirin" in desc:
                    warnings.append("Pediatric patient: Aspirin contraindicated (Reye syndrome risk)")

        return warnings


# Singleton instance
safety_agent = SafetyAgent()
