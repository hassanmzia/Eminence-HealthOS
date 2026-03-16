"""
MCP-FHIR Server
Provides unified access to FHIR resources (Patient, Observation, Condition, etc.)
"""

import httpx
import os
from typing import Optional

# Support both package import and direct execution
try:
    from .base import BaseMCPServer, MCPRequest
except ImportError:
    from base import BaseMCPServer, MCPRequest

FHIR_BASE = os.getenv("FHIR_BASE", "http://hapi-fhir:8080/fhir")


class MCPFHIRServer(BaseMCPServer):
    """MCP Server for FHIR data access"""

    def __init__(self):
        super().__init__(
            name="mcp-fhir",
            description="FHIR R4 data access for patient clinical information",
            version="1.0.0"
        )
        self.setup_tools()

    def setup_tools(self):
        """Register FHIR tools"""

        @self.register_tool(
            name="get_patient",
            description="Get patient demographics and identifiers",
            input_schema={"patient_id": "string"},
            output_schema={"patient": "Patient resource"},
            category="demographics"
        )
        async def get_patient(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Patient/{patient_id}")
                if r.status_code == 404:
                    return {"error": "Patient not found", "patient_id": patient_id}
                r.raise_for_status()
                return r.json()

        @self.register_tool(
            name="get_vitals",
            description="Get patient vital signs including ECG and glucose (heart rate, BP, SpO2, temp, glucose, ECG, etc.)",
            input_schema={
                "patient_id": "string",
                "count": "integer (default 50)",
                "from_date": "ISO date string (optional)",
                "to_date": "ISO date string (optional)"
            },
            output_schema={"vitals": "list of Observation resources"},
            category="vitals"
        )
        async def get_vitals(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id
            count = request.arguments.get("count", 50)

            params = {
                "subject:Patient": patient_id,
                "_count": str(count),
                "_sort": "-date"
            }

            if request.arguments.get("from_date"):
                params["date"] = f"ge{request.arguments['from_date']}"

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Observation", params=params)
                r.raise_for_status()
                bundle = r.json()

                # Extract and normalize vitals
                vitals = []
                for entry in bundle.get("entry", []):
                    obs = entry.get("resource", {})
                    loinc_code = obs.get("code", {}).get("coding", [{}])[0].get("code", "")

                    vital_entry = {
                        "id": obs.get("id"),
                        "code": loinc_code,
                        "display": obs.get("code", {}).get("coding", [{}])[0].get("display"),
                        "value": obs.get("valueQuantity", {}).get("value"),
                        "unit": obs.get("valueQuantity", {}).get("unit"),
                        "datetime": obs.get("effectiveDateTime"),
                        "components": [
                            {
                                "code": c.get("code", {}).get("coding", [{}])[0].get("code"),
                                "display": c.get("code", {}).get("coding", [{}])[0].get("display"),
                                "value": c.get("valueQuantity", {}).get("value"),
                                "unit": c.get("valueQuantity", {}).get("unit"),
                                "valueString": c.get("valueString"),
                            }
                            for c in obs.get("component", [])
                        ]
                    }

                    # ECG observations use valueCodeableConcept instead of valueQuantity
                    if loinc_code == "8601-7":
                        concept = obs.get("valueCodeableConcept", {})
                        vital_entry["ecg_rhythm"] = concept.get("coding", [{}])[0].get("display", "")
                        vital_entry["ecg_interpretation"] = concept.get("text", "")
                        vital_entry["ecg_findings"] = [
                            c.get("valueString")
                            for c in obs.get("component", [])
                            if c.get("code", {}).get("coding", [{}])[0].get("code") == "18844-1"
                            and c.get("valueString")
                        ]

                    vitals.append(vital_entry)

                return {"patient_id": patient_id, "count": len(vitals), "vitals": vitals}

        @self.register_tool(
            name="get_conditions",
            description="Get patient diagnoses and conditions (ICD-10 codes)",
            input_schema={
                "patient_id": "string",
                "clinical_status": "active|resolved|inactive (optional)"
            },
            output_schema={"conditions": "list of Condition resources"},
            category="diagnosis"
        )
        async def get_conditions(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id

            params = {
                "subject:Patient": patient_id,
                "_count": "100"
            }

            if request.arguments.get("clinical_status"):
                params["clinical-status"] = request.arguments["clinical_status"]

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Condition", params=params)
                r.raise_for_status()
                bundle = r.json()

                conditions = []
                for entry in bundle.get("entry", []):
                    cond = entry.get("resource", {})
                    code_info = cond.get("code", {}).get("coding", [{}])[0]
                    conditions.append({
                        "id": cond.get("id"),
                        "code": code_info.get("code"),
                        "system": code_info.get("system"),
                        "display": code_info.get("display"),
                        "clinical_status": cond.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
                        "verification_status": cond.get("verificationStatus", {}).get("coding", [{}])[0].get("code"),
                        "onset_date": cond.get("onsetDateTime"),
                        "recorded_date": cond.get("recordedDate")
                    })

                return {"patient_id": patient_id, "count": len(conditions), "conditions": conditions}

        @self.register_tool(
            name="get_encounters",
            description="Get patient encounters (visits, admissions)",
            input_schema={
                "patient_id": "string",
                "status": "planned|arrived|in-progress|finished (optional)",
                "count": "integer (default 20)"
            },
            output_schema={"encounters": "list of Encounter resources"},
            category="encounters"
        )
        async def get_encounters(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id
            count = request.arguments.get("count", 20)

            params = {
                "subject:Patient": patient_id,
                "_count": str(count),
                "_sort": "-date"
            }

            if request.arguments.get("status"):
                params["status"] = request.arguments["status"]

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Encounter", params=params)
                r.raise_for_status()
                bundle = r.json()

                encounters = []
                for entry in bundle.get("entry", []):
                    enc = entry.get("resource", {})
                    enc_type = enc.get("type", [{}])[0].get("coding", [{}])[0]
                    encounters.append({
                        "id": enc.get("id"),
                        "status": enc.get("status"),
                        "class": enc.get("class", {}).get("code"),
                        "type_code": enc_type.get("code"),
                        "type_display": enc_type.get("display"),
                        "period_start": enc.get("period", {}).get("start"),
                        "period_end": enc.get("period", {}).get("end"),
                        "reason": [
                            r.get("coding", [{}])[0].get("display")
                            for r in enc.get("reasonCode", [])
                        ]
                    })

                return {"patient_id": patient_id, "count": len(encounters), "encounters": encounters}

        @self.register_tool(
            name="get_medications",
            description="Get patient medication list (active prescriptions)",
            input_schema={
                "patient_id": "string",
                "status": "active|completed|stopped (optional)"
            },
            output_schema={"medications": "list of MedicationRequest resources"},
            category="medications"
        )
        async def get_medications(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id

            params = {
                "subject:Patient": patient_id,
                "_count": "100"
            }

            if request.arguments.get("status"):
                params["status"] = request.arguments["status"]

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/MedicationRequest", params=params)
                r.raise_for_status()
                bundle = r.json()

                medications = []
                for entry in bundle.get("entry", []):
                    med = entry.get("resource", {})
                    med_code = med.get("medicationCodeableConcept", {}).get("coding", [{}])[0]
                    dosage = med.get("dosageInstruction", [{}])[0]
                    medications.append({
                        "id": med.get("id"),
                        "status": med.get("status"),
                        "medication_code": med_code.get("code"),
                        "medication_name": med_code.get("display"),
                        "dosage_text": dosage.get("text"),
                        "route": dosage.get("route", {}).get("coding", [{}])[0].get("display"),
                        "frequency": dosage.get("timing", {}).get("code", {}).get("text"),
                        "authored_on": med.get("authoredOn")
                    })

                return {"patient_id": patient_id, "count": len(medications), "medications": medications}

        @self.register_tool(
            name="get_allergies",
            description="Get patient allergies and intolerances",
            input_schema={"patient_id": "string"},
            output_schema={"allergies": "list of AllergyIntolerance resources"},
            category="safety"
        )
        async def get_allergies(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id

            params = {
                "patient:Patient": patient_id,
                "_count": "100"
            }

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/AllergyIntolerance", params=params)
                r.raise_for_status()
                bundle = r.json()

                allergies = []
                for entry in bundle.get("entry", []):
                    allergy = entry.get("resource", {})
                    code_info = allergy.get("code", {}).get("coding", [{}])[0]
                    allergies.append({
                        "id": allergy.get("id"),
                        "clinical_status": allergy.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
                        "verification_status": allergy.get("verificationStatus", {}).get("coding", [{}])[0].get("code"),
                        "type": allergy.get("type"),
                        "category": allergy.get("category", []),
                        "criticality": allergy.get("criticality"),
                        "code": code_info.get("code"),
                        "substance": code_info.get("display"),
                        "reactions": [
                            {
                                "manifestation": r.get("manifestation", [{}])[0].get("coding", [{}])[0].get("display"),
                                "severity": r.get("severity")
                            }
                            for r in allergy.get("reaction", [])
                        ]
                    })

                return {"patient_id": patient_id, "count": len(allergies), "allergies": allergies}

        @self.register_tool(
            name="get_procedures",
            description="Get patient procedure history",
            input_schema={
                "patient_id": "string",
                "count": "integer (default 50)"
            },
            output_schema={"procedures": "list of Procedure resources"},
            category="procedures"
        )
        async def get_procedures(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id
            count = request.arguments.get("count", 50)

            params = {
                "subject:Patient": patient_id,
                "_count": str(count),
                "_sort": "-date"
            }

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Procedure", params=params)
                r.raise_for_status()
                bundle = r.json()

                procedures = []
                for entry in bundle.get("entry", []):
                    proc = entry.get("resource", {})
                    code_info = proc.get("code", {}).get("coding", [{}])[0]
                    procedures.append({
                        "id": proc.get("id"),
                        "status": proc.get("status"),
                        "code": code_info.get("code"),
                        "display": code_info.get("display"),
                        "system": code_info.get("system"),
                        "performed_date": proc.get("performedDateTime") or proc.get("performedPeriod", {}).get("start"),
                        "reason": [
                            r.get("coding", [{}])[0].get("display")
                            for r in proc.get("reasonCode", [])
                        ]
                    })

                return {"patient_id": patient_id, "count": len(procedures), "procedures": procedures}

        @self.register_tool(
            name="get_full_patient_context",
            description="Get comprehensive patient context (demographics, vitals, conditions, meds, allergies)",
            input_schema={"patient_id": "string"},
            output_schema={"context": "Complete patient clinical context"},
            category="aggregation"
        )
        async def get_full_patient_context(request: MCPRequest):
            """Aggregate all patient data for AI analysis"""
            patient_id = request.arguments.get("patient_id") or request.patient_id

            # Gather all data in parallel
            import asyncio

            patient_req = MCPRequest(tool_name="get_patient", arguments={"patient_id": patient_id})
            vitals_req = MCPRequest(tool_name="get_vitals", arguments={"patient_id": patient_id, "count": 20})
            conditions_req = MCPRequest(tool_name="get_conditions", arguments={"patient_id": patient_id})
            meds_req = MCPRequest(tool_name="get_medications", arguments={"patient_id": patient_id, "status": "active"})
            allergies_req = MCPRequest(tool_name="get_allergies", arguments={"patient_id": patient_id})
            encounters_req = MCPRequest(tool_name="get_encounters", arguments={"patient_id": patient_id, "count": 5})

            results = await asyncio.gather(
                self.tools["get_patient"](patient_req),
                self.tools["get_vitals"](vitals_req),
                self.tools["get_conditions"](conditions_req),
                self.tools["get_medications"](meds_req),
                self.tools["get_allergies"](allergies_req),
                self.tools["get_encounters"](encounters_req),
                return_exceptions=True
            )

            return {
                "patient_id": patient_id,
                "patient": results[0] if not isinstance(results[0], Exception) else None,
                "vitals": results[1] if not isinstance(results[1], Exception) else None,
                "conditions": results[2] if not isinstance(results[2], Exception) else None,
                "medications": results[3] if not isinstance(results[3], Exception) else None,
                "allergies": results[4] if not isinstance(results[4], Exception) else None,
                "encounters": results[5] if not isinstance(results[5], Exception) else None,
            }


# Create server instance
server = MCPFHIRServer()
app = server.app
