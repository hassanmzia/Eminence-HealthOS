"""
MCP-RAG Server
Provides access to clinical knowledge base, guidelines, and medical literature
Uses vector store for semantic search over medical knowledge
"""

import os
from typing import Optional, List

# Support both package import and direct execution
try:
    from .base import BaseMCPServer, MCPRequest
except ImportError:
    from base import BaseMCPServer, MCPRequest

# In production, use actual vector DB (Pinecone, Weaviate, ChromaDB)
# This is a simplified implementation for demonstration

# Clinical Guidelines Knowledge Base (simplified)
CLINICAL_GUIDELINES = {
    "hypertension": {
        "icd10": ["I10", "I11", "I12", "I13", "I15"],
        "title": "Hypertension Management Guidelines (ACC/AHA 2017)",
        "content": """
        Blood Pressure Categories:
        - Normal: <120/<80 mmHg
        - Elevated: 120-129/<80 mmHg
        - Stage 1 HTN: 130-139/80-89 mmHg
        - Stage 2 HTN: ≥140/≥90 mmHg
        - Hypertensive Crisis: >180/>120 mmHg

        Treatment Recommendations:
        1. Lifestyle modifications for all patients
        2. For Stage 1 with ASCVD risk ≥10%: Start antihypertensive medication
        3. For Stage 2: Start 2 first-line agents of different classes

        First-line agents:
        - Thiazide diuretics (chlorthalidone, hydrochlorothiazide)
        - ACE inhibitors (lisinopril, enalapril)
        - ARBs (losartan, valsartan)
        - Calcium channel blockers (amlodipine, diltiazem)

        Target BP: <130/80 mmHg for most adults
        """,
        "cpt_codes": ["99213", "99214", "93000"],
        "source": "ACC/AHA 2017 Guideline for High Blood Pressure"
    },
    "diabetes_type2": {
        "icd10": ["E11.9", "E11.65", "E11.21", "E11.22"],
        "title": "Type 2 Diabetes Management (ADA Standards 2024)",
        "content": """
        Diagnostic Criteria:
        - Fasting glucose ≥126 mg/dL
        - 2-hour glucose ≥200 mg/dL during OGTT
        - HbA1c ≥6.5%
        - Random glucose ≥200 mg/dL with symptoms

        Treatment Goals:
        - HbA1c target: <7% for most adults
        - Fasting glucose: 80-130 mg/dL
        - Post-prandial glucose: <180 mg/dL

        Pharmacotherapy:
        1. First-line: Metformin (unless contraindicated)
        2. Add-on options based on patient factors:
           - SGLT2 inhibitors (empagliflozin, dapagliflozin) - if heart failure or CKD
           - GLP-1 agonists (semaglutide, liraglutide) - if ASCVD or weight management
           - DPP-4 inhibitors (sitagliptin)
           - Sulfonylureas (glipizide, glimepiride)
           - Insulin if needed

        Monitoring:
        - HbA1c every 3-6 months
        - Annual: eye exam, foot exam, kidney function, lipids
        """,
        "cpt_codes": ["99213", "99214", "82947", "83036"],
        "source": "ADA Standards of Care in Diabetes 2024"
    },
    "chest_pain": {
        "icd10": ["R07.9", "R07.89", "I20.9", "I21.9"],
        "title": "Acute Chest Pain Evaluation (ACC/AHA)",
        "content": """
        Risk Stratification:

        High Risk Features (consider ACS):
        - Chest pain at rest >20 min
        - New ST changes
        - Positive troponin
        - Hemodynamic instability
        - Heart failure symptoms

        HEART Score Components:
        - History: 0-2 points
        - ECG: 0-2 points
        - Age: 0-2 points
        - Risk factors: 0-2 points
        - Troponin: 0-2 points

        HEART Score Interpretation:
        - 0-3: Low risk (2% MACE) - consider discharge
        - 4-6: Intermediate risk - observation, serial troponins
        - 7-10: High risk - admission, cardiology consult

        Initial Workup:
        1. 12-lead ECG within 10 minutes
        2. Troponin (high-sensitivity preferred)
        3. CXR
        4. Basic metabolic panel

        Treatment for ACS:
        - Aspirin 325mg
        - Anticoagulation (heparin)
        - Consider P2Y12 inhibitor
        - Cardiology consult for catheterization
        """,
        "cpt_codes": ["99284", "99285", "93000", "71046"],
        "source": "ACC/AHA Guidelines for Acute Coronary Syndromes"
    },
    "sepsis": {
        "icd10": ["A41.9", "R65.20", "R65.21"],
        "title": "Sepsis Management (Surviving Sepsis Campaign 2021)",
        "content": """
        Sepsis Definition (Sepsis-3):
        - Suspected infection PLUS
        - SOFA score increase ≥2 points

        qSOFA (Quick SOFA) - 2+ indicates high risk:
        - Respiratory rate ≥22/min
        - Altered mentation
        - Systolic BP ≤100 mmHg

        Hour-1 Bundle:
        1. Measure lactate (repeat if >2 mmol/L)
        2. Obtain blood cultures before antibiotics
        3. Administer broad-spectrum antibiotics
        4. Begin rapid fluid resuscitation (30 mL/kg crystalloid)
        5. Apply vasopressors if hypotensive during/after fluids

        Septic Shock Criteria:
        - Sepsis PLUS
        - Vasopressors needed for MAP ≥65 mmHg
        - Lactate >2 mmol/L despite adequate fluid resuscitation

        Antibiotic Selection:
        - Community-acquired: Ceftriaxone + Azithromycin OR Fluoroquinolone
        - Healthcare-associated: Piperacillin-tazobactam OR Meropenem
        - Add Vancomycin if MRSA risk

        Target MAP: ≥65 mmHg
        """,
        "cpt_codes": ["99291", "99292", "36556", "36620"],
        "source": "Surviving Sepsis Campaign 2021"
    },
    "heart_failure": {
        "icd10": ["I50.9", "I50.1", "I50.20", "I50.21", "I50.22", "I50.23"],
        "title": "Heart Failure Management (ACC/AHA/HFSA 2022)",
        "content": """
        Classification:
        - HFrEF: EF ≤40%
        - HFmrEF: EF 41-49%
        - HFpEF: EF ≥50%

        NYHA Functional Class:
        - I: No limitation
        - II: Slight limitation
        - III: Marked limitation
        - IV: Symptoms at rest

        Guideline-Directed Medical Therapy (GDMT) for HFrEF:
        1. ACE-I/ARB/ARNI (sacubitril-valsartan preferred)
        2. Beta-blocker (carvedilol, metoprolol succinate, bisoprolol)
        3. MRA (spironolactone, eplerenone)
        4. SGLT2 inhibitor (dapagliflozin, empagliflozin)

        Device Therapy:
        - ICD: EF ≤35% with NYHA II-III
        - CRT: EF ≤35%, LBBB, QRS ≥150ms

        Acute Decompensation:
        - IV diuretics (furosemide)
        - Consider inotropes if cardiogenic shock
        - Oxygen/ventilation as needed
        - Identify and treat precipitants

        Target: Uptitrate GDMT to maximum tolerated doses
        """,
        "cpt_codes": ["99213", "99214", "93306", "93000"],
        "source": "ACC/AHA/HFSA 2022 Heart Failure Guidelines"
    },
    "copd": {
        "icd10": ["J44.9", "J44.0", "J44.1"],
        "title": "COPD Management (GOLD 2024)",
        "content": """
        Diagnosis:
        - Post-bronchodilator FEV1/FVC <0.7
        - Spirometry required for diagnosis

        GOLD Classification (by FEV1):
        - GOLD 1 (Mild): FEV1 ≥80%
        - GOLD 2 (Moderate): 50% ≤ FEV1 < 80%
        - GOLD 3 (Severe): 30% ≤ FEV1 < 50%
        - GOLD 4 (Very Severe): FEV1 <30%

        ABE Assessment Groups:
        - Group A: Low symptoms, low exacerbation risk
        - Group B: High symptoms, low exacerbation risk
        - Group E: ≥2 moderate or ≥1 severe exacerbation

        Pharmacotherapy:
        - Group A: Bronchodilator (SABA or LAMA)
        - Group B: LABA + LAMA
        - Group E: LABA + LAMA ± ICS (if eos ≥300)

        Non-pharmacologic:
        - Smoking cessation (most important)
        - Pulmonary rehabilitation
        - Vaccinations (influenza, pneumococcal, COVID-19)
        - Oxygen if PaO2 ≤55 mmHg

        Exacerbation Management:
        - Increase bronchodilator frequency
        - Systemic corticosteroids (prednisone 40mg x 5 days)
        - Antibiotics if increased sputum purulence
        """,
        "cpt_codes": ["99213", "99214", "94010", "94060"],
        "source": "GOLD 2024 Report"
    }
}

# Drug Interaction Database (simplified)
DRUG_INTERACTIONS = {
    ("warfarin", "aspirin"): {
        "severity": "major",
        "effect": "Increased bleeding risk",
        "recommendation": "Monitor closely, consider PPI for GI protection"
    },
    ("lisinopril", "potassium"): {
        "severity": "major",
        "effect": "Risk of hyperkalemia",
        "recommendation": "Monitor potassium levels closely"
    },
    ("metformin", "contrast"): {
        "severity": "major",
        "effect": "Risk of lactic acidosis",
        "recommendation": "Hold metformin 48h before and after contrast"
    },
    ("simvastatin", "amlodipine"): {
        "severity": "moderate",
        "effect": "Increased statin exposure, myopathy risk",
        "recommendation": "Limit simvastatin to 20mg daily"
    },
    ("ssri", "tramadol"): {
        "severity": "major",
        "effect": "Serotonin syndrome risk",
        "recommendation": "Avoid combination or monitor closely"
    },
    ("methotrexate", "nsaid"): {
        "severity": "major",
        "effect": "Increased methotrexate toxicity",
        "recommendation": "Avoid NSAIDs or reduce MTX dose"
    }
}

# ICD-10 to diagnosis mapping
ICD10_DATABASE = {
    "I10": {"description": "Essential (primary) hypertension", "category": "cardiovascular"},
    "E11.9": {"description": "Type 2 diabetes mellitus without complications", "category": "endocrine"},
    "E11.65": {"description": "Type 2 diabetes mellitus with hyperglycemia", "category": "endocrine"},
    "I50.9": {"description": "Heart failure, unspecified", "category": "cardiovascular"},
    "J44.9": {"description": "Chronic obstructive pulmonary disease, unspecified", "category": "respiratory"},
    "I21.9": {"description": "Acute myocardial infarction, unspecified", "category": "cardiovascular"},
    "A41.9": {"description": "Sepsis, unspecified organism", "category": "infectious"},
    "N18.3": {"description": "Chronic kidney disease, stage 3", "category": "renal"},
    "F32.9": {"description": "Major depressive disorder, single episode", "category": "mental health"},
    "M54.5": {"description": "Low back pain", "category": "musculoskeletal"},
}

# CPT Code Database
CPT_DATABASE = {
    "99213": {"description": "Office visit, established patient, low complexity", "category": "E&M"},
    "99214": {"description": "Office visit, established patient, moderate complexity", "category": "E&M"},
    "99215": {"description": "Office visit, established patient, high complexity", "category": "E&M"},
    "99284": {"description": "Emergency department visit, moderate severity", "category": "E&M"},
    "99285": {"description": "Emergency department visit, high severity", "category": "E&M"},
    "99291": {"description": "Critical care, first 30-74 minutes", "category": "Critical Care"},
    "93000": {"description": "Electrocardiogram, complete", "category": "Cardiology"},
    "93306": {"description": "Echocardiography, complete", "category": "Cardiology"},
    "71046": {"description": "Chest X-ray, 2 views", "category": "Radiology"},
    "82947": {"description": "Glucose, quantitative", "category": "Laboratory"},
    "83036": {"description": "Hemoglobin A1c", "category": "Laboratory"},
}


class MCPRAGServer(BaseMCPServer):
    """MCP Server for clinical knowledge base and RAG capabilities"""

    def __init__(self):
        super().__init__(
            name="mcp-rag",
            description="Clinical guidelines, drug references, and medical knowledge base",
            version="1.0.0"
        )
        self.setup_tools()

    def setup_tools(self):
        """Register RAG tools"""

        @self.register_tool(
            name="search_guidelines",
            description="Search clinical practice guidelines for a condition or symptom",
            input_schema={
                "query": "string - condition, symptom, or clinical question",
                "specialty": "string - optional specialty filter"
            },
            output_schema={"guidelines": "relevant clinical guidelines"},
            category="knowledge",
            requires_patient_context=False
        )
        async def search_guidelines(request: MCPRequest):
            query = request.arguments.get("query", "").lower()

            # Simple keyword matching (in production, use vector similarity)
            results = []
            for key, guideline in CLINICAL_GUIDELINES.items():
                if (query in key or
                    query in guideline["title"].lower() or
                    query in guideline["content"].lower()):
                    results.append({
                        "condition": key,
                        "title": guideline["title"],
                        "content": guideline["content"],
                        "icd10_codes": guideline["icd10"],
                        "cpt_codes": guideline["cpt_codes"],
                        "source": guideline["source"]
                    })

            return {"query": query, "count": len(results), "guidelines": results}

        @self.register_tool(
            name="get_treatment_protocol",
            description="Get evidence-based treatment protocol for a diagnosis",
            input_schema={
                "diagnosis": "string - condition name or ICD-10 code",
                "patient_factors": "dict - age, comorbidities, allergies (optional)"
            },
            output_schema={"protocol": "treatment recommendations"},
            category="treatment"
        )
        async def get_treatment_protocol(request: MCPRequest):
            diagnosis = request.arguments.get("diagnosis", "").lower()
            patient_factors = request.arguments.get("patient_factors", {})

            # Find matching guideline
            matched_guideline = None
            for key, guideline in CLINICAL_GUIDELINES.items():
                if diagnosis in key or diagnosis in [c.lower() for c in guideline["icd10"]]:
                    matched_guideline = guideline
                    break

            if not matched_guideline:
                return {
                    "error": "No protocol found for this diagnosis",
                    "available_conditions": list(CLINICAL_GUIDELINES.keys())
                }

            return {
                "diagnosis": diagnosis,
                "protocol": {
                    "title": matched_guideline["title"],
                    "recommendations": matched_guideline["content"],
                    "icd10_codes": matched_guideline["icd10"],
                    "suggested_cpt_codes": matched_guideline["cpt_codes"],
                    "source": matched_guideline["source"]
                },
                "patient_considerations": self._get_patient_considerations(diagnosis, patient_factors)
            }

        @self.register_tool(
            name="check_drug_interactions",
            description="Check for drug-drug interactions",
            input_schema={
                "medications": "list of medication names",
                "new_medication": "string - medication being considered"
            },
            output_schema={"interactions": "list of potential interactions"},
            category="safety",
            requires_patient_context=False
        )
        async def check_drug_interactions(request: MCPRequest):
            medications = request.arguments.get("medications", [])
            new_med = request.arguments.get("new_medication", "").lower()

            interactions = []
            for med in medications:
                med_lower = med.lower()
                # Check both orderings
                key1 = (med_lower, new_med)
                key2 = (new_med, med_lower)

                interaction = DRUG_INTERACTIONS.get(key1) or DRUG_INTERACTIONS.get(key2)
                if interaction:
                    interactions.append({
                        "drug1": med,
                        "drug2": new_med,
                        **interaction
                    })

            return {
                "new_medication": new_med,
                "current_medications": medications,
                "interactions_found": len(interactions),
                "interactions": interactions,
                "safe_to_add": len([i for i in interactions if i["severity"] == "major"]) == 0
            }

        @self.register_tool(
            name="lookup_icd10",
            description="Look up ICD-10 diagnosis code information",
            input_schema={
                "code": "string - ICD-10 code (optional)",
                "description": "string - search by description (optional)"
            },
            output_schema={"codes": "matching ICD-10 codes with descriptions"},
            category="coding",
            requires_patient_context=False
        )
        async def lookup_icd10(request: MCPRequest):
            code = request.arguments.get("code", "").upper()
            description = request.arguments.get("description", "").lower()

            results = []
            for icd_code, info in ICD10_DATABASE.items():
                if code and code in icd_code:
                    results.append({"code": icd_code, **info})
                elif description and description in info["description"].lower():
                    results.append({"code": icd_code, **info})

            return {"count": len(results), "codes": results}

        @self.register_tool(
            name="lookup_cpt",
            description="Look up CPT procedure code information",
            input_schema={
                "code": "string - CPT code (optional)",
                "description": "string - search by description (optional)",
                "category": "string - E&M, Cardiology, etc. (optional)"
            },
            output_schema={"codes": "matching CPT codes with descriptions"},
            category="coding",
            requires_patient_context=False
        )
        async def lookup_cpt(request: MCPRequest):
            code = request.arguments.get("code", "")
            description = request.arguments.get("description", "").lower()
            category = request.arguments.get("category", "").lower()

            results = []
            for cpt_code, info in CPT_DATABASE.items():
                match = True
                if code and code not in cpt_code:
                    match = False
                if description and description not in info["description"].lower():
                    match = False
                if category and category not in info["category"].lower():
                    match = False

                if match:
                    results.append({"code": cpt_code, **info})

            return {"count": len(results), "codes": results}

        @self.register_tool(
            name="suggest_diagnosis_codes",
            description="Suggest ICD-10 codes based on clinical findings",
            input_schema={
                "symptoms": "list of symptoms/findings",
                "vitals": "dict of vital signs (optional)",
                "lab_results": "dict of abnormal labs (optional)"
            },
            output_schema={"suggested_codes": "ICD-10 codes with rationale"},
            category="coding"
        )
        async def suggest_diagnosis_codes(request: MCPRequest):
            symptoms = request.arguments.get("symptoms", [])
            vitals = request.arguments.get("vitals", {})
            labs = request.arguments.get("lab_results", {})

            suggestions = []

            # Symptom-based suggestions
            symptom_text = " ".join(symptoms).lower()

            if "chest pain" in symptom_text:
                suggestions.append({
                    "code": "R07.9",
                    "description": "Chest pain, unspecified",
                    "rationale": "Presenting symptom of chest pain",
                    "consider_also": ["I20.9 - Angina", "I21.9 - AMI if confirmed"]
                })

            if "shortness of breath" in symptom_text or "dyspnea" in symptom_text:
                suggestions.append({
                    "code": "R06.02",
                    "description": "Shortness of breath",
                    "rationale": "Presenting symptom",
                    "consider_also": ["I50.9 - Heart failure", "J44.9 - COPD"]
                })

            # Vital sign-based suggestions
            bp_sys = vitals.get("bp_systolic") or vitals.get("BP_SYS")
            if bp_sys and bp_sys >= 140:
                suggestions.append({
                    "code": "I10",
                    "description": "Essential hypertension",
                    "rationale": f"Elevated BP: {bp_sys} mmHg",
                    "consider_also": ["I11.9 - Hypertensive heart disease"]
                })

            # Lab-based suggestions
            glucose = labs.get("glucose") or labs.get("Glucose")
            if glucose and glucose >= 126:
                suggestions.append({
                    "code": "E11.9",
                    "description": "Type 2 diabetes mellitus",
                    "rationale": f"Elevated fasting glucose: {glucose} mg/dL",
                    "consider_also": ["E11.65 - With hyperglycemia"]
                })

            hba1c = labs.get("hba1c") or labs.get("HbA1c")
            if hba1c and hba1c >= 6.5:
                if not any(s["code"].startswith("E11") for s in suggestions):
                    suggestions.append({
                        "code": "E11.9",
                        "description": "Type 2 diabetes mellitus",
                        "rationale": f"HbA1c: {hba1c}%",
                        "consider_also": []
                    })

            return {
                "symptoms": symptoms,
                "suggestions": suggestions,
                "note": "These are suggestions only. Clinical judgment required for final coding."
            }

        @self.register_tool(
            name="get_differential_diagnosis",
            description="Generate differential diagnosis based on presentation",
            input_schema={
                "chief_complaint": "string",
                "symptoms": "list of symptoms",
                "vitals": "dict of vital signs",
                "patient_info": "dict with age, sex, history"
            },
            output_schema={"differentials": "list of possible diagnoses ranked by likelihood"},
            category="diagnosis"
        )
        async def get_differential_diagnosis(request: MCPRequest):
            chief_complaint = request.arguments.get("chief_complaint", "").lower()
            symptoms = [s.lower() for s in request.arguments.get("symptoms", [])]
            vitals = request.arguments.get("vitals", {})
            patient_info = request.arguments.get("patient_info", {})

            differentials = []

            # Chest pain differentials
            if "chest pain" in chief_complaint:
                differentials = [
                    {
                        "diagnosis": "Acute Coronary Syndrome",
                        "icd10": "I21.9",
                        "likelihood": "high" if vitals.get("troponin", 0) > 0.04 else "moderate",
                        "supporting": ["chest pain", "troponin elevation"],
                        "workup": ["ECG", "Serial troponins", "Cardiology consult"]
                    },
                    {
                        "diagnosis": "Unstable Angina",
                        "icd10": "I20.0",
                        "likelihood": "moderate",
                        "supporting": ["chest pain at rest"],
                        "workup": ["ECG", "Stress test", "Coronary angiography"]
                    },
                    {
                        "diagnosis": "Pulmonary Embolism",
                        "icd10": "I26.99",
                        "likelihood": "moderate" if "dyspnea" in symptoms else "low",
                        "supporting": ["chest pain", "dyspnea", "tachycardia"],
                        "workup": ["D-dimer", "CT-PA", "Wells score"]
                    },
                    {
                        "diagnosis": "Gastroesophageal Reflux",
                        "icd10": "K21.0",
                        "likelihood": "low",
                        "supporting": ["burning", "postprandial"],
                        "workup": ["PPI trial", "EGD if refractory"]
                    }
                ]

            # Shortness of breath differentials
            elif "shortness of breath" in chief_complaint or "dyspnea" in chief_complaint:
                differentials = [
                    {
                        "diagnosis": "Heart Failure Exacerbation",
                        "icd10": "I50.9",
                        "likelihood": "high" if vitals.get("bnp", 0) > 100 else "moderate",
                        "supporting": ["dyspnea", "edema", "elevated BNP"],
                        "workup": ["BNP", "Echo", "CXR"]
                    },
                    {
                        "diagnosis": "COPD Exacerbation",
                        "icd10": "J44.1",
                        "likelihood": "moderate",
                        "supporting": ["dyspnea", "wheezing", "smoking history"],
                        "workup": ["ABG", "CXR", "Spirometry"]
                    },
                    {
                        "diagnosis": "Pneumonia",
                        "icd10": "J18.9",
                        "likelihood": "moderate" if "fever" in symptoms else "low",
                        "supporting": ["fever", "cough", "dyspnea"],
                        "workup": ["CXR", "CBC", "Procalcitonin"]
                    }
                ]

            return {
                "chief_complaint": chief_complaint,
                "differentials": differentials,
                "recommendation": "Obtain workup as indicated, reassess based on results"
            }

    def _get_patient_considerations(self, diagnosis: str, patient_factors: dict) -> list:
        """Get patient-specific considerations for treatment"""
        considerations = []

        age = patient_factors.get("age")
        if age:
            if age > 65:
                considerations.append("Elderly patient - consider renal dosing, fall risk, polypharmacy")
            if age < 18:
                considerations.append("Pediatric patient - use age-appropriate dosing")

        allergies = patient_factors.get("allergies", [])
        if allergies:
            considerations.append(f"Known allergies: {', '.join(allergies)} - avoid related medications")

        comorbidities = patient_factors.get("comorbidities", [])
        if "CKD" in comorbidities or "kidney" in str(comorbidities).lower():
            considerations.append("CKD present - adjust renally-cleared medications")
        if "liver" in str(comorbidities).lower():
            considerations.append("Liver disease - caution with hepatically-metabolized drugs")

        return considerations


# Create server instance
server = MCPRAGServer()
app = server.app
