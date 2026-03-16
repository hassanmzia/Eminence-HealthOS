"""
Pathology Agent
Analyzes laboratory results, blood work, biopsies, and tissue samples.
Provides diagnostic interpretations and identifies abnormal patterns.
"""

import os
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


# Laboratory reference ranges and interpretations
LAB_PANELS = {
    "cbc": {  # Complete Blood Count
        "wbc": {
            "name": "White Blood Cell Count",
            "unit": "x10^9/L",
            "ranges": {"low": 4.5, "high": 11.0},
            "critical_low": 2.0,
            "critical_high": 30.0,
            "interpretations": {
                "low": {"condition": "Leukopenia", "icd10": "D72.819", "causes": ["Viral infection", "Bone marrow suppression", "Autoimmune"]},
                "high": {"condition": "Leukocytosis", "icd10": "D72.829", "causes": ["Bacterial infection", "Inflammation", "Leukemia"]},
                "critical_low": {"condition": "Severe Leukopenia", "icd10": "D70.9", "causes": ["Neutropenic sepsis risk"]},
                "critical_high": {"condition": "Severe Leukocytosis", "icd10": "D72.829", "causes": ["Possible leukemia", "Severe infection"]}
            }
        },
        "hemoglobin": {
            "name": "Hemoglobin",
            "unit": "g/dL",
            "ranges": {"low": 12.0, "high": 17.5},  # Male ranges
            "critical_low": 7.0,
            "critical_high": 20.0,
            "interpretations": {
                "low": {"condition": "Anemia", "icd10": "D64.9", "causes": ["Iron deficiency", "Chronic disease", "Blood loss"]},
                "high": {"condition": "Polycythemia", "icd10": "D75.1", "causes": ["Dehydration", "Polycythemia vera", "Hypoxia"]},
                "critical_low": {"condition": "Severe Anemia", "icd10": "D64.9", "causes": ["Transfusion may be needed"]},
            }
        },
        "platelets": {
            "name": "Platelet Count",
            "unit": "x10^9/L",
            "ranges": {"low": 150, "high": 400},
            "critical_low": 50,
            "critical_high": 1000,
            "interpretations": {
                "low": {"condition": "Thrombocytopenia", "icd10": "D69.6", "causes": ["ITP", "Bone marrow failure", "DIC"]},
                "high": {"condition": "Thrombocytosis", "icd10": "D75.9", "causes": ["Reactive", "Essential thrombocythemia"]},
                "critical_low": {"condition": "Severe Thrombocytopenia", "icd10": "D69.6", "causes": ["Bleeding risk"]},
            }
        },
        "hematocrit": {
            "name": "Hematocrit",
            "unit": "%",
            "ranges": {"low": 36, "high": 50},
            "critical_low": 20,
            "critical_high": 60,
            "interpretations": {
                "low": {"condition": "Low Hematocrit", "icd10": "D64.9", "causes": ["Anemia", "Blood loss", "Overhydration"]},
                "high": {"condition": "High Hematocrit", "icd10": "D75.1", "causes": ["Dehydration", "Polycythemia"]},
            }
        }
    },
    "metabolic": {  # Basic Metabolic Panel
        "sodium": {
            "name": "Sodium",
            "unit": "mEq/L",
            "ranges": {"low": 136, "high": 145},
            "critical_low": 120,
            "critical_high": 160,
            "interpretations": {
                "low": {"condition": "Hyponatremia", "icd10": "E87.1", "causes": ["SIADH", "Heart failure", "Diuretics"]},
                "high": {"condition": "Hypernatremia", "icd10": "E87.0", "causes": ["Dehydration", "Diabetes insipidus"]},
                "critical_low": {"condition": "Severe Hyponatremia", "icd10": "E87.1", "causes": ["Seizure risk"]},
                "critical_high": {"condition": "Severe Hypernatremia", "icd10": "E87.0", "causes": ["Altered mental status"]}
            }
        },
        "potassium": {
            "name": "Potassium",
            "unit": "mEq/L",
            "ranges": {"low": 3.5, "high": 5.0},
            "critical_low": 2.5,
            "critical_high": 6.5,
            "interpretations": {
                "low": {"condition": "Hypokalemia", "icd10": "E87.6", "causes": ["Diuretics", "GI loss", "Renal"]},
                "high": {"condition": "Hyperkalemia", "icd10": "E87.5", "causes": ["Renal failure", "ACE inhibitors", "Hemolysis"]},
                "critical_low": {"condition": "Severe Hypokalemia", "icd10": "E87.6", "causes": ["Arrhythmia risk"]},
                "critical_high": {"condition": "Severe Hyperkalemia", "icd10": "E87.5", "causes": ["Cardiac arrest risk"]}
            }
        },
        "creatinine": {
            "name": "Creatinine",
            "unit": "mg/dL",
            "ranges": {"low": 0.7, "high": 1.3},
            "critical_high": 10.0,
            "interpretations": {
                "high": {"condition": "Elevated Creatinine", "icd10": "N18.9", "causes": ["Acute kidney injury", "Chronic kidney disease"]},
                "critical_high": {"condition": "Renal Failure", "icd10": "N17.9", "causes": ["Dialysis may be needed"]}
            }
        },
        "bun": {
            "name": "Blood Urea Nitrogen",
            "unit": "mg/dL",
            "ranges": {"low": 7, "high": 20},
            "critical_high": 100,
            "interpretations": {
                "high": {"condition": "Elevated BUN", "icd10": "R79.89", "causes": ["Dehydration", "Kidney disease", "GI bleed"]},
                "critical_high": {"condition": "Uremia", "icd10": "N19", "causes": ["Severe renal failure"]}
            }
        },
        "glucose": {
            "name": "Blood Glucose",
            "unit": "mg/dL",
            "ranges": {"low": 70, "high": 100},
            "critical_low": 40,
            "critical_high": 500,
            "interpretations": {
                "low": {"condition": "Hypoglycemia", "icd10": "E16.2", "causes": ["Insulin excess", "Poor nutrition", "Sepsis"]},
                "high": {"condition": "Hyperglycemia", "icd10": "R73.9", "causes": ["Diabetes", "Stress response", "Steroids"]},
                "critical_low": {"condition": "Severe Hypoglycemia", "icd10": "E16.2", "causes": ["Altered consciousness"]},
                "critical_high": {"condition": "Diabetic Crisis", "icd10": "E11.65", "causes": ["DKA/HHS risk"]}
            }
        }
    },
    "liver": {  # Liver Function Tests
        "alt": {
            "name": "ALT (Alanine Aminotransferase)",
            "unit": "U/L",
            "ranges": {"low": 7, "high": 56},
            "critical_high": 1000,
            "interpretations": {
                "high": {"condition": "Elevated ALT", "icd10": "R74.01", "causes": ["Hepatitis", "Drug-induced", "Fatty liver"]},
                "critical_high": {"condition": "Acute Liver Injury", "icd10": "K72.0", "causes": ["Acute hepatitis", "Drug toxicity"]}
            }
        },
        "ast": {
            "name": "AST (Aspartate Aminotransferase)",
            "unit": "U/L",
            "ranges": {"low": 10, "high": 40},
            "critical_high": 1000,
            "interpretations": {
                "high": {"condition": "Elevated AST", "icd10": "R74.01", "causes": ["Liver disease", "Cardiac injury", "Muscle damage"]},
                "critical_high": {"condition": "Severe Hepatocellular Injury", "icd10": "K72.0", "causes": ["Liver failure"]}
            }
        },
        "bilirubin": {
            "name": "Total Bilirubin",
            "unit": "mg/dL",
            "ranges": {"low": 0.1, "high": 1.2},
            "critical_high": 15,
            "interpretations": {
                "high": {"condition": "Hyperbilirubinemia", "icd10": "E80.7", "causes": ["Hemolysis", "Hepatitis", "Biliary obstruction"]},
                "critical_high": {"condition": "Severe Jaundice", "icd10": "R17", "causes": ["Liver failure", "Complete obstruction"]}
            }
        },
        "albumin": {
            "name": "Albumin",
            "unit": "g/dL",
            "ranges": {"low": 3.5, "high": 5.0},
            "critical_low": 2.0,
            "interpretations": {
                "low": {"condition": "Hypoalbuminemia", "icd10": "E88.09", "causes": ["Liver disease", "Malnutrition", "Nephrotic syndrome"]},
                "critical_low": {"condition": "Severe Hypoalbuminemia", "icd10": "E88.09", "causes": ["Ascites risk"]}
            }
        }
    },
    "cardiac": {  # Cardiac Markers
        "troponin": {
            "name": "Troponin I",
            "unit": "ng/mL",
            "ranges": {"low": 0, "high": 0.04},
            "critical_high": 0.4,
            "interpretations": {
                "high": {"condition": "Elevated Troponin", "icd10": "R79.89", "causes": ["Myocardial injury", "ACS", "PE", "Myocarditis"]},
                "critical_high": {"condition": "Acute MI", "icd10": "I21.9", "causes": ["STEMI/NSTEMI"]}
            }
        },
        "bnp": {
            "name": "B-type Natriuretic Peptide",
            "unit": "pg/mL",
            "ranges": {"low": 0, "high": 100},
            "critical_high": 900,
            "interpretations": {
                "high": {"condition": "Elevated BNP", "icd10": "I50.9", "causes": ["Heart failure", "Volume overload"]},
                "critical_high": {"condition": "Acute Heart Failure", "icd10": "I50.9", "causes": ["Decompensated HF"]}
            }
        },
        "d_dimer": {
            "name": "D-Dimer",
            "unit": "ng/mL",
            "ranges": {"low": 0, "high": 500},
            "critical_high": 5000,
            "interpretations": {
                "high": {"condition": "Elevated D-Dimer", "icd10": "R79.1", "causes": ["VTE", "DIC", "Infection", "Malignancy"]},
                "critical_high": {"condition": "Significantly Elevated D-Dimer", "icd10": "R79.1", "causes": ["High suspicion for PE/DVT"]}
            }
        }
    },
    "coagulation": {
        "pt_inr": {
            "name": "PT/INR",
            "unit": "ratio",
            "ranges": {"low": 0.9, "high": 1.1},  # For non-anticoagulated patients
            "critical_high": 5.0,
            "interpretations": {
                "high": {"condition": "Elevated INR", "icd10": "R79.1", "causes": ["Warfarin therapy", "Liver disease", "Vitamin K deficiency"]},
                "critical_high": {"condition": "Severe Coagulopathy", "icd10": "D68.9", "causes": ["Bleeding risk"]}
            }
        },
        "ptt": {
            "name": "Partial Thromboplastin Time",
            "unit": "seconds",
            "ranges": {"low": 25, "high": 35},
            "critical_high": 100,
            "interpretations": {
                "high": {"condition": "Elevated PTT", "icd10": "R79.1", "causes": ["Heparin therapy", "Factor deficiency", "Lupus anticoagulant"]},
                "critical_high": {"condition": "Severe PTT Elevation", "icd10": "D68.9", "causes": ["Bleeding risk"]}
            }
        }
    },
    "thyroid": {
        "tsh": {
            "name": "Thyroid Stimulating Hormone",
            "unit": "mIU/L",
            "ranges": {"low": 0.4, "high": 4.0},
            "critical_low": 0.01,
            "critical_high": 50,
            "interpretations": {
                "low": {"condition": "Low TSH", "icd10": "E05.90", "causes": ["Hyperthyroidism", "Pituitary disease"]},
                "high": {"condition": "High TSH", "icd10": "E03.9", "causes": ["Hypothyroidism"]},
                "critical_low": {"condition": "Thyrotoxicosis", "icd10": "E05.90", "causes": ["Thyroid storm risk"]},
                "critical_high": {"condition": "Severe Hypothyroidism", "icd10": "E03.9", "causes": ["Myxedema risk"]}
            }
        }
    },
    "inflammation": {
        "crp": {
            "name": "C-Reactive Protein",
            "unit": "mg/L",
            "ranges": {"low": 0, "high": 10},
            "critical_high": 100,
            "interpretations": {
                "high": {"condition": "Elevated CRP", "icd10": "R79.89", "causes": ["Infection", "Inflammation", "Autoimmune"]},
                "critical_high": {"condition": "Severely Elevated CRP", "icd10": "R79.89", "causes": ["Severe infection", "Sepsis"]}
            }
        },
        "esr": {
            "name": "Erythrocyte Sedimentation Rate",
            "unit": "mm/hr",
            "ranges": {"low": 0, "high": 20},
            "critical_high": 100,
            "interpretations": {
                "high": {"condition": "Elevated ESR", "icd10": "R70.0", "causes": ["Infection", "Inflammation", "Malignancy"]}
            }
        },
        "procalcitonin": {
            "name": "Procalcitonin",
            "unit": "ng/mL",
            "ranges": {"low": 0, "high": 0.5},
            "critical_high": 10,
            "interpretations": {
                "high": {"condition": "Elevated Procalcitonin", "icd10": "R78.89", "causes": ["Bacterial infection", "Sepsis"]},
                "critical_high": {"condition": "Severe Sepsis", "icd10": "A41.9", "causes": ["Septic shock risk"]}
            }
        }
    }
}

# Tissue pathology patterns
HISTOPATHOLOGY_PATTERNS = {
    "breast": {
        "malignant": {
            "findings": ["Invasive ductal carcinoma", "Invasive lobular carcinoma", "DCIS"],
            "icd10": "C50.9",
            "diagnosis": "Breast malignancy",
            "severity": "critical"
        },
        "benign": {
            "findings": ["Fibroadenoma", "Fibrocystic changes", "Phyllodes tumor benign"],
            "icd10": "N60.9",
            "diagnosis": "Benign breast disease",
            "severity": "normal"
        }
    },
    "colon": {
        "malignant": {
            "findings": ["Adenocarcinoma", "High-grade dysplasia", "Carcinoma in situ"],
            "icd10": "C18.9",
            "diagnosis": "Colorectal malignancy",
            "severity": "critical"
        },
        "premalignant": {
            "findings": ["Adenomatous polyp", "Tubular adenoma", "Villous adenoma", "Low-grade dysplasia"],
            "icd10": "K63.5",
            "diagnosis": "Colorectal polyp with dysplasia",
            "severity": "abnormal"
        },
        "benign": {
            "findings": ["Hyperplastic polyp", "Inflammatory polyp"],
            "icd10": "K63.5",
            "diagnosis": "Benign colorectal polyp",
            "severity": "normal"
        }
    },
    "prostate": {
        "malignant": {
            "findings": ["Prostatic adenocarcinoma", "Gleason score"],
            "icd10": "C61",
            "diagnosis": "Prostate carcinoma",
            "severity": "critical"
        },
        "benign": {
            "findings": ["Benign prostatic hyperplasia", "Prostatitis"],
            "icd10": "N40.0",
            "diagnosis": "Benign prostatic condition",
            "severity": "normal"
        }
    },
    "skin": {
        "malignant": {
            "findings": ["Melanoma", "Squamous cell carcinoma", "Basal cell carcinoma"],
            "icd10": "C44.9",
            "diagnosis": "Skin malignancy",
            "severity": "critical"
        },
        "benign": {
            "findings": ["Nevus", "Seborrheic keratosis", "Dermatofibroma"],
            "icd10": "D22.9",
            "diagnosis": "Benign skin lesion",
            "severity": "normal"
        }
    },
    "thyroid": {
        "malignant": {
            "findings": ["Papillary thyroid carcinoma", "Follicular carcinoma", "Medullary carcinoma"],
            "icd10": "C73",
            "diagnosis": "Thyroid malignancy",
            "severity": "critical"
        },
        "benign": {
            "findings": ["Follicular adenoma", "Colloid nodule", "Hashimoto thyroiditis"],
            "icd10": "E04.1",
            "diagnosis": "Benign thyroid nodule",
            "severity": "normal"
        }
    },
    "lung": {
        "malignant": {
            "findings": ["Non-small cell carcinoma", "Small cell carcinoma", "Adenocarcinoma", "Squamous cell carcinoma"],
            "icd10": "C34.90",
            "diagnosis": "Lung malignancy",
            "severity": "critical"
        },
        "benign": {
            "findings": ["Hamartoma", "Granuloma", "Inflammatory pseudotumor"],
            "icd10": "D14.3",
            "diagnosis": "Benign lung lesion",
            "severity": "normal"
        }
    }
}


class PathologyAgent(BaseAgent):
    """
    AI Pathology Agent
    - Analyzes laboratory results (CBC, BMP, LFTs, cardiac markers, etc.)
    - Interprets biopsy and tissue pathology results
    - Identifies critical lab values and patterns
    - Provides diagnostic recommendations based on lab findings
    """

    def __init__(self):
        super().__init__(
            agent_id="pathology",
            name="Pathology Specialist",
            description="Analyzes laboratory results and tissue pathology",
            version="1.0.0"
        )
        self.specialties = ["pathology", "laboratory", "histopathology", "clinical_chemistry"]

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
                name="analyze_labs",
                description="Analyze laboratory results and identify abnormalities",
                input_schema={"labs": "list"},
                output_schema={"interpretations": "list", "diagnoses": "list"}
            ),
            AgentCapability(
                name="analyze_pathology",
                description="Analyze tissue biopsy and histopathology results",
                input_schema={"specimen": "string", "findings": "list"},
                output_schema={"diagnosis": "string", "grade": "string"}
            ),
            AgentCapability(
                name="recommend_labs",
                description="Recommend laboratory tests based on clinical presentation",
                input_schema={"symptoms": "list", "suspected_diagnosis": "string"},
                output_schema={"recommended_tests": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Process laboratory and pathology data"""
        reasoning_steps = []
        findings = []
        diagnoses = []
        warnings = []

        task = task or {}

        reasoning_steps.append("=== Pathology Analysis ===")
        reasoning_steps.append(f"Patient: {context.name}, Age: {context.age}, Sex: {context.sex}")

        # Analyze labs from context
        if context.labs:
            reasoning_steps.append("\n--- Laboratory Results Analysis ---")
            lab_findings, lab_diagnoses, lab_warnings = self._analyze_labs(context.labs, reasoning_steps)
            findings.extend(lab_findings)
            diagnoses.extend(lab_diagnoses)
            warnings.extend(lab_warnings)

        # Analyze pathology/biopsy results if provided in task
        pathology_results = task.get("pathology_results", [])
        if pathology_results:
            reasoning_steps.append("\n--- Histopathology Analysis ---")
            path_findings, path_diagnoses, path_warnings = self._analyze_pathology(pathology_results, reasoning_steps)
            findings.extend(path_findings)
            diagnoses.extend(path_diagnoses)
            warnings.extend(path_warnings)

        # If no lab data, provide recommendations
        if not context.labs and not pathology_results:
            reasoning_steps.append("No laboratory or pathology data available")
            recommendations = self._recommend_labs(context)
            if recommendations:
                reasoning_steps.append("Recommended laboratory workup:")
                for rec in recommendations:
                    reasoning_steps.append(f"  - {rec}")

        # Determine if requires human review
        requires_review = len(warnings) > 0 or any(f.status == "critical" for f in findings)
        review_reason = "Critical laboratory findings require immediate attention" if requires_review else None

        return self._create_output(
            findings=findings,
            diagnoses=diagnoses,
            confidence=0.85 if diagnoses else 0.5,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    def _analyze_labs(self, labs: List[dict], reasoning: List[str]) -> tuple:
        """Analyze laboratory results"""
        findings = []
        diagnoses = []
        warnings = []

        # Create a map of lab results by code/name
        lab_values = {}
        for lab in labs:
            if not lab or not isinstance(lab, dict):
                continue

            code = lab.get("code", "")
            name = lab.get("display", lab.get("name", "")).lower()
            value = lab.get("value")
            unit = lab.get("unit", "")

            if value is not None:
                lab_values[code] = {"value": value, "unit": unit, "name": name}
                lab_values[name] = {"value": value, "unit": unit, "name": name}

        # Check each lab panel
        for panel_name, panel_tests in LAB_PANELS.items():
            panel_findings = []

            for test_key, test_info in panel_tests.items():
                # Try to find this test in patient's labs
                test_name_lower = test_info["name"].lower()
                value_info = None

                for key in [test_key, test_name_lower]:
                    if key in lab_values:
                        value_info = lab_values[key]
                        break

                # Also check by partial match
                if not value_info:
                    for lab_key, lab_val in lab_values.items():
                        if isinstance(lab_key, str) and test_key in lab_key.lower():
                            value_info = lab_val
                            break

                if not value_info:
                    continue

                value = value_info["value"]
                if not isinstance(value, (int, float)):
                    continue

                ranges = test_info["ranges"]
                status = "normal"
                interpretation_key = None

                # Check critical ranges first
                if "critical_low" in test_info and value < test_info["critical_low"]:
                    status = "critical"
                    interpretation_key = "critical_low"
                elif "critical_high" in test_info and value > test_info["critical_high"]:
                    status = "critical"
                    interpretation_key = "critical_high"
                elif "low" in ranges and value < ranges["low"]:
                    status = "abnormal"
                    interpretation_key = "low"
                elif "high" in ranges and value > ranges["high"]:
                    status = "abnormal"
                    interpretation_key = "high"

                if status != "normal" and interpretation_key:
                    interp = test_info["interpretations"].get(interpretation_key, {})
                    condition = interp.get("condition", f"Abnormal {test_info['name']}")
                    icd10 = interp.get("icd10")
                    causes = interp.get("causes", [])

                    reasoning.append(f"  {test_info['name']}: {value} {test_info['unit']} - {status.upper()}")
                    reasoning.append(f"    -> {condition}")

                    finding = ClinicalFinding(
                        type="laboratory",
                        name=test_info["name"],
                        value=f"{value} {test_info['unit']}",
                        status=status,
                        interpretation=f"{condition}. Possible causes: {', '.join(causes[:3])}",
                        source="Laboratory Analysis"
                    )
                    findings.append(finding)
                    panel_findings.append(finding)

                    if icd10:
                        diagnoses.append(DiagnosisRecommendation(
                            diagnosis=condition,
                            icd10_code=icd10,
                            confidence=0.8 if status == "critical" else 0.7,
                            supporting_findings=[finding],
                            rationale=f"Based on laboratory value: {test_info['name']} = {value} {test_info['unit']}"
                        ))

                    if status == "critical":
                        warnings.append(f"CRITICAL LAB: {test_info['name']} = {value} {test_info['unit']} ({condition})")

            if panel_findings:
                reasoning.append(f"  {panel_name.upper()} panel: {len(panel_findings)} abnormal values")

        return findings, diagnoses, warnings

    def _analyze_pathology(self, pathology_results: List[dict], reasoning: List[str]) -> tuple:
        """Analyze histopathology results"""
        findings = []
        diagnoses = []
        warnings = []

        for result in pathology_results:
            if not result or not isinstance(result, dict):
                continue

            specimen = result.get("specimen", "unknown").lower()
            reported_findings = result.get("findings", [])
            diagnosis_text = result.get("diagnosis", "")

            reasoning.append(f"\n  Specimen: {specimen.title()}")

            # Check against known patterns
            patterns = HISTOPATHOLOGY_PATTERNS.get(specimen, {})
            matched = False

            for category, pattern_data in patterns.items():
                pattern_findings = pattern_data["findings"]

                # Check if any pattern findings match
                for pf in pattern_findings:
                    if any(pf.lower() in rf.lower() for rf in reported_findings) or \
                       pf.lower() in diagnosis_text.lower():

                        matched = True
                        reasoning.append(f"    Pattern: {category.title()}")
                        reasoning.append(f"    Diagnosis: {pattern_data['diagnosis']}")

                        finding = ClinicalFinding(
                            type="pathology",
                            name=f"{specimen.title()} Biopsy",
                            value=diagnosis_text or ", ".join(reported_findings[:3]),
                            status=pattern_data["severity"],
                            interpretation=pattern_data["diagnosis"],
                            source="Histopathology"
                        )
                        findings.append(finding)

                        if pattern_data.get("icd10"):
                            diagnoses.append(DiagnosisRecommendation(
                                diagnosis=pattern_data["diagnosis"],
                                icd10_code=pattern_data["icd10"],
                                confidence=0.9,  # Pathology is definitive
                                supporting_findings=[finding],
                                rationale=f"Histopathology confirmed: {diagnosis_text or ', '.join(reported_findings[:3])}"
                            ))

                        if pattern_data["severity"] == "critical":
                            warnings.append(f"MALIGNANCY DETECTED: {pattern_data['diagnosis']} in {specimen}")

                        break

                if matched:
                    break

            if not matched and reported_findings:
                # Generic finding
                findings.append(ClinicalFinding(
                    type="pathology",
                    name=f"{specimen.title()} Biopsy",
                    value=", ".join(reported_findings[:3]),
                    status="abnormal" if "abnormal" in str(reported_findings).lower() else "normal",
                    interpretation=diagnosis_text or "Pending full interpretation",
                    source="Histopathology"
                ))

        return findings, diagnoses, warnings

    def _recommend_labs(self, context: PatientContext) -> List[str]:
        """Recommend laboratory tests based on clinical context"""
        recommendations = []

        # Basic workup for any patient
        recommendations.append("Complete Blood Count (CBC)")
        recommendations.append("Basic Metabolic Panel (BMP)")

        # Check conditions for specific recommendations
        conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]

        if any("chest pain" in c or "cardiac" in c for c in conditions):
            recommendations.append("Troponin I (serial)")
            recommendations.append("BNP or NT-proBNP")
            recommendations.append("Lipid Panel")

        if any("infection" in c or "fever" in c for c in conditions):
            recommendations.append("Procalcitonin")
            recommendations.append("Blood Cultures")
            recommendations.append("Urinalysis")

        if any("diabetes" in c for c in conditions):
            recommendations.append("HbA1c")
            recommendations.append("Fasting Glucose")
            recommendations.append("Lipid Panel")

        if any("liver" in c or "jaundice" in c for c in conditions):
            recommendations.append("Comprehensive Metabolic Panel (CMP)")
            recommendations.append("Liver Function Tests (LFTs)")
            recommendations.append("Coagulation Studies (PT/INR)")

        if any("thyroid" in c for c in conditions):
            recommendations.append("TSH")
            recommendations.append("Free T4")

        if any("bleeding" in c or "clot" in c or "dvt" in c or "pe" in c for c in conditions):
            recommendations.append("D-Dimer")
            recommendations.append("PT/INR, PTT")
            recommendations.append("Fibrinogen")

        return recommendations
