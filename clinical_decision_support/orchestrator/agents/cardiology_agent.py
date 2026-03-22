"""
Cardiology Specialist Agent
Expert agent for cardiovascular conditions, cardiac diagnostics, and treatment.
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


# Cardiac Risk Calculators
def calculate_framingham_risk(age: int, sex: str, systolic_bp: float, total_cholesterol: float,
                                hdl: float, smoker: bool, diabetes: bool, on_bp_meds: bool) -> float:
    """Simplified Framingham Risk Score calculation"""
    # This is a simplified version - real implementation would use full algorithm
    risk = 0

    # Age factor
    if sex == "male":
        if age >= 70: risk += 10
        elif age >= 60: risk += 8
        elif age >= 50: risk += 6
        elif age >= 40: risk += 4
        else: risk += 2
    else:
        if age >= 70: risk += 8
        elif age >= 60: risk += 6
        elif age >= 50: risk += 4
        elif age >= 40: risk += 2
        else: risk += 1

    # BP factor
    if systolic_bp >= 160:
        risk += 4 if on_bp_meds else 3
    elif systolic_bp >= 140:
        risk += 3 if on_bp_meds else 2
    elif systolic_bp >= 130:
        risk += 2 if on_bp_meds else 1

    # Cholesterol factor
    if total_cholesterol >= 280: risk += 3
    elif total_cholesterol >= 240: risk += 2
    elif total_cholesterol >= 200: risk += 1

    # HDL factor (protective)
    if hdl >= 60: risk -= 1
    elif hdl < 40: risk += 2

    # Other factors
    if smoker: risk += 3
    if diabetes: risk += 3

    # Convert to approximate 10-year risk percentage
    return min(max(risk * 2, 1), 50)


# Cardiac-specific clinical thresholds
CARDIAC_THRESHOLDS = {
    "troponin": {"critical": 0.04, "unit": "ng/mL", "interpretation": "Troponin elevation suggests myocardial injury"},
    "bnp": {"elevated": 100, "high": 400, "unit": "pg/mL"},
    "nt_probnp": {"elevated": 300, "high": 900, "unit": "pg/mL"},
    "ck_mb": {"critical": 5, "unit": "ng/mL"},
    "ldl": {"optimal": 100, "borderline": 130, "high": 160, "very_high": 190, "unit": "mg/dL"},
    "hdl": {"low": 40, "optimal": 60, "unit": "mg/dL"},
}

# GDMT (Guideline-Directed Medical Therapy) for Heart Failure
HEART_FAILURE_GDMT = {
    "HFrEF": {  # EF <= 40%
        "first_line": [
            {"drug_class": "ACEi/ARB/ARNI", "examples": ["lisinopril", "losartan", "sacubitril/valsartan"]},
            {"drug_class": "Beta-blocker", "examples": ["carvedilol", "metoprolol succinate", "bisoprolol"]},
            {"drug_class": "MRA", "examples": ["spironolactone", "eplerenone"]},
            {"drug_class": "SGLT2i", "examples": ["dapagliflozin", "empagliflozin"]},
        ],
        "diuretics": ["furosemide", "bumetanide", "torsemide"],
        "device_therapy": ["ICD if EF <= 35%", "CRT if LBBB + QRS >= 150ms"]
    },
    "HFpEF": {  # EF >= 50%
        "first_line": [
            {"drug_class": "SGLT2i", "examples": ["dapagliflozin", "empagliflozin"]},
            {"drug_class": "Diuretics", "examples": ["furosemide"]},
        ],
        "management": ["BP control", "Rate control if AFib", "Treat underlying conditions"]
    }
}


class CardiologyAgent(BaseAgent):
    """
    Cardiology Specialist Agent
    - Evaluates cardiac symptoms and findings
    - Calculates cardiovascular risk scores
    - Recommends cardiac-specific diagnostics
    - Provides GDMT recommendations for heart failure
    - Interprets cardiac markers and ECG findings
    """

    def __init__(self):
        super().__init__(
            agent_id="cardiology",
            name="Cardiology Specialist",
            description="Expert agent for cardiovascular conditions and treatment",
            version="1.0.0"
        )
        self.specialties = ["cardiology", "heart_failure", "coronary_artery_disease"]

        # Initialize LLM
        self.llm: Optional[ClinicalLLM] = None
        if USE_LLM:
            try:
                self.llm = get_clinical_llm()
            except Exception:
                pass

    def _setup_capabilities(self):
        self.capabilities = [
            AgentCapability(
                name="evaluate_chest_pain",
                description="Evaluate chest pain for cardiac etiology",
                input_schema={"symptoms": "dict", "vitals": "dict", "history": "list"},
                output_schema={"risk_level": "string", "recommendations": "list"}
            ),
            AgentCapability(
                name="calculate_cv_risk",
                description="Calculate cardiovascular risk scores",
                input_schema={"patient_data": "dict"},
                output_schema={"framingham_risk": "float", "interpretation": "string"}
            ),
            AgentCapability(
                name="recommend_heart_failure_therapy",
                description="Recommend GDMT for heart failure",
                input_schema={"ef": "float", "current_meds": "list", "contraindications": "list"},
                output_schema={"recommendations": "list", "titration_plan": "list"}
            ),
            AgentCapability(
                name="interpret_cardiac_markers",
                description="Interpret cardiac biomarkers",
                input_schema={"labs": "dict"},
                output_schema={"interpretation": "dict", "urgency": "string"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Process cardiology-specific evaluation"""
        reasoning_steps = []
        findings = []
        diagnoses = []
        treatments = []
        warnings = []

        # Step 1: Analyze cardiac vitals
        reasoning_steps.append("Step 1: Analyzing cardiovascular vitals...")
        cardiac_findings = self._analyze_cardiac_vitals(context.vitals)
        findings.extend(cardiac_findings)

        # Step 2: Check cardiac markers in labs
        reasoning_steps.append("Step 2: Evaluating cardiac biomarkers...")
        marker_findings = self._analyze_cardiac_markers(context.labs)
        findings.extend(marker_findings)

        if any(f.status == "critical" for f in marker_findings):
            warnings.append("CRITICAL: Elevated cardiac markers - evaluate for ACS")

        # Step 3: Assess for heart failure
        reasoning_steps.append("Step 3: Assessing for heart failure indicators...")
        hf_assessment = self._assess_heart_failure(context, findings)
        if hf_assessment:
            diagnoses.append(hf_assessment["diagnosis"])
            treatments.extend(hf_assessment["treatments"])
            reasoning_steps.extend(hf_assessment["reasoning"])

        # Step 4: Evaluate hypertension management
        reasoning_steps.append("Step 4: Evaluating hypertension status...")
        htn_assessment = self._assess_hypertension(context, findings)
        if htn_assessment:
            diagnoses.extend(htn_assessment.get("diagnoses", []))
            treatments.extend(htn_assessment.get("treatments", []))

        # Step 5: Calculate CV risk if we have enough data
        reasoning_steps.append("Step 5: Calculating cardiovascular risk...")
        cv_risk = self._calculate_cv_risk(context)
        if cv_risk:
            reasoning_steps.append(f"  10-year ASCVD risk: {cv_risk['risk']:.1f}%")
            if cv_risk["risk"] >= 20:
                warnings.append(f"High cardiovascular risk ({cv_risk['risk']:.1f}%) - aggressive risk factor modification recommended")
            treatments.extend(cv_risk.get("recommendations", []))

        # Step 6: Recommend cardiac diagnostics
        reasoning_steps.append("Step 6: Recommending cardiac workup...")
        diagnostics = self._recommend_diagnostics(findings, diagnoses)
        treatments.extend(diagnostics)

        # Determine if specialist review needed
        requires_review = False
        review_reason = None
        critical_findings = [f for f in findings if f.status == "critical"]
        if critical_findings:
            requires_review = True
            review_reason = "Critical cardiac findings require immediate cardiology review"
        elif any("heart failure" in d.diagnosis.lower() for d in diagnoses):
            requires_review = True
            review_reason = "Heart failure diagnosis - cardiology consultation recommended"

        return self._create_output(
            findings=findings,
            diagnoses=diagnoses,
            treatments=treatments,
            confidence=0.85 if diagnoses else 0.7,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    def _analyze_cardiac_vitals(self, vitals: Optional[list]) -> List[ClinicalFinding]:
        """Analyze vitals for cardiac significance"""
        findings = []
        if not vitals:
            return findings

        # Get latest vitals
        latest = {}
        for v in vitals:
            if not v or not isinstance(v, dict):
                continue
            code = v.get("code")
            if code and code not in latest:
                latest[code] = v

        # Heart Rate Analysis
        hr_data = latest.get("8867-4", {})
        hr = hr_data.get("value")
        if hr:
            if hr < 50:
                findings.append(ClinicalFinding(
                    type="vital",
                    name="Heart Rate",
                    value=hr,
                    unit="bpm",
                    status="abnormal",
                    interpretation=f"Bradycardia ({hr} bpm) - evaluate for conduction disease, medication effect",
                    source="Cardiology Agent"
                ))
            elif hr > 100:
                status = "critical" if hr > 150 else "abnormal"
                findings.append(ClinicalFinding(
                    type="vital",
                    name="Heart Rate",
                    value=hr,
                    unit="bpm",
                    status=status,
                    interpretation=f"Tachycardia ({hr} bpm) - consider arrhythmia workup, volume status",
                    source="Cardiology Agent"
                ))

        # Blood Pressure Analysis
        bp = latest.get("85354-9", {})
        sys = None
        dia = None
        for comp in bp.get("components", []):
            if comp.get("code") == "8480-6":
                sys = comp.get("value")
            elif comp.get("code") == "8462-4":
                dia = comp.get("value")

        if sys and dia:
            if sys >= 180 or dia >= 120:
                findings.append(ClinicalFinding(
                    type="vital",
                    name="Blood Pressure",
                    value=f"{sys}/{dia}",
                    unit="mmHg",
                    status="critical",
                    interpretation=f"Hypertensive crisis ({sys}/{dia}) - immediate treatment needed, assess for end-organ damage",
                    source="Cardiology Agent"
                ))
            elif sys >= 140 or dia >= 90:
                findings.append(ClinicalFinding(
                    type="vital",
                    name="Blood Pressure",
                    value=f"{sys}/{dia}",
                    unit="mmHg",
                    status="abnormal",
                    interpretation=f"Hypertension Stage 2 ({sys}/{dia}) - optimize antihypertensive therapy",
                    source="Cardiology Agent"
                ))
            elif sys < 90:
                findings.append(ClinicalFinding(
                    type="vital",
                    name="Blood Pressure",
                    value=f"{sys}/{dia}",
                    unit="mmHg",
                    status="abnormal",
                    interpretation=f"Hypotension ({sys}/{dia}) - assess volume status, cardiac output",
                    source="Cardiology Agent"
                ))

        return findings

    def _analyze_cardiac_markers(self, labs: Optional[list]) -> List[ClinicalFinding]:
        """Analyze cardiac biomarkers"""
        findings = []
        if not labs:
            return findings

        for lab in labs:
            name = lab.get("name", "").lower()
            value = lab.get("value")

            if not value:
                continue

            if "troponin" in name:
                if value > 0.04:
                    findings.append(ClinicalFinding(
                        type="lab",
                        name="Troponin",
                        value=value,
                        unit="ng/mL",
                        status="critical",
                        interpretation=f"Elevated troponin ({value}) - myocardial injury, evaluate for ACS/NSTEMI",
                        source="Cardiology Agent"
                    ))

            elif "bnp" in name or "nt-probnp" in name:
                threshold = 400 if "nt" in name else 100
                if value > threshold:
                    findings.append(ClinicalFinding(
                        type="lab",
                        name="BNP/NT-proBNP",
                        value=value,
                        unit="pg/mL",
                        status="abnormal",
                        interpretation=f"Elevated natriuretic peptide ({value}) - suggestive of heart failure",
                        source="Cardiology Agent"
                    ))

        return findings

    def _assess_heart_failure(self, context: PatientContext, findings: List[ClinicalFinding]) -> Optional[Dict]:
        """Assess for heart failure and recommend GDMT"""
        # Check for HF indicators
        hf_indicators = 0
        for finding in findings:
            if "bnp" in finding.name.lower() or "natriuretic" in finding.name.lower():
                hf_indicators += 2
            if "edema" in finding.interpretation.lower():
                hf_indicators += 1

        # Check conditions
        has_hf_diagnosis = False
        for condition in (context.conditions or []):
            if not condition or not isinstance(condition, dict):
                continue
            if "heart failure" in condition.get("display", "").lower():
                has_hf_diagnosis = True
                break

        if not has_hf_diagnosis and hf_indicators < 2:
            return None

        # Generate GDMT recommendations
        treatments = []
        reasoning = ["Heart failure identified - recommending GDMT per 2022 AHA/ACC guidelines"]

        # Check current medications
        current_meds = [m.get("medication_name", "").lower() for m in (context.medications or []) if m and isinstance(m, dict)]

        # ACEi/ARB/ARNI
        has_raas = any(med in current_meds for med in ["lisinopril", "enalapril", "losartan", "valsartan", "entresto"])
        if not has_raas:
            treatments.append(TreatmentRecommendation(
                treatment_type="medication",
                description="Initiate ACEi (lisinopril 2.5-5mg daily) - uptitrate to target dose",
                priority="urgent",
                rationale="RAAS inhibition reduces mortality in HFrEF",
                cpt_code="99214",
                contraindications=["hyperkalemia", "bilateral renal artery stenosis", "angioedema"]
            ))
            reasoning.append("  - Adding ACEi for RAAS inhibition")

        # Beta-blocker
        has_bb = any(med in current_meds for med in ["carvedilol", "metoprolol", "bisoprolol"])
        if not has_bb:
            treatments.append(TreatmentRecommendation(
                treatment_type="medication",
                description="Initiate beta-blocker (carvedilol 3.125mg BID) - uptitrate to target",
                priority="urgent",
                rationale="Beta-blockers reduce mortality in HFrEF",
                cpt_code="99214",
                contraindications=["severe bradycardia", "decompensated HF", "advanced heart block"]
            ))
            reasoning.append("  - Adding beta-blocker")

        # SGLT2i
        has_sglt2 = any(med in current_meds for med in ["dapagliflozin", "empagliflozin"])
        if not has_sglt2:
            treatments.append(TreatmentRecommendation(
                treatment_type="medication",
                description="Add SGLT2 inhibitor (dapagliflozin 10mg daily)",
                priority="routine",
                rationale="SGLT2i reduces HF hospitalizations regardless of diabetes status",
                cpt_code="99214",
                contraindications=["eGFR < 20"]
            ))
            reasoning.append("  - Adding SGLT2 inhibitor")

        # Echo if not recent
        treatments.append(TreatmentRecommendation(
            treatment_type="procedure",
            description="Echocardiogram to assess EF and structure",
            priority="urgent",
            rationale="Baseline echo needed to guide therapy (HFrEF vs HFpEF)",
            cpt_code="93306"
        ))

        return {
            "diagnosis": DiagnosisRecommendation(
                diagnosis="Heart Failure",
                icd10_code="I50.9",
                confidence=0.8,
                supporting_findings=findings,
                rationale="Clinical indicators suggest heart failure - needs echo for EF assessment"
            ),
            "treatments": treatments,
            "reasoning": reasoning
        }

    def _assess_hypertension(self, context: PatientContext, findings: List[ClinicalFinding]) -> Optional[Dict]:
        """Assess hypertension status and recommend treatment"""
        bp_findings = [f for f in findings if "blood pressure" in f.name.lower()]
        if not bp_findings:
            return None

        diagnoses = []
        treatments = []

        for finding in bp_findings:
            if finding.status in ["abnormal", "critical"]:
                diagnoses.append(DiagnosisRecommendation(
                    diagnosis="Essential Hypertension",
                    icd10_code="I10",
                    confidence=0.85,
                    supporting_findings=[finding],
                    rationale=finding.interpretation
                ))

                if finding.status == "critical":
                    treatments.append(TreatmentRecommendation(
                        treatment_type="medication",
                        description="IV labetalol or nicardipine for hypertensive emergency",
                        priority="immediate",
                        rationale="Urgent BP reduction needed",
                        cpt_code="99215"
                    ))

        return {"diagnoses": diagnoses, "treatments": treatments} if diagnoses else None

    def _calculate_cv_risk(self, context: PatientContext) -> Optional[Dict]:
        """Calculate cardiovascular risk"""
        if not context.age or not context.sex:
            return None

        # Get BP from vitals
        systolic = None
        if context.vitals:
            for v in context.vitals:
                if not v or not isinstance(v, dict):
                    continue
                if v.get("code") == "85354-9":
                    for comp in v.get("components", []):
                        if not comp or not isinstance(comp, dict):
                            continue
                        if comp.get("code") == "8480-6":
                            systolic = comp.get("value")
                            break

        if not systolic:
            return None

        # Check for diabetes
        has_diabetes = any(
            "diabetes" in c.get("display", "").lower()
            for c in (context.conditions or [])
            if c and isinstance(c, dict)
        )

        # Simplified risk calculation
        risk = 5.0  # Base risk

        # Age adjustment
        if context.age >= 65:
            risk += 10
        elif context.age >= 55:
            risk += 5
        elif context.age >= 45:
            risk += 2

        # BP adjustment
        if systolic >= 160:
            risk += 8
        elif systolic >= 140:
            risk += 4
        elif systolic >= 130:
            risk += 2

        # Other factors
        if has_diabetes:
            risk += 5
        if context.sex == "male":
            risk += 3

        recommendations = []
        if risk >= 7.5:
            recommendations.append(TreatmentRecommendation(
                treatment_type="medication",
                description="Consider moderate-intensity statin therapy",
                priority="routine",
                rationale=f"10-year ASCVD risk {risk:.1f}% - statin therapy indicated per ACC/AHA guidelines",
                cpt_code="99214"
            ))

        return {
            "risk": risk,
            "recommendations": recommendations
        }

    def _recommend_diagnostics(self, findings: List[ClinicalFinding], diagnoses: List[DiagnosisRecommendation]) -> List[TreatmentRecommendation]:
        """Recommend appropriate cardiac diagnostics"""
        diagnostics = []

        # ECG for any cardiac concern
        if findings:
            diagnostics.append(TreatmentRecommendation(
                treatment_type="procedure",
                description="12-lead ECG",
                priority="urgent",
                rationale="Baseline cardiac rhythm and conduction assessment",
                cpt_code="93000"
            ))

        # Lipid panel if not recent
        diagnostics.append(TreatmentRecommendation(
            treatment_type="procedure",
            description="Lipid panel (fasting)",
            priority="routine",
            rationale="Cardiovascular risk assessment",
            cpt_code="80061"
        ))

        # BNP if HF suspected
        if any("heart failure" in d.diagnosis.lower() for d in diagnoses):
            diagnostics.append(TreatmentRecommendation(
                treatment_type="procedure",
                description="BNP or NT-proBNP",
                priority="urgent",
                rationale="Confirm heart failure diagnosis",
                cpt_code="83880"
            ))

        return diagnostics


# Singleton instance
cardiology_agent = CardiologyAgent()
