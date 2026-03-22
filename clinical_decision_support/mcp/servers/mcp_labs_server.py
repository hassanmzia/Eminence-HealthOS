"""
MCP-Labs Server
Provides access to laboratory results with clinical interpretation
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

# Clinical reference ranges for common labs
REFERENCE_RANGES = {
    # Complete Blood Count
    "WBC": {"low": 4.5, "high": 11.0, "unit": "10^9/L", "critical_low": 2.0, "critical_high": 30.0},
    "RBC": {"low": 4.5, "high": 5.5, "unit": "10^12/L", "critical_low": 2.5, "critical_high": 8.0},
    "Hemoglobin": {"low": 12.0, "high": 17.5, "unit": "g/dL", "critical_low": 7.0, "critical_high": 20.0},
    "Hematocrit": {"low": 36, "high": 50, "unit": "%", "critical_low": 20, "critical_high": 60},
    "Platelets": {"low": 150, "high": 400, "unit": "10^9/L", "critical_low": 50, "critical_high": 1000},

    # Comprehensive Metabolic Panel
    "Glucose": {"low": 70, "high": 100, "unit": "mg/dL", "critical_low": 40, "critical_high": 500},
    "BUN": {"low": 7, "high": 20, "unit": "mg/dL", "critical_low": 2, "critical_high": 100},
    "Creatinine": {"low": 0.6, "high": 1.2, "unit": "mg/dL", "critical_low": 0.3, "critical_high": 10.0},
    "Sodium": {"low": 136, "high": 145, "unit": "mEq/L", "critical_low": 120, "critical_high": 160},
    "Potassium": {"low": 3.5, "high": 5.0, "unit": "mEq/L", "critical_low": 2.5, "critical_high": 6.5},
    "Chloride": {"low": 98, "high": 106, "unit": "mEq/L", "critical_low": 80, "critical_high": 120},
    "CO2": {"low": 23, "high": 29, "unit": "mEq/L", "critical_low": 10, "critical_high": 40},
    "Calcium": {"low": 8.5, "high": 10.5, "unit": "mg/dL", "critical_low": 6.0, "critical_high": 13.0},

    # Liver Function
    "AST": {"low": 10, "high": 40, "unit": "U/L", "critical_high": 1000},
    "ALT": {"low": 7, "high": 56, "unit": "U/L", "critical_high": 1000},
    "ALP": {"low": 44, "high": 147, "unit": "U/L"},
    "Bilirubin": {"low": 0.1, "high": 1.2, "unit": "mg/dL", "critical_high": 15.0},
    "Albumin": {"low": 3.5, "high": 5.0, "unit": "g/dL", "critical_low": 1.5},

    # Cardiac Markers
    "Troponin": {"low": 0, "high": 0.04, "unit": "ng/mL", "critical_high": 0.1},
    "BNP": {"low": 0, "high": 100, "unit": "pg/mL", "critical_high": 500},
    "CK-MB": {"low": 0, "high": 5, "unit": "ng/mL", "critical_high": 10},

    # Thyroid
    "TSH": {"low": 0.4, "high": 4.0, "unit": "mIU/L"},
    "T4": {"low": 4.5, "high": 12.0, "unit": "mcg/dL"},
    "T3": {"low": 80, "high": 200, "unit": "ng/dL"},

    # Coagulation
    "PT": {"low": 11, "high": 13.5, "unit": "seconds", "critical_high": 30},
    "INR": {"low": 0.9, "high": 1.1, "unit": "ratio", "critical_high": 5.0},
    "PTT": {"low": 25, "high": 35, "unit": "seconds", "critical_high": 100},

    # Lipids
    "Total Cholesterol": {"low": 0, "high": 200, "unit": "mg/dL"},
    "LDL": {"low": 0, "high": 100, "unit": "mg/dL"},
    "HDL": {"low": 40, "high": 200, "unit": "mg/dL"},
    "Triglycerides": {"low": 0, "high": 150, "unit": "mg/dL"},

    # HbA1c
    "HbA1c": {"low": 4.0, "high": 5.6, "unit": "%", "critical_high": 14.0},
}

# LOINC code to lab name mapping
LOINC_TO_LAB = {
    "2339-0": "Glucose",
    "3094-0": "BUN",
    "2160-0": "Creatinine",
    "2951-2": "Sodium",
    "2823-3": "Potassium",
    "2075-0": "Chloride",
    "1988-5": "CO2",
    "17861-6": "Calcium",
    "1920-8": "AST",
    "1742-6": "ALT",
    "6768-6": "ALP",
    "1975-2": "Bilirubin",
    "1751-7": "Albumin",
    "6690-2": "WBC",
    "789-8": "RBC",
    "718-7": "Hemoglobin",
    "4544-3": "Hematocrit",
    "777-3": "Platelets",
    "10839-9": "Troponin",
    "42637-9": "BNP",
    "3094-0": "TSH",
    "5902-2": "PT",
    "6301-6": "INR",
    "3173-2": "PTT",
    "2093-3": "Total Cholesterol",
    "13457-7": "LDL",
    "2085-9": "HDL",
    "2571-8": "Triglycerides",
    "4548-4": "HbA1c",
}


class MCPLabsServer(BaseMCPServer):
    """MCP Server for laboratory results with clinical interpretation"""

    def __init__(self):
        super().__init__(
            name="mcp-labs",
            description="Laboratory results access with clinical interpretation and alerts",
            version="1.0.0"
        )
        self.setup_tools()

    def setup_tools(self):
        """Register lab tools"""

        @self.register_tool(
            name="get_lab_results",
            description="Get patient laboratory results with interpretation",
            input_schema={
                "patient_id": "string",
                "panel": "CBC|CMP|LFT|Lipids|Thyroid|Coag|Cardiac|all (optional)",
                "count": "integer (default 50)",
                "from_date": "ISO date (optional)"
            },
            output_schema={"labs": "list of interpreted lab results"},
            category="labs"
        )
        async def get_lab_results(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id
            count = request.arguments.get("count", 50)

            params = {
                "subject:Patient": patient_id,
                "category": "laboratory",
                "_count": str(count),
                "_sort": "-date"
            }

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Observation", params=params)
                r.raise_for_status()
                bundle = r.json()

                labs = []
                for entry in bundle.get("entry", []):
                    obs = entry.get("resource", {})
                    code = obs.get("code", {}).get("coding", [{}])[0].get("code", "")
                    display = obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                    value = obs.get("valueQuantity", {}).get("value")
                    unit = obs.get("valueQuantity", {}).get("unit", "")

                    # Get interpretation
                    lab_name = LOINC_TO_LAB.get(code, display)
                    interpretation = self._interpret_lab(lab_name, value)

                    labs.append({
                        "id": obs.get("id"),
                        "loinc_code": code,
                        "name": lab_name,
                        "display": display,
                        "value": value,
                        "unit": unit,
                        "datetime": obs.get("effectiveDateTime"),
                        "status": obs.get("status"),
                        "interpretation": interpretation,
                        "reference_range": REFERENCE_RANGES.get(lab_name)
                    })

                return {"patient_id": patient_id, "count": len(labs), "labs": labs}

        @self.register_tool(
            name="get_critical_labs",
            description="Get only critical/abnormal lab values requiring immediate attention",
            input_schema={
                "patient_id": "string",
                "hours": "integer - look back period (default 24)"
            },
            output_schema={"critical_labs": "list of critical lab results"},
            category="alerts"
        )
        async def get_critical_labs(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id

            params = {
                "subject:Patient": patient_id,
                "category": "laboratory",
                "_count": "100",
                "_sort": "-date"
            }

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Observation", params=params)
                r.raise_for_status()
                bundle = r.json()

                critical_labs = []
                for entry in bundle.get("entry", []):
                    obs = entry.get("resource", {})
                    code = obs.get("code", {}).get("coding", [{}])[0].get("code", "")
                    display = obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                    value = obs.get("valueQuantity", {}).get("value")

                    lab_name = LOINC_TO_LAB.get(code, display)
                    interpretation = self._interpret_lab(lab_name, value)

                    if interpretation and interpretation.get("severity") in ["critical", "high", "low"]:
                        critical_labs.append({
                            "loinc_code": code,
                            "name": lab_name,
                            "value": value,
                            "unit": obs.get("valueQuantity", {}).get("unit", ""),
                            "datetime": obs.get("effectiveDateTime"),
                            "interpretation": interpretation,
                            "reference_range": REFERENCE_RANGES.get(lab_name),
                            "clinical_significance": self._get_clinical_significance(lab_name, interpretation)
                        })

                return {
                    "patient_id": patient_id,
                    "count": len(critical_labs),
                    "critical_labs": critical_labs,
                    "requires_immediate_action": any(
                        l["interpretation"]["severity"] == "critical" for l in critical_labs
                    )
                }

        @self.register_tool(
            name="get_lab_trends",
            description="Analyze trends in lab values over time",
            input_schema={
                "patient_id": "string",
                "lab_name": "string - e.g., Creatinine, Glucose, HbA1c",
                "days": "integer - look back period (default 90)"
            },
            output_schema={"trend": "trend analysis with direction and values"},
            category="analytics"
        )
        async def get_lab_trends(request: MCPRequest):
            patient_id = request.arguments.get("patient_id") or request.patient_id
            lab_name = request.arguments.get("lab_name")
            days = request.arguments.get("days", 90)

            # Find LOINC code for lab name
            loinc_code = None
            for code, name in LOINC_TO_LAB.items():
                if name.lower() == lab_name.lower():
                    loinc_code = code
                    break

            if not loinc_code:
                return {"error": f"Unknown lab: {lab_name}", "available_labs": list(set(LOINC_TO_LAB.values()))}

            params = {
                "subject:Patient": patient_id,
                "code": loinc_code,
                "_count": "100",
                "_sort": "date"
            }

            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{FHIR_BASE}/Observation", params=params)
                r.raise_for_status()
                bundle = r.json()

                values = []
                for entry in bundle.get("entry", []):
                    obs = entry.get("resource", {})
                    value = obs.get("valueQuantity", {}).get("value")
                    if value is not None:
                        values.append({
                            "value": value,
                            "datetime": obs.get("effectiveDateTime")
                        })

                if len(values) < 2:
                    return {
                        "lab_name": lab_name,
                        "trend": "insufficient_data",
                        "data_points": len(values)
                    }

                # Calculate trend
                first_val = values[0]["value"]
                last_val = values[-1]["value"]
                change = last_val - first_val
                pct_change = (change / first_val * 100) if first_val else 0

                if pct_change > 10:
                    trend = "increasing"
                elif pct_change < -10:
                    trend = "decreasing"
                else:
                    trend = "stable"

                ref = REFERENCE_RANGES.get(lab_name, {})

                return {
                    "patient_id": patient_id,
                    "lab_name": lab_name,
                    "trend": trend,
                    "first_value": first_val,
                    "last_value": last_val,
                    "change": round(change, 2),
                    "percent_change": round(pct_change, 1),
                    "data_points": len(values),
                    "values": values,
                    "reference_range": ref,
                    "clinical_interpretation": self._interpret_trend(lab_name, trend, last_val, ref)
                }

        @self.register_tool(
            name="calculate_egfr",
            description="Calculate estimated GFR from creatinine (kidney function)",
            input_schema={
                "patient_id": "string",
                "creatinine": "float (optional - will fetch latest if not provided)",
                "age": "integer",
                "sex": "male|female",
                "race": "black|other (optional)"
            },
            output_schema={"egfr": "eGFR value with CKD stage"},
            category="calculated"
        )
        async def calculate_egfr(request: MCPRequest):
            creatinine = request.arguments.get("creatinine")
            age = request.arguments.get("age")
            sex = request.arguments.get("sex", "").lower()
            race = request.arguments.get("race", "other").lower()

            if not creatinine:
                # Fetch latest creatinine
                patient_id = request.arguments.get("patient_id") or request.patient_id
                params = {
                    "subject:Patient": patient_id,
                    "code": "2160-0",  # Creatinine LOINC
                    "_count": "1",
                    "_sort": "-date"
                }
                async with httpx.AsyncClient(timeout=30) as client:
                    r = await client.get(f"{FHIR_BASE}/Observation", params=params)
                    r.raise_for_status()
                    bundle = r.json()
                    entries = bundle.get("entry", [])
                    if entries:
                        creatinine = entries[0].get("resource", {}).get("valueQuantity", {}).get("value")

            if not creatinine or not age:
                return {"error": "Creatinine and age required for eGFR calculation"}

            # CKD-EPI equation (2021)
            if sex == "female":
                if creatinine <= 0.7:
                    egfr = 142 * (creatinine / 0.7) ** -0.241 * (0.9938 ** age) * 1.012
                else:
                    egfr = 142 * (creatinine / 0.7) ** -1.200 * (0.9938 ** age) * 1.012
            else:
                if creatinine <= 0.9:
                    egfr = 142 * (creatinine / 0.9) ** -0.302 * (0.9938 ** age)
                else:
                    egfr = 142 * (creatinine / 0.9) ** -1.200 * (0.9938 ** age)

            # Determine CKD stage
            if egfr >= 90:
                stage = "G1 - Normal or high"
            elif egfr >= 60:
                stage = "G2 - Mildly decreased"
            elif egfr >= 45:
                stage = "G3a - Mildly to moderately decreased"
            elif egfr >= 30:
                stage = "G3b - Moderately to severely decreased"
            elif egfr >= 15:
                stage = "G4 - Severely decreased"
            else:
                stage = "G5 - Kidney failure"

            return {
                "creatinine": creatinine,
                "age": age,
                "sex": sex,
                "egfr": round(egfr, 1),
                "unit": "mL/min/1.73m²",
                "ckd_stage": stage,
                "interpretation": self._interpret_egfr(egfr)
            }

    def _interpret_lab(self, lab_name: str, value: float) -> Optional[dict]:
        """Interpret lab value against reference ranges"""
        if value is None or lab_name not in REFERENCE_RANGES:
            return None

        ref = REFERENCE_RANGES[lab_name]
        result = {"value": value, "reference": ref}

        # Check critical values first
        if ref.get("critical_low") and value < ref["critical_low"]:
            result["severity"] = "critical"
            result["flag"] = "critically_low"
            result["message"] = f"{lab_name} critically low at {value} {ref['unit']}"
        elif ref.get("critical_high") and value > ref["critical_high"]:
            result["severity"] = "critical"
            result["flag"] = "critically_high"
            result["message"] = f"{lab_name} critically high at {value} {ref['unit']}"
        elif ref.get("low") and value < ref["low"]:
            result["severity"] = "low"
            result["flag"] = "low"
            result["message"] = f"{lab_name} below normal at {value} {ref['unit']}"
        elif ref.get("high") and value > ref["high"]:
            result["severity"] = "high"
            result["flag"] = "high"
            result["message"] = f"{lab_name} above normal at {value} {ref['unit']}"
        else:
            result["severity"] = "normal"
            result["flag"] = "normal"
            result["message"] = f"{lab_name} within normal range"

        return result

    def _get_clinical_significance(self, lab_name: str, interpretation: dict) -> str:
        """Get clinical significance of abnormal lab"""
        significance = {
            "Glucose": {
                "critically_low": "Hypoglycemia - risk of seizures, loss of consciousness",
                "critically_high": "Hyperglycemia - risk of DKA or HHS",
                "high": "Elevated glucose - evaluate for diabetes"
            },
            "Potassium": {
                "critically_low": "Severe hypokalemia - cardiac arrhythmia risk",
                "critically_high": "Severe hyperkalemia - cardiac arrest risk",
            },
            "Troponin": {
                "critically_high": "Elevated troponin - evaluate for acute MI",
                "high": "Mild troponin elevation - rule out cardiac injury"
            },
            "Creatinine": {
                "high": "Elevated creatinine - evaluate kidney function",
                "critically_high": "Acute kidney injury or chronic kidney disease"
            },
            "Hemoglobin": {
                "critically_low": "Severe anemia - may require transfusion",
                "low": "Anemia - evaluate underlying cause"
            }
        }

        flag = interpretation.get("flag", "normal")
        return significance.get(lab_name, {}).get(flag, "Requires clinical correlation")

    def _interpret_trend(self, lab_name: str, trend: str, current: float, ref: dict) -> str:
        """Interpret lab trend clinically"""
        if not ref:
            return "Trend analysis complete"

        if trend == "increasing":
            if ref.get("high") and current > ref["high"]:
                return f"{lab_name} increasing and now above normal - clinical review recommended"
            return f"{lab_name} trending upward - monitor for continued increase"
        elif trend == "decreasing":
            if ref.get("low") and current < ref["low"]:
                return f"{lab_name} decreasing and now below normal - clinical review recommended"
            return f"{lab_name} trending downward - monitor for continued decrease"
        else:
            return f"{lab_name} stable within expected variation"

    def _interpret_egfr(self, egfr: float) -> str:
        """Interpret eGFR clinically"""
        if egfr >= 90:
            return "Normal kidney function"
        elif egfr >= 60:
            return "Mild reduction in kidney function - monitor annually"
        elif egfr >= 30:
            return "Moderate reduction - nephrology referral recommended"
        elif egfr >= 15:
            return "Severe reduction - prepare for renal replacement therapy"
        else:
            return "Kidney failure - dialysis or transplant evaluation needed"


# Create server instance
server = MCPLabsServer()
app = server.app

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8006")))
