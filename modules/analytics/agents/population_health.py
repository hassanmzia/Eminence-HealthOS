"""
Population Health Agent — population-level analytics and insights.

Analyzes patient cohorts for risk stratification, outcome tracking,
quality metrics, and population health trends.
"""

import logging
from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.population_health")


class PopulationHealthAgent(HealthOSAgent):
    """Generates population health analytics and insights."""

    def __init__(self):
        super().__init__(
            name="population_health",
            tier=AgentTier.DIAGNOSTIC,
            description="Population-level analytics, risk stratification, and quality metrics",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.RISK_SCORING, AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        analysis_type = data.get("analysis_type", "overview")

        if analysis_type == "risk_stratification":
            result = self._risk_stratification(data)
        elif analysis_type == "quality_metrics":
            result = self._quality_metrics(data)
        elif analysis_type == "cohort_analysis":
            result = self._cohort_analysis(data)
        else:
            result = self._overview(data)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=f"analysis_{analysis_type}",
            rationale=f"Population health analysis ({analysis_type}) completed",
            confidence=0.80,
            data=result,
            feature_contributions=[
                {"feature": "population_size", "contribution": 0.3, "value": data.get("total_patients", 0)},
                {"feature": "analysis_type", "contribution": 0.3, "value": analysis_type},
                {"feature": "data_completeness", "contribution": 0.4, "value": "evaluated"},
            ],
        )

    def _overview(self, data: dict) -> dict:
        patients = data.get("patients", [])
        total = len(patients) or data.get("total_patients", 0)

        return {
            "analysis_type": "overview",
            "total_patients": total,
            "metrics": {
                "avg_risk_score": self._safe_avg([p.get("risk_score", 0) for p in patients]),
                "high_risk_percent": self._pct([p for p in patients if p.get("risk_level") in ("HIGH", "CRITICAL")], total),
                "with_active_alerts": self._pct([p for p in patients if p.get("active_alerts", 0) > 0], total),
            },
        }

    def _risk_stratification(self, data: dict) -> dict:
        patients = data.get("patients", [])
        tiers = {"LOW": [], "MEDIUM": [], "HIGH": [], "CRITICAL": []}

        for p in patients:
            level = p.get("risk_level", "LOW")
            tiers.setdefault(level, []).append(p)

        return {
            "analysis_type": "risk_stratification",
            "tiers": {k: len(v) for k, v in tiers.items()},
            "recommendations": [
                {"tier": "CRITICAL", "action": "Daily monitoring, weekly provider review"},
                {"tier": "HIGH", "action": "Twice-weekly monitoring, bi-weekly review"},
                {"tier": "MEDIUM", "action": "Weekly monitoring, monthly review"},
                {"tier": "LOW", "action": "Monthly check-in, quarterly review"},
            ],
        }

    def _quality_metrics(self, data: dict) -> dict:
        return {
            "analysis_type": "quality_metrics",
            "hedis_measures": {
                "bp_control": data.get("bp_control_rate", 0),
                "diabetes_hba1c": data.get("hba1c_control_rate", 0),
                "preventive_screenings": data.get("screening_rate", 0),
                "medication_adherence": data.get("adherence_rate", 0),
            },
            "operational": {
                "avg_response_time_min": data.get("avg_response_time", 0),
                "readmission_rate": data.get("readmission_rate", 0),
                "patient_satisfaction": data.get("satisfaction_score", 0),
            },
        }

    def _cohort_analysis(self, data: dict) -> dict:
        return {
            "analysis_type": "cohort_analysis",
            "cohort_criteria": data.get("criteria", {}),
            "matched_patients": data.get("matched_count", 0),
        }

    def _safe_avg(self, values: list) -> float:
        valid = [v for v in values if v is not None]
        return round(sum(valid) / len(valid), 2) if valid else 0

    def _pct(self, subset: list, total: int) -> float:
        return round(len(subset) / max(total, 1) * 100, 1)
