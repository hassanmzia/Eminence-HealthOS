"""
Supervisor Agent
Orchestrates all specialist agents to generate comprehensive clinical recommendations.
Implements the supervisor pattern for multi-agent coordination.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from .base_agent import (
    BaseAgent, PatientContext, AgentOutput, AgentCapability,
    AgentMessage, ClinicalFinding, DiagnosisRecommendation, TreatmentRecommendation
)
from .diagnostician_agent import DiagnosticianAgent
from .treatment_agent import TreatmentAgent
from .safety_agent import SafetyAgent
from .coding_agent import CodingAgent
from .cardiology_agent import CardiologyAgent
from .radiology_agent import RadiologyAgent
from .pathology_agent import PathologyAgent
from .gastroenterology_agent import GastroenterologyAgent
from .oncology_agent import OncologyAgent


class ComprehensiveRecommendation(BaseModel):
    """Final output combining all agent outputs"""
    patient_id: str
    timestamp: str

    # Patient summary
    patient_summary: dict

    # Clinical findings
    findings: List[ClinicalFinding]
    critical_findings: List[ClinicalFinding]

    # Diagnoses
    primary_diagnosis: Optional[DiagnosisRecommendation]
    differential_diagnoses: List[DiagnosisRecommendation]

    # Treatment plan
    treatments: List[TreatmentRecommendation]
    immediate_actions: List[TreatmentRecommendation]

    # Coding
    icd10_codes: List[dict]
    cpt_codes: List[dict]

    # Quality metrics
    overall_confidence: float
    reasoning_chain: List[str]
    warnings: List[str]

    # Review requirements
    requires_human_review: bool
    review_reasons: List[str]

    # Agent contributions
    agent_outputs: Dict[str, dict]


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent - Orchestrates the multi-agent clinical decision system.

    Workflow:
    1. Gather patient context from MCP servers
    2. Invoke Triage Agent for urgency assessment
    3. Invoke Diagnostician Agent for differential diagnosis
    4. Invoke Treatment Agent for treatment recommendations
    5. Invoke Safety Agent for drug/allergy checks
    6. Aggregate and validate all outputs
    7. Generate comprehensive recommendation
    """

    def __init__(self):
        super().__init__(
            agent_id="supervisor",
            name="Clinical Supervisor",
            description="Orchestrates specialist agents for comprehensive clinical decision support",
            version="2.0.0"
        )
        self.specialties = ["orchestration", "clinical_decision_support"]

        # Initialize core agents
        self.diagnostician = DiagnosticianAgent()
        self.treatment = TreatmentAgent()

        # Initialize safety and compliance agents
        self.safety = SafetyAgent()
        self.coding = CodingAgent()

        # Initialize specialist agents
        self.cardiology = CardiologyAgent()
        self.radiology = RadiologyAgent()
        self.pathology = PathologyAgent()
        self.gastroenterology = GastroenterologyAgent()
        self.oncology = OncologyAgent()

        # Agent registry for A2A communication
        self.agents = {
            "diagnostician": self.diagnostician,
            "treatment": self.treatment,
            "safety": self.safety,
            "coding": self.coding,
            "cardiology": self.cardiology,
            "radiology": self.radiology,
            "pathology": self.pathology,
            "gastroenterology": self.gastroenterology,
            "oncology": self.oncology
        }

    def _setup_capabilities(self):
        self.capabilities = [
            AgentCapability(
                name="comprehensive_assessment",
                description="Run full multi-agent clinical assessment",
                input_schema={"patient_id": "string"},
                output_schema={"recommendation": "ComprehensiveRecommendation"}
            ),
            AgentCapability(
                name="quick_triage",
                description="Rapid triage assessment for urgency",
                input_schema={"patient_id": "string", "vitals": "dict"},
                output_schema={"urgency": "string", "actions": "list"}
            )
        ]

    async def process(self, context: PatientContext, task: dict = None) -> AgentOutput:
        """Run the multi-agent workflow"""
        reasoning_steps = []
        all_findings = []
        all_diagnoses = []
        all_treatments = []
        all_warnings = []
        agent_outputs = {}
        all_icd10_codes = []
        all_cpt_codes = []

        try:
            # Step 1: Triage - Quick urgency assessment
            reasoning_steps.append("=== Step 1: Triage Assessment ===")
            urgency = self._quick_triage(context)
            reasoning_steps.append(f"Urgency level: {urgency}")

            # Step 2: Run Diagnostician
            reasoning_steps.append("\n=== Step 2: Diagnostic Analysis ===")
            diag_output = await self.diagnostician.process(context)
            agent_outputs["diagnostician"] = diag_output.dict()

            all_findings.extend(diag_output.findings)
            all_diagnoses.extend(diag_output.diagnoses)
            all_warnings.extend(diag_output.warnings)
            reasoning_steps.extend([f"[Diagnostician] {r}" for r in diag_output.reasoning_steps])

            # Step 3: Check for specialist involvement and run appropriate specialists
            # 3a: Cardiology
            cardiac_indicators = self._check_cardiac_involvement(context, diag_output.findings)
            if cardiac_indicators:
                reasoning_steps.append("\n=== Step 3a: Cardiology Specialist Review ===")
                cardio_output = await self.cardiology.process(context)
                agent_outputs["cardiology"] = cardio_output.dict()

                all_findings.extend(cardio_output.findings)
                all_diagnoses.extend(cardio_output.diagnoses)
                all_treatments.extend(cardio_output.treatments)
                all_warnings.extend(cardio_output.warnings)
                reasoning_steps.extend([f"[Cardiology] {r}" for r in cardio_output.reasoning_steps])

            # 3b: Pathology (Lab Analysis)
            if self._check_pathology_involvement(context):
                reasoning_steps.append("\n=== Step 3b: Pathology Specialist Review ===")
                path_output = await self.pathology.process(context)
                agent_outputs["pathology"] = path_output.dict()

                all_findings.extend(path_output.findings)
                all_diagnoses.extend(path_output.diagnoses)
                all_warnings.extend(path_output.warnings)
                reasoning_steps.extend([f"[Pathology] {r}" for r in path_output.reasoning_steps])

            # 3c: Radiology (if imaging data available)
            if self._check_radiology_involvement(context):
                reasoning_steps.append("\n=== Step 3c: Radiology Specialist Review ===")
                rad_output = await self.radiology.process(context)
                agent_outputs["radiology"] = rad_output.dict()

                all_findings.extend(rad_output.findings)
                all_diagnoses.extend(rad_output.diagnoses)
                all_warnings.extend(rad_output.warnings)
                reasoning_steps.extend([f"[Radiology] {r}" for r in rad_output.reasoning_steps])

            # 3d: Gastroenterology (if GI involvement)
            if self._check_gi_involvement(context, diag_output.findings):
                reasoning_steps.append("\n=== Step 3d: Gastroenterology Specialist Review ===")
                gi_output = await self.gastroenterology.process(context)
                agent_outputs["gastroenterology"] = gi_output.dict()

                all_findings.extend(gi_output.findings)
                all_diagnoses.extend(gi_output.diagnoses)
                all_treatments.extend(gi_output.treatments)
                all_warnings.extend(gi_output.warnings)
                reasoning_steps.extend([f"[Gastroenterology] {r}" for r in gi_output.reasoning_steps])

            # 3e: Oncology (if cancer suspicion or known malignancy)
            suspicious_findings = [f for f in all_findings if f.status == "critical" and
                                   any(term in f.name.lower() for term in ["mass", "tumor", "nodule", "malignant"])]
            if self._check_oncology_involvement(context, all_findings):
                reasoning_steps.append("\n=== Step 3e: Oncology Specialist Review ===")
                onc_task = {"suspicious_findings": [{"description": f.name, "location": f.source} for f in suspicious_findings]}
                onc_output = await self.oncology.process(context, onc_task)
                agent_outputs["oncology"] = onc_output.dict()

                all_findings.extend(onc_output.findings)
                all_diagnoses.extend(onc_output.diagnoses)
                all_treatments.extend(onc_output.treatments)
                all_warnings.extend(onc_output.warnings)
                reasoning_steps.extend([f"[Oncology] {r}" for r in onc_output.reasoning_steps])

            # Step 4: Run Treatment Agent with diagnoses
            reasoning_steps.append("\n=== Step 4: Treatment Planning ===")
            treatment_task = {"diagnoses": [d.dict() for d in all_diagnoses]}
            treatment_output = await self.treatment.process(context, treatment_task)
            agent_outputs["treatment"] = treatment_output.dict()

            all_treatments.extend(treatment_output.treatments)
            all_warnings.extend(treatment_output.warnings)
            reasoning_steps.extend([f"[Treatment] {r}" for r in treatment_output.reasoning_steps])

            # Step 5: Safety Check - Run Safety Agent
            reasoning_steps.append("\n=== Step 5: Safety Validation ===")
            safety_task = {"treatments": [t.dict() for t in all_treatments]}
            safety_output = await self.safety.process(context, safety_task)
            agent_outputs["safety"] = safety_output.dict()

            all_findings.extend(safety_output.findings)
            all_warnings.extend(safety_output.warnings)
            reasoning_steps.extend([f"[Safety] {r}" for r in safety_output.reasoning_steps])

            # Step 6: Clinical Coding - Run Coding Agent
            reasoning_steps.append("\n=== Step 6: Clinical Coding ===")
            coding_task = {
                "diagnoses": [d.dict() for d in all_diagnoses],
                "treatments": [t.dict() for t in all_treatments],
                "findings": [f.dict() for f in all_findings]
            }
            coding_output = await self.coding.process(context, coding_task)
            agent_outputs["coding"] = coding_output.dict()

            all_icd10_codes.extend(coding_output.icd10_codes)
            all_cpt_codes.extend(coding_output.cpt_codes)
            all_warnings.extend(coding_output.warnings)
            reasoning_steps.extend([f"[Coding] {r}" for r in coding_output.reasoning_steps])

            # Step 7: Aggregate and validate
            reasoning_steps.append("\n=== Step 7: Validation & Aggregation ===")
            recommendation = self._aggregate_outputs(
                context=context,
                findings=all_findings,
                diagnoses=all_diagnoses,
                treatments=all_treatments,
                warnings=all_warnings,
                agent_outputs=agent_outputs,
                reasoning_steps=reasoning_steps,
                urgency=urgency
            )

            # Override codes with coding agent's validated codes
            if all_icd10_codes:
                recommendation.icd10_codes = all_icd10_codes
            if all_cpt_codes:
                recommendation.cpt_codes = all_cpt_codes

            # Step 8: Final quality check
            reasoning_steps.append("\n=== Step 8: Quality Check ===")
            recommendation = self._quality_check(recommendation, reasoning_steps)

            # Convert to AgentOutput
            return AgentOutput(
                agent_id=self.agent_id,
                agent_name=self.name,
                timestamp=datetime.utcnow().isoformat(),
                success=True,
                findings=all_findings,
                diagnoses=all_diagnoses,
                treatments=all_treatments,
                icd10_codes=recommendation.icd10_codes,
                cpt_codes=recommendation.cpt_codes,
                confidence=recommendation.overall_confidence,
                reasoning_steps=reasoning_steps,
                warnings=all_warnings,
                requires_human_review=recommendation.requires_human_review,
                review_reason="; ".join(recommendation.review_reasons) if recommendation.review_reasons else None
            )

        except Exception as e:
            import logging
            logging.error(f"Supervisor workflow failed: {e}")
            return AgentOutput(
                agent_id=self.agent_id,
                agent_name=self.name,
                timestamp=datetime.utcnow().isoformat(),
                success=False,
                errors=[str(e)],
                requires_human_review=True,
                review_reason=f"System error: {e}"
            )

    def _check_cardiac_involvement(self, context: PatientContext, findings: List[ClinicalFinding]) -> bool:
        """Check if cardiology specialist review is needed"""
        # Check for cardiac-related findings
        for finding in findings:
            name_lower = finding.name.lower()
            if any(term in name_lower for term in ["heart", "blood pressure", "cardiac", "chest"]):
                return True
            if finding.name == "Heart Rate" and finding.status in ["abnormal", "critical"]:
                return True

        # Check for cardiac conditions
        for condition in (context.conditions or []):
            if not condition or not isinstance(condition, dict):
                continue
            display = condition.get("display", "").lower()
            if any(term in display for term in ["heart", "cardiac", "hypertension", "coronary", "arrhythmia"]):
                return True

        return False

    def _check_pathology_involvement(self, context: PatientContext) -> bool:
        """Check if pathology/lab specialist review is needed"""
        # Always run pathology if labs are available
        if context.labs and len(context.labs) > 0:
            return True
        return False

    def _check_radiology_involvement(self, context: PatientContext) -> bool:
        """Check if radiology specialist review is needed"""
        # Check for imaging data
        if hasattr(context, 'imaging_results') and context.imaging_results:
            return True

        # Check for imaging-related procedures
        for proc in (context.recent_procedures or []):
            if not proc or not isinstance(proc, dict):
                continue
            display = proc.get("display", "").lower()
            if any(term in display for term in ["x-ray", "xray", "ct", "mri", "radiograph", "scan", "imaging"]):
                return True

        # Check for conditions that warrant imaging
        for condition in (context.conditions or []):
            if not condition or not isinstance(condition, dict):
                continue
            display = condition.get("display", "").lower()
            if any(term in display for term in ["pneumonia", "fracture", "mass", "tumor", "stroke", "trauma"]):
                return True

        return False

    def _check_gi_involvement(self, context: PatientContext, findings: List[ClinicalFinding]) -> bool:
        """Check if gastroenterology specialist review is needed"""
        # Check for GI-related findings
        for finding in findings:
            name_lower = finding.name.lower()
            if any(term in name_lower for term in ["abdominal", "gi", "gastro", "bowel", "liver", "colon"]):
                return True

        # Check for GI conditions
        for condition in (context.conditions or []):
            if not condition or not isinstance(condition, dict):
                continue
            display = condition.get("display", "").lower()
            gi_terms = ["abdominal", "gastro", "bowel", "colon", "liver", "hepat", "gerd",
                       "ulcer", "crohn", "colitis", "diverticul", "pancreat", "gi bleed"]
            if any(term in display for term in gi_terms):
                return True

        # Check for GI procedures
        for proc in (context.recent_procedures or []):
            if not proc or not isinstance(proc, dict):
                continue
            display = proc.get("display", "").lower()
            if any(term in display for term in ["colonoscopy", "endoscopy", "egd", "ercp"]):
                return True

        return False

    def _check_oncology_involvement(self, context: PatientContext, findings: List[ClinicalFinding]) -> bool:
        """Check if oncology specialist review is needed"""
        # Check for cancer-related findings
        for finding in findings:
            name_lower = finding.name.lower()
            if any(term in name_lower for term in ["cancer", "tumor", "mass", "malignant", "carcinoma", "neoplasm"]):
                return True

        # Check for cancer-related conditions
        for condition in (context.conditions or []):
            if not condition or not isinstance(condition, dict):
                continue
            display = condition.get("display", "").lower()
            code = condition.get("code", "")
            # Check ICD-10 C codes (malignant neoplasms)
            if code and code.startswith("C"):
                return True
            cancer_terms = ["cancer", "carcinoma", "malignant", "neoplasm", "tumor", "lymphoma", "leukemia", "melanoma"]
            if any(term in display for term in cancer_terms):
                return True

        # Check for elevated tumor markers
        tumor_marker_codes = ["psa", "cea", "ca125", "ca19-9", "afp"]
        for lab in (context.labs or []):
            if not lab or not isinstance(lab, dict):
                continue
            name = lab.get("display", lab.get("name", "")).lower()
            if any(marker in name for marker in tumor_marker_codes):
                return True

        return False

    def _quick_triage(self, context: PatientContext) -> str:
        """Quick triage based on vitals"""
        if not context.vitals:
            return "unknown"

        critical_indicators = 0

        for vital in context.vitals[:10]:  # Check recent vitals
            if not vital or not isinstance(vital, dict):
                continue

            code = vital.get("code", "")
            value = vital.get("value")

            # ECG observations have no numeric value - check ecg_findings instead
            if code == "8601-7":
                ecg_findings = vital.get("ecg_findings", [])
                if ecg_findings:
                    for finding in ecg_findings:
                        finding_lower = finding.lower() if finding else ""
                        if "fibrillation" in finding_lower or "st elevation" in finding_lower:
                            critical_indicators += 2
                        elif "st depression" in finding_lower or "ischemic" in finding_lower:
                            critical_indicators += 1
                continue

            if not value:
                continue

            # Check for critical values
            if code == "8867-4":  # Heart rate
                if value < 40 or value > 150:
                    critical_indicators += 2
                elif value < 50 or value > 120:
                    critical_indicators += 1

            elif code == "59408-5":  # SpO2
                if value < 88:
                    critical_indicators += 2
                elif value < 92:
                    critical_indicators += 1

            elif code == "8310-5":  # Temperature
                if value >= 40 or value < 35:
                    critical_indicators += 2
                elif value >= 38.5:
                    critical_indicators += 1

            elif code == "2339-0":  # Blood Glucose
                if value > 300 or value < 50:
                    critical_indicators += 2
                elif value > 200 or value < 70:
                    critical_indicators += 1

            # Check BP components
            for comp in vital.get("components", []):
                if not comp or not isinstance(comp, dict):
                    continue
                if comp.get("code") == "8480-6":  # Systolic
                    sys = comp.get("value")
                    if sys and (sys >= 180 or sys < 80):
                        critical_indicators += 2
                    elif sys and (sys >= 160 or sys < 90):
                        critical_indicators += 1

        if critical_indicators >= 3:
            return "critical"
        elif critical_indicators >= 1:
            return "urgent"
        else:
            return "routine"

    def _aggregate_outputs(
        self,
        context: PatientContext,
        findings: List[ClinicalFinding],
        diagnoses: List[DiagnosisRecommendation],
        treatments: List[TreatmentRecommendation],
        warnings: List[str],
        agent_outputs: Dict[str, dict],
        reasoning_steps: List[str],
        urgency: str
    ) -> ComprehensiveRecommendation:
        """Aggregate all agent outputs into comprehensive recommendation"""

        # Identify critical findings
        critical_findings = [f for f in findings if f.status == "critical"]
        abnormal_findings = [f for f in findings if f.status == "abnormal"]
        reasoning_steps.append(
            f"Total findings: {len(findings)} "
            f"({len(critical_findings)} critical, {len(abnormal_findings)} abnormal, "
            f"{len(findings) - len(critical_findings) - len(abnormal_findings)} normal)"
        )

        # Identify primary diagnosis (highest confidence)
        primary_diagnosis = None
        differential_diagnoses = []
        if diagnoses:
            sorted_dx = sorted(diagnoses, key=lambda d: d.confidence, reverse=True)
            primary_diagnosis = sorted_dx[0]
            differential_diagnoses = sorted_dx[1:4]  # Top 3 differentials
            reasoning_steps.append(
                f"Primary diagnosis: {primary_diagnosis.diagnosis} "
                f"(ICD-10: {primary_diagnosis.icd10_code}, confidence: {primary_diagnosis.confidence:.0%})"
            )
            if differential_diagnoses:
                diff_list = ", ".join(
                    f"{d.diagnosis} ({d.confidence:.0%})" for d in differential_diagnoses
                )
                reasoning_steps.append(f"Differential diagnoses: {diff_list}")
        else:
            reasoning_steps.append("No diagnoses determined — physician evaluation required")

        # Identify immediate actions
        immediate_actions = [t for t in treatments if t.priority in ["immediate", "urgent"]]
        reasoning_steps.append(
            f"Treatment plan: {len(treatments)} recommendation(s) "
            f"({len(immediate_actions)} immediate/urgent)"
        )

        # Extract all codes
        icd10_codes = []
        for dx in diagnoses:
            if dx.icd10_code:
                icd10_codes.append({
                    "code": dx.icd10_code,
                    "description": dx.diagnosis,
                    "confidence": dx.confidence
                })

        cpt_codes = []
        for tx in treatments:
            if tx.cpt_code:
                cpt_codes.append({
                    "code": tx.cpt_code,
                    "description": tx.description,
                    "priority": tx.priority
                })

        reasoning_steps.append(
            f"Clinical codes: {len(icd10_codes)} ICD-10, {len(cpt_codes)} CPT"
        )

        # Calculate overall confidence based on primary diagnosis
        # Using primary (highest-confidence) diagnosis rather than averaging all
        # diagnoses, because differentials are expected to have lower confidence
        # and averaging them dilutes the score
        if primary_diagnosis:
            overall_confidence = primary_diagnosis.confidence
        elif diagnoses:
            overall_confidence = max(dx.confidence for dx in diagnoses)
        else:
            overall_confidence = 0.0
        reasoning_steps.append(f"Overall diagnostic confidence: {overall_confidence:.0%}")

        # Determine if human review required
        requires_review = False
        review_reasons = []

        if urgency == "critical":
            requires_review = True
            review_reasons.append("Critical patient status")

        if critical_findings:
            requires_review = True
            review_reasons.append(f"{len(critical_findings)} critical finding(s)")

        if overall_confidence < 0.7:
            requires_review = True
            review_reasons.append("Low diagnostic confidence")

        if warnings:
            requires_review = True
            review_reasons.append("Warnings or interactions detected")

        if not diagnoses:
            requires_review = True
            review_reasons.append("No diagnosis determined")

        if requires_review:
            reasoning_steps.append(f"Human review REQUIRED: {'; '.join(review_reasons)}")
        else:
            reasoning_steps.append("Human review: Not required")

        reasoning_steps.append(f"Agents consulted: {', '.join(agent_outputs.keys())}")

        # Create patient summary
        patient_summary = {
            "patient_id": context.patient_id,
            "name": context.name,
            "age": context.age,
            "sex": context.sex,
            "urgency": urgency,
            "active_conditions": len(context.conditions or []),
            "active_medications": len(context.medications or []),
            "known_allergies": len(context.allergies or []),
            "chief_complaint": context.chief_complaint,
            "history_present_illness": context.history_present_illness,
            "physician_notes": context.physician_notes
        }

        return ComprehensiveRecommendation(
            patient_id=context.patient_id,
            timestamp=datetime.utcnow().isoformat(),
            patient_summary=patient_summary,
            findings=findings,
            critical_findings=critical_findings,
            primary_diagnosis=primary_diagnosis,
            differential_diagnoses=differential_diagnoses,
            treatments=treatments,
            immediate_actions=immediate_actions,
            icd10_codes=icd10_codes,
            cpt_codes=cpt_codes,
            overall_confidence=round(overall_confidence, 2),
            reasoning_chain=reasoning_steps,
            warnings=warnings,
            requires_human_review=requires_review,
            review_reasons=review_reasons,
            agent_outputs=agent_outputs
        )

    def _quality_check(
        self,
        recommendation: ComprehensiveRecommendation,
        reasoning_steps: List[str],
    ) -> ComprehensiveRecommendation:
        """Final quality checks on the recommendation"""
        checks_passed = 0
        checks_failed = 0

        # Check 1: Critical findings have corresponding treatments
        if recommendation.critical_findings:
            if recommendation.immediate_actions:
                reasoning_steps.append(
                    f"QC PASS: {len(recommendation.immediate_actions)} immediate action(s) "
                    f"address {len(recommendation.critical_findings)} critical finding(s)"
                )
                checks_passed += 1
            else:
                recommendation.warnings.append(
                    "QUALITY: Critical findings present but no immediate actions recommended"
                )
                recommendation.requires_human_review = True
                recommendation.review_reasons.append("Critical findings without immediate actions")
                reasoning_steps.append(
                    "QC FAIL: Critical findings present but no immediate actions recommended"
                )
                checks_failed += 1
        else:
            reasoning_steps.append("QC PASS: No critical findings requiring immediate action")
            checks_passed += 1

        # Check 2: Diagnoses have corresponding codes
        if recommendation.primary_diagnosis:
            if recommendation.icd10_codes:
                reasoning_steps.append(
                    f"QC PASS: {len(recommendation.icd10_codes)} ICD-10 code(s) assigned to diagnoses"
                )
                checks_passed += 1
            else:
                recommendation.warnings.append(
                    "QUALITY: Diagnosis present but no ICD-10 code assigned"
                )
                reasoning_steps.append(
                    "QC FAIL: Diagnosis present but no ICD-10 code assigned"
                )
                checks_failed += 1
        else:
            reasoning_steps.append("QC SKIP: No primary diagnosis to validate codes against")

        # Check 3: Treatments have CPT codes
        treatments_without_codes = [
            t for t in recommendation.treatments if not t.cpt_code
        ]
        if recommendation.treatments:
            if not treatments_without_codes:
                reasoning_steps.append(
                    f"QC PASS: All {len(recommendation.treatments)} treatment(s) have CPT codes"
                )
                checks_passed += 1
            else:
                reasoning_steps.append(
                    f"QC INFO: {len(treatments_without_codes)}/{len(recommendation.treatments)} "
                    f"treatment(s) missing CPT codes"
                )

        # Check 4: Confidence threshold
        if recommendation.overall_confidence >= 0.7:
            reasoning_steps.append(
                f"QC PASS: Diagnostic confidence {recommendation.overall_confidence:.0%} meets threshold (≥70%)"
            )
            checks_passed += 1
        else:
            reasoning_steps.append(
                f"QC WARN: Diagnostic confidence {recommendation.overall_confidence:.0%} below threshold (≥70%)"
            )
            checks_failed += 1

        reasoning_steps.append(
            f"Quality check complete: {checks_passed} passed, {checks_failed} failed"
        )

        return recommendation

    async def run_comprehensive_assessment(self, patient_id: str) -> ComprehensiveRecommendation:
        """
        Public method to run full assessment for a patient.
        Gathers context and runs multi-agent workflow.
        """
        # Gather patient context from MCP
        context = await self.mcp.get_patient_context(patient_id)

        # Run the workflow
        output = await self.process(context)

        # Build comprehensive recommendation
        return ComprehensiveRecommendation(
            patient_id=patient_id,
            timestamp=datetime.utcnow().isoformat(),
            patient_summary={
                "patient_id": patient_id,
                "name": context.name,
                "age": context.age,
                "sex": context.sex
            },
            findings=output.findings,
            critical_findings=[f for f in output.findings if f.status == "critical"],
            primary_diagnosis=output.diagnoses[0] if output.diagnoses else None,
            differential_diagnoses=output.diagnoses[1:4] if len(output.diagnoses) > 1 else [],
            treatments=output.treatments,
            immediate_actions=[t for t in output.treatments if t.priority in ["immediate", "urgent"]],
            icd10_codes=output.icd10_codes,
            cpt_codes=output.cpt_codes,
            overall_confidence=output.confidence,
            reasoning_chain=output.reasoning_steps,
            warnings=output.warnings,
            requires_human_review=output.requires_human_review,
            review_reasons=[output.review_reason] if output.review_reason else [],
            agent_outputs={}
        )


# Singleton instance
supervisor = SupervisorAgent()
