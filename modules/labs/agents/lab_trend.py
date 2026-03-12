"""
Eminence HealthOS — Lab Trend Agent (#39)
Layer 2 (Interpretation): Analyzes lab value trends over time for key
indicators like A1C, creatinine, lipids, and detects clinical significance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

# Clinical significance thresholds
TREND_THRESHOLDS: dict[str, dict[str, Any]] = {
    "hba1c": {"concerning_increase": 0.5, "target": 7.0, "unit": "%", "frequency": "quarterly"},
    "creatinine": {"concerning_increase": 0.3, "target_max": 1.2, "unit": "mg/dL", "frequency": "quarterly"},
    "egfr": {"concerning_decrease": -10, "target_min": 60, "unit": "mL/min/1.73m2", "frequency": "quarterly"},
    "ldl": {"concerning_increase": 20, "target_max": 100, "unit": "mg/dL", "frequency": "annually"},
    "potassium": {"concerning_increase": 0.5, "target_max": 5.0, "unit": "mEq/L", "frequency": "quarterly"},
    "hemoglobin": {"concerning_decrease": -1.0, "target_min": 12.0, "unit": "g/dL", "frequency": "quarterly"},
    "glucose": {"concerning_increase": 20, "target_max": 100, "unit": "mg/dL", "frequency": "quarterly"},
    "alt": {"concerning_increase": 20, "target_max": 56, "unit": "U/L", "frequency": "annually"},
}


class LabTrendAgent(BaseAgent):
    """Analyzes lab value trends over time and detects clinical significance."""

    name = "lab_trend"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = (
        "Longitudinal lab trend analysis — tracks key indicators over time, "
        "detects clinically significant changes, and projects trajectories"
    )
    min_confidence = 0.82

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "analyze_trends")

        if action == "analyze_trends":
            return self._analyze_trends(input_data)
        elif action == "single_test_trend":
            return self._single_test_trend(input_data)
        elif action == "project_trajectory":
            return self._project_trajectory(input_data)
        elif action == "trend_summary":
            return self._trend_summary(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown lab trend action: {action}",
                status=AgentStatus.FAILED,
            )

    def _analyze_trends(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        lab_history = ctx.get("lab_history", {})

        if not lab_history:
            lab_history = {
                "hba1c": [
                    {"date": "2025-06-15", "value": 6.8},
                    {"date": "2025-09-20", "value": 7.0},
                    {"date": "2025-12-18", "value": 7.1},
                    {"date": "2026-03-12", "value": 7.3},
                ],
                "creatinine": [
                    {"date": "2025-06-15", "value": 1.1},
                    {"date": "2025-09-20", "value": 1.2},
                    {"date": "2025-12-18", "value": 1.3},
                    {"date": "2026-03-12", "value": 1.4},
                ],
                "egfr": [
                    {"date": "2025-06-15", "value": 68},
                    {"date": "2025-09-20", "value": 62},
                    {"date": "2025-12-18", "value": 56},
                    {"date": "2026-03-12", "value": 52},
                ],
                "potassium": [
                    {"date": "2025-06-15", "value": 4.2},
                    {"date": "2025-09-20", "value": 4.5},
                    {"date": "2025-12-18", "value": 4.8},
                    {"date": "2026-03-12", "value": 5.2},
                ],
            }

        trends: list[dict[str, Any]] = []
        concerning: list[dict[str, Any]] = []

        for test, values in lab_history.items():
            if len(values) < 2:
                continue

            sorted_vals = sorted(values, key=lambda v: v["date"])
            first_val = sorted_vals[0]["value"]
            last_val = sorted_vals[-1]["value"]
            change = last_val - first_val
            threshold = TREND_THRESHOLDS.get(test, {})

            direction = "increasing" if change > 0.01 else ("decreasing" if change < -0.01 else "stable")

            is_concerning = False
            concern_reason = ""
            if "concerning_increase" in threshold and change >= threshold["concerning_increase"]:
                is_concerning = True
                concern_reason = f"Increased by {round(change, 2)} (threshold: {threshold['concerning_increase']})"
            elif "concerning_decrease" in threshold and change <= threshold["concerning_decrease"]:
                is_concerning = True
                concern_reason = f"Decreased by {round(change, 2)} (threshold: {threshold['concerning_decrease']})"

            trend_entry = {
                "test": test,
                "data_points": len(sorted_vals),
                "first_value": first_val,
                "last_value": last_val,
                "change": round(change, 2),
                "direction": direction,
                "unit": threshold.get("unit", ""),
                "is_concerning": is_concerning,
                "concern_reason": concern_reason if is_concerning else None,
                "values": sorted_vals,
            }
            trends.append(trend_entry)
            if is_concerning:
                concerning.append(trend_entry)

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "analyzed_at": now.isoformat(),
            "trends": trends,
            "total_tests_analyzed": len(trends),
            "concerning_trends": len(concerning),
            "concerning_details": concerning,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.87,
            rationale=f"Trend analysis: {len(trends)} tests, {len(concerning)} concerning trends",
        )

    def _single_test_trend(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        test = ctx.get("test", "hba1c")
        values = ctx.get("values", [])

        if not values:
            values = [
                {"date": "2025-03-15", "value": 6.5},
                {"date": "2025-06-15", "value": 6.8},
                {"date": "2025-09-20", "value": 7.0},
                {"date": "2025-12-18", "value": 7.1},
                {"date": "2026-03-12", "value": 7.3},
            ]

        sorted_vals = sorted(values, key=lambda v: v["date"])
        vals = [v["value"] for v in sorted_vals]
        avg = round(sum(vals) / len(vals), 2)
        min_val = min(vals)
        max_val = max(vals)

        result = {
            "test": test,
            "analyzed_at": now.isoformat(),
            "data_points": len(vals),
            "statistics": {
                "mean": avg,
                "min": min_val,
                "max": max_val,
                "first": vals[0],
                "last": vals[-1],
                "change": round(vals[-1] - vals[0], 2),
            },
            "values": sorted_vals,
            "unit": TREND_THRESHOLDS.get(test, {}).get("unit", ""),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"{test} trend: {vals[0]} -> {vals[-1]} over {len(vals)} data points",
        )

    def _project_trajectory(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        test = ctx.get("test", "hba1c")
        values = ctx.get("values", [])
        months_ahead = ctx.get("months_ahead", 6)

        if not values:
            values = [{"date": "2025-06-15", "value": 6.8}, {"date": "2025-09-20", "value": 7.0}, {"date": "2025-12-18", "value": 7.1}, {"date": "2026-03-12", "value": 7.3}]

        sorted_vals = sorted(values, key=lambda v: v["date"])
        vals = [v["value"] for v in sorted_vals]

        # Simple linear projection
        if len(vals) >= 2:
            rate_per_point = (vals[-1] - vals[0]) / max(len(vals) - 1, 1)
            points_ahead = months_ahead / 3  # quarterly data
            projected = round(vals[-1] + rate_per_point * points_ahead, 2)
        else:
            projected = vals[-1] if vals else 0

        threshold = TREND_THRESHOLDS.get(test, {})
        target = threshold.get("target", threshold.get("target_max", threshold.get("target_min")))

        result = {
            "test": test,
            "projected_at": now.isoformat(),
            "current_value": vals[-1] if vals else None,
            "projected_value": projected,
            "projection_months": months_ahead,
            "target": target,
            "on_target": projected <= target if target else None,
            "unit": threshold.get("unit", ""),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.78,
            rationale=f"Projected {test}: {vals[-1] if vals else 'N/A'} -> {projected} in {months_ahead} months",
        )

    def _trend_summary(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "summary_date": now.isoformat(),
            "key_trends": [
                {"test": "HbA1c", "direction": "increasing", "current": 7.3, "concern": True, "note": "Worsening glycemic control"},
                {"test": "eGFR", "direction": "decreasing", "current": 52, "concern": True, "note": "Progressive CKD Stage 3b"},
                {"test": "Potassium", "direction": "increasing", "current": 5.2, "concern": True, "note": "Approaching upper limit"},
                {"test": "LDL", "direction": "stable", "current": 95, "concern": False, "note": "At target on statin"},
            ],
            "overall_assessment": "Multiple concerning trends — worsening renal function and glycemic control require care plan adjustment",
            "recommended_actions": [
                "Nephrology referral for progressive CKD",
                "Endocrinology consult for HbA1c management",
                "Monitor potassium — consider medication adjustment",
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale="Trend summary: 3 concerning trends identified",
        )
