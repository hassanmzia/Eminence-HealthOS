"""
MCP-Pharmacy Server
Provides access to pharmacy data, drug formulary, prescriptions, and medication management.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# Support both package import and direct execution
try:
    from .base import BaseMCPServer, MCPRequest
except ImportError:
    from base import BaseMCPServer, MCPRequest

FHIR_BASE = os.getenv("FHIR_BASE", "http://hapi-fhir:8080/fhir")


# Comprehensive Drug Formulary Database
DRUG_FORMULARY = {
    # Cardiovascular
    "lisinopril": {
        "generic_name": "lisinopril",
        "brand_names": ["Prinivil", "Zestril"],
        "drug_class": "ACE Inhibitor",
        "category": "cardiovascular",
        "formulary_tier": 1,  # 1=Generic/Preferred, 2=Brand Preferred, 3=Non-preferred
        "dosage_forms": ["tablet 2.5mg", "tablet 5mg", "tablet 10mg", "tablet 20mg", "tablet 40mg"],
        "typical_dosing": "Start 5-10mg daily, max 40mg daily",
        "indications": ["Hypertension", "Heart Failure", "Post-MI", "Diabetic Nephropathy"],
        "contraindications": ["Pregnancy", "Angioedema history", "Bilateral renal artery stenosis"],
        "side_effects": ["Dry cough", "Hyperkalemia", "Dizziness", "Angioedema (rare)"],
        "monitoring": ["Potassium", "Creatinine", "Blood pressure"],
        "interactions": ["Potassium supplements", "Potassium-sparing diuretics", "NSAIDs", "Lithium"],
        "black_box_warning": "Pregnancy: Can cause fetal harm. Discontinue when pregnancy detected.",
        "requires_prior_auth": False
    },
    "metoprolol_succinate": {
        "generic_name": "metoprolol succinate",
        "brand_names": ["Toprol-XL"],
        "drug_class": "Beta Blocker",
        "category": "cardiovascular",
        "formulary_tier": 1,
        "dosage_forms": ["ER tablet 25mg", "ER tablet 50mg", "ER tablet 100mg", "ER tablet 200mg"],
        "typical_dosing": "Start 25-50mg daily, titrate to effect, max 400mg",
        "indications": ["Hypertension", "Heart Failure (HFrEF)", "Angina", "Post-MI"],
        "contraindications": ["Severe bradycardia", "Heart block", "Cardiogenic shock", "Decompensated HF"],
        "side_effects": ["Fatigue", "Bradycardia", "Hypotension", "Cold extremities"],
        "monitoring": ["Heart rate", "Blood pressure"],
        "interactions": ["Calcium channel blockers", "Digoxin", "MAOIs"],
        "black_box_warning": None,
        "requires_prior_auth": False
    },
    "atorvastatin": {
        "generic_name": "atorvastatin",
        "brand_names": ["Lipitor"],
        "drug_class": "HMG-CoA Reductase Inhibitor (Statin)",
        "category": "cardiovascular",
        "formulary_tier": 1,
        "dosage_forms": ["tablet 10mg", "tablet 20mg", "tablet 40mg", "tablet 80mg"],
        "typical_dosing": "10-80mg daily, take at any time",
        "indications": ["Hyperlipidemia", "ASCVD prevention", "Familial hypercholesterolemia"],
        "contraindications": ["Active liver disease", "Pregnancy", "Breastfeeding"],
        "side_effects": ["Myalgia", "Elevated transaminases", "Rhabdomyolysis (rare)"],
        "monitoring": ["Lipid panel", "LFTs", "CK if symptomatic"],
        "interactions": ["Gemfibrozil", "Cyclosporine", "Strong CYP3A4 inhibitors"],
        "black_box_warning": None,
        "requires_prior_auth": False
    },
    # Diabetes
    "metformin": {
        "generic_name": "metformin",
        "brand_names": ["Glucophage", "Glumetza"],
        "drug_class": "Biguanide",
        "category": "diabetes",
        "formulary_tier": 1,
        "dosage_forms": ["tablet 500mg", "tablet 850mg", "tablet 1000mg", "ER tablet 500mg", "ER tablet 750mg"],
        "typical_dosing": "Start 500mg BID with meals, max 2550mg/day",
        "indications": ["Type 2 Diabetes Mellitus"],
        "contraindications": ["eGFR <30", "Metabolic acidosis", "IV contrast (hold 48h)"],
        "side_effects": ["GI upset", "Diarrhea", "B12 deficiency", "Lactic acidosis (rare)"],
        "monitoring": ["HbA1c", "Renal function", "B12 annually"],
        "interactions": ["IV contrast media", "Alcohol"],
        "black_box_warning": "Lactic acidosis: Rare but serious. Contraindicated in renal impairment.",
        "requires_prior_auth": False
    },
    "empagliflozin": {
        "generic_name": "empagliflozin",
        "brand_names": ["Jardiance"],
        "drug_class": "SGLT2 Inhibitor",
        "category": "diabetes",
        "formulary_tier": 2,
        "dosage_forms": ["tablet 10mg", "tablet 25mg"],
        "typical_dosing": "10mg daily, may increase to 25mg",
        "indications": ["Type 2 Diabetes", "Heart Failure (HFrEF)", "CKD"],
        "contraindications": ["Type 1 diabetes", "Dialysis", "History of DKA"],
        "side_effects": ["UTI", "Genital mycotic infections", "Hypotension", "DKA (rare)"],
        "monitoring": ["HbA1c", "Renal function", "Blood pressure"],
        "interactions": ["Diuretics", "Insulin (hypoglycemia risk)"],
        "black_box_warning": None,
        "requires_prior_auth": True
    },
    "semaglutide": {
        "generic_name": "semaglutide",
        "brand_names": ["Ozempic", "Rybelsus", "Wegovy"],
        "drug_class": "GLP-1 Receptor Agonist",
        "category": "diabetes",
        "formulary_tier": 3,
        "dosage_forms": ["injection 0.25mg/dose", "injection 0.5mg/dose", "injection 1mg/dose", "injection 2mg/dose", "tablet 3mg", "tablet 7mg", "tablet 14mg"],
        "typical_dosing": "SC: Start 0.25mg weekly x4wk, then 0.5mg, may increase to 2mg. PO: Start 3mg daily",
        "indications": ["Type 2 Diabetes", "Weight management", "CV risk reduction"],
        "contraindications": ["Personal/family history of MTC", "MEN 2 syndrome"],
        "side_effects": ["Nausea", "Vomiting", "Diarrhea", "Pancreatitis (rare)"],
        "monitoring": ["HbA1c", "Weight", "Renal function"],
        "interactions": ["Insulin (dose reduction needed)", "Sulfonylureas"],
        "black_box_warning": "Thyroid C-cell tumors: Contraindicated with MTC history or MEN 2.",
        "requires_prior_auth": True
    },
    # Pain/Anti-inflammatory
    "ibuprofen": {
        "generic_name": "ibuprofen",
        "brand_names": ["Advil", "Motrin"],
        "drug_class": "NSAID",
        "category": "pain",
        "formulary_tier": 1,
        "dosage_forms": ["tablet 200mg", "tablet 400mg", "tablet 600mg", "tablet 800mg"],
        "typical_dosing": "200-800mg every 6-8 hours, max 3200mg/day",
        "indications": ["Pain", "Inflammation", "Fever", "Arthritis"],
        "contraindications": ["CABG perioperative", "Active GI bleed", "Severe renal impairment"],
        "side_effects": ["GI upset", "GI bleeding", "Renal impairment", "CV events"],
        "monitoring": ["Renal function", "GI symptoms"],
        "interactions": ["Aspirin", "Anticoagulants", "ACE inhibitors", "Methotrexate"],
        "black_box_warning": "CV and GI risk: Increased risk of serious CV events and GI bleeding.",
        "requires_prior_auth": False
    },
    # Respiratory
    "albuterol": {
        "generic_name": "albuterol",
        "brand_names": ["ProAir", "Ventolin", "Proventil"],
        "drug_class": "Short-Acting Beta Agonist (SABA)",
        "category": "respiratory",
        "formulary_tier": 1,
        "dosage_forms": ["HFA inhaler 90mcg/puff", "nebulizer solution 2.5mg/3mL"],
        "typical_dosing": "1-2 puffs q4-6h PRN, max 12 puffs/day",
        "indications": ["Asthma", "COPD", "Bronchospasm"],
        "contraindications": ["Hypersensitivity"],
        "side_effects": ["Tachycardia", "Tremor", "Nervousness", "Hypokalemia"],
        "monitoring": ["Heart rate", "Potassium if frequent use"],
        "interactions": ["Beta blockers (antagonism)", "MAOIs"],
        "black_box_warning": None,
        "requires_prior_auth": False
    },
    # Antibiotics
    "amoxicillin": {
        "generic_name": "amoxicillin",
        "brand_names": ["Amoxil"],
        "drug_class": "Penicillin Antibiotic",
        "category": "antibiotic",
        "formulary_tier": 1,
        "dosage_forms": ["capsule 250mg", "capsule 500mg", "tablet 875mg", "suspension 125mg/5mL", "suspension 250mg/5mL"],
        "typical_dosing": "250-500mg TID or 875mg BID, duration varies by indication",
        "indications": ["Respiratory infections", "UTI", "H. pylori", "Dental infections"],
        "contraindications": ["Penicillin allergy"],
        "side_effects": ["Diarrhea", "Rash", "Nausea", "C. diff (rare)"],
        "monitoring": ["Clinical response"],
        "interactions": ["Methotrexate", "Warfarin"],
        "black_box_warning": None,
        "requires_prior_auth": False
    },
    # Psychiatric
    "sertraline": {
        "generic_name": "sertraline",
        "brand_names": ["Zoloft"],
        "drug_class": "SSRI",
        "category": "psychiatric",
        "formulary_tier": 1,
        "dosage_forms": ["tablet 25mg", "tablet 50mg", "tablet 100mg"],
        "typical_dosing": "Start 50mg daily, may increase to max 200mg",
        "indications": ["Major Depression", "OCD", "Panic Disorder", "PTSD", "Social Anxiety"],
        "contraindications": ["MAOIs (14-day washout)", "Pimozide"],
        "side_effects": ["Nausea", "Diarrhea", "Insomnia", "Sexual dysfunction"],
        "monitoring": ["Mood", "Suicidality (especially in young patients)"],
        "interactions": ["MAOIs", "Serotonergic drugs", "Warfarin", "NSAIDs"],
        "black_box_warning": "Suicidality: Increased risk in children, adolescents, and young adults.",
        "requires_prior_auth": False
    },
    # Anticoagulants
    "apixaban": {
        "generic_name": "apixaban",
        "brand_names": ["Eliquis"],
        "drug_class": "Factor Xa Inhibitor (DOAC)",
        "category": "anticoagulant",
        "formulary_tier": 2,
        "dosage_forms": ["tablet 2.5mg", "tablet 5mg"],
        "typical_dosing": "AF: 5mg BID (2.5mg if criteria met). VTE: 10mg BID x7d then 5mg BID",
        "indications": ["Atrial Fibrillation", "DVT/PE treatment", "VTE prophylaxis"],
        "contraindications": ["Active bleeding", "Severe hepatic impairment"],
        "side_effects": ["Bleeding", "Anemia", "Bruising"],
        "monitoring": ["Signs of bleeding", "Renal function"],
        "interactions": ["Strong CYP3A4 inhibitors", "P-gp inhibitors", "Antiplatelet agents"],
        "black_box_warning": "Spinal/epidural hematoma risk with neuraxial anesthesia. Premature discontinuation increases stroke risk.",
        "requires_prior_auth": False
    },
    "warfarin": {
        "generic_name": "warfarin",
        "brand_names": ["Coumadin", "Jantoven"],
        "drug_class": "Vitamin K Antagonist",
        "category": "anticoagulant",
        "formulary_tier": 1,
        "dosage_forms": ["tablet 1mg", "tablet 2mg", "tablet 2.5mg", "tablet 3mg", "tablet 4mg", "tablet 5mg", "tablet 6mg", "tablet 7.5mg", "tablet 10mg"],
        "typical_dosing": "Individualized based on INR, typical 2-10mg daily",
        "indications": ["Atrial Fibrillation", "Mechanical heart valves", "DVT/PE", "Hypercoagulable states"],
        "contraindications": ["Pregnancy", "Active major bleeding", "Recent CNS surgery"],
        "side_effects": ["Bleeding", "Skin necrosis", "Purple toe syndrome"],
        "monitoring": ["INR (target 2-3 usually)", "Signs of bleeding"],
        "interactions": ["Many - extensive drug and food interactions", "Vitamin K foods"],
        "black_box_warning": "Bleeding: Can cause major or fatal bleeding. Regular INR monitoring required.",
        "requires_prior_auth": False
    }
}

# Controlled Substances Schedule
CONTROLLED_SUBSTANCES = {
    "oxycodone": {"schedule": "II", "requires_epcs": True},
    "hydrocodone": {"schedule": "II", "requires_epcs": True},
    "morphine": {"schedule": "II", "requires_epcs": True},
    "fentanyl": {"schedule": "II", "requires_epcs": True},
    "amphetamine": {"schedule": "II", "requires_epcs": True},
    "methylphenidate": {"schedule": "II", "requires_epcs": True},
    "alprazolam": {"schedule": "IV", "requires_epcs": True},
    "lorazepam": {"schedule": "IV", "requires_epcs": True},
    "diazepam": {"schedule": "IV", "requires_epcs": True},
    "zolpidem": {"schedule": "IV", "requires_epcs": True},
    "tramadol": {"schedule": "IV", "requires_epcs": True},
    "gabapentin": {"schedule": "V", "requires_epcs": False},  # Schedule varies by state
}


class MCPPharmacyServer(BaseMCPServer):
    """MCP Server for pharmacy and medication management"""

    def __init__(self):
        super().__init__(
            name="mcp-pharmacy",
            description="Drug formulary, medication management, and prescription services",
            version="1.0.0"
        )
        self.setup_tools()

    def setup_tools(self):
        """Register pharmacy tools"""

        @self.register_tool(
            name="lookup_drug",
            description="Look up drug information by name",
            input_schema={
                "drug_name": "string - generic or brand name",
                "include_alternatives": "bool - include therapeutic alternatives (optional)"
            },
            output_schema={"drug": "drug information"},
            category="formulary",
            requires_patient_context=False
        )
        async def lookup_drug(request: MCPRequest):
            drug_name = request.arguments.get("drug_name", "").lower().replace(" ", "_")
            include_alternatives = request.arguments.get("include_alternatives", False)

            # Search by generic name or brand name
            result = None
            for generic, info in DRUG_FORMULARY.items():
                if generic == drug_name or drug_name in [b.lower() for b in info["brand_names"]]:
                    result = {"generic_name": generic, **info}
                    break

            if not result:
                # Fuzzy search
                matches = []
                for generic, info in DRUG_FORMULARY.items():
                    if drug_name in generic or any(drug_name in b.lower() for b in info["brand_names"]):
                        matches.append({"generic_name": generic, **info})
                if matches:
                    result = matches[0]
                    if len(matches) > 1:
                        return {"drug": result, "other_matches": [m["generic_name"] for m in matches[1:]]}

            if not result:
                return {"error": "Drug not found", "search_term": drug_name}

            # Find alternatives if requested
            if include_alternatives:
                alternatives = []
                for generic, info in DRUG_FORMULARY.items():
                    if info["drug_class"] == result["drug_class"] and generic != result["generic_name"]:
                        alternatives.append({
                            "generic_name": generic,
                            "formulary_tier": info["formulary_tier"],
                            "brand_names": info["brand_names"]
                        })
                result["therapeutic_alternatives"] = alternatives

            return {"drug": result}

        @self.register_tool(
            name="check_formulary",
            description="Check drug formulary status and coverage",
            input_schema={
                "drug_name": "string",
                "insurance_plan": "string (optional)"
            },
            output_schema={"formulary_status": "coverage information"},
            category="formulary",
            requires_patient_context=False
        )
        async def check_formulary(request: MCPRequest):
            drug_name = request.arguments.get("drug_name", "").lower().replace(" ", "_")

            # Find drug
            drug_info = None
            for generic, info in DRUG_FORMULARY.items():
                if generic == drug_name or drug_name in [b.lower() for b in info["brand_names"]]:
                    drug_info = {"generic_name": generic, **info}
                    break

            if not drug_info:
                return {"error": "Drug not found", "formulary_status": "unknown"}

            tier = drug_info["formulary_tier"]
            requires_pa = drug_info["requires_prior_auth"]

            coverage = {
                "drug_name": drug_info["generic_name"],
                "brand_names": drug_info["brand_names"],
                "formulary_tier": tier,
                "tier_description": {1: "Generic/Preferred - Lowest copay", 2: "Brand Preferred - Moderate copay", 3: "Non-preferred - Highest copay"}.get(tier, "Unknown"),
                "requires_prior_authorization": requires_pa,
                "quantity_limits": self._get_quantity_limits(drug_info["generic_name"]),
                "step_therapy_required": drug_info["generic_name"] in ["semaglutide", "empagliflozin"]
            }

            # Suggest lower-tier alternatives
            if tier > 1:
                alternatives = []
                for generic, info in DRUG_FORMULARY.items():
                    if (info["drug_class"] == drug_info["drug_class"] and
                        info["formulary_tier"] < tier):
                        alternatives.append({
                            "generic_name": generic,
                            "tier": info["formulary_tier"]
                        })
                if alternatives:
                    coverage["lower_cost_alternatives"] = alternatives

            return {"formulary_status": coverage}

        @self.register_tool(
            name="check_interactions",
            description="Check for drug-drug interactions",
            input_schema={
                "medications": "list of medication names",
                "new_medication": "string - medication to check against list"
            },
            output_schema={"interactions": "list of interactions"},
            category="safety",
            requires_patient_context=False
        )
        async def check_interactions(request: MCPRequest):
            medications = request.arguments.get("medications", [])
            new_med = request.arguments.get("new_medication", "").lower()

            interactions = []

            # Get drug info for new medication
            new_drug_info = None
            for generic, info in DRUG_FORMULARY.items():
                if generic == new_med.replace(" ", "_") or new_med in [b.lower() for b in info["brand_names"]]:
                    new_drug_info = info
                    break

            if not new_drug_info:
                return {"error": f"Drug {new_med} not found", "interactions": []}

            # Check each current medication
            for med in medications:
                med_lower = med.lower().replace(" ", "_")

                # Check if listed in interactions
                for interaction_drug in new_drug_info.get("interactions", []):
                    if interaction_drug.lower() in med_lower or med_lower in interaction_drug.lower():
                        interactions.append({
                            "drug1": new_med,
                            "drug2": med,
                            "severity": self._get_interaction_severity(new_med, med),
                            "description": f"Potential interaction between {new_med} and {med}",
                            "recommendation": self._get_interaction_recommendation(new_med, med)
                        })

                # Check drug class interactions
                current_drug_info = None
                for generic, info in DRUG_FORMULARY.items():
                    if generic == med_lower or med_lower in [b.lower() for b in info.get("brand_names", [])]:
                        current_drug_info = info
                        break

                if current_drug_info:
                    class_interaction = self._check_class_interaction(
                        new_drug_info["drug_class"],
                        current_drug_info["drug_class"]
                    )
                    if class_interaction:
                        interactions.append({
                            "drug1": new_med,
                            "drug2": med,
                            "severity": class_interaction["severity"],
                            "description": class_interaction["description"],
                            "recommendation": class_interaction["recommendation"]
                        })

            return {
                "new_medication": new_med,
                "current_medications": medications,
                "interactions_found": len(interactions),
                "interactions": interactions,
                "safe_to_prescribe": len([i for i in interactions if i["severity"] == "major"]) == 0
            }

        @self.register_tool(
            name="get_dosing",
            description="Get dosing recommendations for a medication",
            input_schema={
                "drug_name": "string",
                "indication": "string - condition being treated",
                "patient_factors": "dict - age, weight, renal_function, hepatic_function (optional)"
            },
            output_schema={"dosing": "dosing recommendations"},
            category="clinical"
        )
        async def get_dosing(request: MCPRequest):
            drug_name = request.arguments.get("drug_name", "").lower().replace(" ", "_")
            indication = request.arguments.get("indication", "")
            patient_factors = request.arguments.get("patient_factors", {})

            # Find drug
            drug_info = None
            for generic, info in DRUG_FORMULARY.items():
                if generic == drug_name or drug_name in [b.lower() for b in info["brand_names"]]:
                    drug_info = {"generic_name": generic, **info}
                    break

            if not drug_info:
                return {"error": "Drug not found"}

            dosing = {
                "drug_name": drug_info["generic_name"],
                "indication": indication,
                "standard_dosing": drug_info["typical_dosing"],
                "available_forms": drug_info["dosage_forms"],
                "adjustments": []
            }

            # Renal adjustment
            egfr = patient_factors.get("egfr") or patient_factors.get("renal_function")
            if egfr:
                if drug_name == "metformin" and egfr < 30:
                    dosing["adjustments"].append({
                        "reason": f"Renal impairment (eGFR {egfr})",
                        "adjustment": "CONTRAINDICATED - do not use"
                    })
                elif drug_name == "metformin" and egfr < 45:
                    dosing["adjustments"].append({
                        "reason": f"Renal impairment (eGFR {egfr})",
                        "adjustment": "Max 1000mg/day, monitor renal function closely"
                    })
                elif egfr < 30 and drug_name in ["lisinopril", "enalapril"]:
                    dosing["adjustments"].append({
                        "reason": f"Severe renal impairment (eGFR {egfr})",
                        "adjustment": "Start at lower dose, titrate cautiously"
                    })

            # Age adjustment
            age = patient_factors.get("age")
            if age and age >= 65:
                dosing["adjustments"].append({
                    "reason": "Elderly patient (≥65 years)",
                    "adjustment": "Consider starting at lower dose, monitor closely"
                })
                if drug_name in ["alprazolam", "lorazepam", "diazepam", "zolpidem"]:
                    dosing["adjustments"].append({
                        "reason": "Elderly + benzodiazepine/sedative",
                        "adjustment": "BEERS Criteria: Avoid if possible. If used, lowest effective dose."
                    })

            # Hepatic adjustment
            if patient_factors.get("hepatic_impairment"):
                if drug_name == "atorvastatin":
                    dosing["adjustments"].append({
                        "reason": "Hepatic impairment",
                        "adjustment": "CONTRAINDICATED in active liver disease"
                    })

            return {"dosing": dosing}

        @self.register_tool(
            name="check_controlled_status",
            description="Check if medication is a controlled substance",
            input_schema={"drug_name": "string"},
            output_schema={"controlled_status": "DEA schedule and requirements"},
            category="compliance",
            requires_patient_context=False
        )
        async def check_controlled_status(request: MCPRequest):
            drug_name = request.arguments.get("drug_name", "").lower()

            for controlled, info in CONTROLLED_SUBSTANCES.items():
                if controlled in drug_name or drug_name in controlled:
                    return {
                        "drug_name": drug_name,
                        "is_controlled": True,
                        "schedule": info["schedule"],
                        "schedule_description": self._get_schedule_description(info["schedule"]),
                        "requires_epcs": info["requires_epcs"],
                        "prescription_requirements": self._get_prescription_requirements(info["schedule"])
                    }

            return {
                "drug_name": drug_name,
                "is_controlled": False,
                "schedule": None
            }

        @self.register_tool(
            name="get_patient_medications",
            description="Get active medications for a patient from FHIR",
            input_schema={"patient_id": "string"},
            output_schema={"medications": "list of active medications"},
            category="patient_data"
        )
        async def get_patient_medications(request: MCPRequest):
            import httpx
            patient_id = request.arguments.get("patient_id") or request.patient_id

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{FHIR_BASE}/MedicationRequest",
                    params={
                        "subject:Patient": patient_id,
                        "status": "active",
                        "_count": "100"
                    }
                )
                r.raise_for_status()
                bundle = r.json()

                medications = []
                for entry in bundle.get("entry", []):
                    med = entry.get("resource", {})
                    med_code = med.get("medicationCodeableConcept", {}).get("coding", [{}])[0]
                    dosage = med.get("dosageInstruction", [{}])[0]

                    med_name = med_code.get("display", "Unknown")

                    # Enrich with formulary data
                    formulary_info = None
                    for generic, info in DRUG_FORMULARY.items():
                        if generic in med_name.lower() or any(b.lower() in med_name.lower() for b in info["brand_names"]):
                            formulary_info = info
                            break

                    medications.append({
                        "id": med.get("id"),
                        "medication_name": med_name,
                        "status": med.get("status"),
                        "dosage_instruction": dosage.get("text"),
                        "route": dosage.get("route", {}).get("coding", [{}])[0].get("display"),
                        "authored_on": med.get("authoredOn"),
                        "drug_class": formulary_info.get("drug_class") if formulary_info else None,
                        "black_box_warning": formulary_info.get("black_box_warning") if formulary_info else None
                    })

                return {"patient_id": patient_id, "count": len(medications), "medications": medications}

        @self.register_tool(
            name="suggest_alternatives",
            description="Suggest therapeutic alternatives for a medication",
            input_schema={
                "drug_name": "string",
                "reason": "string - cost, allergy, side_effect, formulary (optional)"
            },
            output_schema={"alternatives": "list of alternative medications"},
            category="clinical",
            requires_patient_context=False
        )
        async def suggest_alternatives(request: MCPRequest):
            drug_name = request.arguments.get("drug_name", "").lower().replace(" ", "_")
            reason = request.arguments.get("reason", "general")

            # Find drug class
            drug_info = None
            for generic, info in DRUG_FORMULARY.items():
                if generic == drug_name or drug_name in [b.lower() for b in info["brand_names"]]:
                    drug_info = {"generic_name": generic, **info}
                    break

            if not drug_info:
                return {"error": "Drug not found"}

            alternatives = []
            for generic, info in DRUG_FORMULARY.items():
                if generic == drug_info["generic_name"]:
                    continue

                # Same drug class
                if info["drug_class"] == drug_info["drug_class"]:
                    alt = {
                        "generic_name": generic,
                        "brand_names": info["brand_names"],
                        "drug_class": info["drug_class"],
                        "formulary_tier": info["formulary_tier"],
                        "typical_dosing": info["typical_dosing"],
                        "key_differences": []
                    }

                    # Note differences
                    if info["formulary_tier"] < drug_info["formulary_tier"]:
                        alt["key_differences"].append("Lower formulary tier (lower cost)")
                    if not info["requires_prior_auth"] and drug_info["requires_prior_auth"]:
                        alt["key_differences"].append("No prior authorization required")

                    alternatives.append(alt)

            # Sort by formulary tier
            alternatives.sort(key=lambda x: x["formulary_tier"])

            return {
                "original_drug": drug_info["generic_name"],
                "drug_class": drug_info["drug_class"],
                "reason_for_alternative": reason,
                "alternatives": alternatives
            }

    def _get_quantity_limits(self, drug_name: str) -> Optional[Dict]:
        """Get quantity limits for a drug"""
        limits = {
            "semaglutide": {"quantity": 4, "days_supply": 28, "note": "One pen per week"},
            "oxycodone": {"quantity": 120, "days_supply": 30, "note": "Controlled substance limit"},
            "alprazolam": {"quantity": 90, "days_supply": 30, "note": "Controlled substance limit"},
        }
        return limits.get(drug_name)

    def _get_interaction_severity(self, drug1: str, drug2: str) -> str:
        """Determine interaction severity"""
        major_interactions = [
            ("warfarin", "aspirin"),
            ("metformin", "contrast"),
            ("ssri", "maoi"),
            ("ace_inhibitor", "potassium")
        ]
        for d1, d2 in major_interactions:
            if (d1 in drug1.lower() or d1 in drug2.lower()) and (d2 in drug1.lower() or d2 in drug2.lower()):
                return "major"
        return "moderate"

    def _get_interaction_recommendation(self, drug1: str, drug2: str) -> str:
        """Get recommendation for interaction"""
        return "Monitor closely. Consider alternative therapy if clinically appropriate."

    def _check_class_interaction(self, class1: str, class2: str) -> Optional[Dict]:
        """Check for drug class interactions"""
        class_interactions = {
            ("ACE Inhibitor", "Potassium-sparing diuretic"): {
                "severity": "major",
                "description": "Risk of hyperkalemia",
                "recommendation": "Monitor potassium closely"
            },
            ("NSAID", "Anticoagulant"): {
                "severity": "major",
                "description": "Increased bleeding risk",
                "recommendation": "Avoid combination if possible, use PPI if needed"
            },
            ("SSRI", "NSAID"): {
                "severity": "moderate",
                "description": "Increased GI bleeding risk",
                "recommendation": "Consider PPI for gastroprotection"
            },
        }

        for (c1, c2), info in class_interactions.items():
            if (c1 in class1 and c2 in class2) or (c1 in class2 and c2 in class1):
                return info
        return None

    def _get_schedule_description(self, schedule: str) -> str:
        """Get DEA schedule description"""
        descriptions = {
            "I": "No accepted medical use, high abuse potential",
            "II": "High abuse potential, severe dependence liability",
            "III": "Moderate abuse potential",
            "IV": "Low abuse potential relative to Schedule III",
            "V": "Low abuse potential relative to Schedule IV"
        }
        return descriptions.get(schedule, "Unknown")

    def _get_prescription_requirements(self, schedule: str) -> List[str]:
        """Get prescription requirements for controlled substance"""
        requirements = ["Valid DEA registration required"]

        if schedule in ["II"]:
            requirements.extend([
                "Written prescription required (no refills)",
                "EPCS (Electronic Prescribing for Controlled Substances) required in most states",
                "90-day supply maximum",
                "Prescription valid for 6 months"
            ])
        elif schedule in ["III", "IV"]:
            requirements.extend([
                "Up to 5 refills in 6 months",
                "May be transmitted electronically"
            ])
        elif schedule == "V":
            requirements.append("May be dispensed OTC in some states with pharmacist discretion")

        return requirements


# Create server instance
server = MCPPharmacyServer()
app = server.app
