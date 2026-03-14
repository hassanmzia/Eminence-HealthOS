"""
Eminence HealthOS — Population Health Agent
Layer 5 (Measurement): Analyzes patient cohorts for risk stratification,
quality metrics tracking, and population health trends.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = structlog.get_logger()


class PopulationHealthAgent(BaseAgent):
    """Generates population health analytics and insights."""

    name = "population_health"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Population-level analytics, risk stratification, and quality metrics"
    min_confidence = 0.75

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "overview")

        if action == "risk_stratification":
            return self._risk_stratification(input_data)
        elif action == "quality_metrics":
            return await self._quality_metrics(input_data)
        elif action == "cohort_analysis":
            return self._cohort_analysis(input_data)
        elif action == "overview":
            return await self._overview(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown population health action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _overview(self, input_data: AgentInput) -> AgentOutput:
        """Generate population health overview with LLM-powered narrative."""
        ctx = input_data.context
        patients = ctx.get("patients", [])
        total = len(patients) or ctx.get("total_patients", 0)

        avg_risk = self._safe_avg([p.get("risk_score", 0) for p in patients])
        high_risk = self._pct(
            [p for p in patients if p.get("risk_level", "").lower() in ("high", "critical")],
            total,
        )
        with_alerts = self._pct(
            [p for p in patients if p.get("active_alerts", 0) > 0],
            total,
        )

        result = {
            "total_patients": total,
            "metrics": {
                "avg_risk_score": avg_risk,
                "high_risk_percent": high_risk,
                "with_active_alerts": with_alerts,
            },
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        # LLM-powered executive summary
        if total > 0:
            try:
                import json
                prompt = (
                    f"Generate a brief executive summary for a population health dashboard.\n\n"
                    f"Total patients: {total}\n"
                    f"Average risk score: {avg_risk}\n"
                    f"High/critical risk: {high_risk}%\n"
                    f"With active alerts: {with_alerts}%\n\n"
                    f"Provide a 2-3 sentence summary highlighting key concerns and trends."
                )
                llm_resp = await llm_router.complete(LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system="You are a population health analyst generating concise executive summaries for healthcare leadership.",
                    temperature=0.3,
                    max_tokens=512,
                ))
                result["executive_summary"] = llm_resp.content
            except Exception as exc:
                logger.warning("population_health.overview_llm_failed", error=str(exc))

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82 if patients else 0.65,
            rationale=f"Population overview: {total} patients, avg risk {avg_risk}",
        )

    def _risk_stratification(self, input_data: AgentInput) -> AgentOutput:
        """Stratify patient population by risk level."""
        ctx = input_data.context
        patients = ctx.get("patients", [])

        tiers: dict[str, list] = {"low": [], "moderate": [], "high": [], "critical": []}
        for p in patients:
            level = p.get("risk_level", "low").lower()
            tiers.setdefault(level, []).append(p)

        distribution = {k: len(v) for k, v in tiers.items()}

        recommendations = [
            {"tier": "critical", "action": "Daily monitoring, weekly provider review", "priority": 1},
            {"tier": "high", "action": "Twice-weekly monitoring, bi-weekly review", "priority": 2},
            {"tier": "moderate", "action": "Weekly monitoring, monthly review", "priority": 3},
            {"tier": "low", "action": "Monthly check-in, quarterly review", "priority": 4},
        ]

        result = {
            "total_patients": len(patients),
            "distribution": distribution,
            "recommendations": recommendations,
            "high_risk_patients": [
                {"patient_id": p.get("patient_id", ""), "risk_score": p.get("risk_score", 0)}
                for p in (tiers.get("critical", []) + tiers.get("high", []))[:20]
            ],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85 if patients else 0.60,
            rationale=(
                f"Risk stratification: {len(patients)} patients — "
                f"{distribution.get('critical', 0)} critical, {distribution.get('high', 0)} high"
            ),
        )

    async def _quality_metrics(self, input_data: AgentInput) -> AgentOutput:
        """Generate HEDIS-style quality metrics with LLM-powered insights."""
        ctx = input_data.context

        hedis = {
            "bp_control": ctx.get("bp_control_rate", 0),
            "diabetes_hba1c": ctx.get("hba1c_control_rate", 0),
            "preventive_screenings": ctx.get("screening_rate", 0),
            "medication_adherence": ctx.get("adherence_rate", 0),
        }

        operational = {
            "avg_response_time_min": ctx.get("avg_response_time", 0),
            "readmission_rate": ctx.get("readmission_rate", 0),
            "patient_satisfaction": ctx.get("satisfaction_score", 0),
        }

        # Score each measure against targets
        targets = {"bp_control": 0.70, "diabetes_hba1c": 0.65, "preventive_screenings": 0.80, "medication_adherence": 0.80}
        gaps = []
        for measure, target in targets.items():
            actual = hedis.get(measure, 0)
            if actual < target:
                gaps.append({"measure": measure, "actual": actual, "target": target, "gap": round(target - actual, 3)})

        result = {
            "hedis_measures": hedis,
            "operational_metrics": operational,
            "quality_gaps": sorted(gaps, key=lambda g: g["gap"], reverse=True),
            "overall_quality_score": round(sum(hedis.values()) / max(len(hedis), 1), 3),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        # LLM-powered quality improvement recommendations
        try:
            import json
            prompt = (
                f"Analyze these population health quality metrics and provide actionable improvement recommendations.\n\n"
                f"HEDIS Measures: {json.dumps(hedis)}\n"
                f"Operational: {json.dumps(operational)}\n"
                f"Quality Gaps: {json.dumps(gaps)}\n\n"
                f"Provide 3-5 specific, evidence-based recommendations to close the quality gaps. "
                f"Focus on the largest gaps first. Be concise."
            )
            llm_resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a population health analytics expert. Provide actionable quality "
                    "improvement recommendations based on HEDIS measures and operational metrics. "
                    "Be specific and evidence-based."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["llm_recommendations"] = llm_resp.content
        except Exception as exc:
            logger.warning("population_health.llm_failed", error=str(exc))

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.80,
            rationale=f"Quality metrics: {len(gaps)} gaps identified, overall score {result['overall_quality_score']:.2f}",
        )

    def _cohort_analysis(self, input_data: AgentInput) -> AgentOutput:
        """Basic cohort analysis on population data."""
        ctx = input_data.context
        criteria = ctx.get("criteria", {})
        matched_count = ctx.get("matched_count", 0)
        total = ctx.get("total_patients", 0)

        result = {
            "cohort_criteria": criteria,
            "matched_patients": matched_count,
            "total_patients": total,
            "match_rate": round(matched_count / max(total, 1), 3),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.78,
            rationale=f"Cohort analysis: {matched_count}/{total} matched",
        )

    @staticmethod
    def _safe_avg(values: list) -> float:
        valid = [v for v in values if v is not None]
        return round(sum(valid) / len(valid), 2) if valid else 0

    @staticmethod
    def _pct(subset: list, total: int) -> float:
        return round(len(subset) / max(total, 1) * 100, 1)
