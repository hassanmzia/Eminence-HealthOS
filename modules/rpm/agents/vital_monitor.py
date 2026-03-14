"""
Vital Signs Monitor Agent — Tier 1 (Monitoring).

Continuously monitors incoming vital signs against patient-specific
thresholds and clinical guidelines. Generates alerts for abnormal values.
"""

import logging
from typing import Optional

from healthos_platform.ml.llm.router import llm_router, LLMRequest

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.vital_monitor")

# Standard vital sign reference ranges (adult defaults)
VITAL_RANGES = {
    "8480-6": {"name": "Systolic BP", "unit": "mmHg", "low": 90, "high": 140, "critical_low": 70, "critical_high": 180},
    "8462-4": {"name": "Diastolic BP", "unit": "mmHg", "low": 60, "high": 90, "critical_low": 40, "critical_high": 120},
    "8867-4": {"name": "Heart Rate", "unit": "bpm", "low": 60, "high": 100, "critical_low": 40, "critical_high": 150},
    "9279-1": {"name": "Respiratory Rate", "unit": "/min", "low": 12, "high": 20, "critical_low": 8, "critical_high": 30},
    "8310-5": {"name": "Body Temperature", "unit": "°C", "low": 36.1, "high": 37.5, "critical_low": 35.0, "critical_high": 39.5},
    "2708-6": {"name": "SpO2", "unit": "%", "low": 95, "high": 100, "critical_low": 90, "critical_high": 100},
    "39156-5": {"name": "BMI", "unit": "kg/m2", "low": 18.5, "high": 25.0, "critical_low": 15.0, "critical_high": 40.0},
    "29463-7": {"name": "Body Weight", "unit": "kg", "low": 40, "high": 150, "critical_low": 30, "critical_high": 200},
    "55284-4": {"name": "Blood Pressure Panel", "unit": "mmHg", "low": 90, "high": 140, "critical_low": 70, "critical_high": 180},
}


class VitalMonitorAgent(HealthOSAgent):
    """Monitors vital signs and generates alerts for abnormal readings."""

    def __init__(self):
        super().__init__(
            name="vital_monitor",
            tier=AgentTier.MONITORING,
            description="Monitors incoming vital signs against thresholds and generates alerts",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.VITAL_MONITORING, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        loinc_code = data.get("loinc_code", "")
        value = data.get("value_quantity")
        unit = data.get("value_unit", "")

        if value is None or loinc_code not in VITAL_RANGES:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_action",
                rationale="Unsupported or missing vital sign data",
                confidence=1.0,
            )

        ref = VITAL_RANGES[loinc_code]
        assessment = self._assess_vital(value, ref)

        # LLM enhancement: generate monitoring narrative summarizing vital status
        monitoring_narrative = ""
        try:
            prompt = (
                f"Summarize this patient's current vital sign status:\n\n"
                f"Vital: {ref['name']}\n"
                f"Value: {value} {unit or ref['unit']}\n"
                f"Reference range: {ref['low']}-{ref['high']} {ref['unit']}\n"
                f"Interpretation: {assessment['interpretation']} "
                f"(severity: {assessment['severity']})\n"
                f"Assessment: {assessment['rationale']}\n\n"
                f"Provide a concise clinical summary of the patient's current vital "
                f"status and any monitoring recommendations in 2-3 sentences."
            )
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system="You are a clinical monitoring system. Provide concise, "
                       "evidence-based summaries of vital sign readings. Include "
                       "clinical context and monitoring recommendations when appropriate.",
                temperature=0.3,
                max_tokens=1024,
            ))
            monitoring_narrative = llm_response.content
        except Exception as e:
            logger.warning("LLM call failed for monitoring narrative, using rule-based only: %s", e)

        feature_contributions = [
            {"feature": "value", "contribution": 0.6, "value": value},
            {"feature": "reference_range", "contribution": 0.3, "value": f"{ref['low']}-{ref['high']}"},
            {"feature": "loinc_code", "contribution": 0.1, "value": loinc_code},
        ]

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=assessment["decision"],
            rationale=assessment["rationale"],
            confidence=assessment["confidence"],
            data={
                "loinc_code": loinc_code,
                "vital_name": ref["name"],
                "value": value,
                "unit": unit or ref["unit"],
                "severity": assessment["severity"],
                "interpretation": assessment["interpretation"],
                "reference_range": {"low": ref["low"], "high": ref["high"]},
                "monitoring_narrative": monitoring_narrative,
            },
            feature_contributions=feature_contributions,
            requires_hitl=assessment["severity"] in ("CRITICAL", "EMERGENCY"),
            safety_flags=[f"critical_{ref['name'].lower().replace(' ', '_')}"]
            if assessment["severity"] in ("CRITICAL", "EMERGENCY")
            else [],
            risk_level=assessment["severity"].lower(),
            downstream_agents=assessment.get("downstream", []),
        )

    def _assess_vital(self, value: float, ref: dict) -> dict:
        name = ref["name"]

        if value <= ref["critical_low"]:
            return {
                "decision": "critical_alert",
                "rationale": f"{name} critically low at {value} {ref['unit']} (critical threshold: {ref['critical_low']})",
                "severity": "CRITICAL",
                "interpretation": "LL",
                "confidence": 0.95,
                "downstream": ["risk_scoring", "alert_generation"],
            }
        elif value >= ref["critical_high"]:
            return {
                "decision": "critical_alert",
                "rationale": f"{name} critically high at {value} {ref['unit']} (critical threshold: {ref['critical_high']})",
                "severity": "CRITICAL",
                "interpretation": "HH",
                "confidence": 0.95,
                "downstream": ["risk_scoring", "alert_generation"],
            }
        elif value < ref["low"]:
            return {
                "decision": "abnormal_alert",
                "rationale": f"{name} below normal at {value} {ref['unit']} (normal range: {ref['low']}-{ref['high']})",
                "severity": "MEDIUM",
                "interpretation": "L",
                "confidence": 0.85,
                "downstream": ["risk_scoring"],
            }
        elif value > ref["high"]:
            return {
                "decision": "abnormal_alert",
                "rationale": f"{name} above normal at {value} {ref['unit']} (normal range: {ref['low']}-{ref['high']})",
                "severity": "MEDIUM",
                "interpretation": "H",
                "confidence": 0.85,
                "downstream": ["risk_scoring"],
            }
        else:
            return {
                "decision": "normal",
                "rationale": f"{name} within normal range at {value} {ref['unit']}",
                "severity": "LOW",
                "interpretation": "N",
                "confidence": 0.95,
            }
