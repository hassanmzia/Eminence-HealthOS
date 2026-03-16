"""
Oncology Agent
Analyzes cancer-related findings, staging, tumor markers, and treatment planning.
Provides comprehensive oncological assessment and recommendations.
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


# Cancer staging criteria (simplified TNM)
CANCER_STAGING = {
    "breast": {
        "stage_0": {"description": "Ductal carcinoma in situ (DCIS)", "treatment": "Surgery ± radiation"},
        "stage_I": {"description": "Tumor ≤2cm, no lymph nodes", "treatment": "Surgery, consider adjuvant therapy"},
        "stage_II": {"description": "Tumor 2-5cm or lymph node positive", "treatment": "Surgery + adjuvant chemotherapy/radiation"},
        "stage_III": {"description": "Locally advanced, multiple lymph nodes", "treatment": "Neoadjuvant chemotherapy + surgery + radiation"},
        "stage_IV": {"description": "Metastatic disease", "treatment": "Systemic therapy, palliative care"}
    },
    "lung": {
        "stage_I": {"description": "Tumor confined to lung, no nodes", "treatment": "Surgery if operable"},
        "stage_II": {"description": "Larger tumor or hilar nodes", "treatment": "Surgery + adjuvant chemotherapy"},
        "stage_III": {"description": "Mediastinal involvement", "treatment": "Chemoradiation ± immunotherapy"},
        "stage_IV": {"description": "Metastatic disease", "treatment": "Systemic therapy, targeted/immunotherapy"}
    },
    "colorectal": {
        "stage_0": {"description": "Carcinoma in situ", "treatment": "Endoscopic resection"},
        "stage_I": {"description": "Through muscularis propria", "treatment": "Surgery"},
        "stage_II": {"description": "Through bowel wall, no nodes", "treatment": "Surgery ± adjuvant chemo (high risk)"},
        "stage_III": {"description": "Lymph node positive", "treatment": "Surgery + adjuvant chemotherapy"},
        "stage_IV": {"description": "Metastatic disease", "treatment": "Systemic therapy, consider resection"}
    },
    "prostate": {
        "low_risk": {"description": "Gleason ≤6, PSA <10, T1-T2a", "treatment": "Active surveillance or local therapy"},
        "intermediate_risk": {"description": "Gleason 7, PSA 10-20, T2b-T2c", "treatment": "Radiation or surgery"},
        "high_risk": {"description": "Gleason ≥8, PSA >20, T3+", "treatment": "Multimodal therapy"},
        "metastatic": {"description": "Distant metastases", "treatment": "Androgen deprivation + systemic therapy"}
    }
}

# Tumor markers and their significance
TUMOR_MARKERS = {
    "psa": {
        "name": "Prostate Specific Antigen",
        "cancer_type": "prostate",
        "unit": "ng/mL",
        "normal_high": 4.0,
        "elevated_threshold": 10.0,
        "highly_elevated": 20.0,
        "icd10": "C61",
        "interpretations": {
            "elevated": "Elevated PSA - consider prostate biopsy",
            "highly_elevated": "Significantly elevated PSA - high suspicion for prostate cancer"
        }
    },
    "cea": {
        "name": "Carcinoembryonic Antigen",
        "cancer_type": "colorectal",
        "unit": "ng/mL",
        "normal_high": 3.0,
        "elevated_threshold": 10.0,
        "highly_elevated": 50.0,
        "icd10": "C18.9",
        "interpretations": {
            "elevated": "Elevated CEA - monitor for colorectal cancer recurrence",
            "highly_elevated": "Markedly elevated CEA - suggests advanced/metastatic disease"
        }
    },
    "ca125": {
        "name": "Cancer Antigen 125",
        "cancer_type": "ovarian",
        "unit": "U/mL",
        "normal_high": 35.0,
        "elevated_threshold": 65.0,
        "highly_elevated": 200.0,
        "icd10": "C56.9",
        "interpretations": {
            "elevated": "Elevated CA-125 - evaluate for ovarian pathology",
            "highly_elevated": "Significantly elevated CA-125 - high suspicion for ovarian cancer"
        }
    },
    "ca19_9": {
        "name": "Cancer Antigen 19-9",
        "cancer_type": "pancreatic",
        "unit": "U/mL",
        "normal_high": 37.0,
        "elevated_threshold": 100.0,
        "highly_elevated": 1000.0,
        "icd10": "C25.9",
        "interpretations": {
            "elevated": "Elevated CA 19-9 - evaluate for pancreaticobiliary pathology",
            "highly_elevated": "Markedly elevated CA 19-9 - suggests pancreatic/biliary malignancy"
        }
    },
    "afp": {
        "name": "Alpha-Fetoprotein",
        "cancer_type": "liver",
        "unit": "ng/mL",
        "normal_high": 10.0,
        "elevated_threshold": 200.0,
        "highly_elevated": 500.0,
        "icd10": "C22.0",
        "interpretations": {
            "elevated": "Elevated AFP - evaluate for hepatocellular carcinoma or germ cell tumor",
            "highly_elevated": "Markedly elevated AFP - high suspicion for HCC"
        }
    },
    "beta_hcg": {
        "name": "Beta Human Chorionic Gonadotropin",
        "cancer_type": "germ_cell",
        "unit": "mIU/mL",
        "normal_high": 5.0,
        "elevated_threshold": 10.0,
        "highly_elevated": 1000.0,
        "icd10": "C62.90",
        "interpretations": {
            "elevated": "Elevated beta-hCG - evaluate for pregnancy or germ cell tumor",
            "highly_elevated": "Markedly elevated beta-hCG - suggests germ cell neoplasm"
        }
    },
    "ldh": {
        "name": "Lactate Dehydrogenase",
        "cancer_type": "lymphoma",
        "unit": "U/L",
        "normal_high": 250.0,
        "elevated_threshold": 500.0,
        "highly_elevated": 1000.0,
        "icd10": "C85.90",
        "interpretations": {
            "elevated": "Elevated LDH - nonspecific, consider lymphoma or tissue damage",
            "highly_elevated": "Markedly elevated LDH - suggests aggressive lymphoma or widespread disease"
        }
    }
}

# Cancer screening recommendations by risk
SCREENING_GUIDELINES = {
    "breast": {
        "average_risk": {"start_age": 40, "modality": "Mammography", "interval": "annually"},
        "high_risk": {"start_age": 30, "modality": "Mammography + MRI", "interval": "annually"}
    },
    "colorectal": {
        "average_risk": {"start_age": 45, "modality": "Colonoscopy", "interval": "10 years"},
        "high_risk": {"start_age": 40, "modality": "Colonoscopy", "interval": "5 years"}
    },
    "lung": {
        "high_risk": {"start_age": 50, "modality": "Low-dose CT", "interval": "annually",
                     "criteria": "20+ pack-years smoking history"}
    },
    "prostate": {
        "average_risk": {"start_age": 50, "modality": "PSA + DRE", "interval": "1-2 years"},
        "high_risk": {"start_age": 45, "modality": "PSA + DRE", "interval": "annually"}
    },
    "cervical": {
        "average_risk": {"start_age": 21, "modality": "Pap smear ± HPV", "interval": "3-5 years"}
    }
}


class OncologyAgent(BaseAgent):
    """
    AI Oncology Agent
    - Analyzes cancer-related findings and tumor markers
    - Provides cancer staging assessments
    - Identifies suspicious findings requiring oncology workup
    - Recommends appropriate screening based on risk factors
    - Suggests treatment pathways based on cancer type and stage
    """

    def __init__(self):
        super().__init__(
            agent_id="oncology",
            name="Oncology Specialist",
            description="Analyzes cancer-related findings and provides oncological assessment",
            version="1.0.0"
        )
        self.specialties = ["oncology", "cancer", "tumor", "chemotherapy", "staging"]

        if USE_LLM:
            try:
                self.llm = get_clinical_llm()
            except:
                self.llm = None
        else:
            self.llm = None

    def _setup_capabilities(self):
        self.capabilities = [
            AgentCapability(
                name="analyze_tumor_markers",
                description="Analyze tumor marker levels and provide interpretation",
                input_schema={"markers": "dict"},
                output_schema={"interpretations": "list", "recommendations": "list"}
            ),
            AgentCapability(
                name="cancer_staging",
                description="Provide cancer staging assessment based on available data",
                input_schema={"cancer_type": "string", "findings": "dict"},
                output_schema={"stage": "string", "treatment_recommendations": "list"}
            ),
            AgentCapability(
                name="screening_recommendations",
                description="Recommend cancer screening based on risk factors",
                input_schema={"age": "int", "risk_factors": "list"},
                output_schema={"screenings": "list"}
            ),
            AgentCapability(
                name="suspicious_findings_review",
                description="Review findings for potential malignancy",
                input_schema={"findings": "list"},
                output_schema={"suspicion_level": "string", "workup": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Process oncology-related data and provide assessment"""
        reasoning_steps = []
        findings = []
        diagnoses = []
        treatments = []
        warnings = []

        task = task or {}

        reasoning_steps.append("=== Oncology Analysis ===")
        reasoning_steps.append(f"Patient: {context.name}, Age: {context.age}, Sex: {context.sex}")

        # Step 1: Analyze tumor markers from labs
        reasoning_steps.append("\n--- Tumor Marker Analysis ---")
        marker_findings, marker_diagnoses, marker_warnings = self._analyze_tumor_markers(context, reasoning_steps)
        findings.extend(marker_findings)
        diagnoses.extend(marker_diagnoses)
        warnings.extend(marker_warnings)

        # Step 2: Review existing conditions for cancer-related diagnoses
        reasoning_steps.append("\n--- Cancer History Review ---")
        cancer_findings, cancer_diagnoses = self._review_cancer_history(context, reasoning_steps)
        findings.extend(cancer_findings)
        diagnoses.extend(cancer_diagnoses)

        # Step 3: If cancer diagnosis exists, assess staging
        cancer_types = task.get("cancer_diagnoses", [])
        if cancer_types or cancer_diagnoses:
            reasoning_steps.append("\n--- Staging Assessment ---")
            staging_findings, staging_treatments = self._assess_staging(
                context, cancer_types or [d.diagnosis for d in cancer_diagnoses], reasoning_steps
            )
            findings.extend(staging_findings)
            treatments.extend(staging_treatments)

        # Step 4: Review suspicious findings from other agents
        suspicious_findings = task.get("suspicious_findings", [])
        if suspicious_findings:
            reasoning_steps.append("\n--- Suspicious Findings Review ---")
            susp_findings, susp_diagnoses, susp_warnings = self._review_suspicious_findings(
                suspicious_findings, reasoning_steps
            )
            findings.extend(susp_findings)
            diagnoses.extend(susp_diagnoses)
            warnings.extend(susp_warnings)

        # Step 5: Provide screening recommendations
        reasoning_steps.append("\n--- Screening Recommendations ---")
        screening_treatments = self._recommend_screening(context, reasoning_steps)
        treatments.extend(screening_treatments)

        # Determine if requires human review
        requires_review = len(warnings) > 0 or any(f.status == "critical" for f in findings) or len(cancer_diagnoses) > 0
        review_reason = "Oncology findings require specialist review" if requires_review else None

        return self._create_output(
            findings=findings,
            diagnoses=diagnoses,
            treatments=treatments,
            confidence=0.85 if diagnoses else 0.6,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    def _analyze_tumor_markers(self, context: PatientContext, reasoning: List[str]) -> tuple:
        """Analyze tumor marker levels from labs"""
        findings = []
        diagnoses = []
        warnings = []

        if not context.labs:
            reasoning.append("  No laboratory data available for tumor marker analysis")
            return findings, diagnoses, warnings

        # Create lab value map
        lab_values = {}
        for lab in context.labs:
            if not lab or not isinstance(lab, dict):
                continue
            name = lab.get("display", lab.get("name", "")).lower()
            code = lab.get("code", "").lower()
            value = lab.get("value")
            if value is not None:
                lab_values[name] = value
                lab_values[code] = value

        # Check each tumor marker
        for marker_key, marker_info in TUMOR_MARKERS.items():
            marker_name = marker_info["name"].lower()
            value = None

            # Try to find marker in labs
            for lab_key in [marker_key, marker_name, marker_info["name"]]:
                if lab_key.lower() in lab_values:
                    value = lab_values[lab_key.lower()]
                    break

            if value is None:
                continue

            if not isinstance(value, (int, float)):
                continue

            # Evaluate marker level
            status = "normal"
            interpretation = ""

            if value > marker_info["highly_elevated"]:
                status = "critical"
                interpretation = marker_info["interpretations"]["highly_elevated"]
                warnings.append(f"CRITICAL TUMOR MARKER: {marker_info['name']} = {value} {marker_info['unit']}")
            elif value > marker_info["elevated_threshold"]:
                status = "abnormal"
                interpretation = marker_info["interpretations"]["elevated"]
            elif value > marker_info["normal_high"]:
                status = "abnormal"
                interpretation = f"Mildly elevated {marker_info['name']} - monitor closely"

            if status != "normal":
                reasoning.append(f"  {marker_info['name']}: {value} {marker_info['unit']} - {status.upper()}")
                reasoning.append(f"    -> {interpretation}")

                finding = ClinicalFinding(
                    type="tumor_marker",
                    name=marker_info["name"],
                    value=f"{value} {marker_info['unit']}",
                    status=status,
                    interpretation=interpretation,
                    source="Oncology - Tumor Marker Analysis"
                )
                findings.append(finding)

                if status == "critical":
                    diagnoses.append(DiagnosisRecommendation(
                        diagnosis=f"Elevated {marker_info['name']} - {marker_info['cancer_type'].title()} cancer workup needed",
                        icd10_code=marker_info["icd10"],
                        confidence=0.7,  # Markers are not diagnostic alone
                        supporting_findings=[finding],
                        rationale=interpretation
                    ))

        if not findings:
            reasoning.append("  No elevated tumor markers identified")

        return findings, diagnoses, warnings

    def _review_cancer_history(self, context: PatientContext, reasoning: List[str]) -> tuple:
        """Review patient's cancer history from conditions"""
        findings = []
        diagnoses = []

        if not context.conditions:
            reasoning.append("  No existing conditions to review")
            return findings, diagnoses

        cancer_keywords = ["cancer", "carcinoma", "malignant", "neoplasm", "tumor", "lymphoma", "leukemia", "melanoma", "sarcoma"]

        for condition in context.conditions:
            if not condition or not isinstance(condition, dict):
                continue

            display = condition.get("display", "").lower()
            code = condition.get("code", "")

            # Check if this is a cancer-related condition
            if any(kw in display for kw in cancer_keywords) or (code and code.startswith("C")):
                reasoning.append(f"  Cancer history: {condition.get('display', 'Unknown')}")

                finding = ClinicalFinding(
                    type="cancer_history",
                    name="Known Cancer Diagnosis",
                    value=condition.get("display", "Cancer NOS"),
                    status="critical",
                    interpretation=f"Patient has history of {condition.get('display', 'cancer')}",
                    source="Medical History"
                )
                findings.append(finding)

                diagnoses.append(DiagnosisRecommendation(
                    diagnosis=condition.get("display", "Malignant neoplasm"),
                    icd10_code=code if code.startswith("C") else "C80.1",
                    confidence=0.95,  # Known diagnosis
                    supporting_findings=[finding],
                    rationale="Documented cancer diagnosis in patient history"
                ))

        if not findings:
            reasoning.append("  No cancer history identified")

        return findings, diagnoses

    def _assess_staging(self, context: PatientContext, cancer_types: List[str], reasoning: List[str]) -> tuple:
        """Assess cancer staging based on available data"""
        findings = []
        treatments = []

        for cancer_type in cancer_types:
            cancer_type_lower = cancer_type.lower()

            # Determine cancer category
            category = None
            for cat in CANCER_STAGING.keys():
                if cat in cancer_type_lower:
                    category = cat
                    break

            if not category:
                reasoning.append(f"  Unable to stage: {cancer_type} (no staging criteria available)")
                continue

            # Simplified staging based on available context
            # In production, this would use TNM data from pathology
            staging_data = CANCER_STAGING[category]

            # Default to unknown stage, recommend staging workup
            reasoning.append(f"  {cancer_type}:")
            reasoning.append(f"    Staging workup recommended")

            finding = ClinicalFinding(
                type="staging",
                name=f"{category.title()} Cancer Staging",
                value="Staging workup recommended",
                status="abnormal",
                interpretation=f"Complete staging workup needed for {cancer_type}",
                source="Oncology Assessment"
            )
            findings.append(finding)

            # Add staging workup recommendations
            treatments.append(TreatmentRecommendation(
                type="diagnostic",
                description=f"Complete staging workup for {cancer_type}",
                priority="urgent",
                rationale="Required for treatment planning"
            ))

            if category in ["breast", "lung", "colorectal"]:
                treatments.append(TreatmentRecommendation(
                    type="imaging",
                    description="PET-CT scan for staging",
                    priority="urgent",
                    rationale=f"Staging imaging for {cancer_type}",
                    cpt_code="78815"
                ))

            treatments.append(TreatmentRecommendation(
                type="referral",
                description="Medical oncology consultation",
                priority="urgent",
                rationale=f"Multidisciplinary care planning for {cancer_type}"
            ))

            treatments.append(TreatmentRecommendation(
                type="referral",
                description="Tumor board discussion",
                priority="routine",
                rationale="Multidisciplinary treatment planning"
            ))

        return findings, treatments

    def _review_suspicious_findings(self, suspicious_findings: List[dict], reasoning: List[str]) -> tuple:
        """Review suspicious findings from other agents"""
        findings = []
        diagnoses = []
        warnings = []

        for susp in suspicious_findings:
            if not susp or not isinstance(susp, dict):
                continue

            finding_type = susp.get("type", "unknown")
            description = susp.get("description", "")
            location = susp.get("location", "")
            suspicion_level = susp.get("suspicion_level", "low")

            reasoning.append(f"  Reviewing: {finding_type} - {description}")

            status = "critical" if suspicion_level == "high" else "abnormal"

            finding = ClinicalFinding(
                type="suspicious_finding",
                name=f"Suspicious {finding_type.title()}",
                value=description,
                status=status,
                interpretation=f"{suspicion_level.title()} suspicion for malignancy",
                source="Oncology Review"
            )
            findings.append(finding)

            if suspicion_level == "high":
                warnings.append(f"HIGH SUSPICION FOR MALIGNANCY: {description} in {location}")

                diagnoses.append(DiagnosisRecommendation(
                    diagnosis=f"Suspected malignancy - {location}",
                    icd10_code="D49.9",  # Neoplasm of unspecified behavior
                    confidence=0.6,
                    supporting_findings=[finding],
                    rationale=f"Suspicious finding: {description}"
                ))

        return findings, diagnoses, warnings

    def _recommend_screening(self, context: PatientContext, reasoning: List[str]) -> List[TreatmentRecommendation]:
        """Recommend cancer screening based on patient profile"""
        treatments = []

        age = context.age or 0
        sex = (context.sex or "").lower()

        # Determine risk level (simplified)
        conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]
        high_risk = any("family history" in c and "cancer" in c for c in conditions)

        reasoning.append(f"  Patient age: {age}, Sex: {sex}, High-risk features: {high_risk}")

        # Breast cancer screening
        if sex in ["female", "f"] or sex == "":
            guidelines = SCREENING_GUIDELINES["breast"]
            risk_level = "high_risk" if high_risk else "average_risk"
            guideline = guidelines[risk_level]

            if age >= guideline["start_age"]:
                reasoning.append(f"  -> Breast cancer screening: {guideline['modality']} {guideline['interval']}")
                treatments.append(TreatmentRecommendation(
                    type="screening",
                    description=f"{guideline['modality']} for breast cancer screening",
                    priority="routine",
                    rationale=f"Age {age}, {risk_level.replace('_', ' ')} - screen {guideline['interval']}",
                    cpt_code="77067"  # Bilateral mammography
                ))

        # Colorectal cancer screening
        guidelines = SCREENING_GUIDELINES["colorectal"]
        risk_level = "high_risk" if high_risk else "average_risk"
        guideline = guidelines[risk_level]

        if age >= guideline["start_age"]:
            reasoning.append(f"  -> Colorectal screening: {guideline['modality']} every {guideline['interval']}")
            treatments.append(TreatmentRecommendation(
                type="screening",
                description=f"{guideline['modality']} for colorectal cancer screening",
                priority="routine",
                rationale=f"Age {age}, {risk_level.replace('_', ' ')} - repeat every {guideline['interval']}",
                cpt_code="45378"
            ))

        # Prostate cancer screening (males)
        if sex in ["male", "m"]:
            guidelines = SCREENING_GUIDELINES["prostate"]
            risk_level = "high_risk" if high_risk else "average_risk"
            guideline = guidelines[risk_level]

            if age >= guideline["start_age"]:
                reasoning.append(f"  -> Prostate screening: {guideline['modality']} {guideline['interval']}")
                treatments.append(TreatmentRecommendation(
                    type="screening",
                    description=f"{guideline['modality']} for prostate cancer screening",
                    priority="routine",
                    rationale=f"Male age {age}, {risk_level.replace('_', ' ')}"
                ))

        # Lung cancer screening (high-risk smokers)
        smoking_history = any("smoking" in c or "tobacco" in c for c in conditions)
        if smoking_history and age >= 50:
            reasoning.append("  -> Lung cancer screening: Low-dose CT annually (smoking history)")
            treatments.append(TreatmentRecommendation(
                type="screening",
                description="Low-dose CT for lung cancer screening",
                priority="routine",
                rationale="Smoking history, eligible for lung cancer screening",
                cpt_code="71271"
            ))

        # Cervical cancer screening (females)
        if sex in ["female", "f"] and age >= 21:
            reasoning.append("  -> Cervical screening: Pap smear ± HPV testing")
            treatments.append(TreatmentRecommendation(
                type="screening",
                description="Pap smear with HPV co-testing for cervical cancer screening",
                priority="routine",
                rationale=f"Female age {age}, routine cervical screening"
            ))

        if not treatments:
            reasoning.append("  No specific cancer screening recommendations at this time")

        return treatments
