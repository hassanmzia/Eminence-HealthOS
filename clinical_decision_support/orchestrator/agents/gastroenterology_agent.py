"""
Gastroenterology Agent
Analyzes colonoscopy, endoscopy, and other GI procedure findings.
Provides diagnostic interpretations and follow-up recommendations.
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


# Colonoscopy findings patterns
COLONOSCOPY_PATTERNS = {
    "polyp": {
        "adenomatous": {
            "findings": ["Adenomatous polyp", "Tubular adenoma", "Villous adenoma", "Tubulovillous adenoma"],
            "icd10": "K63.5",
            "diagnosis": "Adenomatous polyp",
            "severity": "abnormal",
            "surveillance": "3-5 years",
            "malignancy_risk": "moderate"
        },
        "hyperplastic": {
            "findings": ["Hyperplastic polyp"],
            "icd10": "K63.5",
            "diagnosis": "Hyperplastic polyp",
            "severity": "normal",
            "surveillance": "10 years",
            "malignancy_risk": "low"
        },
        "sessile_serrated": {
            "findings": ["Sessile serrated adenoma", "SSA", "Sessile serrated lesion"],
            "icd10": "K63.5",
            "diagnosis": "Sessile serrated adenoma",
            "severity": "abnormal",
            "surveillance": "3-5 years",
            "malignancy_risk": "moderate"
        },
        "dysplastic": {
            "findings": ["High-grade dysplasia", "HGD", "Low-grade dysplasia", "LGD"],
            "icd10": "K63.5",
            "diagnosis": "Dysplastic polyp",
            "severity": "critical",
            "surveillance": "1 year",
            "malignancy_risk": "high"
        },
        "malignant": {
            "findings": ["Adenocarcinoma", "Carcinoma", "Malignant polyp", "Cancer"],
            "icd10": "C18.9",
            "diagnosis": "Colorectal carcinoma",
            "severity": "critical",
            "surveillance": "immediate referral",
            "malignancy_risk": "confirmed"
        }
    },
    "inflammation": {
        "colitis": {
            "findings": ["Colitis", "Mucosal inflammation", "Erythema", "Friability"],
            "icd10": "K52.9",
            "diagnosis": "Colitis",
            "severity": "abnormal"
        },
        "ulcerative_colitis": {
            "findings": ["Ulcerative colitis", "Continuous inflammation", "Pseudopolyps", "Crypt abscesses"],
            "icd10": "K51.90",
            "diagnosis": "Ulcerative colitis",
            "severity": "abnormal"
        },
        "crohns": {
            "findings": ["Crohn's disease", "Skip lesions", "Cobblestoning", "Stricture", "Fistula"],
            "icd10": "K50.90",
            "diagnosis": "Crohn's disease",
            "severity": "abnormal"
        },
        "ischemic": {
            "findings": ["Ischemic colitis", "Pale mucosa", "Watershed distribution"],
            "icd10": "K55.9",
            "diagnosis": "Ischemic colitis",
            "severity": "critical"
        }
    },
    "diverticular": {
        "diverticulosis": {
            "findings": ["Diverticulosis", "Diverticula"],
            "icd10": "K57.30",
            "diagnosis": "Diverticulosis",
            "severity": "normal"
        },
        "diverticulitis": {
            "findings": ["Diverticulitis", "Inflamed diverticulum", "Peridiverticular inflammation"],
            "icd10": "K57.32",
            "diagnosis": "Diverticulitis",
            "severity": "abnormal"
        }
    },
    "vascular": {
        "hemorrhoids": {
            "findings": ["Internal hemorrhoids", "Hemorrhoidal cushions"],
            "icd10": "K64.8",
            "diagnosis": "Internal hemorrhoids",
            "severity": "normal"
        },
        "angiodysplasia": {
            "findings": ["Angiodysplasia", "AVM", "Arteriovenous malformation"],
            "icd10": "K55.21",
            "diagnosis": "Angiodysplasia",
            "severity": "abnormal"
        }
    },
    "normal": {
        "findings": ["Normal colonoscopy", "No polyps", "No masses", "Normal mucosa"],
        "icd10": None,
        "diagnosis": "Normal colonoscopy",
        "severity": "normal",
        "surveillance": "10 years"
    }
}

# Upper endoscopy (EGD) findings patterns
ENDOSCOPY_PATTERNS = {
    "esophagus": {
        "esophagitis": {
            "findings": ["Esophagitis", "Erosive esophagitis", "LA Grade"],
            "icd10": "K21.0",
            "diagnosis": "Reflux esophagitis",
            "severity": "abnormal"
        },
        "barretts": {
            "findings": ["Barrett's esophagus", "Intestinal metaplasia", "Columnar mucosa"],
            "icd10": "K22.70",
            "diagnosis": "Barrett's esophagus",
            "severity": "abnormal",
            "surveillance": "3-5 years"
        },
        "stricture": {
            "findings": ["Esophageal stricture", "Stenosis", "Narrowing"],
            "icd10": "K22.2",
            "diagnosis": "Esophageal stricture",
            "severity": "abnormal"
        },
        "varices": {
            "findings": ["Esophageal varices", "Variceal columns"],
            "icd10": "I85.00",
            "diagnosis": "Esophageal varices",
            "severity": "critical"
        },
        "cancer": {
            "findings": ["Esophageal carcinoma", "Esophageal mass", "Adenocarcinoma of esophagus", "Squamous cell carcinoma"],
            "icd10": "C15.9",
            "diagnosis": "Esophageal carcinoma",
            "severity": "critical"
        }
    },
    "stomach": {
        "gastritis": {
            "findings": ["Gastritis", "Erythematous mucosa", "Antral gastritis"],
            "icd10": "K29.70",
            "diagnosis": "Gastritis",
            "severity": "abnormal"
        },
        "ulcer": {
            "findings": ["Gastric ulcer", "Peptic ulcer", "Ulcer crater"],
            "icd10": "K25.9",
            "diagnosis": "Gastric ulcer",
            "severity": "abnormal"
        },
        "h_pylori": {
            "findings": ["H. pylori positive", "Helicobacter pylori"],
            "icd10": "B96.81",
            "diagnosis": "H. pylori infection",
            "severity": "abnormal"
        },
        "gastric_cancer": {
            "findings": ["Gastric carcinoma", "Gastric mass", "Adenocarcinoma of stomach"],
            "icd10": "C16.9",
            "diagnosis": "Gastric carcinoma",
            "severity": "critical"
        },
        "gist": {
            "findings": ["GIST", "Gastrointestinal stromal tumor", "Submucosal mass"],
            "icd10": "C16.9",
            "diagnosis": "Gastrointestinal stromal tumor",
            "severity": "critical"
        }
    },
    "duodenum": {
        "duodenitis": {
            "findings": ["Duodenitis", "Duodenal erythema"],
            "icd10": "K29.80",
            "diagnosis": "Duodenitis",
            "severity": "abnormal"
        },
        "duodenal_ulcer": {
            "findings": ["Duodenal ulcer", "Bulb ulcer"],
            "icd10": "K26.9",
            "diagnosis": "Duodenal ulcer",
            "severity": "abnormal"
        },
        "celiac": {
            "findings": ["Celiac disease", "Villous atrophy", "Scalloping"],
            "icd10": "K90.0",
            "diagnosis": "Celiac disease",
            "severity": "abnormal"
        }
    },
    "normal": {
        "findings": ["Normal EGD", "Normal upper endoscopy", "Normal esophagus", "Normal stomach", "Normal duodenum"],
        "icd10": None,
        "diagnosis": "Normal upper endoscopy",
        "severity": "normal"
    }
}

# ERCP findings
ERCP_PATTERNS = {
    "stones": {
        "findings": ["Choledocholithiasis", "CBD stones", "Common bile duct stone"],
        "icd10": "K80.50",
        "diagnosis": "Choledocholithiasis",
        "severity": "abnormal"
    },
    "stricture": {
        "findings": ["Biliary stricture", "CBD stricture", "Pancreatic duct stricture"],
        "icd10": "K83.1",
        "diagnosis": "Biliary stricture",
        "severity": "abnormal"
    },
    "cholangitis": {
        "findings": ["Cholangitis", "Biliary infection"],
        "icd10": "K83.0",
        "diagnosis": "Cholangitis",
        "severity": "critical"
    },
    "cholangiocarcinoma": {
        "findings": ["Cholangiocarcinoma", "Bile duct cancer", "Klatskin tumor"],
        "icd10": "C22.1",
        "diagnosis": "Cholangiocarcinoma",
        "severity": "critical"
    },
    "pancreatitis": {
        "findings": ["Pancreatitis", "Pancreatic inflammation", "Post-ERCP pancreatitis"],
        "icd10": "K85.9",
        "diagnosis": "Pancreatitis",
        "severity": "critical"
    }
}


class GastroenterologyAgent(BaseAgent):
    """
    AI Gastroenterology Agent
    - Analyzes colonoscopy findings (polyps, inflammation, masses)
    - Analyzes upper endoscopy findings (EGD)
    - Interprets ERCP results
    - Provides surveillance recommendations
    - Identifies urgent/critical findings
    """

    def __init__(self):
        super().__init__(
            agent_id="gastroenterology",
            name="Gastroenterology Specialist",
            description="Analyzes GI procedures and provides diagnostic interpretations",
            version="1.0.0"
        )
        self.specialties = ["gastroenterology", "colonoscopy", "endoscopy", "ercp", "gi"]

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
                name="analyze_colonoscopy",
                description="Analyze colonoscopy findings and provide recommendations",
                input_schema={"findings": "list", "polyp_count": "int"},
                output_schema={"diagnoses": "list", "surveillance": "string"}
            ),
            AgentCapability(
                name="analyze_egd",
                description="Analyze upper endoscopy findings",
                input_schema={"findings": "list"},
                output_schema={"diagnoses": "list", "recommendations": "list"}
            ),
            AgentCapability(
                name="analyze_ercp",
                description="Analyze ERCP findings",
                input_schema={"findings": "list"},
                output_schema={"diagnoses": "list", "interventions": "list"}
            ),
            AgentCapability(
                name="recommend_screening",
                description="Recommend GI screening based on risk factors",
                input_schema={"age": "int", "risk_factors": "list"},
                output_schema={"recommendations": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Process GI procedure data and provide interpretations"""
        reasoning_steps = []
        findings = []
        diagnoses = []
        treatments = []
        warnings = []

        task = task or {}
        gi_procedures = task.get("procedures", [])

        reasoning_steps.append("=== Gastroenterology Analysis ===")
        reasoning_steps.append(f"Patient: {context.name}, Age: {context.age}, Sex: {context.sex}")

        # If no procedures provided, extract from context
        if not gi_procedures:
            gi_procedures = self._extract_gi_procedures(context)

        if not gi_procedures:
            reasoning_steps.append("No GI procedure data available")
            # Provide screening recommendations
            recommendations = self._recommend_screening(context)
            if recommendations:
                reasoning_steps.append("GI screening recommendations:")
                for rec in recommendations:
                    reasoning_steps.append(f"  - {rec}")

            return self._create_output(
                findings=findings,
                diagnoses=diagnoses,
                treatments=treatments,
                confidence=0.0,
                reasoning=reasoning_steps,
                warnings=["No GI procedure data available for analysis"],
                requires_review=False
            )

        # Analyze each procedure
        for procedure in gi_procedures:
            proc_type = procedure.get("type", "").lower()
            proc_findings = procedure.get("findings", [])
            proc_location = procedure.get("location", "")

            reasoning_steps.append(f"\nAnalyzing: {proc_type.upper()}")

            if proc_type in ["colonoscopy", "colon"]:
                proc_f, proc_d, proc_t, proc_w = self._analyze_colonoscopy(proc_findings, reasoning_steps)
            elif proc_type in ["egd", "upper endoscopy", "esophagogastroduodenoscopy"]:
                proc_f, proc_d, proc_t, proc_w = self._analyze_egd(proc_findings, reasoning_steps)
            elif proc_type in ["ercp"]:
                proc_f, proc_d, proc_t, proc_w = self._analyze_ercp(proc_findings, reasoning_steps)
            else:
                proc_f, proc_d, proc_t, proc_w = self._analyze_generic_gi(proc_type, proc_findings, reasoning_steps)

            findings.extend(proc_f)
            diagnoses.extend(proc_d)
            treatments.extend(proc_t)
            warnings.extend(proc_w)

        # Determine if requires human review
        requires_review = len(warnings) > 0 or any(f.status == "critical" for f in findings)
        review_reason = "Critical GI findings require immediate specialist attention" if requires_review else None

        return self._create_output(
            findings=findings,
            diagnoses=diagnoses,
            treatments=treatments,
            confidence=0.85 if diagnoses else 0.5,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    def _extract_gi_procedures(self, context: PatientContext) -> List[Dict]:
        """Extract GI procedure data from patient context"""
        procedures = []

        if context.recent_procedures:
            for proc in context.recent_procedures:
                if not proc or not isinstance(proc, dict):
                    continue

                display = proc.get("display", "").lower()
                code = proc.get("code", "")

                if any(term in display for term in ["colonoscopy", "colon"]):
                    procedures.append({
                        "type": "colonoscopy",
                        "findings": proc.get("findings", []),
                        "date": proc.get("performed_date")
                    })
                elif any(term in display for term in ["egd", "upper endoscopy", "esophagogastroduodenoscopy"]):
                    procedures.append({
                        "type": "egd",
                        "findings": proc.get("findings", []),
                        "date": proc.get("performed_date")
                    })
                elif "ercp" in display:
                    procedures.append({
                        "type": "ercp",
                        "findings": proc.get("findings", []),
                        "date": proc.get("performed_date")
                    })

        return procedures

    def _analyze_colonoscopy(self, reported_findings: List[str], reasoning: List[str]) -> tuple:
        """Analyze colonoscopy findings"""
        findings = []
        diagnoses = []
        treatments = []
        warnings = []

        polyp_count = 0
        most_severe_polyp = None
        surveillance_interval = "10 years"

        # Check for polyp patterns
        for category, patterns in COLONOSCOPY_PATTERNS.items():
            if category == "polyp":
                for polyp_type, pattern_data in patterns.items():
                    for pf in pattern_data["findings"]:
                        if any(pf.lower() in rf.lower() for rf in reported_findings):
                            polyp_count += 1
                            reasoning.append(f"  Polyp identified: {polyp_type}")

                            finding = ClinicalFinding(
                                type="procedure",
                                name=f"Colonoscopy - {pattern_data['diagnosis']}",
                                value=pf,
                                status=pattern_data["severity"],
                                interpretation=pattern_data["diagnosis"],
                                source="Colonoscopy"
                            )
                            findings.append(finding)

                            if pattern_data.get("icd10"):
                                diagnoses.append(DiagnosisRecommendation(
                                    diagnosis=pattern_data["diagnosis"],
                                    icd10_code=pattern_data["icd10"],
                                    confidence=0.9,
                                    supporting_findings=[finding],
                                    rationale=f"Colonoscopy finding: {pf}"
                                ))

                            # Update surveillance based on most severe finding
                            if pattern_data.get("surveillance"):
                                if most_severe_polyp is None or \
                                   pattern_data["severity"] == "critical" or \
                                   (pattern_data.get("malignancy_risk") == "high" and most_severe_polyp.get("malignancy_risk") != "confirmed"):
                                    most_severe_polyp = pattern_data
                                    surveillance_interval = pattern_data["surveillance"]

                            if pattern_data["severity"] == "critical":
                                warnings.append(f"CRITICAL: {pattern_data['diagnosis']} - immediate attention required")

                            break

            elif category == "normal":
                if any(pattern_data["findings"][0].lower() in rf.lower() for rf in reported_findings for pattern_data in [patterns]):
                    findings.append(ClinicalFinding(
                        type="procedure",
                        name="Colonoscopy",
                        value="Normal examination",
                        status="normal",
                        interpretation="Normal colonoscopy",
                        source="Colonoscopy"
                    ))

            else:
                # Check inflammation, diverticular, vascular
                for condition, pattern_data in patterns.items():
                    for pf in pattern_data["findings"]:
                        if any(pf.lower() in rf.lower() for rf in reported_findings):
                            reasoning.append(f"  Finding identified: {condition}")

                            finding = ClinicalFinding(
                                type="procedure",
                                name=f"Colonoscopy - {pattern_data['diagnosis']}",
                                value=pf,
                                status=pattern_data["severity"],
                                interpretation=pattern_data["diagnosis"],
                                source="Colonoscopy"
                            )
                            findings.append(finding)

                            if pattern_data.get("icd10"):
                                diagnoses.append(DiagnosisRecommendation(
                                    diagnosis=pattern_data["diagnosis"],
                                    icd10_code=pattern_data["icd10"],
                                    confidence=0.85,
                                    supporting_findings=[finding],
                                    rationale=f"Colonoscopy finding: {pf}"
                                ))

                            if pattern_data["severity"] == "critical":
                                warnings.append(f"CRITICAL: {pattern_data['diagnosis']}")

                            break

        # Add surveillance recommendation
        if polyp_count > 0 or findings:
            reasoning.append(f"  Total polyps: {polyp_count}")
            reasoning.append(f"  Recommended surveillance: {surveillance_interval}")

            treatments.append(TreatmentRecommendation(
                type="surveillance",
                description=f"Repeat colonoscopy in {surveillance_interval}",
                priority="routine",
                rationale=f"Based on {polyp_count} polyp(s) found during colonoscopy",
                cpt_code="45378"  # Colonoscopy CPT
            ))

        return findings, diagnoses, treatments, warnings

    def _analyze_egd(self, reported_findings: List[str], reasoning: List[str]) -> tuple:
        """Analyze upper endoscopy (EGD) findings"""
        findings = []
        diagnoses = []
        treatments = []
        warnings = []

        # Check each anatomic region
        for region, patterns in ENDOSCOPY_PATTERNS.items():
            if region == "normal":
                if any(patterns["findings"][0].lower() in rf.lower() for rf in reported_findings):
                    findings.append(ClinicalFinding(
                        type="procedure",
                        name="Upper Endoscopy",
                        value="Normal examination",
                        status="normal",
                        interpretation="Normal EGD",
                        source="EGD"
                    ))
                continue

            for condition, pattern_data in patterns.items():
                for pf in pattern_data["findings"]:
                    if any(pf.lower() in rf.lower() for rf in reported_findings):
                        reasoning.append(f"  {region.title()} finding: {condition}")

                        finding = ClinicalFinding(
                            type="procedure",
                            name=f"EGD - {pattern_data['diagnosis']}",
                            value=pf,
                            status=pattern_data["severity"],
                            interpretation=pattern_data["diagnosis"],
                            source="Upper Endoscopy"
                        )
                        findings.append(finding)

                        if pattern_data.get("icd10"):
                            diagnoses.append(DiagnosisRecommendation(
                                diagnosis=pattern_data["diagnosis"],
                                icd10_code=pattern_data["icd10"],
                                confidence=0.9,
                                supporting_findings=[finding],
                                rationale=f"EGD finding in {region}: {pf}"
                            ))

                        # Add treatment recommendations
                        if "ulcer" in condition or "gastritis" in condition:
                            treatments.append(TreatmentRecommendation(
                                type="medication",
                                description="Proton pump inhibitor (PPI) therapy",
                                priority="routine",
                                rationale=f"Treatment for {pattern_data['diagnosis']}"
                            ))

                        if "h_pylori" in condition:
                            treatments.append(TreatmentRecommendation(
                                type="medication",
                                description="H. pylori eradication therapy (triple or quadruple therapy)",
                                priority="routine",
                                rationale="H. pylori infection confirmed"
                            ))

                        if pattern_data.get("surveillance"):
                            treatments.append(TreatmentRecommendation(
                                type="surveillance",
                                description=f"Surveillance EGD in {pattern_data['surveillance']}",
                                priority="routine",
                                rationale=f"Surveillance for {pattern_data['diagnosis']}"
                            ))

                        if pattern_data["severity"] == "critical":
                            warnings.append(f"CRITICAL: {pattern_data['diagnosis']} - urgent specialist referral needed")

                        break

        return findings, diagnoses, treatments, warnings

    def _analyze_ercp(self, reported_findings: List[str], reasoning: List[str]) -> tuple:
        """Analyze ERCP findings"""
        findings = []
        diagnoses = []
        treatments = []
        warnings = []

        for condition, pattern_data in ERCP_PATTERNS.items():
            for pf in pattern_data["findings"]:
                if any(pf.lower() in rf.lower() for rf in reported_findings):
                    reasoning.append(f"  ERCP finding: {condition}")

                    finding = ClinicalFinding(
                        type="procedure",
                        name=f"ERCP - {pattern_data['diagnosis']}",
                        value=pf,
                        status=pattern_data["severity"],
                        interpretation=pattern_data["diagnosis"],
                        source="ERCP"
                    )
                    findings.append(finding)

                    if pattern_data.get("icd10"):
                        diagnoses.append(DiagnosisRecommendation(
                            diagnosis=pattern_data["diagnosis"],
                            icd10_code=pattern_data["icd10"],
                            confidence=0.9,
                            supporting_findings=[finding],
                            rationale=f"ERCP finding: {pf}"
                        ))

                    # Add treatment based on finding
                    if "stones" in condition:
                        treatments.append(TreatmentRecommendation(
                            type="procedure",
                            description="Sphincterotomy and stone extraction",
                            priority="urgent",
                            rationale="CBD stones identified on ERCP",
                            cpt_code="43264"
                        ))

                    if "stricture" in condition:
                        treatments.append(TreatmentRecommendation(
                            type="procedure",
                            description="Biliary stent placement",
                            priority="urgent",
                            rationale="Biliary stricture identified",
                            cpt_code="43274"
                        ))

                    if pattern_data["severity"] == "critical":
                        warnings.append(f"CRITICAL: {pattern_data['diagnosis']} - urgent intervention required")

                    break

        return findings, diagnoses, treatments, warnings

    def _analyze_generic_gi(self, proc_type: str, reported_findings: List[str], reasoning: List[str]) -> tuple:
        """Analyze generic GI procedure findings"""
        findings = []
        diagnoses = []
        treatments = []
        warnings = []

        reasoning.append(f"  Generic analysis of {proc_type}")

        for rf in reported_findings:
            status = "abnormal" if any(term in rf.lower() for term in ["mass", "tumor", "cancer", "malignant", "stricture"]) else "normal"

            findings.append(ClinicalFinding(
                type="procedure",
                name=proc_type.title(),
                value=rf,
                status=status,
                interpretation=rf,
                source=proc_type.title()
            ))

            if status == "abnormal":
                warnings.append(f"Abnormal finding on {proc_type}: {rf}")

        return findings, diagnoses, treatments, warnings

    def _recommend_screening(self, context: PatientContext) -> List[str]:
        """Recommend GI screening based on patient profile"""
        recommendations = []

        age = context.age or 0

        # Colonoscopy screening
        if age >= 45:
            recommendations.append("Colonoscopy screening recommended (age ≥45)")
        elif age >= 40:
            # Check for family history
            conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]
            if any("family history" in c and "colon" in c for c in conditions):
                recommendations.append("Early colonoscopy screening recommended (family history of colorectal cancer)")

        # Upper endoscopy indications
        conditions = [c.get("display", "").lower() for c in (context.conditions or []) if c and isinstance(c, dict)]

        if any("gerd" in c or "reflux" in c for c in conditions):
            recommendations.append("Consider upper endoscopy for chronic GERD evaluation")

        if any("dysphagia" in c or "difficulty swallowing" in c for c in conditions):
            recommendations.append("Upper endoscopy recommended for dysphagia evaluation")

        if any("gi bleed" in c or "blood in stool" in c or "melena" in c for c in conditions):
            recommendations.append("Urgent endoscopy/colonoscopy for GI bleeding evaluation")

        if any("weight loss" in c and "unexplained" in c for c in conditions):
            recommendations.append("Consider endoscopy and colonoscopy for unexplained weight loss")

        return recommendations
