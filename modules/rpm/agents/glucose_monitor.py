"""
Glucose Monitor Agent — Tier 1 (Monitoring).

Specialized agent for continuous glucose monitoring with diabetes-specific
logic, trend analysis, and time-in-range calculations.
"""

import logging
from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.glucose_monitor")

# ADA glucose targets
GLUCOSE_TARGETS = {
    "fasting": {"low": 80, "high": 130, "critical_low": 54, "critical_high": 250},
    "postprandial": {"low": 80, "high": 180, "critical_low": 54, "critical_high": 300},
    "general": {"low": 70, "high": 180, "critical_low": 54, "critical_high": 300},
}


class GlucoseMonitorAgent(HealthOSAgent):
    """Specialized glucose monitoring with diabetes management logic."""

    def __init__(self):
        super().__init__(
            name="glucose_monitor",
            tier=AgentTier.MONITORING,
            description="Monitors glucose levels with diabetes-specific thresholds and trend analysis",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.VITAL_MONITORING, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        glucose = data.get("value_quantity") or data.get("glucose")
        context_type = data.get("glucose_context", "general")  # fasting, postprandial, general
        history = data.get("glucose_history", [])

        if glucose is None:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_data",
                rationale="No glucose value provided",
                confidence=1.0,
            )

        targets = GLUCOSE_TARGETS.get(context_type, GLUCOSE_TARGETS["general"])
        assessment = self._assess_glucose(glucose, targets, context_type)

        # Trend analysis if history available
        trend = self._analyze_trend(glucose, history)
        if trend["trend"] != "stable":
            assessment["rationale"] += f" Trend: {trend['description']}"

        # Time in range calculation
        tir = self._time_in_range(history + [glucose]) if history else None

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=assessment["decision"],
            rationale=assessment["rationale"],
            confidence=assessment["confidence"],
            data={
                "glucose": glucose,
                "context": context_type,
                "severity": assessment["severity"],
                "trend": trend,
                "time_in_range": tir,
                "targets": targets,
            },
            feature_contributions=[
                {"feature": "glucose_value", "contribution": 0.5, "value": glucose},
                {"feature": "trend", "contribution": 0.3, "value": trend["trend"]},
                {"feature": "context", "contribution": 0.2, "value": context_type},
            ],
            requires_hitl=assessment["severity"] in ("CRITICAL", "EMERGENCY"),
            safety_flags=["hypoglycemia"] if glucose < targets["critical_low"] else
                        ["severe_hyperglycemia"] if glucose > targets["critical_high"] else [],
            risk_level=assessment["severity"].lower(),
            downstream_agents=["risk_scorer"] if assessment["severity"] != "LOW" else [],
        )

    def _assess_glucose(self, glucose: float, targets: dict, context: str) -> dict:
        if glucose < targets["critical_low"]:
            return {
                "decision": "critical_hypoglycemia",
                "rationale": f"CRITICAL: Glucose {glucose} mg/dL — severe hypoglycemia (<{targets['critical_low']}). Immediate intervention required.",
                "severity": "EMERGENCY",
                "confidence": 0.98,
            }
        elif glucose > targets["critical_high"]:
            return {
                "decision": "critical_hyperglycemia",
                "rationale": f"CRITICAL: Glucose {glucose} mg/dL — severe hyperglycemia (>{targets['critical_high']}). Assess for DKA/HHS.",
                "severity": "CRITICAL",
                "confidence": 0.95,
            }
        elif glucose < targets["low"]:
            return {
                "decision": "hypoglycemia",
                "rationale": f"Glucose {glucose} mg/dL below target range ({targets['low']}-{targets['high']}) for {context} reading.",
                "severity": "HIGH",
                "confidence": 0.90,
            }
        elif glucose > targets["high"]:
            return {
                "decision": "hyperglycemia",
                "rationale": f"Glucose {glucose} mg/dL above target range ({targets['low']}-{targets['high']}) for {context} reading.",
                "severity": "MEDIUM",
                "confidence": 0.85,
            }
        else:
            return {
                "decision": "in_range",
                "rationale": f"Glucose {glucose} mg/dL within target range ({targets['low']}-{targets['high']}).",
                "severity": "LOW",
                "confidence": 0.95,
            }

    def _analyze_trend(self, current: float, history: list) -> dict:
        if len(history) < 2:
            return {"trend": "stable", "description": "Insufficient history for trend", "rate": 0}

        recent = history[-3:]
        avg_recent = sum(recent) / len(recent)
        rate = (current - avg_recent) / max(len(recent), 1)

        if rate > 15:
            return {"trend": "rising_fast", "description": f"Rapidly rising ({rate:.0f} mg/dL/reading)", "rate": rate}
        elif rate > 5:
            return {"trend": "rising", "description": f"Rising trend ({rate:.0f} mg/dL/reading)", "rate": rate}
        elif rate < -15:
            return {"trend": "falling_fast", "description": f"Rapidly falling ({rate:.0f} mg/dL/reading)", "rate": rate}
        elif rate < -5:
            return {"trend": "falling", "description": f"Falling trend ({rate:.0f} mg/dL/reading)", "rate": rate}
        else:
            return {"trend": "stable", "description": "Stable readings", "rate": rate}

    def _time_in_range(self, values: list) -> dict:
        if not values:
            return {"tir_percent": 0, "below_range": 0, "above_range": 0}

        in_range = sum(1 for v in values if 70 <= v <= 180)
        below = sum(1 for v in values if v < 70)
        above = sum(1 for v in values if v > 180)
        total = len(values)

        return {
            "tir_percent": round(in_range / total * 100, 1),
            "below_range_percent": round(below / total * 100, 1),
            "above_range_percent": round(above / total * 100, 1),
            "readings_count": total,
        }
