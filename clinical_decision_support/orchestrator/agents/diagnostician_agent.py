"""
Diagnostician Agent
Analyzes patient data to generate differential diagnoses with ICD-10 codes.
Uses LLM for clinical reasoning and MCP-RAG for guideline references.
"""

import os
import json
from typing import List, Optional
from .base_agent import (
    BaseAgent, PatientContext, AgentOutput, AgentCapability,
    ClinicalFinding, DiagnosisRecommendation
)

# Support both package import and direct execution
try:
    from ..llm import get_clinical_llm, ClinicalLLM
except ImportError:
    from llm import get_clinical_llm, ClinicalLLM

# LLM Configuration
USE_LLM = os.getenv("USE_LLM", "true").lower() == "true"


class DiagnosticianAgent(BaseAgent):
    """
    AI Diagnostician Agent
    - Analyzes clinical data to generate differential diagnoses
    - Provides ICD-10 codes with confidence scores
    - Uses clinical guidelines for evidence-based reasoning
    """

    def __init__(self):
        super().__init__(
            agent_id="diagnostician",
            name="AI Diagnostician",
            description="Analyzes clinical data to generate differential diagnoses with ICD-10 codes",
            version="1.0.0"
        )
        self.specialties = ["internal_medicine", "emergency_medicine", "primary_care"]

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
                name="generate_differential",
                description="Generate differential diagnosis from clinical presentation",
                input_schema={"patient_context": "PatientContext"},
                output_schema={"diagnoses": "List[DiagnosisRecommendation]"}
            ),
            AgentCapability(
                name="interpret_labs",
                description="Interpret laboratory results in clinical context",
                input_schema={"labs": "dict", "conditions": "list"},
                output_schema={"interpretations": "list"}
            ),
            AgentCapability(
                name="suggest_icd10",
                description="Suggest ICD-10 codes for documented findings",
                input_schema={"findings": "list"},
                output_schema={"icd10_codes": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Main processing: analyze patient and generate diagnoses"""
        reasoning_steps = []
        findings = []
        warnings = []

        # Step 0: Review chief complaint, physician notes, and patient questionnaires
        if context.chief_complaint:
            reasoning_steps.append(f"Chief Complaint: {context.chief_complaint}")
            findings.append(ClinicalFinding(
                type="history",
                name="Chief Complaint",
                value=context.chief_complaint,
                status="normal",  # Will be updated based on content
                interpretation=f"Patient presents with: {context.chief_complaint}",
                source="Clinical History"
            ))

        if context.physician_notes:
            reasoning_steps.append(f"Physician Notes: {context.physician_notes[:200]}...")
            findings.append(ClinicalFinding(
                type="notes",
                name="Physician Assessment",
                value=context.physician_notes[:500] if len(context.physician_notes) > 500 else context.physician_notes,
                status="normal",
                interpretation="See physician notes for clinical assessment",
                source="Physician Notes"
            ))

        if context.history_present_illness:
            reasoning_steps.append(f"HPI reviewed: {context.history_present_illness[:100]}...")
            findings.append(ClinicalFinding(
                type="history",
                name="History of Present Illness",
                value=context.history_present_illness,
                status="normal",
                interpretation=context.history_present_illness,
                source="Clinical History"
            ))

        # Step 0b: Process patient-submitted questionnaire data
        if context.questionnaire_responses:
            reasoning_steps.append(f"Reviewing {len(context.questionnaire_responses)} patient questionnaire(s)...")
            q_findings = self._analyze_questionnaires(context.questionnaire_responses)
            findings.extend(q_findings)

        # Step 1: Analyze vitals
        reasoning_steps.append("Step 1: Analyzing vital signs...")
        vital_findings = self._analyze_vitals(context.vitals)
        findings.extend(vital_findings)

        # Step 2: Analyze labs
        reasoning_steps.append("Step 2: Analyzing laboratory results...")
        lab_findings = self._analyze_labs(context.labs)
        findings.extend(lab_findings)

        # Step 3: Review current conditions
        reasoning_steps.append("Step 3: Reviewing current conditions and medications...")
        condition_context = self._build_condition_context(context)

        # Step 4: Generate differential diagnosis
        reasoning_steps.append("Step 4: Generating differential diagnosis...")

        if self.llm:
            diagnoses = await self._llm_differential(context, findings)
        else:
            diagnoses = self._rule_based_differential(context, findings)

        # Step 5: Validate against guidelines
        reasoning_steps.append("Step 5: Validating against clinical guidelines...")
        diagnoses = await self._validate_with_guidelines(diagnoses)

        # Check for critical findings
        critical_findings = [f for f in findings if f.status == "critical"]
        if critical_findings:
            warnings.append(f"CRITICAL: {len(critical_findings)} critical findings require immediate attention")

        # Determine if human review needed
        requires_review = False
        review_reason = None
        if any(d.confidence < 0.7 for d in diagnoses):
            requires_review = True
            review_reason = "Low confidence diagnoses require physician review"
        if len(diagnoses) == 0:
            requires_review = True
            review_reason = "Unable to determine diagnosis - physician evaluation required"

        return self._create_output(
            findings=findings,
            diagnoses=diagnoses,
            confidence=max([d.confidence for d in diagnoses]) if diagnoses else 0.0,
            reasoning=reasoning_steps,
            warnings=warnings,
            requires_review=requires_review,
            review_reason=review_reason
        )

    def _analyze_vitals(self, vitals: Optional[list]) -> List[ClinicalFinding]:
        """Analyze vital signs and generate findings"""
        findings = []
        if not vitals:
            return findings

        # Get latest vitals by type
        latest = {}
        for v in vitals:
            if not v or not isinstance(v, dict):
                continue
            code = v.get("code")
            if code and code not in latest:
                latest[code] = v

        # Heart Rate
        hr = latest.get("8867-4", {}).get("value")
        if hr:
            status = "normal"
            interpretation = "Heart rate within normal limits"
            if hr < 60:
                status = "abnormal"
                interpretation = f"Bradycardia ({hr} bpm)"
            elif hr > 100:
                status = "abnormal"
                interpretation = f"Tachycardia ({hr} bpm)"
            elif hr > 150:
                status = "critical"
                interpretation = f"Severe tachycardia ({hr} bpm) - evaluate for arrhythmia"

            findings.append(ClinicalFinding(
                type="vital",
                name="Heart Rate",
                value=hr,
                unit="bpm",
                status=status,
                interpretation=interpretation,
                source="FHIR Observation"
            ))

        # Blood Pressure (from BP panel)
        bp = latest.get("85354-9") or {}
        sys = None
        dia = None
        for comp in bp.get("components", []):
            if not comp or not isinstance(comp, dict):
                continue
            if comp.get("code") == "8480-6":
                sys = comp.get("value")
            elif comp.get("code") == "8462-4":
                dia = comp.get("value")

        if sys and dia:
            status = "normal"
            interpretation = "Blood pressure within normal limits"
            if sys >= 180 or dia >= 120:
                status = "critical"
                interpretation = f"Hypertensive crisis ({sys}/{dia} mmHg) - immediate treatment needed"
            elif sys >= 140 or dia >= 90:
                status = "abnormal"
                interpretation = f"Hypertension Stage 2 ({sys}/{dia} mmHg)"
            elif sys >= 130 or dia >= 80:
                status = "abnormal"
                interpretation = f"Hypertension Stage 1 ({sys}/{dia} mmHg)"
            elif sys < 90 or dia < 60:
                status = "abnormal"
                interpretation = f"Hypotension ({sys}/{dia} mmHg) - assess for cause"

            findings.append(ClinicalFinding(
                type="vital",
                name="Blood Pressure",
                value=f"{sys}/{dia}",
                unit="mmHg",
                status=status,
                interpretation=interpretation,
                source="FHIR Observation"
            ))

        # SpO2
        spo2 = latest.get("59408-5", {}).get("value")
        if spo2:
            status = "normal"
            interpretation = "Oxygen saturation normal"
            if spo2 < 88:
                status = "critical"
                interpretation = f"Severe hypoxemia (SpO2 {spo2}%) - supplemental oxygen needed"
            elif spo2 < 92:
                status = "abnormal"
                interpretation = f"Hypoxemia (SpO2 {spo2}%) - monitor closely"

            findings.append(ClinicalFinding(
                type="vital",
                name="SpO2",
                value=spo2,
                unit="%",
                status=status,
                interpretation=interpretation,
                source="FHIR Observation"
            ))

        # Temperature
        temp = latest.get("8310-5", {}).get("value")
        if temp:
            status = "normal"
            interpretation = "Temperature normal"
            if temp >= 38.3:
                status = "abnormal"
                interpretation = f"Fever ({temp}°C) - evaluate for infection"
            elif temp >= 40:
                status = "critical"
                interpretation = f"High fever ({temp}°C) - urgent evaluation needed"
            elif temp < 36:
                status = "abnormal"
                interpretation = f"Hypothermia ({temp}°C)"

            findings.append(ClinicalFinding(
                type="vital",
                name="Temperature",
                value=temp,
                unit="°C",
                status=status,
                interpretation=interpretation,
                source="FHIR Observation"
            ))

        # Blood Glucose
        glucose = latest.get("2339-0", {}).get("value")
        if glucose:
            status = "normal"
            interpretation = "Blood glucose within normal limits"
            if glucose >= 400:
                status = "critical"
                interpretation = f"Severe hyperglycemia ({glucose} mg/dL) - risk of DKA/HHS"
            elif glucose >= 250:
                status = "abnormal"
                interpretation = f"Hyperglycemia ({glucose} mg/dL) - adjust insulin/medications"
            elif glucose >= 126:
                status = "abnormal"
                interpretation = f"Elevated fasting glucose ({glucose} mg/dL) - diabetic range"
            elif glucose >= 100:
                status = "abnormal"
                interpretation = f"Impaired fasting glucose ({glucose} mg/dL) - pre-diabetic"
            elif glucose < 70:
                status = "critical"
                interpretation = f"Hypoglycemia ({glucose} mg/dL) - treat immediately"
            elif glucose < 54:
                status = "critical"
                interpretation = f"Severe hypoglycemia ({glucose} mg/dL) - emergency treatment needed"

            findings.append(ClinicalFinding(
                type="vital",
                name="Blood Glucose",
                value=glucose,
                unit="mg/dL",
                status=status,
                interpretation=interpretation,
                source="FHIR Observation"
            ))

        # Respiratory Rate
        rr = latest.get("9279-1", {}).get("value")
        if rr:
            status = "normal"
            interpretation = "Respiratory rate within normal limits"
            if rr < 8:
                status = "critical"
                interpretation = f"Severe bradypnea ({rr} /min) - assess airway"
            elif rr < 12:
                status = "abnormal"
                interpretation = f"Bradypnea ({rr} /min)"
            elif rr > 30:
                status = "critical"
                interpretation = f"Severe tachypnea ({rr} /min) - assess respiratory distress"
            elif rr > 20:
                status = "abnormal"
                interpretation = f"Tachypnea ({rr} /min) - evaluate for respiratory distress"

            findings.append(ClinicalFinding(
                type="vital",
                name="Respiratory Rate",
                value=rr,
                unit="/min",
                status=status,
                interpretation=interpretation,
                source="FHIR Observation"
            ))

        # ECG - Look for ECG interpretation observations
        ecg = latest.get("8601-7", {})
        if ecg:
            # Use top-level ecg fields from MCP server if available
            rhythm = ecg.get("ecg_rhythm")
            ecg_findings = ecg.get("ecg_findings", [])

            # Fall back to component parsing if top-level fields not present
            if not rhythm and not ecg_findings:
                components = ecg.get("components", [])
                for comp in components:
                    if not comp or not isinstance(comp, dict):
                        continue
                    code = comp.get("code")
                    value = comp.get("value") or comp.get("valueString")
                    if code == "8884-9":  # Heart rhythm
                        rhythm = value
                    elif code == "18844-1":  # ECG finding
                        if value:
                            ecg_findings.append(value)

            if rhythm or ecg_findings:
                status = "normal"
                interpretation = rhythm or "Normal sinus rhythm"

                # Check for concerning findings
                concerning_terms = ["fibrillation", "flutter", "ST elevation", "ST depression",
                                   "MI", "ischemic", "block", "tachycardia", "bradycardia"]
                for finding in ecg_findings:
                    if any(term.lower() in finding.lower() for term in concerning_terms):
                        status = "abnormal"
                        break

                if "fibrillation" in str(rhythm).lower() or "MI" in str(ecg_findings):
                    status = "critical"

                findings.append(ClinicalFinding(
                    type="ecg",
                    name="ECG Interpretation",
                    value=rhythm or "See findings",
                    unit="",
                    status=status,
                    interpretation=f"{interpretation}. Findings: {', '.join(ecg_findings) if ecg_findings else 'None'}",
                    source="ECG Monitor"
                ))

        return findings

    def _analyze_labs(self, labs: Optional[list]) -> List[ClinicalFinding]:
        """Analyze laboratory results"""
        findings = []
        if not labs:
            return findings

        for lab in labs[:20]:  # Limit to recent labs
            if not lab or not isinstance(lab, dict):
                continue
            interpretation = lab.get("interpretation") or {}
            if interpretation and interpretation.get("severity") != "normal":
                findings.append(ClinicalFinding(
                    type="lab",
                    name=lab.get("name", "Unknown"),
                    value=lab.get("value"),
                    unit=lab.get("unit", ""),
                    status=interpretation.get("severity", "abnormal"),
                    interpretation=interpretation.get("message", "Abnormal result"),
                    source="Laboratory"
                ))

        return findings

    def _build_condition_context(self, context: PatientContext) -> dict:
        """Build context from current conditions and medications"""
        return {
            "conditions": [c.get("display") for c in (context.conditions or []) if c and isinstance(c, dict)],
            "medications": [m.get("medication_name") for m in (context.medications or []) if m and isinstance(m, dict)],
            "allergies": [a.get("substance") for a in (context.allergies or []) if a and isinstance(a, dict)]
        }

    def _rule_based_differential(
        self,
        context: PatientContext,
        findings: List[ClinicalFinding]
    ) -> List[DiagnosisRecommendation]:
        """Generate differential diagnosis using clinical rules"""
        diagnoses = []
        finding_names = [f.name.lower() for f in findings]
        abnormal = [f for f in findings if f.status in ["abnormal", "critical"]]

        # Pattern matching for common diagnoses
        patterns = [
            {
                "name": "Essential Hypertension",
                "icd10": "I10",
                "triggers": ["blood pressure"],
                "condition": lambda f: any(
                    "hypertension" in f.interpretation.lower()
                    for f in findings if f.name == "Blood Pressure"
                )
            },
            {
                "name": "Tachycardia",
                "icd10": "R00.0",
                "triggers": ["heart rate"],
                "condition": lambda f: any(
                    "tachycardia" in f.interpretation.lower()
                    for f in findings if f.name == "Heart Rate"
                )
            },
            {
                "name": "Hypoxemia",
                "icd10": "R09.02",
                "triggers": ["spo2"],
                "condition": lambda f: any(
                    f.status in ["abnormal", "critical"]
                    for f in findings if f.name == "SpO2"
                )
            },
            {
                "name": "Fever, unspecified",
                "icd10": "R50.9",
                "triggers": ["temperature"],
                "condition": lambda f: any(
                    "fever" in f.interpretation.lower()
                    for f in findings if f.name == "Temperature"
                )
            },
            {
                "name": "Atrial fibrillation, unspecified",
                "icd10": "I48.91",
                "triggers": ["ecg"],
                "condition": lambda f: any(
                    "fibrillation" in f.interpretation.lower()
                    for f in findings if f.name == "ECG Interpretation"
                )
            },
            {
                "name": "Cardiac arrhythmia, unspecified",
                "icd10": "I49.9",
                "triggers": ["ecg"],
                "condition": lambda f: any(
                    f.status in ["abnormal", "critical"]
                    for f in findings if f.name == "ECG Interpretation"
                )
            },
            {
                "name": "Hyperglycemia, unspecified",
                "icd10": "R73.9",
                "triggers": ["blood glucose"],
                "condition": lambda f: any(
                    "hyperglycemia" in f.interpretation.lower() or "diabetic" in f.interpretation.lower()
                    for f in findings if f.name == "Blood Glucose"
                )
            },
            {
                "name": "Hypoglycemia, unspecified",
                "icd10": "E16.2",
                "triggers": ["blood glucose"],
                "condition": lambda f: any(
                    "hypoglycemia" in f.interpretation.lower()
                    for f in findings if f.name == "Blood Glucose"
                )
            },
            {
                "name": "Tachypnea",
                "icd10": "R06.82",
                "triggers": ["respiratory rate"],
                "condition": lambda f: any(
                    "tachypnea" in f.interpretation.lower()
                    for f in findings if f.name == "Respiratory Rate"
                )
            },
        ]

        for pattern in patterns:
            if any(t in " ".join(finding_names) for t in pattern["triggers"]):
                if pattern["condition"](findings):
                    supporting = [f for f in abnormal if any(t in f.name.lower() for t in pattern["triggers"])]
                    diagnoses.append(DiagnosisRecommendation(
                        diagnosis=pattern["name"],
                        icd10_code=pattern["icd10"],
                        confidence=0.75,
                        supporting_findings=supporting,
                        rationale=f"Based on abnormal {', '.join(pattern['triggers'])} findings"
                    ))

        # If no specific patterns matched but have abnormal findings
        if not diagnoses and abnormal:
            diagnoses.append(DiagnosisRecommendation(
                diagnosis="Abnormal clinical findings, unspecified",
                icd10_code="R68.89",
                confidence=0.5,
                supporting_findings=abnormal,
                rationale="Multiple abnormal findings requiring clinical correlation"
            ))

        return diagnoses

    async def _llm_differential(
        self,
        context: PatientContext,
        findings: List[ClinicalFinding]
    ) -> List[DiagnosisRecommendation]:
        """Use LLM for advanced differential diagnosis"""
        if not self.llm:
            return self._rule_based_differential(context, findings)

        # Build prompt
        chief_complaint = context.chief_complaint or "Not documented"
        hpi = context.history_present_illness or "Not documented"
        physician_notes = context.physician_notes or "Not documented"

        prompt = f"""Analyze this patient data and provide a differential diagnosis.

Patient Information:
- Age: {context.age or 'Unknown'}
- Sex: {context.sex or 'Unknown'}

Chief Complaint:
{chief_complaint}

History of Present Illness:
{hpi}

Physician Notes/Assessment:
{physician_notes}

Clinical Findings:
{self._format_findings(findings)}

Current Conditions:
{', '.join([c.get('display', '') for c in (context.conditions or []) if c and isinstance(c, dict)]) or 'None documented'}

Current Medications:
{', '.join([m.get('medication_name', '') for m in (context.medications or []) if m and isinstance(m, dict)]) or 'None documented'}

Allergies:
{', '.join([a.get('substance', '') for a in (context.allergies or []) if a and isinstance(a, dict)]) or 'NKDA'}

Past Medical History:
{', '.join(context.past_medical_history or []) or 'Not documented'}

Family History:
{', '.join(context.family_history or []) or 'Not documented'}

Patient-Reported Symptoms (from questionnaires):
{self._format_questionnaire_data(context)}

Please provide:
1. Primary diagnosis with ICD-10 code and confidence (0-1)
2. Up to 3 differential diagnoses with ICD-10 codes
3. Rationale for each diagnosis

Format your response as JSON:
{{
    "primary": {{
        "diagnosis": "...",
        "icd10": "...",
        "confidence": 0.0-1.0,
        "rationale": "..."
    }},
    "differentials": [
        {{"diagnosis": "...", "icd10": "...", "confidence": 0.0-1.0, "rationale": "..."}}
    ]
}}"""

        try:
            # Use unified LLM interface
            response = await self.llm.generate(
                prompt=prompt,
                task_type="differential_diagnosis",
                patient_id=context.patient_id,
                json_mode=True
            )

            content = response["content"]

            # Extract JSON from response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(content[start:end])

                diagnoses = []
                if data.get("primary"):
                    p = data["primary"]
                    diagnoses.append(DiagnosisRecommendation(
                        diagnosis=p.get("diagnosis", ""),
                        icd10_code=p.get("icd10", ""),
                        confidence=p.get("confidence", 0.8),
                        supporting_findings=findings,
                        rationale=p.get("rationale", ""),
                        differential_diagnoses=data.get("differentials", [])
                    ))

                for diff in data.get("differentials", []):
                    diagnoses.append(DiagnosisRecommendation(
                        diagnosis=diff.get("diagnosis", ""),
                        icd10_code=diff.get("icd10", ""),
                        confidence=diff.get("confidence", 0.5),
                        supporting_findings=[],
                        rationale=diff.get("rationale", "")
                    ))

                return diagnoses

        except Exception as e:
            import logging
            logging.error(f"LLM diagnosis failed: {e}")

        # Fall back to rule-based
        return self._rule_based_differential(context, findings)

    async def _validate_with_guidelines(
        self,
        diagnoses: List[DiagnosisRecommendation]
    ) -> List[DiagnosisRecommendation]:
        """Validate diagnoses against clinical guidelines"""
        try:
            for diagnosis in diagnoses:
                # Query RAG for supporting guidelines
                result = await self.mcp.call_tool(
                    "rag",
                    "search_guidelines",
                    {"query": diagnosis.diagnosis}
                )

                guidelines = result.get("guidelines", [])
                if guidelines:
                    diagnosis.rationale += f"\n\nGuideline support: {guidelines[0].get('title', '')}"

        except Exception as e:
            import logging
            logging.warning(f"Guideline validation failed: {e}")

        return diagnoses

    def _format_findings(self, findings: List[ClinicalFinding]) -> str:
        """Format findings for LLM prompt"""
        lines = []
        for f in findings:
            status_emoji = "🔴" if f.status == "critical" else "🟡" if f.status == "abnormal" else "🟢"
            lines.append(f"{status_emoji} {f.name}: {f.value} {f.unit or ''} - {f.interpretation}")
        return "\n".join(lines) if lines else "No significant findings"

    def _analyze_questionnaires(self, questionnaires: Optional[List[dict]]) -> List[ClinicalFinding]:
        """Extract clinical findings from patient-submitted questionnaires."""
        findings = []
        if not questionnaires:
            return findings

        for q in questionnaires:
            q_type = q.get("questionnaire_type", "")
            responses = q.get("responses", {})
            if not responses:
                continue

            if q_type == "review_of_systems":
                # Extract positive ROS findings
                positive_symptoms = []
                for key, val in responses.items():
                    if val is True:
                        symptom = key.replace("_", " ")
                        positive_symptoms.append(symptom)
                if positive_symptoms:
                    findings.append(ClinicalFinding(
                        type="questionnaire",
                        name="Review of Systems - Positive",
                        value=", ".join(positive_symptoms),
                        status="abnormal" if len(positive_symptoms) > 5 else "normal",
                        interpretation=f"Patient reports {len(positive_symptoms)} positive ROS finding(s): {', '.join(positive_symptoms[:10])}",
                        source="Patient Questionnaire"
                    ))

            elif q_type == "history_presenting_illness":
                if responses.get("chief_complaint"):
                    findings.append(ClinicalFinding(
                        type="questionnaire",
                        name="Patient-Reported Chief Complaint",
                        value=responses["chief_complaint"],
                        status="normal",
                        interpretation=f"Patient reports: {responses['chief_complaint']}",
                        source="Patient Questionnaire"
                    ))
                severity = responses.get("severity")
                if severity and severity in ("Moderate", "Severe"):
                    findings.append(ClinicalFinding(
                        type="questionnaire",
                        name="Patient-Reported Severity",
                        value=severity,
                        status="abnormal" if severity == "Severe" else "normal",
                        interpretation=f"Patient rates symptom severity as {severity}",
                        source="Patient Questionnaire"
                    ))

            elif q_type == "pre_visit":
                pain = responses.get("pain_level")
                if pain and str(pain) not in ("0", ""):
                    pain_val = int(pain) if str(pain).isdigit() else 0
                    findings.append(ClinicalFinding(
                        type="questionnaire",
                        name="Patient-Reported Pain Level",
                        value=f"{pain}/10",
                        status="critical" if pain_val >= 8 else "abnormal" if pain_val >= 5 else "normal",
                        interpretation=f"Patient reports pain level {pain}/10",
                        source="Patient Questionnaire"
                    ))
                # PHQ-2/GAD-2 mental health screening
                for key, label in [("feeling_down", "Depression screen"), ("feeling_nervous", "Anxiety screen")]:
                    val = responses.get(key)
                    if val and val != "Not at all":
                        findings.append(ClinicalFinding(
                            type="questionnaire",
                            name=f"Mental Health - {label}",
                            value=val,
                            status="abnormal" if val in ("More than half the days", "Nearly every day") else "normal",
                            interpretation=f"{label}: {val}",
                            source="Patient Questionnaire"
                        ))

        return findings

    def _format_questionnaire_data(self, context: PatientContext) -> str:
        """Format questionnaire data for LLM prompt."""
        if not context.questionnaire_responses:
            return "No patient questionnaires submitted"

        parts = []
        for q in context.questionnaire_responses:
            q_type = q.get("questionnaire_type", "unknown")
            responses = q.get("responses", {})

            if q_type == "review_of_systems":
                positive = [k.replace("_", " ") for k, v in responses.items() if v is True]
                if positive:
                    parts.append(f"Review of Systems - Positive findings: {', '.join(positive)}")
                notes = [f"{k}: {v}" for k, v in responses.items() if isinstance(v, str) and v.strip() and k.endswith("_notes")]
                if notes:
                    parts.append(f"ROS Notes: {'; '.join(notes)}")

            elif q_type == "history_presenting_illness":
                for key in ["chief_complaint", "onset", "duration", "severity",
                            "characteristics", "aggravating_factors", "relieving_factors",
                            "associated_symptoms", "prior_treatments"]:
                    val = responses.get(key)
                    if val:
                        parts.append(f"HPI {key.replace('_', ' ')}: {val}")

            elif q_type == "pre_visit":
                for key in ["visit_reason", "pain_level", "pain_description",
                            "functional_status", "current_medications",
                            "smoking_status", "alcohol_use"]:
                    val = responses.get(key)
                    if val:
                        parts.append(f"{key.replace('_', ' ').title()}: {val}")
                # Mental health items
                for key in ["feeling_down", "little_interest", "feeling_nervous", "worry_control"]:
                    val = responses.get(key)
                    if val and val != "Not at all":
                        parts.append(f"{key.replace('_', ' ').title()}: {val}")

        return "\n".join(parts) if parts else "No significant questionnaire data"
