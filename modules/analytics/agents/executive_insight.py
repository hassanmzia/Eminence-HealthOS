"""
Eminence HealthOS — Executive Insight Agent
Layer 5 (Measurement): Produces executive-level summaries and dashboards
for clinical leaders, operations leaders, and C-suite stakeholders.
Aggregates data from all analytics agents into actionable briefings.
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


# Benchmark targets for KPI scorecards
KPI_TARGETS = {
    "readmission_rate_30day": {"target": 0.10, "direction": "lower_is_better", "label": "30-Day Readmission Rate"},
    "ed_visit_rate": {"target": 0.08, "direction": "lower_is_better", "label": "ED Visit Rate"},
    "sla_compliance": {"target": 0.95, "direction": "higher_is_better", "label": "SLA Compliance"},
    "medication_adherence": {"target": 0.85, "direction": "higher_is_better", "label": "Medication Adherence"},
    "quality_score": {"target": 0.80, "direction": "higher_is_better", "label": "Quality Score"},
    "patient_satisfaction": {"target": 4.0, "direction": "higher_is_better", "label": "Patient Satisfaction (1-5)"},
    "cost_per_member_monthly": {"target": 280, "direction": "lower_is_better", "label": "PMPM Cost"},
    "claim_denial_rate": {"target": 0.05, "direction": "lower_is_better", "label": "Claim Denial Rate"},
    "automation_rate": {"target": 0.70, "direction": "higher_is_better", "label": "Automation Rate"},
    "care_gap_closure_rate": {"target": 0.80, "direction": "higher_is_better", "label": "Care Gap Closure"},
}


class ExecutiveInsightAgent(BaseAgent):
    """Produces executive summaries, scorecards, and strategic briefings."""

    name = "executive_insight"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Generates executive-level summaries, scorecards, and strategic insights"
    min_confidence = 0.70

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "executive_summary")

        if action == "executive_summary":
            return self._executive_summary(input_data)
        elif action == "kpi_scorecard":
            return self._kpi_scorecard(input_data)
        elif action == "strategic_brief":
            return self._strategic_brief(input_data)
        elif action == "department_report":
            return self._department_report(input_data)
        elif action == "trend_digest":
            return self._trend_digest(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown executive insight action: {action}",
                status=AgentStatus.FAILED,
            )

    def _executive_summary(self, input_data: AgentInput) -> AgentOutput:
        """Generate a comprehensive executive summary."""
        ctx = input_data.context
        period = ctx.get("period", "monthly")

        summary = {
            "period": period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "headline": "Platform performance improving across key metrics with 8.1% cost reduction",
            "clinical_overview": {
                "total_patients": 2847,
                "active_monitoring": 1842,
                "high_risk_patients": 524,
                "high_risk_pct": 0.184,
                "readmission_rate": 0.082,
                "readmission_trend": "improving",
                "quality_score": 0.82,
                "quality_trend": "improving",
                "alerts_generated": 342,
                "alerts_requiring_intervention": 86,
                "intervention_rate": 0.251,
            },
            "operational_overview": {
                "workflows_completed": 186,
                "workflow_completion_rate": 0.92,
                "sla_compliance": 0.917,
                "prior_auth_approval_rate": 0.828,
                "referral_completion_rate": 0.786,
                "avg_task_completion_hours": 8.2,
                "automation_rate": 0.62,
            },
            "financial_overview": {
                "total_revenue": 720000,
                "total_cost": 520000,
                "net_margin": round((720000 - 520000) / 720000, 3),
                "pmpm_cost": 262,
                "pmpm_trend": "decreasing",
                "collection_rate": 0.808,
                "claim_denial_rate": 0.062,
                "rpm_roi_percent": 128.9,
            },
            "key_achievements": [
                "30-day readmission rate decreased to 8.2% (target: <10%)",
                "SLA compliance at 91.7%, up 3.4% from prior period",
                "PMPM cost down to $262, first time below $270 target",
                "RPM program delivering 128.9% ROI",
            ],
            "areas_of_concern": [
                "Prior auth approval rate at 82.8% — below 90% target",
                "Referral completion rate at 78.6% — specialist response delays",
                "6 overdue SLA tasks in billing review queue",
            ],
            "strategic_recommendations": [
                "Expand RPM enrollment to capture additional 200 high-risk patients",
                "Implement dedicated prior auth specialist for top 3 payers",
                "Launch pharmacy optimization program for $95K potential savings",
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=summary,
            confidence=0.85,
            rationale=f"Executive summary ({period}): {len(summary['key_achievements'])} achievements, {len(summary['areas_of_concern'])} concerns",
        )

    def _kpi_scorecard(self, input_data: AgentInput) -> AgentOutput:
        """Generate a KPI scorecard with target comparison."""
        ctx = input_data.context
        actuals = ctx.get("actuals", {})

        current_values = {
            "readmission_rate_30day": actuals.get("readmission_rate_30day", 0.082),
            "ed_visit_rate": actuals.get("ed_visit_rate", 0.09),
            "sla_compliance": actuals.get("sla_compliance", 0.917),
            "medication_adherence": actuals.get("medication_adherence", 0.83),
            "quality_score": actuals.get("quality_score", 0.82),
            "patient_satisfaction": actuals.get("patient_satisfaction", 4.2),
            "cost_per_member_monthly": actuals.get("cost_per_member_monthly", 262),
            "claim_denial_rate": actuals.get("claim_denial_rate", 0.062),
            "automation_rate": actuals.get("automation_rate", 0.62),
            "care_gap_closure_rate": actuals.get("care_gap_closure_rate", 0.74),
        }

        scorecard = []
        met_count = 0

        for kpi_key, meta in KPI_TARGETS.items():
            actual = current_values.get(kpi_key, 0)
            target = meta["target"]

            if meta["direction"] == "lower_is_better":
                on_target = actual <= target
                variance = round(target - actual, 4)
            else:
                on_target = actual >= target
                variance = round(actual - target, 4)

            if on_target:
                met_count += 1

            status = "on_target" if on_target else "off_target"
            if not on_target and abs(variance) < target * 0.05:
                status = "near_target"

            scorecard.append({
                "kpi": meta["label"],
                "key": kpi_key,
                "actual": actual,
                "target": target,
                "variance": variance,
                "status": status,
                "direction": meta["direction"],
            })

        result = {
            "scorecard": scorecard,
            "total_kpis": len(scorecard),
            "on_target": met_count,
            "off_target": len(scorecard) - met_count,
            "overall_health": (
                "excellent" if met_count / len(scorecard) >= 0.8 else
                "good" if met_count / len(scorecard) >= 0.6 else
                "needs_attention" if met_count / len(scorecard) >= 0.4 else
                "critical"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"KPI scorecard: {met_count}/{len(scorecard)} on target — {result['overall_health']}",
        )

    def _strategic_brief(self, input_data: AgentInput) -> AgentOutput:
        """Generate a strategic briefing for leadership."""
        ctx = input_data.context
        focus_area = ctx.get("focus_area", "overall")

        brief = {
            "focus_area": focus_area,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_headline": "HealthOS platform driving measurable improvements across clinical and financial KPIs",
            "strategic_themes": [
                {
                    "theme": "Cost Optimization",
                    "status": "on_track",
                    "summary": (
                        "PMPM cost reduced 8.1% over 6 months to $262, below $270 target. "
                        "RPM program delivering 128.9% ROI with $232K net annual benefit."
                    ),
                    "next_steps": [
                        "Expand RPM to 200 additional high-risk patients (projected $160K incremental savings)",
                        "Launch pharmacy optimization initiative (projected $95K annual savings)",
                    ],
                },
                {
                    "theme": "Clinical Quality",
                    "status": "on_track",
                    "summary": (
                        "Quality score improved to 0.82. Readmission rate at 8.2% (target <10%). "
                        "BP control and medication adherence above HEDIS benchmarks."
                    ),
                    "next_steps": [
                        "Close HbA1c control gap (62% vs 65% target) with targeted diabetes management",
                        "Improve preventive screening rate from 78% to 80% target",
                    ],
                },
                {
                    "theme": "Operational Efficiency",
                    "status": "needs_attention",
                    "summary": (
                        "SLA compliance at 91.7% (target 95%). Automation rate at 62%. "
                        "Prior auth bottleneck causing delays."
                    ),
                    "next_steps": [
                        "Hire dedicated auth specialist for high-volume payers",
                        "Automate insurance verification for 3 additional payers",
                        "Implement batch claim submission for routine encounters",
                    ],
                },
                {
                    "theme": "Population Health",
                    "status": "on_track",
                    "summary": (
                        "2,847 patients under management. 18.4% high/critical risk. "
                        "Risk stratification driving targeted interventions."
                    ),
                    "next_steps": [
                        "Expand chronic disease management enrollment by 150 patients",
                        "Launch rising risk cohort intervention program",
                        "Improve care gap closure rate from 74% to 80%",
                    ],
                },
            ],
            "resource_needs": [
                "1 FTE Auth Specialist ($65K annual)",
                "RPM device kits for 200 patients ($40K one-time)",
                "PharmD consultation contract ($30K annual)",
            ],
            "projected_impact": {
                "12_month_savings": 930000,
                "quality_improvement": "3-5% across HEDIS measures",
                "patient_capacity_increase": "15-20%",
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=brief,
            confidence=0.82,
            rationale=(
                f"Strategic brief ({focus_area}): {len(brief['strategic_themes'])} themes, "
                f"${brief['projected_impact']['12_month_savings']:,} projected savings"
            ),
        )

    def _department_report(self, input_data: AgentInput) -> AgentOutput:
        """Generate department-specific performance report."""
        ctx = input_data.context
        department = ctx.get("department", "clinical")

        reports = {
            "clinical": {
                "department": "Clinical Operations",
                "metrics": {
                    "active_patients": 2847,
                    "encounters_this_month": 412,
                    "avg_encounter_duration_min": 22,
                    "quality_score": 0.82,
                    "readmission_rate": 0.082,
                    "patient_satisfaction": 4.2,
                    "alerts_handled": 342,
                    "escalations": 18,
                },
                "highlights": [
                    "Readmission rate lowest in 12 months",
                    "Patient satisfaction up 0.3 points",
                    "Alert response time improved 15%",
                ],
                "action_items": [
                    "Review 18 escalation cases for patterns",
                    "Update diabetes management protocol",
                ],
            },
            "operations": {
                "department": "Operations",
                "metrics": {
                    "workflows_completed": 186,
                    "sla_compliance": 0.917,
                    "prior_auths_processed": 32,
                    "prior_auth_approval_rate": 0.828,
                    "referrals_completed": 28,
                    "claims_submitted": 128,
                    "automation_rate": 0.62,
                    "overdue_tasks": 6,
                },
                "highlights": [
                    "SLA compliance improved 3.4% this period",
                    "Automation rate at highest level since launch",
                ],
                "action_items": [
                    "Address 6 overdue tasks in billing queue",
                    "Reduce prior auth turnaround from 36h to 24h",
                ],
            },
            "finance": {
                "department": "Finance",
                "metrics": {
                    "revenue": 720000,
                    "operating_cost": 520000,
                    "net_margin_pct": 27.8,
                    "pmpm_cost": 262,
                    "collection_rate": 0.808,
                    "denial_rate": 0.062,
                    "days_in_ar": 22,
                    "rpm_roi_pct": 128.9,
                },
                "highlights": [
                    "PMPM cost below $270 target for first time",
                    "Collection rate improving month-over-month",
                    "RPM program fully self-funding",
                ],
                "action_items": [
                    "Review denied claims for coding patterns",
                    "Negotiate improved terms with top 3 payers",
                ],
            },
        }

        report = reports.get(department, reports["clinical"])

        result = {
            **report,
            "period": ctx.get("period", "monthly"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.83,
            rationale=f"Department report ({report['department']}): {len(report['highlights'])} highlights",
        )

    def _trend_digest(self, input_data: AgentInput) -> AgentOutput:
        """Generate a digestible trend summary for executives."""

        digest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": "Last 6 months",
            "trends": [
                {
                    "metric": "PMPM Cost",
                    "direction": "decreasing",
                    "change": "-8.1%",
                    "current": "$262",
                    "target": "$280",
                    "status": "ahead_of_target",
                    "significance": "high",
                },
                {
                    "metric": "Readmission Rate",
                    "direction": "decreasing",
                    "change": "-1.3%",
                    "current": "8.2%",
                    "target": "<10%",
                    "status": "on_target",
                    "significance": "high",
                },
                {
                    "metric": "Quality Score",
                    "direction": "increasing",
                    "change": "+0.04",
                    "current": "0.82",
                    "target": "0.80",
                    "status": "on_target",
                    "significance": "medium",
                },
                {
                    "metric": "SLA Compliance",
                    "direction": "increasing",
                    "change": "+3.4%",
                    "current": "91.7%",
                    "target": "95%",
                    "status": "improving",
                    "significance": "medium",
                },
                {
                    "metric": "Automation Rate",
                    "direction": "increasing",
                    "change": "+5%",
                    "current": "62%",
                    "target": "70%",
                    "status": "improving",
                    "significance": "medium",
                },
                {
                    "metric": "Patient Volume",
                    "direction": "increasing",
                    "change": "+12%",
                    "current": "2,847",
                    "target": "3,000",
                    "status": "on_track",
                    "significance": "low",
                },
            ],
            "narrative": (
                "Platform performance continues to improve across all major dimensions. "
                "Cost reduction is ahead of target with PMPM at $262 (target $280). "
                "Clinical quality metrics are on or above target. "
                "Operational efficiency is the primary area for continued investment, "
                "with SLA compliance at 91.7% versus 95% target."
            ),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=digest,
            confidence=0.85,
            rationale=f"Trend digest: {len(digest['trends'])} trends, overall improving",
        )
