"""
Eminence HealthOS — Cost Analyzer Agent
Layer 5 (Measurement): Analyzes care delivery costs, identifies cost reduction
opportunities, tracks ROI for RPM programs, and generates savings forecasts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger("healthos.agent.cost_analyzer")


class CostAnalyzerAgent(BaseAgent):
    """Analyzes healthcare costs and identifies optimization opportunities."""

    name = "cost_analyzer"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Healthcare cost analysis, ROI tracking, and optimization"
    min_confidence = 0.75

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "summary")

        if action == "rpm_roi":
            return self._rpm_roi_analysis(input_data)
        elif action == "cost_per_patient":
            return self._cost_per_patient(input_data)
        elif action == "savings_forecast":
            return self._savings_forecast(input_data)
        elif action == "summary":
            return await self._cost_summary(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown cost analysis action: {action}",
                status=AgentStatus.FAILED,
            )

    def _rpm_roi_analysis(self, input_data: AgentInput) -> AgentOutput:
        """Analyze ROI for Remote Patient Monitoring programs."""
        ctx = input_data.context

        patients = ctx.get("patient_count", 100)
        monthly_cost = ctx.get("monthly_rpm_cost", 150)
        avg_er_visits_avoided = ctx.get("er_visits_avoided_per_patient", 0.3)
        avg_er_cost = ctx.get("avg_er_cost", 2500)
        readmission_reduction = ctx.get("readmission_reduction_percent", 15)
        avg_readmission_cost = ctx.get("avg_readmission_cost", 15000)

        total_rpm_cost = patients * monthly_cost * 12
        er_savings = patients * avg_er_visits_avoided * avg_er_cost * 12
        readmission_savings = (
            patients * 0.15 * avg_readmission_cost * readmission_reduction / 100
        )
        total_savings = er_savings + readmission_savings
        roi = ((total_savings - total_rpm_cost) / total_rpm_cost * 100) if total_rpm_cost > 0 else 0

        result = {
            "annual_rpm_cost": total_rpm_cost,
            "er_visit_savings": round(er_savings),
            "readmission_savings": round(readmission_savings),
            "total_annual_savings": round(total_savings),
            "net_benefit": round(total_savings - total_rpm_cost),
            "roi_percent": round(roi, 1),
            "payback_months": round(total_rpm_cost / max(total_savings / 12, 1), 1),
            "patients_analyzed": patients,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.80,
            rationale=f"RPM ROI: {roi:.1f}% return, ${result['net_benefit']:,} net benefit",
        )

    def _cost_per_patient(self, input_data: AgentInput) -> AgentOutput:
        """Analyze cost per patient by risk level."""
        ctx = input_data.context

        cost_by_risk = {
            "low": ctx.get("cost_low_risk", 50),
            "moderate": ctx.get("cost_moderate_risk", 150),
            "high": ctx.get("cost_high_risk", 400),
            "critical": ctx.get("cost_critical_risk", 1200),
        }

        patients_by_risk = ctx.get("patients_by_risk", {
            "low": 500, "moderate": 300, "high": 150, "critical": 50,
        })

        total_cost = sum(
            cost_by_risk.get(level, 0) * patients_by_risk.get(level, 0)
            for level in cost_by_risk
        )
        total_patients = sum(patients_by_risk.values())
        weighted_avg = total_cost / max(total_patients, 1)

        result = {
            "avg_monthly_cost": round(weighted_avg, 2),
            "cost_by_risk_level": cost_by_risk,
            "patients_by_risk_level": patients_by_risk,
            "total_monthly_cost": total_cost,
            "total_patients": total_patients,
            "cost_concentration": round(
                (cost_by_risk["high"] * patients_by_risk.get("high", 0) +
                 cost_by_risk["critical"] * patients_by_risk.get("critical", 0)) /
                max(total_cost, 1), 3
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.78,
            rationale=f"Cost per patient: ${weighted_avg:.2f}/month avg, {total_patients} patients",
        )

    def _savings_forecast(self, input_data: AgentInput) -> AgentOutput:
        """Project savings over multiple years."""
        ctx = input_data.context

        base_savings = ctx.get("current_annual_savings", 100000)
        growth_rate = ctx.get("patient_growth_rate", 0.10)

        forecast = []
        for year in range(1, 4):
            projected = base_savings * (1 + growth_rate) ** year
            forecast.append({
                "year": year,
                "projected_savings": round(projected),
                "cumulative_savings": round(sum(
                    base_savings * (1 + growth_rate) ** y for y in range(1, year + 1)
                )),
            })

        result = {
            "base_annual_savings": base_savings,
            "growth_rate": growth_rate,
            "forecast": forecast,
            "three_year_total": forecast[-1]["cumulative_savings"] if forecast else 0,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.72,
            rationale=f"Savings forecast: ${result['three_year_total']:,} over 3 years at {growth_rate:.0%} growth",
        )

    async def _cost_summary(self, input_data: AgentInput) -> AgentOutput:
        """Generate cost summary overview."""
        ctx = input_data.context

        total_patients = ctx.get("patient_count", 0)
        monthly_cost = ctx.get("monthly_cost", 0)
        efficiency_score = ctx.get("efficiency_score", 0)
        cost_trend = ctx.get("cost_trend", "stable")

        # --- LLM: generate cost narrative ---
        cost_narrative: str | None = None
        try:
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Analyze the following healthcare cost data and provide a narrative "
                    f"covering cost drivers, efficiency opportunities, and savings recommendations.\n\n"
                    f"Total patients: {total_patients}\n"
                    f"Monthly operating cost: ${monthly_cost:,}\n"
                    f"Cost efficiency score: {efficiency_score}\n"
                    f"Cost trend: {cost_trend}\n\n"
                    f"Provide actionable insights on cost drivers and savings opportunities."
                )}],
                system=(
                    "You are a healthcare financial analyst for Eminence HealthOS. "
                    "Provide clear, actionable cost analysis narratives. Focus on "
                    "identifying cost drivers, benchmarking, and savings opportunities."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            cost_narrative = resp.content
        except Exception:
            logger.warning("LLM cost_narrative generation failed; continuing without it")

        result = {
            "total_patients": total_patients,
            "monthly_operating_cost": monthly_cost,
            "cost_efficiency_score": efficiency_score,
            "cost_trend": cost_trend,
            "cost_narrative": cost_narrative,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.75,
            rationale=f"Cost summary: {result['total_patients']} patients, efficiency {result['cost_efficiency_score']}",
        )
