"""
Risk Scoring Agent — Tier 3 (Risk).

Computes composite risk scores for patients based on vitals, labs,
medications, conditions, and demographic factors. Supports multiple
scoring models (NEWS2, MEWS, custom ML ensemble).
"""

import logging
from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.risk_scorer")

# NEWS2 scoring parameters
NEWS2_PARAMS = {
    "9279-1": {  # Respiratory Rate
        "scores": [(8, 3), (9, 1), (12, 0), (20, 0), (24, 2), (25, 3)],
    },
    "2708-6": {  # SpO2
        "scores": [(91, 3), (93, 2), (95, 1), (96, 0)],
    },
    "8310-5": {  # Temperature
        "scores": [(35.0, 3), (36.0, 1), (36.1, 0), (38.0, 0), (39.0, 1), (39.1, 2)],
    },
    "8480-6": {  # Systolic BP
        "scores": [(90, 3), (100, 2), (110, 1), (111, 0), (219, 0), (220, 3)],
    },
    "8867-4": {  # Heart Rate
        "scores": [(40, 3), (41, 1), (51, 0), (90, 0), (110, 1), (130, 2), (131, 3)],
    },
}


class RiskScorerAgent(HealthOSAgent):
    """Computes composite patient risk scores from available data."""

    def __init__(self):
        super().__init__(
            name="risk_scorer",
            tier=AgentTier.RISK,
            description="Computes patient risk scores using clinical scoring models",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.RISK_SCORING]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        vitals = data.get("vitals", {})
        prior_outputs = agent_input.context.get("prior_outputs", [])

        # Collect vitals from data or prior agent outputs
        vital_values = {}
        for output in prior_outputs:
            if isinstance(output, dict) and output.get("agent") == "vital_monitor":
                out_data = output.get("data", {})
                if "loinc_code" in out_data and "value" in out_data:
                    vital_values[out_data["loinc_code"]] = out_data["value"]

        # Also accept direct vital input
        for loinc, info in vitals.items():
            if isinstance(info, dict):
                vital_values[loinc] = info.get("value", info.get("value_quantity"))
            else:
                vital_values[loinc] = info

        # Compute NEWS2 score
        news2_score, news2_details = self._compute_news2(vital_values)

        # Determine risk level
        if news2_score >= 7:
            risk_level = "CRITICAL"
            decision = "high_risk_patient"
            rationale = f"NEWS2 score {news2_score} (≥7) — immediate clinical review required"
        elif news2_score >= 5:
            risk_level = "HIGH"
            decision = "elevated_risk"
            rationale = f"NEWS2 score {news2_score} (5-6) — urgent response needed"
        elif news2_score >= 3:
            risk_level = "MEDIUM"
            decision = "moderate_risk"
            rationale = f"NEWS2 score {news2_score} (3-4) — increased monitoring recommended"
        else:
            risk_level = "LOW"
            decision = "low_risk"
            rationale = f"NEWS2 score {news2_score} (0-2) — routine monitoring"

        feature_contribs = [
            {"feature": f"vital_{loinc}", "contribution": detail["contribution"], "value": detail["value"], "score": detail["score"]}
            for loinc, detail in news2_details.items()
        ]

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=decision,
            rationale=rationale,
            confidence=min(0.95, 0.6 + len(vital_values) * 0.07),
            data={
                "news2_score": news2_score,
                "risk_level": risk_level,
                "component_scores": news2_details,
                "vitals_available": len(vital_values),
            },
            feature_contributions=feature_contribs,
            requires_hitl=news2_score >= 7,
            risk_level=risk_level.lower(),
            downstream_agents=["care_plan_generator"] if news2_score >= 5 else [],
        )

    def _compute_news2(self, vitals: dict) -> tuple[int, dict]:
        """Compute NEWS2 (National Early Warning Score 2)."""
        total = 0
        details = {}

        for loinc, params in NEWS2_PARAMS.items():
            value = vitals.get(loinc)
            if value is None:
                continue

            score = self._score_value(value, params["scores"])
            contribution = score / max(total + score, 1)
            details[loinc] = {
                "value": value,
                "score": score,
                "contribution": round(contribution, 3),
            }
            total += score

        return total, details

    def _score_value(self, value: float, thresholds: list[tuple]) -> int:
        """Score a value against NEWS2 thresholds."""
        last_score = 0
        for threshold, score in thresholds:
            if value <= threshold:
                return score
            last_score = score
        return last_score
