"""
Radiology Agent
Analyzes imaging studies (X-ray, CT, MRI) and provides diagnostic interpretations.
"""

import os
import json
from typing import List, Optional, Dict, Any
from .base_agent import (
    BaseAgent, PatientContext, AgentOutput, AgentCapability,
    ClinicalFinding, DiagnosisRecommendation
)

# Support both package import and direct execution
try:
    from ..llm import get_clinical_llm, ClinicalLLM
except ImportError:
    from llm import get_clinical_llm, ClinicalLLM

USE_LLM = os.getenv("USE_LLM", "true").lower() == "true"


# Common radiological findings patterns
XRAY_PATTERNS = {
    "chest": {
        "cardiomegaly": {
            "findings": ["Enlarged cardiac silhouette", "CTR > 0.5"],
            "icd10": "I51.7",
            "diagnosis": "Cardiomegaly",
            "severity": "abnormal"
        },
        "pneumonia": {
            "findings": ["Consolidation", "Air bronchograms", "Infiltrate"],
            "icd10": "J18.9",
            "diagnosis": "Pneumonia, unspecified",
            "severity": "abnormal"
        },
        "pleural_effusion": {
            "findings": ["Blunting of costophrenic angle", "Meniscus sign"],
            "icd10": "J90",
            "diagnosis": "Pleural effusion",
            "severity": "abnormal"
        },
        "pneumothorax": {
            "findings": ["Absent lung markings", "Visible pleural line"],
            "icd10": "J93.9",
            "diagnosis": "Pneumothorax",
            "severity": "critical"
        },
        "pulmonary_edema": {
            "findings": ["Kerley B lines", "Bat wing pattern", "Cephalization"],
            "icd10": "J81.0",
            "diagnosis": "Acute pulmonary edema",
            "severity": "critical"
        },
        "normal": {
            "findings": ["Clear lung fields", "Normal cardiac silhouette", "No acute abnormality"],
            "icd10": None,
            "diagnosis": "Normal chest X-ray",
            "severity": "normal"
        }
    },
    "abdominal": {
        "bowel_obstruction": {
            "findings": ["Dilated loops of bowel", "Air-fluid levels", "String of beads sign"],
            "icd10": "K56.60",
            "diagnosis": "Intestinal obstruction",
            "severity": "critical"
        },
        "free_air": {
            "findings": ["Free air under diaphragm", "Pneumoperitoneum"],
            "icd10": "K63.1",
            "diagnosis": "Perforation of intestine",
            "severity": "critical"
        },
        "normal": {
            "findings": ["Normal bowel gas pattern", "No obstruction", "No free air"],
            "icd10": None,
            "diagnosis": "Normal abdominal X-ray",
            "severity": "normal"
        }
    }
}

CT_PATTERNS = {
    "head": {
        "hemorrhage": {
            "findings": ["Hyperdense lesion", "Mass effect", "Midline shift"],
            "icd10": "I62.9",
            "diagnosis": "Intracranial hemorrhage",
            "severity": "critical"
        },
        "stroke_ischemic": {
            "findings": ["Hypodense region", "Loss of gray-white differentiation", "Insular ribbon sign"],
            "icd10": "I63.9",
            "diagnosis": "Cerebral infarction",
            "severity": "critical"
        },
        "mass": {
            "findings": ["Space-occupying lesion", "Enhancement", "Surrounding edema"],
            "icd10": "D49.6",
            "diagnosis": "Intracranial mass",
            "severity": "critical"
        },
        "normal": {
            "findings": ["No acute intracranial abnormality", "Normal gray-white differentiation"],
            "icd10": None,
            "diagnosis": "Normal head CT",
            "severity": "normal"
        }
    },
    "chest": {
        "pulmonary_embolism": {
            "findings": ["Filling defect in pulmonary artery", "Mosaic attenuation"],
            "icd10": "I26.99",
            "diagnosis": "Pulmonary embolism",
            "severity": "critical"
        },
        "lung_nodule": {
            "findings": ["Solitary pulmonary nodule", "Ground glass opacity"],
            "icd10": "R91.1",
            "diagnosis": "Solitary pulmonary nodule",
            "severity": "abnormal"
        },
        "lung_mass": {
            "findings": ["Mass >3cm", "Spiculated margins", "Mediastinal adenopathy"],
            "icd10": "R91.8",
            "diagnosis": "Lung mass - malignancy suspected",
            "severity": "critical"
        },
        "normal": {
            "findings": ["No pulmonary embolism", "Clear lung fields", "No mediastinal abnormality"],
            "icd10": None,
            "diagnosis": "Normal CT chest",
            "severity": "normal"
        }
    },
    "abdomen": {
        "appendicitis": {
            "findings": ["Dilated appendix >6mm", "Periappendiceal fat stranding", "Appendicolith"],
            "icd10": "K35.80",
            "diagnosis": "Acute appendicitis",
            "severity": "critical"
        },
        "kidney_stone": {
            "findings": ["Hyperdense focus in ureter", "Hydronephrosis", "Perinephric stranding"],
            "icd10": "N20.0",
            "diagnosis": "Kidney stone with obstruction",
            "severity": "abnormal"
        },
        "aortic_aneurysm": {
            "findings": ["Aortic diameter >3cm", "Mural thrombus"],
            "icd10": "I71.4",
            "diagnosis": "Abdominal aortic aneurysm",
            "severity": "critical"
        },
        "normal": {
            "findings": ["No acute abdominal pathology", "Normal solid organs"],
            "icd10": None,
            "diagnosis": "Normal CT abdomen",
            "severity": "normal"
        }
    }
}


class RadiologyAgent(BaseAgent):
    """
    AI Radiology Agent
    - Analyzes X-ray, CT, and MRI imaging studies
    - Provides structured radiological interpretations
    - Identifies urgent/critical findings
    - Suggests follow-up imaging when needed
    """

    def __init__(self):
        super().__init__(
            agent_id="radiology",
            name="Radiology Specialist",
            description="Analyzes imaging studies and provides diagnostic interpretations",
            version="1.0.0"
        )
        self.specialties = ["radiology", "imaging", "x-ray", "ct", "mri"]

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
                name="analyze_xray",
                description="Analyze X-ray images and provide interpretation",
                input_schema={"study_type": "string", "findings": "list"},
                output_schema={"interpretation": "string", "diagnoses": "list"}
            ),
            AgentCapability(
                name="analyze_ct",
                description="Analyze CT scans and provide interpretation",
                input_schema={"body_part": "string", "findings": "list"},
                output_schema={"interpretation": "string", "diagnoses": "list"}
            ),
            AgentCapability(
                name="recommend_imaging",
                description="Recommend appropriate imaging studies based on clinical presentation",
                input_schema={"symptoms": "list", "suspected_diagnosis": "string"},
                output_schema={"recommended_studies": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Process imaging data and provide radiological interpretation"""
        reasoning_steps = []
        findings = []
        diagnoses = []
        warnings = []

        task = task or {}
        imaging_studies = task.get("imaging_studies", [])

        reasoning_steps.append("=== Radiology Analysis ===")
        reasoning_steps.append(f"Patient: {context.name}, Age: {context.age}, Sex: {context.sex}")

        # If no imaging studies provided, analyze from context
        if not imaging_studies:
            imaging_studies = self._extract_imaging_from_context(context)

        if not imaging_studies:
            reasoning_steps.append("No imaging studies available for analysis")
            # Provide recommendations based on clinical context
            recommendations = self._recommend_imaging(context)
            if recommendations:
                reasoning_steps.append("Imaging recommendations based on clinical presentation:")
                for rec in recommendations:
                    reasoning_steps.append(f"  - {rec}")

            return self._create_output(
                findings=findings,
                diagnoses=diagnoses,
                confidence=0.0,
                reasoning=reasoning_steps,
                warnings=["No imaging studies available for analysis"],
                requires_review=False
            )

        # Analyze each imaging study
        for study in imaging_studies:
            study_type = study.get("type", "unknown").lower()
            body_part = study.get("body_part", "unknown").lower()
            reported_findings = study.get("findings", [])

            reasoning_steps.append(f"\nAnalyzing {study_type.upper()} - {body_part.title()}")

            if study_type in ["xray", "x-ray", "radiograph"]:
                study_findings, study_diagnoses = self._analyze_xray(body_part, reported_findings, reasoning_steps)
            elif study_type in ["ct", "cat", "computed tomography"]:
                study_findings, study_diagnoses = self._analyze_ct(body_part, reported_findings, reasoning_steps)
            else:
                study_findings, study_diagnoses = self._analyze_generic(study_type, body_part, reported_findings, reasoning_steps)

            findings.extend(study_findings)
            diagnoses.extend(study_diagnoses)

            # Check for critical findings
            critical = [f for f in study_findings if f.status == "critical"]
            if critical:
                warnings.append(f"CRITICAL FINDING on {study_type}: {', '.join([c.name for c in critical])}")

        # Determine if requires human review
        requires_review = len(warnings) > 0 or any(f.status == "critical" for f in findings)
        review_reason = "Critical radiological findings require immediate attention" if requires_review else None

        return self._create_output(
            findings=findings,
            diagnoses=diagnoses,
            confidence=0.85 if diagnoses else 0.5,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    def _extract_imaging_from_context(self, context: PatientContext) -> List[Dict]:
        """Extract imaging studies from patient context"""
        imaging = []

        # Check recent procedures for imaging
        if context.recent_procedures:
            for proc in context.recent_procedures:
                if not proc or not isinstance(proc, dict):
                    continue
                code = proc.get("code", "").lower()
                display = proc.get("display", "").lower()

                if any(term in display for term in ["x-ray", "radiograph", "xray"]):
                    imaging.append({
                        "type": "xray",
                        "body_part": self._extract_body_part(display),
                        "findings": [],
                        "date": proc.get("performed_date")
                    })
                elif any(term in display for term in ["ct", "computed tomography", "cat scan"]):
                    imaging.append({
                        "type": "ct",
                        "body_part": self._extract_body_part(display),
                        "findings": [],
                        "date": proc.get("performed_date")
                    })

        # Check imaging results if available
        if context.imaging_results:
            for img in context.imaging_results:
                if img and isinstance(img, dict):
                    imaging.append(img)

        return imaging

    def _extract_body_part(self, description: str) -> str:
        """Extract body part from imaging description"""
        description = description.lower()
        body_parts = {
            "chest": ["chest", "thorax", "lung", "thoracic"],
            "abdomen": ["abdomen", "abdominal", "belly"],
            "head": ["head", "brain", "cranial", "skull"],
            "spine": ["spine", "spinal", "vertebral", "lumbar", "cervical", "thoracic spine"],
            "extremity": ["arm", "leg", "hand", "foot", "knee", "ankle", "wrist", "elbow"],
            "pelvis": ["pelvis", "pelvic", "hip"]
        }

        for part, keywords in body_parts.items():
            if any(kw in description for kw in keywords):
                return part

        return "unknown"

    def _analyze_xray(self, body_part: str, reported_findings: List[str], reasoning: List[str]) -> tuple:
        """Analyze X-ray study"""
        findings = []
        diagnoses = []

        patterns = XRAY_PATTERNS.get(body_part, XRAY_PATTERNS.get("chest", {}))

        # Match findings to known patterns
        matched_patterns = []
        for pattern_name, pattern_data in patterns.items():
            if pattern_name == "normal":
                continue

            pattern_findings = pattern_data["findings"]
            for pf in pattern_findings:
                if any(pf.lower() in rf.lower() for rf in reported_findings):
                    matched_patterns.append((pattern_name, pattern_data))
                    break

        if matched_patterns:
            for pattern_name, pattern_data in matched_patterns:
                reasoning.append(f"  Pattern identified: {pattern_name}")

                findings.append(ClinicalFinding(
                    type="imaging",
                    name=f"X-ray {body_part.title()} - {pattern_name.replace('_', ' ').title()}",
                    value=", ".join(pattern_data["findings"]),
                    status=pattern_data["severity"],
                    interpretation=pattern_data["diagnosis"],
                    source="X-ray Analysis"
                ))

                if pattern_data.get("icd10"):
                    diagnoses.append(DiagnosisRecommendation(
                        diagnosis=pattern_data["diagnosis"],
                        icd10_code=pattern_data["icd10"],
                        confidence=0.8,
                        supporting_findings=[findings[-1]],
                        rationale=f"Based on X-ray findings: {', '.join(pattern_data['findings'])}"
                    ))
        else:
            reasoning.append("  No significant abnormality detected")
            findings.append(ClinicalFinding(
                type="imaging",
                name=f"X-ray {body_part.title()}",
                value="No acute abnormality",
                status="normal",
                interpretation="Normal study",
                source="X-ray Analysis"
            ))

        return findings, diagnoses

    def _analyze_ct(self, body_part: str, reported_findings: List[str], reasoning: List[str]) -> tuple:
        """Analyze CT study"""
        findings = []
        diagnoses = []

        patterns = CT_PATTERNS.get(body_part, CT_PATTERNS.get("chest", {}))

        # Match findings to known patterns
        matched_patterns = []
        for pattern_name, pattern_data in patterns.items():
            if pattern_name == "normal":
                continue

            pattern_findings = pattern_data["findings"]
            for pf in pattern_findings:
                if any(pf.lower() in rf.lower() for rf in reported_findings):
                    matched_patterns.append((pattern_name, pattern_data))
                    break

        if matched_patterns:
            for pattern_name, pattern_data in matched_patterns:
                reasoning.append(f"  CT pattern identified: {pattern_name}")

                findings.append(ClinicalFinding(
                    type="imaging",
                    name=f"CT {body_part.title()} - {pattern_name.replace('_', ' ').title()}",
                    value=", ".join(pattern_data["findings"]),
                    status=pattern_data["severity"],
                    interpretation=pattern_data["diagnosis"],
                    source="CT Analysis"
                ))

                if pattern_data.get("icd10"):
                    diagnoses.append(DiagnosisRecommendation(
                        diagnosis=pattern_data["diagnosis"],
                        icd10_code=pattern_data["icd10"],
                        confidence=0.85,
                        supporting_findings=[findings[-1]],
                        rationale=f"Based on CT findings: {', '.join(pattern_data['findings'])}"
                    ))
        else:
            reasoning.append("  No significant abnormality detected on CT")
            findings.append(ClinicalFinding(
                type="imaging",
                name=f"CT {body_part.title()}",
                value="No acute abnormality",
                status="normal",
                interpretation="Normal study",
                source="CT Analysis"
            ))

        return findings, diagnoses

    def _analyze_generic(self, study_type: str, body_part: str, reported_findings: List[str], reasoning: List[str]) -> tuple:
        """Analyze generic imaging study"""
        findings = []
        diagnoses = []

        reasoning.append(f"  Generic analysis of {study_type} - {body_part}")

        if reported_findings:
            for rf in reported_findings:
                status = "abnormal" if any(term in rf.lower() for term in ["mass", "tumor", "fracture", "hemorrhage"]) else "normal"
                findings.append(ClinicalFinding(
                    type="imaging",
                    name=f"{study_type.title()} {body_part.title()}",
                    value=rf,
                    status=status,
                    interpretation=rf,
                    source=f"{study_type.title()} Analysis"
                ))
        else:
            findings.append(ClinicalFinding(
                type="imaging",
                name=f"{study_type.title()} {body_part.title()}",
                value="Pending interpretation",
                status="normal",
                interpretation="No specific findings reported",
                source=f"{study_type.title()} Analysis"
            ))

        return findings, diagnoses

    def _recommend_imaging(self, context: PatientContext) -> List[str]:
        """Recommend imaging studies based on clinical context"""
        recommendations = []

        # Check conditions for imaging recommendations
        conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]

        if any("pneumonia" in c or "respiratory" in c for c in conditions):
            recommendations.append("Chest X-ray to evaluate for pneumonia/infiltrates")

        if any("abdominal pain" in c for c in conditions):
            recommendations.append("CT Abdomen/Pelvis with contrast to evaluate for acute pathology")

        if any("headache" in c or "neurological" in c for c in conditions):
            recommendations.append("CT Head without contrast to rule out acute intracranial pathology")

        if any("chest pain" in c for c in conditions):
            recommendations.append("CT Chest with contrast (CTA) if PE suspected")
            recommendations.append("Chest X-ray as initial evaluation")

        return recommendations
