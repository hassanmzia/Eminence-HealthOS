"""
Clinical Coding Agent
Suggests and validates ICD-10 diagnosis codes and CPT procedure codes.
Ensures coding accuracy and compliance.
"""

import os
from typing import List, Optional, Dict, Any
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


# ICD-10 Code Database (simplified)
ICD10_CODES = {
    # Hypertension
    "I10": {"description": "Essential (primary) hypertension", "category": "cardiovascular"},
    "I11.0": {"description": "Hypertensive heart disease with heart failure", "category": "cardiovascular"},
    "I11.9": {"description": "Hypertensive heart disease without heart failure", "category": "cardiovascular"},
    "I12.9": {"description": "Hypertensive chronic kidney disease", "category": "cardiovascular"},
    "I13.10": {"description": "Hypertensive heart and CKD without heart failure", "category": "cardiovascular"},

    # Diabetes
    "E11.9": {"description": "Type 2 diabetes mellitus without complications", "category": "endocrine"},
    "E11.65": {"description": "Type 2 DM with hyperglycemia", "category": "endocrine"},
    "E11.21": {"description": "Type 2 DM with diabetic nephropathy", "category": "endocrine"},
    "E11.22": {"description": "Type 2 DM with diabetic CKD", "category": "endocrine"},
    "E11.40": {"description": "Type 2 DM with diabetic neuropathy", "category": "endocrine"},
    "E11.51": {"description": "Type 2 DM with diabetic peripheral angiopathy", "category": "endocrine"},
    "E10.9": {"description": "Type 1 diabetes mellitus without complications", "category": "endocrine"},

    # Heart Failure
    "I50.9": {"description": "Heart failure, unspecified", "category": "cardiovascular"},
    "I50.1": {"description": "Left ventricular failure, unspecified", "category": "cardiovascular"},
    "I50.20": {"description": "Unspecified systolic (congestive) heart failure", "category": "cardiovascular"},
    "I50.30": {"description": "Unspecified diastolic (congestive) heart failure", "category": "cardiovascular"},
    "I50.40": {"description": "Combined systolic and diastolic heart failure", "category": "cardiovascular"},

    # Respiratory
    "J44.9": {"description": "COPD, unspecified", "category": "respiratory"},
    "J44.1": {"description": "COPD with acute exacerbation", "category": "respiratory"},
    "J45.20": {"description": "Mild intermittent asthma, uncomplicated", "category": "respiratory"},
    "J45.40": {"description": "Moderate persistent asthma, uncomplicated", "category": "respiratory"},
    "J18.9": {"description": "Pneumonia, unspecified organism", "category": "respiratory"},

    # Signs/Symptoms
    "R00.0": {"description": "Tachycardia, unspecified", "category": "symptoms"},
    "R00.1": {"description": "Bradycardia, unspecified", "category": "symptoms"},
    "R09.02": {"description": "Hypoxemia", "category": "symptoms"},
    "R50.9": {"description": "Fever, unspecified", "category": "symptoms"},
    "R06.02": {"description": "Shortness of breath", "category": "symptoms"},
    "R07.9": {"description": "Chest pain, unspecified", "category": "symptoms"},

    # Kidney
    "N18.1": {"description": "Chronic kidney disease, stage 1", "category": "renal"},
    "N18.2": {"description": "Chronic kidney disease, stage 2", "category": "renal"},
    "N18.3": {"description": "Chronic kidney disease, stage 3", "category": "renal"},
    "N18.4": {"description": "Chronic kidney disease, stage 4", "category": "renal"},
    "N18.5": {"description": "Chronic kidney disease, stage 5", "category": "renal"},
    "N18.6": {"description": "End-stage renal disease", "category": "renal"},
}

# CPT Code Database (simplified)
CPT_CODES = {
    # E/M Codes
    "99212": {"description": "Office visit, established patient, straightforward", "category": "evaluation"},
    "99213": {"description": "Office visit, established patient, low complexity", "category": "evaluation"},
    "99214": {"description": "Office visit, established patient, moderate complexity", "category": "evaluation"},
    "99215": {"description": "Office visit, established patient, high complexity", "category": "evaluation"},
    "99243": {"description": "Office consultation, moderate complexity", "category": "consultation"},
    "99244": {"description": "Office consultation, high complexity", "category": "consultation"},

    # Chronic Care / Remote Monitoring
    "99457": {"description": "Remote physiologic monitoring treatment mgmt, 20 min", "category": "remote_monitoring"},
    "99473": {"description": "Self-measured blood pressure using validated device", "category": "remote_monitoring"},
    "99490": {"description": "Chronic care management, 20 min/month", "category": "care_management"},

    # Lab Codes
    "80048": {"description": "Basic metabolic panel", "category": "laboratory"},
    "80053": {"description": "Comprehensive metabolic panel", "category": "laboratory"},
    "85025": {"description": "CBC with differential", "category": "laboratory"},
    "83036": {"description": "Hemoglobin A1c", "category": "laboratory"},
    "82565": {"description": "Creatinine, blood", "category": "laboratory"},
    "82947": {"description": "Glucose, blood", "category": "laboratory"},
    "84443": {"description": "TSH", "category": "laboratory"},
    "80061": {"description": "Lipid panel", "category": "laboratory"},
    "83519": {"description": "Immunoassay, analyte, quantitative (IgE)", "category": "laboratory"},
    "82040": {"description": "Albumin, serum", "category": "laboratory"},
    "83880": {"description": "Natriuretic peptide (BNP/NT-proBNP)", "category": "laboratory"},
    "84100": {"description": "Phosphorus, blood", "category": "laboratory"},
    "82374": {"description": "Carbon dioxide (bicarbonate)", "category": "laboratory"},
    "81001": {"description": "Urinalysis, automated, with microscopy", "category": "laboratory"},
    "87040": {"description": "Blood culture", "category": "laboratory"},

    # Cardiology
    "93000": {"description": "ECG with interpretation", "category": "cardiology"},
    "93015": {"description": "Cardiovascular stress test", "category": "cardiology"},
    "93306": {"description": "Echocardiogram, complete", "category": "cardiology"},
    "93350": {"description": "Stress echocardiogram", "category": "cardiology"},
    "93452": {"description": "Left heart catheterization", "category": "cardiology"},
    "93279": {"description": "Device evaluation, single lead pacemaker", "category": "cardiology"},

    # Pulmonary
    "94010": {"description": "Spirometry", "category": "pulmonary"},
    "94060": {"description": "Bronchodilator response spirometry", "category": "pulmonary"},
    "94150": {"description": "Vital capacity", "category": "pulmonary"},
    "94664": {"description": "Aerosol/vapor inhalation treatment", "category": "pulmonary"},
    "94640": {"description": "Pressurized inhalation treatment (nebulizer)", "category": "pulmonary"},

    # Imaging
    "71046": {"description": "Chest X-ray, 2 views", "category": "imaging"},
    "71250": {"description": "CT chest without contrast", "category": "imaging"},
    "71260": {"description": "CT chest with contrast", "category": "imaging"},
    "74176": {"description": "CT abdomen/pelvis without contrast", "category": "imaging"},

    # Procedures / Counseling
    "99401": {"description": "Preventive counseling, 15 min", "category": "counseling"},
    "99402": {"description": "Preventive counseling, 30 min", "category": "counseling"},
    "G0108": {"description": "Diabetes self-management training", "category": "education"},
    "G0109": {"description": "DSMT, group session", "category": "education"},
    "G0447": {"description": "Behavioral counseling for obesity, 15 min", "category": "counseling"},
    "92004": {"description": "Comprehensive eye exam, new patient", "category": "ophthalmology"},
    "96127": {"description": "Brief emotional/behavioral assessment", "category": "psychiatry"},
    "90832": {"description": "Psychotherapy, 30 min", "category": "psychiatry"},
    "90834": {"description": "Psychotherapy, 45 min", "category": "psychiatry"},
    "96160": {"description": "Health risk assessment instrument", "category": "preventive"},
}


class CodingAgent(BaseAgent):
    """
    Clinical Coding Agent
    - Suggests ICD-10 codes for diagnoses
    - Suggests CPT codes for procedures
    - Validates code accuracy
    - Ensures specificity requirements
    """

    def __init__(self):
        super().__init__(
            agent_id="coding",
            name="Clinical Coder",
            description="Suggests and validates ICD-10 and CPT codes",
            version="1.0.0"
        )
        self.specialties = ["medical_coding", "billing", "compliance"]

        # Initialize LLM for enhanced code suggestions
        self.llm: Optional[ClinicalLLM] = None
        if USE_LLM:
            try:
                self.llm = get_clinical_llm()
            except Exception:
                pass

    def _setup_capabilities(self):
        self.capabilities = [
            AgentCapability(
                name="suggest_icd10",
                description="Suggest ICD-10 codes for diagnoses",
                input_schema={"diagnoses": "list", "findings": "list"},
                output_schema={"codes": "list[{code, description, confidence}]"}
            ),
            AgentCapability(
                name="suggest_cpt",
                description="Suggest CPT codes for treatments/procedures",
                input_schema={"treatments": "list"},
                output_schema={"codes": "list[{code, description}]"}
            ),
            AgentCapability(
                name="validate_codes",
                description="Validate and verify code accuracy",
                input_schema={"icd10_codes": "list", "cpt_codes": "list"},
                output_schema={"valid": "list", "invalid": "list", "suggestions": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Generate and validate clinical codes"""
        reasoning_steps = []
        warnings = []

        diagnoses = task.get("diagnoses", []) if task else []
        treatments = task.get("treatments", []) if task else []
        findings = task.get("findings", []) if task else []

        # Step 1: Suggest ICD-10 codes
        reasoning_steps.append("Step 1: Analyzing diagnoses for ICD-10 coding...")
        icd10_codes = self._suggest_icd10_codes(diagnoses, findings, context)

        # Step 2: Suggest CPT codes
        reasoning_steps.append("Step 2: Analyzing treatments for CPT coding...")
        cpt_codes = self._suggest_cpt_codes(treatments)

        # Step 3: Validate code specificity
        reasoning_steps.append("Step 3: Checking code specificity requirements...")
        specificity_warnings = self._check_specificity(icd10_codes, context)
        warnings.extend(specificity_warnings)

        # Step 4: Check for HCC (Hierarchical Condition Categories)
        reasoning_steps.append("Step 4: Identifying HCC-relevant codes...")
        hcc_notes = self._check_hcc_relevance(icd10_codes)
        for note in hcc_notes:
            reasoning_steps.append(f"  HCC: {note}")

        # Step 5: Use LLM for enhanced coding if available
        if self.llm and diagnoses:
            reasoning_steps.append("Step 5: LLM-enhanced code verification...")
            enhanced = await self._llm_enhance_codes(diagnoses, icd10_codes)
            if enhanced:
                for suggestion in enhanced:
                    if suggestion not in [c["code"] for c in icd10_codes]:
                        icd10_codes.append(suggestion)
                        reasoning_steps.append(f"  Added: {suggestion['code']} - {suggestion['description']}")

        return self._create_output(
            icd10_codes=icd10_codes,
            cpt_codes=cpt_codes,
            confidence=0.9 if icd10_codes else 0.0,
            reasoning=reasoning_steps,
            warnings=warnings
        )

    def _suggest_icd10_codes(
        self,
        diagnoses: List,
        findings: List[ClinicalFinding],
        context: PatientContext
    ) -> List[Dict]:
        """Suggest ICD-10 codes based on diagnoses and findings"""
        codes = []

        # Process diagnoses
        for dx in diagnoses:
            if isinstance(dx, dict):
                icd10 = dx.get("icd10_code", "")
                diagnosis = dx.get("diagnosis", "")
            elif hasattr(dx, "icd10_code"):
                icd10 = dx.icd10_code
                diagnosis = dx.diagnosis
            else:
                continue

            if icd10 and icd10 in ICD10_CODES:
                codes.append({
                    "code": icd10,
                    "description": ICD10_CODES[icd10]["description"],
                    "category": ICD10_CODES[icd10]["category"],
                    "confidence": 0.9
                })
            elif diagnosis:
                # Try to match by description
                matched = self._match_diagnosis_to_code(diagnosis)
                if matched:
                    codes.append(matched)

        # Process findings for symptom codes
        for finding in findings:
            if isinstance(finding, dict):
                name = finding.get("name", "").lower()
                status = finding.get("status", "")
            elif hasattr(finding, "name"):
                name = finding.name.lower()
                status = finding.status
            else:
                continue

            if status in ["abnormal", "critical"]:
                symptom_code = self._finding_to_icd10(name)
                if symptom_code and symptom_code["code"] not in [c["code"] for c in codes]:
                    codes.append(symptom_code)

        return codes

    def _match_diagnosis_to_code(self, diagnosis: str) -> Optional[Dict]:
        """Match a diagnosis description to an ICD-10 code"""
        diagnosis_lower = diagnosis.lower()

        # Mapping of keywords to codes
        keyword_map = {
            "hypertension": "I10",
            "diabetes type 2": "E11.9",
            "type 2 diabetes": "E11.9",
            "heart failure": "I50.9",
            "copd": "J44.9",
            "pneumonia": "J18.9",
            "tachycardia": "R00.0",
            "bradycardia": "R00.1",
            "hypoxemia": "R09.02",
            "fever": "R50.9",
            "chest pain": "R07.9",
        }

        for keyword, code in keyword_map.items():
            if keyword in diagnosis_lower:
                return {
                    "code": code,
                    "description": ICD10_CODES[code]["description"],
                    "category": ICD10_CODES[code]["category"],
                    "confidence": 0.8
                }

        return None

    def _finding_to_icd10(self, finding_name: str) -> Optional[Dict]:
        """Convert a clinical finding to symptom ICD-10 code"""
        symptom_map = {
            "tachycardia": "R00.0",
            "bradycardia": "R00.1",
            "hypoxemia": "R09.02",
            "fever": "R50.9",
            "temperature": "R50.9",
            "shortness of breath": "R06.02",
            "chest pain": "R07.9",
            "blood pressure": None,  # Needs context
        }

        for symptom, code in symptom_map.items():
            if symptom in finding_name.lower() and code:
                return {
                    "code": code,
                    "description": ICD10_CODES[code]["description"],
                    "category": "symptoms",
                    "confidence": 0.75
                }

        return None

    def _suggest_cpt_codes(self, treatments: List) -> List[Dict]:
        """Suggest CPT codes based on treatments and backfill missing codes"""
        codes = []

        for i, tx in enumerate(treatments):
            if isinstance(tx, dict):
                cpt = tx.get("cpt_code")
                desc = tx.get("description", "")
                tx_type = tx.get("type", tx.get("treatment_type", ""))
            elif hasattr(tx, "cpt_code"):
                cpt = tx.cpt_code
                desc = tx.description
                tx_type = tx.treatment_type
            else:
                continue

            if cpt and cpt in CPT_CODES:
                codes.append({
                    "code": cpt,
                    "description": CPT_CODES[cpt]["description"],
                    "category": CPT_CODES[cpt]["category"],
                    "_treatment_index": i,
                })
            elif desc:
                # Try to match by description and backfill
                matched = self._match_treatment_to_cpt(desc, tx_type)
                if matched:
                    matched["_treatment_index"] = i
                    codes.append(matched)
                    # Backfill the CPT code onto the treatment
                    if isinstance(tx, dict):
                        tx["cpt_code"] = matched["code"]
                    elif hasattr(tx, "cpt_code"):
                        tx.cpt_code = matched["code"]

        # Deduplicate by code for the summary list
        seen = set()
        unique_codes = []
        for c in codes:
            code = c["code"]
            if code not in seen:
                seen.add(code)
                unique_codes.append({k: v for k, v in c.items() if k != "_treatment_index"})

        return unique_codes

    def _match_treatment_to_cpt(self, description: str, tx_type: str) -> Optional[Dict]:
        """Match treatment description to CPT code"""
        desc_lower = description.lower()

        # Procedure / lab matching
        procedure_map = {
            "basic metabolic panel": "80048",
            "metabolic panel": "80053",
            "cbc": "85025",
            "hemoglobin a1c": "83036",
            "hba1c": "83036",
            "a1c": "83036",
            "ecg": "93000",
            "ekg": "93000",
            "12-lead": "93000",
            "electrocardiogram": "93000",
            "echocardiogram": "93306",
            "echo": "93306",
            "stress test": "93015",
            "stress echo": "93350",
            "chest x-ray": "71046",
            "chest xray": "71046",
            "ct chest": "71250",
            "lipid panel": "80061",
            "tsh": "84443",
            "spirometry": "94010",
            "bronchodilator": "94060",
            "nebulizer": "94640",
            "inhalation treatment": "94664",
            "urinalysis": "81001",
            "blood culture": "87040",
            "creatinine": "82565",
            "glucose": "82947",
            "ige": "83519",
            "albumin": "82040",
            "bnp": "83880",
            "nt-probnp": "83880",
            "natriuretic": "83880",
        }

        for keyword, code in procedure_map.items():
            if keyword in desc_lower and code in CPT_CODES:
                return {
                    "code": code,
                    "description": CPT_CODES[code]["description"],
                    "category": CPT_CODES[code]["category"]
                }

        # Type-based fallbacks for treatments without specific procedure codes
        type_map = {
            "medication": "99214",      # E&M visit for medication management
            "referral": "99243",        # Office consultation
            "counseling": "99401",      # Preventive counseling
        }

        # Specific pattern matches for monitoring/management
        if tx_type == "monitoring":
            if "blood pressure" in desc_lower or "bp monitor" in desc_lower:
                return {"code": "99473", "description": CPT_CODES["99473"]["description"], "category": CPT_CODES["99473"]["category"]}
            if "weight" in desc_lower or "remote" in desc_lower:
                return {"code": "99457", "description": CPT_CODES["99457"]["description"], "category": CPT_CODES["99457"]["category"]}
            return {"code": "99212", "description": CPT_CODES["99212"]["description"], "category": CPT_CODES["99212"]["category"]}

        # Counseling patterns
        if "counseling" in desc_lower or "education" in desc_lower:
            if "diabet" in desc_lower:
                return {"code": "G0108", "description": CPT_CODES["G0108"]["description"], "category": CPT_CODES["G0108"]["category"]}
            if "obesity" in desc_lower or "weight" in desc_lower:
                return {"code": "G0447", "description": CPT_CODES["G0447"]["description"], "category": CPT_CODES["G0447"]["category"]}
            return {"code": "99401", "description": CPT_CODES["99401"]["description"], "category": CPT_CODES["99401"]["category"]}

        # Psychotherapy
        if "psychotherapy" in desc_lower or "cognitive behavioral" in desc_lower or "cbt" in desc_lower:
            return {"code": "90834", "description": CPT_CODES["90834"]["description"], "category": CPT_CODES["90834"]["category"]}
        if "anxiety" in desc_lower and "assessment" in desc_lower:
            return {"code": "96127", "description": CPT_CODES["96127"]["description"], "category": CPT_CODES["96127"]["category"]}

        # Fall back to type-based default
        if tx_type in type_map:
            code = type_map[tx_type]
            if code in CPT_CODES:
                return {"code": code, "description": CPT_CODES[code]["description"], "category": CPT_CODES[code]["category"]}

        return None

    def _check_specificity(self, codes: List[Dict], context: PatientContext) -> List[str]:
        """Check if codes meet specificity requirements"""
        warnings = []

        for code_info in codes:
            code = code_info.get("code", "")

            # Check for unspecified codes that could be more specific
            if code == "I10" and context.conditions:
                # Check if there's heart or kidney involvement
                conditions = [c.get("display", "").lower() for c in context.conditions if c and isinstance(c, dict)]
                if any("heart" in c or "cardiac" in c for c in conditions):
                    warnings.append(f"Consider I11.9 (hypertensive heart disease) instead of {code}")
                if any("kidney" in c or "renal" in c for c in conditions):
                    warnings.append(f"Consider I12.9 (hypertensive CKD) instead of {code}")

            if code == "E11.9":
                # Check for diabetes complications
                conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]
                if any("nephropathy" in c or "kidney" in c for c in conditions):
                    warnings.append(f"Consider E11.21 (DM with nephropathy) instead of {code}")
                if any("neuropathy" in c for c in conditions):
                    warnings.append(f"Consider E11.40 (DM with neuropathy) instead of {code}")

        return warnings

    def _check_hcc_relevance(self, codes: List[Dict]) -> List[str]:
        """Identify HCC-relevant codes for risk adjustment"""
        hcc_notes = []

        # HCC-relevant categories
        hcc_categories = {
            "E11": "Diabetes HCC - affects risk adjustment",
            "I50": "Heart Failure HCC - affects risk adjustment",
            "N18.4": "CKD Stage 4 HCC - affects risk adjustment",
            "N18.5": "CKD Stage 5 HCC - affects risk adjustment",
            "J44": "COPD HCC - affects risk adjustment",
        }

        for code_info in codes:
            code = code_info.get("code", "")
            for hcc_prefix, note in hcc_categories.items():
                if code.startswith(hcc_prefix):
                    hcc_notes.append(f"{code}: {note}")

        return hcc_notes

    async def _llm_enhance_codes(self, diagnoses: List, existing_codes: List[Dict]) -> List[Dict]:
        """Use LLM to suggest additional relevant codes"""
        if not self.llm:
            return []

        try:
            diagnoses_text = ", ".join([
                d.get("diagnosis", "") if isinstance(d, dict) else str(d)
                for d in diagnoses
            ])

            prompt = f"""Given these diagnoses: {diagnoses_text}

Current ICD-10 codes assigned: {[c['code'] for c in existing_codes]}

Suggest any additional ICD-10 codes that should be captured for complete documentation.
Only suggest codes you are confident about.

Return JSON:
{{
    "additional_codes": [
        {{"code": "X00.0", "description": "...", "rationale": "..."}}
    ]
}}"""

            response = await self.llm.generate(
                prompt=prompt,
                task_type="icd10_coding",
                json_mode=True
            )

            content = response["content"]
            import json
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(content[start:end])
                return [
                    {
                        "code": c.get("code"),
                        "description": c.get("description", ""),
                        "category": "llm_suggested",
                        "confidence": 0.7
                    }
                    for c in data.get("additional_codes", [])
                    if c.get("code") in ICD10_CODES  # Only accept valid codes
                ]

        except Exception:
            pass

        return []


# Singleton instance
coding_agent = CodingAgent()
