"""
Treatment Agent
Generates evidence-based treatment recommendations with CPT codes.
Considers patient context, contraindications, and drug interactions.
"""

import os
from typing import List, Optional
from .base_agent import (
    BaseAgent, PatientContext, AgentOutput, AgentCapability,
    ClinicalFinding, DiagnosisRecommendation, TreatmentRecommendation
)

# Support both package import and direct execution
try:
    from ..llm import get_clinical_llm, ClinicalLLM
except ImportError:
    from llm import get_clinical_llm, ClinicalLLM

USE_LLM = os.getenv("USE_LLM", "true").lower() == "true"


# Treatment protocols for common diagnoses
TREATMENT_PROTOCOLS = {
    "I10": {  # Essential Hypertension
        "diagnosis": "Essential Hypertension",
        "treatments": [
            {
                "type": "medication",
                "description": "Start lisinopril 10mg daily",
                "cpt": "99214",
                "priority": "routine",
                "rationale": "ACE inhibitor first-line for hypertension per ACC/AHA guidelines"
            },
            {
                "type": "monitoring",
                "description": "Home blood pressure monitoring twice daily",
                "cpt": "99473",
                "priority": "routine",
                "rationale": "Track response to therapy"
            },
            {
                "type": "procedure",
                "description": "Basic metabolic panel to check baseline renal function and potassium",
                "cpt": "80048",
                "priority": "routine",
                "rationale": "Baseline labs before ACE inhibitor"
            },
            {
                "type": "referral",
                "description": "Lifestyle counseling: DASH diet, sodium restriction, exercise",
                "cpt": "99401",
                "priority": "routine",
                "rationale": "Non-pharmacologic BP management"
            }
        ],
        "contraindications": ["angioedema", "pregnancy", "bilateral renal artery stenosis"],
        "alternatives": ["amlodipine", "losartan", "hydrochlorothiazide"]
    },
    "E11.9": {  # Type 2 Diabetes
        "diagnosis": "Type 2 Diabetes Mellitus",
        "treatments": [
            {
                "type": "medication",
                "description": "Start metformin 500mg twice daily with meals",
                "cpt": "99214",
                "priority": "routine",
                "rationale": "First-line therapy per ADA guidelines"
            },
            {
                "type": "monitoring",
                "description": "HbA1c every 3 months until at goal",
                "cpt": "83036",
                "priority": "routine",
                "rationale": "Track glycemic control"
            },
            {
                "type": "procedure",
                "description": "Comprehensive metabolic panel",
                "cpt": "80053",
                "priority": "routine",
                "rationale": "Baseline renal/hepatic function"
            },
            {
                "type": "referral",
                "description": "Diabetic education and nutrition counseling",
                "cpt": "G0108",
                "priority": "routine",
                "rationale": "Self-management education"
            },
            {
                "type": "referral",
                "description": "Ophthalmology for diabetic eye exam",
                "cpt": "92004",
                "priority": "routine",
                "rationale": "Screen for diabetic retinopathy"
            }
        ],
        "contraindications": ["eGFR <30", "metabolic acidosis", "liver failure"],
        "alternatives": ["SGLT2 inhibitor", "GLP-1 agonist", "sulfonylurea"]
    },
    "I50.9": {  # Heart Failure
        "diagnosis": "Heart Failure",
        "treatments": [
            {
                "type": "medication",
                "description": "Start lisinopril 2.5-5mg daily (uptitrate as tolerated)",
                "cpt": "99214",
                "priority": "urgent",
                "rationale": "GDMT for HFrEF - ACEi/ARB/ARNI"
            },
            {
                "type": "medication",
                "description": "Start carvedilol 3.125mg twice daily (uptitrate)",
                "cpt": "99214",
                "priority": "urgent",
                "rationale": "GDMT for HFrEF - beta blocker"
            },
            {
                "type": "medication",
                "description": "Add furosemide 20-40mg daily if volume overloaded",
                "cpt": "99214",
                "priority": "urgent",
                "rationale": "Diuretic for congestion"
            },
            {
                "type": "procedure",
                "description": "Echocardiogram",
                "cpt": "93306",
                "priority": "urgent",
                "rationale": "Assess ejection fraction and structure"
            },
            {
                "type": "monitoring",
                "description": "Daily weights, sodium restriction <2g/day, fluid restriction",
                "cpt": "99457",
                "priority": "routine",
                "rationale": "Monitor for volume status"
            },
            {
                "type": "referral",
                "description": "Cardiology referral for optimization",
                "cpt": "99243",
                "priority": "urgent",
                "rationale": "GDMT optimization and device evaluation"
            }
        ],
        "contraindications": [],
        "alternatives": []
    },
    "R50.9": {  # Fever
        "diagnosis": "Fever",
        "treatments": [
            {
                "type": "monitoring",
                "description": "Monitor temperature every 4 hours",
                "cpt": "99212",
                "priority": "routine",
                "rationale": "Track fever curve"
            },
            {
                "type": "medication",
                "description": "Acetaminophen 650mg every 6 hours as needed for fever >38.5°C",
                "cpt": "99214",
                "priority": "routine",
                "rationale": "Symptomatic treatment"
            },
            {
                "type": "procedure",
                "description": "CBC with differential, CMP, urinalysis, blood cultures x2",
                "cpt": "85025",
                "priority": "urgent",
                "rationale": "Workup for source of infection"
            },
            {
                "type": "procedure",
                "description": "Chest X-ray if respiratory symptoms",
                "cpt": "71046",
                "priority": "urgent",
                "rationale": "Evaluate for pneumonia"
            }
        ],
        "contraindications": [],
        "alternatives": ["ibuprofen if no contraindication"]
    }
}


class TreatmentAgent(BaseAgent):
    """
    Treatment Planning Agent
    - Generates evidence-based treatment recommendations
    - Provides CPT codes for procedures
    - Checks for drug interactions and contraindications
    """

    def __init__(self):
        super().__init__(
            agent_id="treatment",
            name="Treatment Planner",
            description="Generates evidence-based treatment plans with CPT codes",
            version="1.0.0"
        )
        self.specialties = ["internal_medicine", "primary_care"]

        # Initialize unified LLM client
        self.llm: Optional[ClinicalLLM] = None
        if USE_LLM:
            try:
                self.llm = get_clinical_llm()
            except Exception as e:
                import logging
                logging.warning(f"Failed to initialize LLM: {e}")

    def _setup_capabilities(self):
        self.capabilities = [
            AgentCapability(
                name="generate_treatment_plan",
                description="Generate comprehensive treatment plan for diagnoses",
                input_schema={"diagnoses": "List[DiagnosisRecommendation]", "context": "PatientContext"},
                output_schema={"treatments": "List[TreatmentRecommendation]"}
            ),
            AgentCapability(
                name="check_contraindications",
                description="Check if treatments are safe given patient context",
                input_schema={"treatments": "list", "allergies": "list", "conditions": "list"},
                output_schema={"safe_treatments": "list", "contraindicated": "list"}
            ),
            AgentCapability(
                name="suggest_cpt_codes",
                description="Suggest CPT codes for planned procedures",
                input_schema={"procedures": "list"},
                output_schema={"cpt_codes": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Generate treatment plan based on diagnoses"""
        reasoning_steps = []
        treatments = []
        warnings = []

        # Get diagnoses from task or infer from context
        diagnoses = task.get("diagnoses", []) if task else []

        # If no diagnoses provided, infer from conditions
        if not diagnoses and context.conditions:
            reasoning_steps.append("Step 1: Extracting diagnoses from patient conditions...")
            for condition in context.conditions:
                if not condition or not isinstance(condition, dict):
                    continue
                icd10 = condition.get("code", "")
                if icd10 in TREATMENT_PROTOCOLS:
                    diagnoses.append({
                        "icd10_code": icd10,
                        "diagnosis": condition.get("display", "")
                    })

        reasoning_steps.append(f"Step 2: Processing {len(diagnoses)} diagnosis(es)...")

        # Generate treatments for each diagnosis
        for dx in diagnoses:
            icd10 = dx.get("icd10_code", "") if isinstance(dx, dict) else dx.icd10_code
            dx_treatments = await self._get_treatments_for_diagnosis(icd10, context)
            treatments.extend(dx_treatments)

        # Check for drug interactions
        reasoning_steps.append("Step 3: Checking for drug interactions...")
        med_treatments = [t for t in treatments if t.treatment_type == "medication"]
        if med_treatments and context.medications:
            interactions = await self._check_interactions(med_treatments, context.medications)
            if interactions:
                warnings.extend(interactions)

        # Check contraindications
        reasoning_steps.append("Step 4: Checking contraindications...")
        treatments, contraindicated = self._check_contraindications(treatments, context)
        if contraindicated:
            warnings.append(f"{len(contraindicated)} treatment(s) contraindicated and removed")

        # Prioritize treatments
        reasoning_steps.append("Step 5: Prioritizing treatment plan...")
        treatments.sort(key=lambda t: {"immediate": 0, "urgent": 1, "routine": 2}.get(t.priority, 3))

        # Determine if human review needed
        requires_review = False
        review_reason = None
        if any(t.priority == "immediate" for t in treatments):
            requires_review = True
            review_reason = "Immediate interventions required - physician approval needed"
        if warnings:
            requires_review = True
            review_reason = "Drug interactions or contraindications detected"

        return self._create_output(
            treatments=treatments,
            confidence=0.85 if treatments else 0.0,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    async def _get_treatments_for_diagnosis(
        self,
        icd10: str,
        context: PatientContext
    ) -> List[TreatmentRecommendation]:
        """Get treatment recommendations for a diagnosis"""
        treatments = []

        # Check protocol database
        protocol = TREATMENT_PROTOCOLS.get(icd10)
        if protocol:
            for tx in protocol["treatments"]:
                treatments.append(TreatmentRecommendation(
                    treatment_type=tx["type"],
                    description=tx["description"],
                    cpt_code=tx.get("cpt"),
                    priority=tx["priority"],
                    rationale=tx["rationale"],
                    contraindications=protocol.get("contraindications", []),
                    alternatives=protocol.get("alternatives", [])
                ))
        else:
            # Try to get from RAG
            try:
                result = await self.mcp.call_tool(
                    "rag",
                    "get_treatment_protocol",
                    {"diagnosis": icd10}
                )
                if result.get("protocol"):
                    # Create generic treatment recommendation
                    treatments.append(TreatmentRecommendation(
                        treatment_type="monitoring",
                        description=f"Follow clinical guidelines for {icd10}",
                        cpt_code="99214",
                        priority="routine",
                        rationale="Based on clinical guidelines",
                        contraindications=[],
                        alternatives=[]
                    ))
            except Exception:
                pass

        # If using LLM, enhance recommendations
        if self.llm and treatments:
            treatments = await self._enhance_with_llm(treatments, context)

        return treatments

    async def _enhance_with_llm(
        self,
        treatments: List[TreatmentRecommendation],
        context: PatientContext
    ) -> List[TreatmentRecommendation]:
        """Use LLM to personalize treatment recommendations"""
        if not self.llm or not treatments:
            return treatments

        try:
            # Build prompt for treatment personalization
            treatments_json = [
                {
                    "type": t.treatment_type,
                    "description": t.description,
                    "priority": t.priority,
                    "rationale": t.rationale
                }
                for t in treatments
            ]

            prompt = f"""Review and personalize these treatment recommendations for this patient.

Patient Context:
- Age: {context.age or 'Unknown'}
- Sex: {context.sex or 'Unknown'}
- Current Medications: {', '.join([m.get('medication_name', '') for m in (context.medications or []) if m and isinstance(m, dict)]) or 'None'}
- Allergies: {', '.join([a.get('substance', '') for a in (context.allergies or []) if a and isinstance(a, dict)]) or 'NKDA'}
- Conditions: {', '.join([c.get('display', '') for c in (context.conditions or []) if c and isinstance(c, dict)]) or 'None'}

Proposed Treatments:
{treatments_json}

Consider:
1. Age-appropriate dosing adjustments
2. Drug-drug interactions with current medications
3. Contraindications based on existing conditions
4. Allergy cross-reactivity concerns

Return JSON with personalized recommendations:
{{
    "treatments": [
        {{
            "original_index": 0,
            "adjusted_description": "...",
            "dosing_notes": "...",
            "warnings": []
        }}
    ]
}}"""

            response = await self.llm.generate(
                prompt=prompt,
                task_type="treatment_personalization",
                patient_id=context.patient_id,
                json_mode=True
            )

            content = response["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                import json
                data = json.loads(content[start:end])

                # Apply personalization to treatments
                for adjustment in data.get("treatments", []):
                    idx = adjustment.get("original_index", 0)
                    if idx < len(treatments):
                        if adjustment.get("adjusted_description"):
                            treatments[idx].description = adjustment["adjusted_description"]
                        if adjustment.get("dosing_notes"):
                            treatments[idx].rationale += f" | {adjustment['dosing_notes']}"

        except Exception as e:
            import logging
            logging.warning(f"LLM treatment enhancement failed: {e}")

        return treatments

    async def _check_interactions(
        self,
        new_treatments: List[TreatmentRecommendation],
        current_meds: List[dict]
    ) -> List[str]:
        """Check for drug-drug interactions"""
        warnings = []

        try:
            current_med_names = [m.get("medication_name", "") for m in current_meds]

            for tx in new_treatments:
                # Extract medication name from description
                description = tx.description.lower()

                result = await self.mcp.call_tool(
                    "rag",
                    "check_drug_interactions",
                    {
                        "medications": current_med_names,
                        "new_medication": description.split()[1] if len(description.split()) > 1 else ""
                    }
                )

                interactions = result.get("interactions", [])
                for interaction in interactions:
                    if interaction.get("severity") == "major":
                        warnings.append(
                            f"MAJOR INTERACTION: {interaction.get('drug1')} + {interaction.get('drug2')}: "
                            f"{interaction.get('effect')}. {interaction.get('recommendation')}"
                        )
                    elif interaction.get("severity") == "moderate":
                        warnings.append(
                            f"Moderate interaction: {interaction.get('drug1')} + {interaction.get('drug2')}: "
                            f"{interaction.get('recommendation')}"
                        )

        except Exception as e:
            import logging
            logging.warning(f"Drug interaction check failed: {e}")

        return warnings

    def _check_contraindications(
        self,
        treatments: List[TreatmentRecommendation],
        context: PatientContext
    ) -> tuple[List[TreatmentRecommendation], List[TreatmentRecommendation]]:
        """Check treatments against patient allergies and conditions"""
        safe = []
        contraindicated = []

        allergies = [a.get("substance", "").lower() for a in (context.allergies or []) if a and isinstance(a, dict)]
        conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]

        for tx in treatments:
            is_safe = True
            description_lower = tx.description.lower()

            # Check allergies
            for allergy in allergies:
                if allergy and allergy in description_lower:
                    is_safe = False
                    break

            # Check known contraindications
            for contraindication in tx.contraindications:
                ci_lower = contraindication.lower()
                if any(ci_lower in cond for cond in conditions):
                    is_safe = False
                    break

            # Special checks
            if "ace inhibitor" in description_lower or "lisinopril" in description_lower:
                if "pregnancy" in conditions or "angioedema" in conditions:
                    is_safe = False

            if "metformin" in description_lower:
                if "chronic kidney disease, stage 4" in conditions or "ckd stage 5" in conditions:
                    is_safe = False

            if is_safe:
                safe.append(tx)
            else:
                contraindicated.append(tx)

        return safe, contraindicated
