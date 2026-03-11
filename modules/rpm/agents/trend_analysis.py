"""
Eminence HealthOS — Trend Analysis Agent
Layer 2 (Interpretation): Detects multi-day trends, patterns, and trajectory
changes in patient vital signs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    AnomalyDetection,
    NormalizedVital,
    PipelineState,
    Severity,
    VitalType,
)


class TrendAnalysisAgent(BaseAgent):
    name = "trend_analysis"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Detects multi-day trends and trajectory changes in vital signs"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        vitals = input_data.context.get("normalized_vitals", [])
        trends = self._analyze_trends_raw(vitals)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"trends": trends, "trend_count": len(trends)},
            confidence=0.85,
            rationale=f"Identified {len(trends)} trending patterns",
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Analyze trends across normalized vitals."""
        trend_anomalies = self._analyze_trends(state.normalized_vitals, state)
        state.anomalies.extend(trend_anomalies)
        state.executed_agents.append(self.name)
        return state

    def _analyze_trends(
        self, vitals: list[NormalizedVital], state: PipelineState
    ) -> list[AnomalyDetection]:
        """Analyze vital sign trends over time."""
        anomalies: list[AnomalyDetection] = []

        # Group by vital type
        by_type: dict[str, list[NormalizedVital]] = {}
        for v in vitals:
            if v.is_valid:
                by_type.setdefault(v.vital_type.value, []).append(v)

        for vital_type, readings in by_type.items():
            if len(readings) < 3:
                continue

            # Sort chronologically
            readings.sort(key=lambda x: x.recorded_at)

            # Extract numeric values
            values = self._extract_values(readings)
            if len(values) < 3:
                continue

            # Linear trend detection
            trend_direction, trend_strength = self._linear_trend(values)

            if abs(trend_strength) > 0.1:  # Meaningful trend
                severity = self._trend_severity(vital_type, trend_direction, trend_strength)
                if severity:
                    anomalies.append(
                        AnomalyDetection(
                            patient_id=readings[0].patient_id,
                            org_id=readings[0].org_id,
                            anomaly_type="trend_drift",
                            vital_type=readings[0].vital_type,
                            severity=severity,
                            description=self._describe_trend(
                                vital_type, trend_direction, trend_strength, values
                            ),
                            confidence_score=min(0.95, abs(trend_strength)),
                            detected_by=self.name,
                        )
                    )

            # Volatility detection
            volatility = self._compute_volatility(values)
            if volatility > 0.15:
                anomalies.append(
                    AnomalyDetection(
                        patient_id=readings[0].patient_id,
                        org_id=readings[0].org_id,
                        anomaly_type="pattern_anomaly",
                        vital_type=readings[0].vital_type,
                        severity=Severity.MODERATE if volatility < 0.3 else Severity.HIGH,
                        description=f"High volatility ({volatility:.1%}) in {vital_type} readings",
                        confidence_score=min(0.9, volatility * 2),
                        detected_by=self.name,
                    )
                )

        return anomalies

    def _extract_values(self, readings: list[NormalizedVital]) -> list[float]:
        """Extract the primary numeric value from each reading."""
        values: list[float] = []
        for r in readings:
            val = r.value.get("value") or r.value.get("systolic")
            if val is not None:
                try:
                    values.append(float(val))
                except (TypeError, ValueError):
                    continue
        return values

    def _linear_trend(self, values: list[float]) -> tuple[str, float]:
        """Compute linear trend direction and strength using least squares."""
        n = len(values)
        if n < 2:
            return "stable", 0.0

        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator

        # Normalize slope by mean value to get relative strength
        if y_mean == 0:
            return "stable", 0.0

        relative_slope = slope / y_mean
        direction = "increasing" if relative_slope > 0.01 else "decreasing" if relative_slope < -0.01 else "stable"

        return direction, abs(relative_slope)

    def _compute_volatility(self, values: list[float]) -> float:
        """Compute coefficient of variation as a volatility measure."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        return std_dev / abs(mean)

    def _trend_severity(
        self, vital_type: str, direction: str, strength: float
    ) -> Severity | None:
        """Determine if a trend is clinically concerning."""
        # Trends that are concerning in specific directions
        concerning_increases = {"blood_pressure", "glucose", "heart_rate", "temperature", "respiratory_rate"}
        concerning_decreases = {"spo2", "weight"}

        is_concerning = (
            (direction == "increasing" and vital_type in concerning_increases)
            or (direction == "decreasing" and vital_type in concerning_decreases)
        )

        if not is_concerning:
            return None

        if strength > 0.3:
            return Severity.HIGH
        elif strength > 0.15:
            return Severity.MODERATE
        return None

    def _describe_trend(
        self, vital_type: str, direction: str, strength: float, values: list[float]
    ) -> str:
        """Build a human-readable trend description."""
        first = values[0]
        last = values[-1]
        pct_change = ((last - first) / first * 100) if first != 0 else 0

        return (
            f"{vital_type} trending {direction} ({pct_change:+.1f}% over {len(values)} readings, "
            f"from {first:.1f} to {last:.1f}, trend strength: {strength:.2f})"
        )

    def _analyze_trends_raw(self, vitals: list[dict]) -> list[dict[str, Any]]:
        """Analyze trends from raw dict-format vitals."""
        by_type: dict[str, list[float]] = {}
        for v in vitals:
            vt = v.get("vital_type", "")
            val = v.get("value", {})
            num = val.get("value") if isinstance(val, dict) else val
            if num is not None and vt:
                by_type.setdefault(vt, []).append(float(num))

        trends = []
        for vt, vals in by_type.items():
            if len(vals) >= 3:
                direction, strength = self._linear_trend(vals)
                if abs(strength) > 0.05:
                    trends.append({
                        "vital_type": vt,
                        "direction": direction,
                        "strength": round(strength, 4),
                        "readings": len(vals),
                    })
        return trends
