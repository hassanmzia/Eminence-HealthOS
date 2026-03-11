"""
Lab Results Analyzer Agent — Tier 2 (Diagnostic).

Analyzes incoming lab results, identifies abnormalities, trends,
and correlations with other clinical data.
"""

import logging
from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.lab_analyzer")

# Common lab reference ranges
LAB_RANGES = {
    "2345-7": {"name": "Glucose", "unit": "mg/dL", "low": 70, "high": 100, "critical_low": 50, "critical_high": 400},
    "2160-0": {"name": "Creatinine", "unit": "mg/dL", "low": 0.6, "high": 1.2, "critical_low": 0.3, "critical_high": 10.0},
    "3094-0": {"name": "BUN", "unit": "mg/dL", "low": 7, "high": 20, "critical_low": 2, "critical_high": 100},
    "2951-2": {"name": "Sodium", "unit": "mEq/L", "low": 136, "high": 145, "critical_low": 120, "critical_high": 160},
    "2823-3": {"name": "Potassium", "unit": "mEq/L", "low": 3.5, "high": 5.0, "critical_low": 2.5, "critical_high": 6.5},
    "4548-4": {"name": "HbA1c", "unit": "%", "low": 4.0, "high": 5.7, "critical_low": 3.0, "critical_high": 14.0},
    "718-7": {"name": "Hemoglobin", "unit": "g/dL", "low": 12.0, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0},
    "787-2": {"name": "MCV", "unit": "fL", "low": 80, "high": 100, "critical_low": 60, "critical_high": 120},
    "6690-2": {"name": "WBC", "unit": "10*3/uL", "low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0},
    "777-3": {"name": "Platelets", "unit": "10*3/uL", "low": 150, "high": 400, "critical_low": 50, "critical_high": 1000},
    "2093-3": {"name": "Total Cholesterol", "unit": "mg/dL", "low": 0, "high": 200, "critical_low": 0, "critical_high": 400},
    "13457-7": {"name": "LDL Cholesterol", "unit": "mg/dL", "low": 0, "high": 100, "critical_low": 0, "critical_high": 300},
    "2085-9": {"name": "HDL Cholesterol", "unit": "mg/dL", "low": 40, "high": 200, "critical_low": 20, "critical_high": 200},
}


class LabAnalyzerAgent(HealthOSAgent):
    """Analyzes lab results and identifies clinical significance."""

    def __init__(self):
        super().__init__(
            name="lab_analyzer",
            tier=AgentTier.DIAGNOSTIC,
            description="Analyzes lab results for abnormalities and clinical patterns",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.LAB_ANALYSIS, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        loinc_code = data.get("loinc_code", "")
        value = data.get("value_quantity")

        if value is None or loinc_code not in LAB_RANGES:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="unsupported_lab",
                rationale=f"Lab code {loinc_code} not in analysis registry",
                confidence=0.5,
            )

        ref = LAB_RANGES[loinc_code]
        assessment = self._analyze_result(value, ref)

        # Check for clinical patterns from prior agent outputs
        prior_outputs = agent_input.context.get("prior_outputs", [])
        pattern_notes = self._check_patterns(loinc_code, value, prior_outputs)
        if pattern_notes:
            assessment["rationale"] += f" {pattern_notes}"

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=assessment["decision"],
            rationale=assessment["rationale"],
            confidence=assessment["confidence"],
            data={
                "loinc_code": loinc_code,
                "lab_name": ref["name"],
                "value": value,
                "unit": ref["unit"],
                "severity": assessment["severity"],
                "clinical_significance": assessment["significance"],
            },
            feature_contributions=[
                {"feature": "lab_value", "contribution": 0.5, "value": value},
                {"feature": "reference_range", "contribution": 0.3, "value": f"{ref['low']}-{ref['high']}"},
                {"feature": "clinical_context", "contribution": 0.2, "value": "prior_results"},
            ],
            requires_hitl=assessment["severity"] == "CRITICAL",
            risk_level=assessment["severity"].lower(),
        )

    def _analyze_result(self, value: float, ref: dict) -> dict:
        name = ref["name"]

        if value <= ref["critical_low"] or value >= ref["critical_high"]:
            direction = "low" if value <= ref["critical_low"] else "high"
            return {
                "decision": "critical_lab",
                "rationale": f"{name} critically {direction} at {value} {ref['unit']}",
                "severity": "CRITICAL",
                "significance": "immediate_attention",
                "confidence": 0.95,
            }
        elif value < ref["low"] or value > ref["high"]:
            direction = "low" if value < ref["low"] else "high"
            return {
                "decision": "abnormal_lab",
                "rationale": f"{name} {direction} at {value} {ref['unit']} (range: {ref['low']}-{ref['high']})",
                "severity": "MEDIUM",
                "significance": "review_needed",
                "confidence": 0.85,
            }
        else:
            return {
                "decision": "normal_lab",
                "rationale": f"{name} within normal limits at {value} {ref['unit']}",
                "severity": "LOW",
                "significance": "normal",
                "confidence": 0.95,
            }

    def _check_patterns(self, loinc_code: str, value: float, prior_outputs: list) -> str:
        """Check for clinical patterns combining lab + vital data."""
        # Example: high glucose + elevated HbA1c pattern
        if loinc_code == "2345-7" and value > 126:
            return "Fasting glucose elevated — consider HbA1c correlation and diabetes screening."
        if loinc_code == "4548-4" and value > 6.5:
            return "HbA1c in diabetic range — recommend comprehensive metabolic panel."
        if loinc_code == "2823-3" and (value < 3.0 or value > 6.0):
            return "Potassium abnormality — correlate with EKG and renal function."
        return ""
