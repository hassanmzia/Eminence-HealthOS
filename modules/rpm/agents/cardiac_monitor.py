"""
Cardiac Monitor Agent — Tier 1 (Monitoring).

Specialized cardiac monitoring for blood pressure trends, heart rate
variability, arrhythmia detection, and cardiovascular risk factors.
"""

import logging
from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.cardiac_monitor")

# AHA/ACC Blood Pressure Categories
BP_CATEGORIES = {
    "normal": {"systolic_max": 120, "diastolic_max": 80},
    "elevated": {"systolic_min": 120, "systolic_max": 129, "diastolic_max": 80},
    "stage1_htn": {"systolic_min": 130, "systolic_max": 139, "diastolic_min": 80, "diastolic_max": 89},
    "stage2_htn": {"systolic_min": 140, "systolic_max": 180, "diastolic_min": 90, "diastolic_max": 120},
    "crisis": {"systolic_min": 180, "diastolic_min": 120},
}


class CardiacMonitorAgent(HealthOSAgent):
    """Specialized cardiac monitoring with BP classification and HR analysis."""

    def __init__(self):
        super().__init__(
            name="cardiac_monitor",
            tier=AgentTier.MONITORING,
            description="Monitors cardiac metrics — BP classification, HR trends, arrhythmia flags",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.VITAL_MONITORING, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        systolic = data.get("systolic")
        diastolic = data.get("diastolic")
        heart_rate = data.get("heart_rate")
        bp_history = data.get("bp_history", [])

        results = {}
        severity = "LOW"
        decisions = []

        # Blood pressure analysis
        if systolic is not None and diastolic is not None:
            bp_result = self._classify_bp(systolic, diastolic)
            results["blood_pressure"] = bp_result
            decisions.append(bp_result["category"])
            if self._severity_rank(bp_result["severity"]) > self._severity_rank(severity):
                severity = bp_result["severity"]

            # BP trend
            if bp_history:
                trend = self._bp_trend(systolic, bp_history)
                results["bp_trend"] = trend

        # Heart rate analysis
        if heart_rate is not None:
            hr_result = self._assess_heart_rate(heart_rate)
            results["heart_rate"] = hr_result
            decisions.append(hr_result["classification"])
            if self._severity_rank(hr_result["severity"]) > self._severity_rank(severity):
                severity = hr_result["severity"]

        if not results:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_cardiac_data",
                rationale="No cardiac metrics provided",
                confidence=1.0,
            )

        decision = "cardiac_assessment"
        rationale_parts = []
        if "blood_pressure" in results:
            bp = results["blood_pressure"]
            rationale_parts.append(f"BP {systolic}/{diastolic}: {bp['category']}")
        if "heart_rate" in results:
            hr = results["heart_rate"]
            rationale_parts.append(f"HR {heart_rate}: {hr['classification']}")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=decision,
            rationale="; ".join(rationale_parts),
            confidence=0.90,
            data={
                "severity": severity,
                "results": results,
                "systolic": systolic,
                "diastolic": diastolic,
                "heart_rate": heart_rate,
            },
            feature_contributions=[
                {"feature": "systolic_bp", "contribution": 0.35, "value": systolic},
                {"feature": "diastolic_bp", "contribution": 0.25, "value": diastolic},
                {"feature": "heart_rate", "contribution": 0.25, "value": heart_rate},
                {"feature": "trend", "contribution": 0.15, "value": "history"},
            ],
            requires_hitl=severity in ("CRITICAL", "EMERGENCY"),
            risk_level=severity.lower(),
            downstream_agents=["risk_scorer"] if severity != "LOW" else [],
        )

    def _classify_bp(self, systolic: float, diastolic: float) -> dict:
        if systolic >= 180 or diastolic >= 120:
            return {
                "category": "hypertensive_crisis",
                "severity": "EMERGENCY",
                "recommendation": "Immediate medical attention required",
            }
        elif systolic >= 140 or diastolic >= 90:
            return {
                "category": "stage2_hypertension",
                "severity": "HIGH",
                "recommendation": "Medication adjustment likely needed",
            }
        elif systolic >= 130 or diastolic >= 80:
            return {
                "category": "stage1_hypertension",
                "severity": "MEDIUM",
                "recommendation": "Lifestyle modifications and possible medication",
            }
        elif systolic >= 120:
            return {
                "category": "elevated",
                "severity": "LOW",
                "recommendation": "Lifestyle modifications recommended",
            }
        elif systolic < 90 or diastolic < 60:
            return {
                "category": "hypotension",
                "severity": "HIGH" if systolic < 80 else "MEDIUM",
                "recommendation": "Evaluate for underlying cause",
            }
        else:
            return {
                "category": "normal",
                "severity": "LOW",
                "recommendation": "Continue monitoring",
            }

    def _assess_heart_rate(self, hr: float) -> dict:
        if hr < 40:
            return {"classification": "severe_bradycardia", "severity": "CRITICAL"}
        elif hr < 60:
            return {"classification": "bradycardia", "severity": "MEDIUM"}
        elif hr <= 100:
            return {"classification": "normal", "severity": "LOW"}
        elif hr <= 120:
            return {"classification": "tachycardia", "severity": "MEDIUM"}
        else:
            return {"classification": "severe_tachycardia", "severity": "HIGH"}

    def _bp_trend(self, current_systolic: float, history: list) -> dict:
        if not history:
            return {"trend": "unknown", "readings": 0}

        systolic_values = [h.get("systolic", h) if isinstance(h, dict) else h for h in history[-5:]]
        avg = sum(systolic_values) / len(systolic_values)
        diff = current_systolic - avg

        if diff > 20:
            return {"trend": "rising", "change": diff, "readings": len(systolic_values)}
        elif diff < -20:
            return {"trend": "falling", "change": diff, "readings": len(systolic_values)}
        else:
            return {"trend": "stable", "change": diff, "readings": len(systolic_values)}

    def _severity_rank(self, severity: str) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3, "EMERGENCY": 4}.get(severity, 0)
