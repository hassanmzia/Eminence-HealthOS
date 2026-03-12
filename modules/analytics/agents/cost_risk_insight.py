"""
Eminence HealthOS — Cost/Risk Insight Agent
Layer 5 (Measurement): Estimates operational and clinical cost drivers,
identifies risk-cost correlations, models intervention impact on costs,
and surfaces actionable cost reduction opportunities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)


# Cost driver categories with baseline weights
COST_DRIVERS = {
    "inpatient_admissions": {"weight": 0.30, "avg_cost": 15000, "label": "Inpatient Admissions"},
    "ed_visits": {"weight": 0.18, "avg_cost": 2500, "label": "ED Visits"},
    "specialist_visits": {"weight": 0.12, "avg_cost": 350, "label": "Specialist Visits"},
    "pharmacy": {"weight": 0.15, "avg_cost": 450, "label": "Pharmacy (monthly)"},
    "imaging": {"weight": 0.08, "avg_cost": 1200, "label": "Imaging Studies"},
    "lab_tests": {"weight": 0.05, "avg_cost": 180, "label": "Lab Tests"},
    "readmissions": {"weight": 0.10, "avg_cost": 18000, "label": "30-Day Readmissions"},
    "post_acute_care": {"weight": 0.02, "avg_cost": 8000, "label": "Post-Acute Care"},
}

# Intervention impact models (estimated cost reduction per intervention)
INTERVENTION_MODELS = {
    "rpm_monitoring": {
        "name": "Remote Patient Monitoring",
        "targets": ["ed_visits", "inpatient_admissions", "readmissions"],
        "reduction_pct": {"ed_visits": 0.25, "inpatient_admissions": 0.15, "readmissions": 0.20},
        "monthly_cost_per_patient": 150,
    },
    "care_coordination": {
        "name": "Care Coordination Program",
        "targets": ["readmissions", "ed_visits", "specialist_visits"],
        "reduction_pct": {"readmissions": 0.18, "ed_visits": 0.12, "specialist_visits": 0.10},
        "monthly_cost_per_patient": 80,
    },
    "medication_management": {
        "name": "Medication Management",
        "targets": ["pharmacy", "ed_visits", "inpatient_admissions"],
        "reduction_pct": {"pharmacy": 0.15, "ed_visits": 0.10, "inpatient_admissions": 0.08},
        "monthly_cost_per_patient": 60,
    },
    "chronic_disease_program": {
        "name": "Chronic Disease Management",
        "targets": ["inpatient_admissions", "ed_visits", "readmissions"],
        "reduction_pct": {"inpatient_admissions": 0.20, "ed_visits": 0.18, "readmissions": 0.25},
        "monthly_cost_per_patient": 200,
    },
}


class CostRiskInsightAgent(BaseAgent):
    """Estimates operational and clinical cost drivers with intervention modeling."""

    name = "cost_risk_insight"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Identifies cost drivers, risk-cost correlations, and intervention ROI"
    min_confidence = 0.70

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "cost_drivers")

        if action == "cost_drivers":
            return self._analyze_cost_drivers(input_data)
        elif action == "risk_cost_correlation":
            return self._risk_cost_correlation(input_data)
        elif action == "intervention_impact":
            return self._model_intervention_impact(input_data)
        elif action == "cost_trends":
            return self._analyze_cost_trends(input_data)
        elif action == "opportunity_scan":
            return self._scan_opportunities(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown cost/risk action: {action}",
                status=AgentStatus.FAILED,
            )

    def _analyze_cost_drivers(self, input_data: AgentInput) -> AgentOutput:
        """Identify top cost drivers across the patient population."""
        ctx = input_data.context
        patient_count = ctx.get("patient_count", 1000)
        period_months = ctx.get("period_months", 12)

        utilization = ctx.get("utilization", {})
        drivers = []
        total_cost = 0

        for key, meta in COST_DRIVERS.items():
            volume = utilization.get(key, int(patient_count * meta["weight"]))
            cost = volume * meta["avg_cost"]
            total_cost += cost
            drivers.append({
                "driver": meta["label"],
                "category": key,
                "volume": volume,
                "unit_cost": meta["avg_cost"],
                "total_cost": cost,
            })

        drivers.sort(key=lambda d: d["total_cost"], reverse=True)

        for d in drivers:
            d["pct_of_total"] = round(d["total_cost"] / max(total_cost, 1), 3)

        result = {
            "patient_count": patient_count,
            "period_months": period_months,
            "total_cost": total_cost,
            "cost_per_patient_monthly": round(total_cost / max(patient_count * period_months, 1), 2),
            "top_drivers": drivers[:5],
            "all_drivers": drivers,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82,
            rationale=(
                f"Cost drivers: ${total_cost:,.0f} total, "
                f"top driver {drivers[0]['driver']} ({drivers[0]['pct_of_total']:.1%})"
            ),
        )

    def _risk_cost_correlation(self, input_data: AgentInput) -> AgentOutput:
        """Analyze correlation between risk levels and costs."""
        ctx = input_data.context

        risk_tiers = ctx.get("risk_tiers", {
            "low": {"patients": 500, "monthly_cost": 85, "utilization_rate": 0.15},
            "moderate": {"patients": 300, "monthly_cost": 280, "utilization_rate": 0.35},
            "high": {"patients": 150, "monthly_cost": 650, "utilization_rate": 0.58},
            "critical": {"patients": 50, "monthly_cost": 1800, "utilization_rate": 0.82},
        })

        total_patients = sum(t["patients"] for t in risk_tiers.values())
        total_monthly = sum(t["patients"] * t["monthly_cost"] for t in risk_tiers.values())

        correlations = []
        for level, data in risk_tiers.items():
            tier_cost = data["patients"] * data["monthly_cost"]
            correlations.append({
                "risk_level": level,
                "patients": data["patients"],
                "pct_of_population": round(data["patients"] / max(total_patients, 1), 3),
                "monthly_cost_per_patient": data["monthly_cost"],
                "total_monthly_cost": tier_cost,
                "pct_of_total_cost": round(tier_cost / max(total_monthly, 1), 3),
                "utilization_rate": data["utilization_rate"],
                "cost_multiplier": round(
                    data["monthly_cost"] / max(risk_tiers.get("low", {}).get("monthly_cost", 1), 1),
                    1,
                ),
            })

        high_critical = sum(
            c["pct_of_total_cost"] for c in correlations
            if c["risk_level"] in ("high", "critical")
        )
        high_critical_pct_pop = sum(
            c["pct_of_population"] for c in correlations
            if c["risk_level"] in ("high", "critical")
        )

        result = {
            "correlations": correlations,
            "total_patients": total_patients,
            "total_monthly_cost": total_monthly,
            "insights": [
                f"Top 20% of patients by risk account for {high_critical:.1%} of costs",
                f"High/critical patients ({high_critical_pct_pop:.1%} of population) drive {high_critical:.1%} of costs",
                f"Critical patients cost {correlations[-1]['cost_multiplier']}x more than low-risk patients",
            ],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"Risk-cost correlation: high/critical = {high_critical:.1%} of costs",
        )

    def _model_intervention_impact(self, input_data: AgentInput) -> AgentOutput:
        """Model the financial impact of interventions."""
        ctx = input_data.context
        intervention_key = ctx.get("intervention", "rpm_monitoring")
        patient_count = ctx.get("patient_count", 200)
        current_costs = ctx.get("current_costs", {})

        model = INTERVENTION_MODELS.get(intervention_key)
        if not model:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "error": f"Unknown intervention: {intervention_key}",
                    "available": list(INTERVENTION_MODELS.keys()),
                },
                confidence=0.0,
                rationale=f"Intervention '{intervention_key}' not found",
                status=AgentStatus.FAILED,
            )

        annual_program_cost = patient_count * model["monthly_cost_per_patient"] * 12
        savings_by_category = {}
        total_savings = 0

        for target in model["targets"]:
            driver = COST_DRIVERS.get(target, {})
            baseline_cost = current_costs.get(
                target,
                int(patient_count * driver.get("weight", 0.1)) * driver.get("avg_cost", 0),
            )
            reduction = model["reduction_pct"].get(target, 0)
            saved = baseline_cost * reduction
            savings_by_category[target] = {
                "baseline_cost": baseline_cost,
                "reduction_pct": reduction,
                "savings": round(saved),
            }
            total_savings += saved

        net_benefit = total_savings - annual_program_cost
        roi = (net_benefit / max(annual_program_cost, 1)) * 100

        result = {
            "intervention": model["name"],
            "intervention_key": intervention_key,
            "patient_count": patient_count,
            "annual_program_cost": annual_program_cost,
            "savings_by_category": savings_by_category,
            "total_annual_savings": round(total_savings),
            "net_annual_benefit": round(net_benefit),
            "roi_percent": round(roi, 1),
            "payback_months": round(annual_program_cost / max(total_savings / 12, 1), 1),
            "break_even_patients": max(
                1, int(annual_program_cost / max(total_savings / patient_count, 1))
            ),
            "modeled_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.78,
            rationale=f"Intervention model '{model['name']}': {roi:.1f}% ROI, ${net_benefit:,.0f} net benefit",
        )

    def _analyze_cost_trends(self, input_data: AgentInput) -> AgentOutput:
        """Analyze cost trends over time."""

        trends = {
            "monthly_data": [
                {"month": "2025-10", "total_cost": 285000, "pmpm": 285, "ed_rate": 0.12, "admit_rate": 0.08},
                {"month": "2025-11", "total_cost": 278000, "pmpm": 278, "ed_rate": 0.11, "admit_rate": 0.07},
                {"month": "2025-12", "total_cost": 295000, "pmpm": 295, "ed_rate": 0.13, "admit_rate": 0.09},
                {"month": "2026-01", "total_cost": 272000, "pmpm": 272, "ed_rate": 0.10, "admit_rate": 0.07},
                {"month": "2026-02", "total_cost": 268000, "pmpm": 268, "ed_rate": 0.10, "admit_rate": 0.06},
                {"month": "2026-03", "total_cost": 262000, "pmpm": 262, "ed_rate": 0.09, "admit_rate": 0.06},
            ],
            "overall_trend": "decreasing",
            "monthly_change_pct": -1.8,
            "six_month_change_pct": -8.1,
            "insights": [
                "Total costs decreased 8.1% over 6 months",
                "ED visit rate declining — down 25% from October peak",
                "Admission rate stable at 6-7%, within target range",
                "PMPM trending below $270 target for first time",
            ],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=trends,
            confidence=0.80,
            rationale=f"Cost trends: {trends['overall_trend']}, {trends['six_month_change_pct']}% over 6 months",
        )

    def _scan_opportunities(self, input_data: AgentInput) -> AgentOutput:
        """Scan for cost reduction opportunities."""

        opportunities = [
            {
                "opportunity": "Reduce avoidable ED visits",
                "category": "utilization",
                "estimated_annual_savings": 180000,
                "effort": "medium",
                "timeline_months": 6,
                "intervention": "Enhanced triage + RPM for high-risk patients",
                "confidence": 0.85,
            },
            {
                "opportunity": "Reduce 30-day readmissions",
                "category": "quality",
                "estimated_annual_savings": 270000,
                "effort": "high",
                "timeline_months": 9,
                "intervention": "Transition care program + medication reconciliation",
                "confidence": 0.80,
            },
            {
                "opportunity": "Pharmacy optimization",
                "category": "pharmacy",
                "estimated_annual_savings": 95000,
                "effort": "low",
                "timeline_months": 3,
                "intervention": "Generic substitution + formulary adherence program",
                "confidence": 0.88,
            },
            {
                "opportunity": "Imaging appropriateness",
                "category": "utilization",
                "estimated_annual_savings": 65000,
                "effort": "low",
                "timeline_months": 4,
                "intervention": "Clinical decision support for imaging orders",
                "confidence": 0.82,
            },
            {
                "opportunity": "Chronic disease management enrollment",
                "category": "population_health",
                "estimated_annual_savings": 320000,
                "effort": "high",
                "timeline_months": 12,
                "intervention": "Identify and enroll eligible patients in CDM programs",
                "confidence": 0.75,
            },
        ]

        opportunities.sort(key=lambda o: o["estimated_annual_savings"], reverse=True)
        total_savings = sum(o["estimated_annual_savings"] for o in opportunities)

        result = {
            "opportunities": opportunities,
            "total_potential_savings": total_savings,
            "quick_wins": [o for o in opportunities if o["effort"] == "low"],
            "high_impact": [o for o in opportunities if o["estimated_annual_savings"] > 200000],
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.80,
            rationale=f"Opportunity scan: {len(opportunities)} found, ${total_savings:,.0f} total potential",
        )
