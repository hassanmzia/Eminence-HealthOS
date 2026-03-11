"""
Cost Analyzer Agent — healthcare cost analysis and optimization.

Analyzes care delivery costs, identifies cost reduction opportunities,
and tracks ROI for RPM programs and interventions.
"""

import logging
from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.cost_analyzer")


class CostAnalyzerAgent(HealthOSAgent):
    """Analyzes healthcare costs and identifies optimization opportunities."""

    def __init__(self):
        super().__init__(
            name="cost_analyzer",
            tier=AgentTier.DIAGNOSTIC,
            description="Healthcare cost analysis, ROI tracking, and optimization",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        analysis_type = data.get("analysis_type", "summary")

        if analysis_type == "rpm_roi":
            result = self._rpm_roi_analysis(data)
        elif analysis_type == "cost_per_patient":
            result = self._cost_per_patient(data)
        elif analysis_type == "savings_forecast":
            result = self._savings_forecast(data)
        else:
            result = self._cost_summary(data)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=f"cost_analysis_{analysis_type}",
            rationale=f"Cost analysis ({analysis_type}) completed",
            confidence=0.75,
            data=result,
            feature_contributions=[
                {"feature": "patient_volume", "contribution": 0.3, "value": data.get("patient_count", 0)},
                {"feature": "cost_data", "contribution": 0.4, "value": "analyzed"},
                {"feature": "historical_trend", "contribution": 0.3, "value": "evaluated"},
            ],
        )

    def _rpm_roi_analysis(self, data: dict) -> dict:
        patients = data.get("patient_count", 100)
        monthly_cost = data.get("monthly_rpm_cost", 150)  # per patient
        avg_er_visits_avoided = data.get("er_visits_avoided_per_patient", 0.3)
        avg_er_cost = data.get("avg_er_cost", 2500)
        readmission_reduction = data.get("readmission_reduction_percent", 15)
        avg_readmission_cost = data.get("avg_readmission_cost", 15000)

        total_rpm_cost = patients * monthly_cost * 12
        er_savings = patients * avg_er_visits_avoided * avg_er_cost * 12
        readmission_savings = (patients * 0.15 * avg_readmission_cost *
                               readmission_reduction / 100)
        total_savings = er_savings + readmission_savings
        roi = ((total_savings - total_rpm_cost) / total_rpm_cost * 100) if total_rpm_cost > 0 else 0

        return {
            "analysis_type": "rpm_roi",
            "annual_rpm_cost": total_rpm_cost,
            "er_visit_savings": round(er_savings),
            "readmission_savings": round(readmission_savings),
            "total_annual_savings": round(total_savings),
            "net_benefit": round(total_savings - total_rpm_cost),
            "roi_percent": round(roi, 1),
            "payback_months": round(total_rpm_cost / max(total_savings / 12, 1), 1),
        }

    def _cost_per_patient(self, data: dict) -> dict:
        return {
            "analysis_type": "cost_per_patient",
            "avg_monthly_cost": data.get("avg_monthly_cost", 0),
            "cost_by_risk_level": {
                "LOW": data.get("cost_low_risk", 50),
                "MEDIUM": data.get("cost_medium_risk", 150),
                "HIGH": data.get("cost_high_risk", 400),
                "CRITICAL": data.get("cost_critical_risk", 1200),
            },
        }

    def _savings_forecast(self, data: dict) -> dict:
        base_savings = data.get("current_annual_savings", 100000)
        growth_rate = data.get("patient_growth_rate", 0.10)

        forecast = []
        for year in range(1, 4):
            projected = base_savings * (1 + growth_rate) ** year
            forecast.append({"year": year, "projected_savings": round(projected)})

        return {
            "analysis_type": "savings_forecast",
            "forecast": forecast,
        }

    def _cost_summary(self, data: dict) -> dict:
        return {
            "analysis_type": "summary",
            "total_patients": data.get("patient_count", 0),
            "monthly_operating_cost": data.get("monthly_cost", 0),
            "cost_efficiency_score": data.get("efficiency_score", 0),
        }
