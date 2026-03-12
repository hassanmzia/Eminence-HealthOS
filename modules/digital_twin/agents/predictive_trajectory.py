"""
Eminence HealthOS — Predictive Trajectory Agent (#65)
Layer 5 (Measurement): Forecasts health outcomes 30/60/90 days out based on
current trends, identifies improving/stable/declining patterns, and estimates
deterioration risk and clinical milestone timelines.
"""

from __future__ import annotations

import math
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

# Clinical thresholds for deterioration events
DETERIORATION_THRESHOLDS: dict[str, dict[str, Any]] = {
    "bp_systolic": {"critical_high": 180.0, "high": 160.0, "normal_high": 140.0},
    "bp_diastolic": {"critical_high": 120.0, "high": 100.0, "normal_high": 90.0},
    "hba1c": {"critical_high": 10.0, "high": 9.0, "normal_high": 7.0},
    "heart_rate": {"critical_high": 120.0, "high": 100.0, "critical_low": 40.0, "low": 50.0},
    "egfr": {"critical_low": 15.0, "low": 30.0, "normal_low": 60.0},
    "cholesterol_ldl": {"critical_high": 190.0, "high": 160.0, "normal_high": 130.0},
    "bmi": {"critical_high": 40.0, "high": 35.0, "normal_high": 30.0},
}

# Clinical target values for milestone prediction
CLINICAL_TARGETS: dict[str, float] = {
    "bp_systolic": 130.0,
    "bp_diastolic": 80.0,
    "hba1c": 7.0,
    "cholesterol_ldl": 100.0,
    "bmi": 25.0,
    "egfr": 60.0,
    "heart_rate": 72.0,
}

PROJECTION_DAYS = [30, 60, 90]


class PredictiveTrajectoryAgent(BaseAgent):
    name = "predictive_trajectory"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = (
        "Forecasts health outcomes 30/60/90 days out based on current trends, "
        "identifies trajectory patterns, and estimates deterioration risk"
    )
    min_confidence = 0.55

    async def process(self, input_data: AgentInput) -> AgentOutput:
        action = input_data.context.get("action", "forecast")

        if action == "forecast":
            return self._forecast(input_data)
        elif action == "trend_analysis":
            return self._trend_analysis(input_data)
        elif action == "deterioration_risk":
            return self._deterioration_risk(input_data)
        elif action == "milestone_prediction":
            return self._milestone_prediction(input_data)
        elif action == "population_trajectory":
            return self._population_trajectory(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unsupported action '{action}' requested",
                status=AgentStatus.FAILED,
            )

    # ── forecast ──────────────────────────────────────────────────────────────

    def _forecast(self, input_data: AgentInput) -> AgentOutput:
        """Project 30/60/90-day values using linear extrapolation with confidence intervals."""
        ctx = input_data.context
        current_vitals = ctx.get("current_vitals", {})
        history = ctx.get("history", [])

        if not current_vitals:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No current vitals provided"},
                confidence=0.0,
                rationale="Cannot forecast without current vital data",
                status=AgentStatus.FAILED,
            )

        # Compute per-metric slopes from history (daily rate of change)
        slopes = self._compute_slopes(current_vitals, history)

        projections: list[dict[str, Any]] = []
        for days in PROJECTION_DAYS:
            projected: dict[str, Any] = {}
            for metric, current in current_vitals.items():
                if not isinstance(current, (int, float)):
                    projected[metric] = current
                    continue
                slope = slopes.get(metric, 0.0)
                point_estimate = current + slope * days
                # Confidence interval widens with projection horizon
                uncertainty = abs(slope) * days * 0.3 + abs(current) * 0.02 * (days / 30)
                projected[metric] = {
                    "value": round(point_estimate, 2),
                    "lower_ci": round(point_estimate - uncertainty, 2),
                    "upper_ci": round(point_estimate + uncertainty, 2),
                    "daily_slope": round(slope, 4),
                }

            projections.append({
                "day": days,
                "projected_vitals": projected,
            })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
                "current_vitals": current_vitals,
                "projections": projections,
                "slopes": {k: round(v, 4) for k, v in slopes.items()},
                "history_points_used": len(history),
                "forecasted_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.78 if history else 0.60,
            rationale=(
                f"Forecasted {len(current_vitals)} metrics over 30/60/90 days "
                f"using {len(history)} historical data points"
            ),
        )

    # ── trend_analysis ────────────────────────────────────────────────────────

    def _trend_analysis(self, input_data: AgentInput) -> AgentOutput:
        """Identify improving/stable/declining trends per metric."""
        ctx = input_data.context
        current_vitals = ctx.get("current_vitals", {})
        history = ctx.get("history", [])

        if not current_vitals:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No current vitals provided"},
                confidence=0.0,
                rationale="Cannot analyze trends without current vitals",
                status=AgentStatus.FAILED,
            )

        slopes = self._compute_slopes(current_vitals, history)

        trends: dict[str, dict[str, Any]] = {}
        summary_counts = {"improving": 0, "stable": 0, "declining": 0}

        for metric, current in current_vitals.items():
            if not isinstance(current, (int, float)):
                continue
            slope = slopes.get(metric, 0.0)
            direction = self._classify_trend(metric, slope, current)
            magnitude = self._trend_magnitude(slope, current)

            trends[metric] = {
                "current_value": current,
                "daily_slope": round(slope, 4),
                "monthly_change": round(slope * 30, 2),
                "direction": direction,
                "magnitude": magnitude,
            }
            summary_counts[direction] = summary_counts.get(direction, 0) + 1

        overall = "stable"
        if summary_counts["declining"] > summary_counts["improving"]:
            overall = "declining"
        elif summary_counts["improving"] > summary_counts["declining"]:
            overall = "improving"

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
                "trends": trends,
                "summary": summary_counts,
                "overall_trajectory": overall,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.80 if history else 0.60,
            rationale=(
                f"Trend analysis: {summary_counts['improving']} improving, "
                f"{summary_counts['stable']} stable, {summary_counts['declining']} declining — "
                f"overall trajectory: {overall}"
            ),
        )

    # ── deterioration_risk ────────────────────────────────────────────────────

    def _deterioration_risk(self, input_data: AgentInput) -> AgentOutput:
        """Calculate probability of clinical deterioration events."""
        ctx = input_data.context
        current_vitals = ctx.get("current_vitals", {})
        history = ctx.get("history", [])
        conditions = ctx.get("conditions", [])
        age = ctx.get("age", 50)

        if not current_vitals:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No current vitals provided"},
                confidence=0.0,
                rationale="Cannot assess deterioration risk without vitals",
                status=AgentStatus.FAILED,
            )

        slopes = self._compute_slopes(current_vitals, history)

        # Assess individual deterioration event risks
        event_risks: dict[str, dict[str, Any]] = {}

        # Hospitalization risk
        hosp_risk = self._calculate_event_risk(
            current_vitals, slopes, conditions, age, event_type="hospitalization",
        )
        event_risks["hospitalization"] = hosp_risk

        # ED visit risk
        ed_risk = self._calculate_event_risk(
            current_vitals, slopes, conditions, age, event_type="ed_visit",
        )
        event_risks["ed_visit"] = ed_risk

        # Acute exacerbation risk
        acute_risk = self._calculate_event_risk(
            current_vitals, slopes, conditions, age, event_type="acute_exacerbation",
        )
        event_risks["acute_exacerbation"] = acute_risk

        # Medication adverse event risk
        med_risk = self._calculate_event_risk(
            current_vitals, slopes, conditions, age, event_type="medication_adverse_event",
        )
        event_risks["medication_adverse_event"] = med_risk

        # Overall composite risk
        individual_probs = [e["probability_30d"] for e in event_risks.values()]
        composite_30d = 1.0 - math.prod(1.0 - p for p in individual_probs)

        risk_level = (
            "critical" if composite_30d > 0.5
            else "high" if composite_30d > 0.3
            else "moderate" if composite_30d > 0.15
            else "low"
        )

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
                "event_risks": event_risks,
                "composite_risk_30d": round(composite_30d, 4),
                "risk_level": risk_level,
                "contributing_factors": self._identify_contributing_factors(
                    current_vitals, slopes,
                ),
                "assessed_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.75,
            rationale=(
                f"Deterioration risk assessment: composite 30-day risk = "
                f"{composite_30d:.1%} ({risk_level})"
            ),
        )

    # ── milestone_prediction ──────────────────────────────────────────────────

    def _milestone_prediction(self, input_data: AgentInput) -> AgentOutput:
        """Predict when patient will reach clinical milestones."""
        ctx = input_data.context
        current_vitals = ctx.get("current_vitals", {})
        history = ctx.get("history", [])
        custom_targets = ctx.get("targets", {})

        if not current_vitals:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No current vitals provided"},
                confidence=0.0,
                rationale="Cannot predict milestones without current vitals",
                status=AgentStatus.FAILED,
            )

        slopes = self._compute_slopes(current_vitals, history)
        targets = {**CLINICAL_TARGETS, **custom_targets}

        milestones: list[dict[str, Any]] = []
        for metric, current in current_vitals.items():
            if not isinstance(current, (int, float)):
                continue
            target = targets.get(metric)
            if target is None:
                continue

            slope = slopes.get(metric, 0.0)
            distance = target - current

            # Determine if we're moving toward or away from target
            if slope == 0:
                days_to_target = None
                on_track = abs(distance) < abs(current) * 0.05
                status = "at_target" if on_track else "stalled"
            elif (distance > 0 and slope > 0) or (distance < 0 and slope < 0):
                # Moving toward target
                days_to_target = abs(distance / slope)
                on_track = True
                status = "on_track"
            else:
                # Moving away from target
                days_to_target = None
                on_track = False
                status = "off_track"

            milestones.append({
                "metric": metric,
                "current_value": current,
                "target_value": target,
                "distance_to_target": round(distance, 2),
                "daily_slope": round(slope, 4),
                "estimated_days_to_target": round(days_to_target, 0) if days_to_target is not None else None,
                "on_track": on_track,
                "status": status,
            })

        on_track_count = sum(1 for m in milestones if m["on_track"])

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
                "milestones": milestones,
                "on_track_count": on_track_count,
                "total_milestones": len(milestones),
                "predicted_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.72 if history else 0.55,
            rationale=(
                f"Milestone prediction: {on_track_count}/{len(milestones)} metrics "
                f"on track to reach clinical targets"
            ),
        )

    # ── population_trajectory ─────────────────────────────────────────────────

    def _population_trajectory(self, input_data: AgentInput) -> AgentOutput:
        """Aggregate trajectories for a cohort of patients."""
        ctx = input_data.context
        cohort = ctx.get("cohort", [])
        metric = ctx.get("metric", "bp_systolic")

        if not cohort:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": "No cohort data provided"},
                confidence=0.0,
                rationale="Cannot compute population trajectory without cohort data",
                status=AgentStatus.FAILED,
            )

        # Aggregate current values and slopes for the metric
        values: list[float] = []
        slopes: list[float] = []
        improving_count = 0
        declining_count = 0
        stable_count = 0

        for patient in cohort:
            vitals = patient.get("current_vitals", {})
            history = patient.get("history", [])
            val = vitals.get(metric)
            if val is None or not isinstance(val, (int, float)):
                continue
            values.append(val)
            patient_slopes = self._compute_slopes(vitals, history)
            slope = patient_slopes.get(metric, 0.0)
            slopes.append(slope)

            direction = self._classify_trend(metric, slope, val)
            if direction == "improving":
                improving_count += 1
            elif direction == "declining":
                declining_count += 1
            else:
                stable_count += 1

        if not values:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"No valid {metric} data in cohort"},
                confidence=0.0,
                rationale=f"No patients in cohort have valid {metric} values",
                status=AgentStatus.FAILED,
            )

        n = len(values)
        mean_val = sum(values) / n
        std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / n) if n > 1 else 0.0
        mean_slope = sum(slopes) / n
        median_val = sorted(values)[n // 2]

        # Project population averages
        pop_projections: list[dict[str, Any]] = []
        for days in PROJECTION_DAYS:
            projected_mean = mean_val + mean_slope * days
            pop_projections.append({
                "day": days,
                "projected_mean": round(projected_mean, 2),
                "projected_std": round(std_val * (1 + 0.01 * days / 30), 2),
            })

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "metric": metric,
                "cohort_size": n,
                "current_mean": round(mean_val, 2),
                "current_median": round(median_val, 2),
                "current_std": round(std_val, 2),
                "mean_daily_slope": round(mean_slope, 4),
                "trajectory_distribution": {
                    "improving": improving_count,
                    "stable": stable_count,
                    "declining": declining_count,
                },
                "population_projections": pop_projections,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
            confidence=0.80 if n >= 30 else 0.65,
            rationale=(
                f"Population trajectory for {metric}: {n} patients, "
                f"mean={mean_val:.1f}, slope={mean_slope:+.4f}/day — "
                f"{improving_count} improving, {stable_count} stable, {declining_count} declining"
            ),
        )

    # ── Internal Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_slopes(
        current_vitals: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> dict[str, float]:
        """
        Compute daily rate of change per metric using linear regression over history.
        Falls back to zero slope when insufficient history is available.
        """
        slopes: dict[str, float] = {}

        if not history:
            for metric in current_vitals:
                if isinstance(current_vitals[metric], (int, float)):
                    slopes[metric] = 0.0
            return slopes

        for metric in current_vitals:
            if not isinstance(current_vitals[metric], (int, float)):
                continue

            data_points: list[tuple[float, float]] = []
            for idx, entry in enumerate(history):
                val = entry.get(metric)
                days_ago = entry.get("days_ago", len(history) - idx)
                if val is not None and isinstance(val, (int, float)):
                    data_points.append((float(-days_ago), float(val)))

            # Add current as day 0
            data_points.append((0.0, float(current_vitals[metric])))

            if len(data_points) < 2:
                slopes[metric] = 0.0
                continue

            # Simple linear regression
            n = len(data_points)
            sum_x = sum(p[0] for p in data_points)
            sum_y = sum(p[1] for p in data_points)
            sum_xy = sum(p[0] * p[1] for p in data_points)
            sum_x2 = sum(p[0] ** 2 for p in data_points)

            denom = n * sum_x2 - sum_x ** 2
            if abs(denom) < 1e-10:
                slopes[metric] = 0.0
            else:
                slopes[metric] = (n * sum_xy - sum_x * sum_y) / denom

        return slopes

    @staticmethod
    def _classify_trend(metric: str, slope: float, current: float) -> str:
        """Classify a metric trend as improving, stable, or declining."""
        # For most metrics, lower is better (bp, hba1c, ldl, bmi)
        # For egfr, higher is better
        higher_is_better = {"egfr"}
        threshold = abs(current) * 0.001 if current != 0 else 0.01

        if abs(slope) < threshold:
            return "stable"

        if metric in higher_is_better:
            return "improving" if slope > 0 else "declining"
        else:
            return "improving" if slope < 0 else "declining"

    @staticmethod
    def _trend_magnitude(slope: float, current: float) -> str:
        """Classify trend magnitude as minimal, moderate, or significant."""
        if current == 0:
            return "minimal"
        pct_change_monthly = abs(slope * 30 / current) * 100
        if pct_change_monthly > 5.0:
            return "significant"
        elif pct_change_monthly > 1.0:
            return "moderate"
        return "minimal"

    def _calculate_event_risk(
        self,
        current_vitals: dict[str, Any],
        slopes: dict[str, float],
        conditions: list[str],
        age: int,
        event_type: str,
    ) -> dict[str, Any]:
        """Calculate the probability of a specific deterioration event within 30 days."""
        base_risk = 0.05  # 5% baseline

        # Age adjustment
        if age > 75:
            base_risk += 0.08
        elif age > 65:
            base_risk += 0.05
        elif age > 55:
            base_risk += 0.02

        # Condition adjustments
        high_risk_conditions = {"chf", "copd", "ckd", "diabetes", "heart_failure"}
        condition_set = {c.lower() for c in conditions}
        condition_overlap = condition_set & high_risk_conditions
        base_risk += len(condition_overlap) * 0.04

        # Vital-based risk adjustments
        risk_adjustment = 0.0
        for metric, thresholds in DETERIORATION_THRESHOLDS.items():
            val = current_vitals.get(metric)
            if val is None or not isinstance(val, (int, float)):
                continue

            if "critical_high" in thresholds and val >= thresholds["critical_high"]:
                risk_adjustment += 0.12
            elif "high" in thresholds and val >= thresholds["high"]:
                risk_adjustment += 0.06
            elif "normal_high" in thresholds and val >= thresholds["normal_high"]:
                risk_adjustment += 0.02

            if "critical_low" in thresholds and val <= thresholds["critical_low"]:
                risk_adjustment += 0.12
            elif "low" in thresholds and val <= thresholds["low"]:
                risk_adjustment += 0.06
            elif "normal_low" in thresholds and val <= thresholds["normal_low"]:
                risk_adjustment += 0.02

        # Worsening trends increase risk
        for metric, slope in slopes.items():
            direction = self._classify_trend(metric, slope, current_vitals.get(metric, 0))
            if direction == "declining":
                risk_adjustment += 0.02

        # Event-type specific multipliers
        multipliers = {
            "hospitalization": 1.0,
            "ed_visit": 1.3,
            "acute_exacerbation": 0.9,
            "medication_adverse_event": 0.6,
        }
        multiplier = multipliers.get(event_type, 1.0)

        probability = min(0.95, max(0.01, (base_risk + risk_adjustment) * multiplier))

        return {
            "event_type": event_type,
            "probability_30d": round(probability, 4),
            "risk_level": (
                "critical" if probability > 0.5
                else "high" if probability > 0.3
                else "moderate" if probability > 0.15
                else "low"
            ),
        }

    @staticmethod
    def _identify_contributing_factors(
        current_vitals: dict[str, Any],
        slopes: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Identify the top contributing factors to deterioration risk."""
        factors: list[dict[str, Any]] = []

        for metric, thresholds in DETERIORATION_THRESHOLDS.items():
            val = current_vitals.get(metric)
            if val is None or not isinstance(val, (int, float)):
                continue

            concern = None
            if "critical_high" in thresholds and val >= thresholds["critical_high"]:
                concern = "critically_elevated"
            elif "high" in thresholds and val >= thresholds["high"]:
                concern = "elevated"
            elif "critical_low" in thresholds and val <= thresholds["critical_low"]:
                concern = "critically_low"
            elif "low" in thresholds and val <= thresholds["low"]:
                concern = "low"

            if concern:
                factors.append({
                    "metric": metric,
                    "current_value": val,
                    "concern": concern,
                    "trend_slope": round(slopes.get(metric, 0.0), 4),
                })

        factors.sort(key=lambda f: abs(slopes.get(f["metric"], 0.0)), reverse=True)
        return factors
