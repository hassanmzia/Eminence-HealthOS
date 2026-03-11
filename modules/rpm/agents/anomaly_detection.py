"""
Eminence HealthOS — Anomaly Detection Agent
Layer 2 (Interpretation): Detects anomalies in vital signs using threshold,
statistical, and pattern-based methods.
"""

from __future__ import annotations

import math
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


# Clinical threshold ranges (normal values)
CLINICAL_THRESHOLDS: dict[str, dict[str, dict[str, tuple[float, float]]]] = {
    "heart_rate": {
        "normal": {"value": (60, 100)},
        "warning": {"value": (50, 120)},
        "critical": {"value": (40, 150)},
    },
    "blood_pressure": {
        "normal": {"systolic": (90, 130), "diastolic": (60, 85)},
        "warning": {"systolic": (80, 140), "diastolic": (50, 90)},
        "critical": {"systolic": (70, 180), "diastolic": (40, 120)},
    },
    "glucose": {
        "normal": {"value": (70, 140)},
        "warning": {"value": (54, 250)},
        "critical": {"value": (40, 400)},
    },
    "spo2": {
        "normal": {"value": (95, 100)},
        "warning": {"value": (90, 100)},
        "critical": {"value": (85, 100)},
    },
    "temperature": {
        "normal": {"value": (97.0, 99.5)},
        "warning": {"value": (96.0, 101.0)},
        "critical": {"value": (95.0, 104.0)},
    },
    "respiratory_rate": {
        "normal": {"value": (12, 20)},
        "warning": {"value": (10, 24)},
        "critical": {"value": (8, 30)},
    },
}


class AnomalyDetectionAgent(BaseAgent):
    name = "anomaly_detection"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Detects anomalies in patient vitals using threshold and statistical methods"
    min_confidence = 0.6

    async def process(self, input_data: AgentInput) -> AgentOutput:
        vitals = input_data.context.get("normalized_vitals", [])
        anomalies = self._check_thresholds_raw(vitals)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
            },
            confidence=0.9 if anomalies else 0.95,
            rationale=f"Detected {len(anomalies)} anomalies across {len(vitals)} readings",
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Detect anomalies from normalized vitals."""
        anomalies: list[AnomalyDetection] = []

        for vital in state.normalized_vitals:
            if not vital.is_valid:
                continue

            threshold_anomalies = self._check_thresholds(vital, state)
            anomalies.extend(threshold_anomalies)

        # Statistical anomaly detection across multiple readings
        stat_anomalies = self._statistical_detection(state.normalized_vitals, state)
        anomalies.extend(stat_anomalies)

        state.anomalies = anomalies
        state.executed_agents.append(self.name)
        return state

    def _check_thresholds(
        self, vital: NormalizedVital, state: PipelineState
    ) -> list[AnomalyDetection]:
        """Check a single vital against clinical thresholds."""
        anomalies: list[AnomalyDetection] = []
        thresholds = CLINICAL_THRESHOLDS.get(vital.vital_type.value)

        if not thresholds:
            return anomalies

        severity = self._determine_severity(vital.vital_type.value, vital.value, thresholds)

        if severity:
            description = self._build_description(vital, severity)
            anomalies.append(
                AnomalyDetection(
                    patient_id=vital.patient_id,
                    org_id=vital.org_id,
                    anomaly_type="threshold_breach",
                    vital_type=vital.vital_type,
                    severity=severity,
                    description=description,
                    confidence_score=0.95,
                    detected_by=self.name,
                )
            )

        return anomalies

    def _determine_severity(
        self,
        vital_type: str,
        value: dict[str, Any],
        thresholds: dict[str, dict[str, tuple[float, float]]],
    ) -> Severity | None:
        """Determine severity based on how far outside thresholds the value is."""
        # Check critical first, then warning, then normal
        for severity_name, severity_enum in [
            ("critical", Severity.CRITICAL),
            ("warning", Severity.HIGH),
            ("normal", Severity.MODERATE),
        ]:
            ranges = thresholds.get(severity_name, {})
            for key, (low, high) in ranges.items():
                val = value.get(key)
                if val is None:
                    continue
                try:
                    fval = float(val)
                except (TypeError, ValueError):
                    continue

                if severity_name == "critical" and (fval < low or fval > high):
                    return Severity.CRITICAL
                elif severity_name == "warning" and (fval < low or fval > high):
                    return Severity.HIGH
                elif severity_name == "normal" and (fval < low or fval > high):
                    return Severity.MODERATE

        return None

    def _statistical_detection(
        self, vitals: list[NormalizedVital], state: PipelineState
    ) -> list[AnomalyDetection]:
        """Detect statistical anomalies (sudden changes between consecutive readings)."""
        anomalies: list[AnomalyDetection] = []

        # Group vitals by type
        by_type: dict[str, list[NormalizedVital]] = {}
        for v in vitals:
            by_type.setdefault(v.vital_type.value, []).append(v)

        for vital_type, readings in by_type.items():
            if len(readings) < 2:
                continue

            # Sort by recorded_at
            readings.sort(key=lambda x: x.recorded_at)

            # Check for sudden changes
            for i in range(1, len(readings)):
                prev = readings[i - 1]
                curr = readings[i]

                change = self._calc_change_pct(prev.value, curr.value)
                if change and change > 30:  # >30% change between consecutive readings
                    anomalies.append(
                        AnomalyDetection(
                            patient_id=curr.patient_id,
                            org_id=curr.org_id,
                            anomaly_type="sudden_change",
                            vital_type=curr.vital_type,
                            severity=Severity.HIGH if change > 50 else Severity.MODERATE,
                            description=f"Sudden {change:.0f}% change in {vital_type}",
                            confidence_score=min(0.95, change / 100),
                            detected_by=self.name,
                        )
                    )

        return anomalies

    def _calc_change_pct(self, prev: dict[str, Any], curr: dict[str, Any]) -> float | None:
        """Calculate percentage change between two readings."""
        prev_val = prev.get("value") or prev.get("systolic")
        curr_val = curr.get("value") or curr.get("systolic")

        if prev_val is None or curr_val is None:
            return None
        try:
            pf, cf = float(prev_val), float(curr_val)
            if pf == 0:
                return None
            return abs((cf - pf) / pf) * 100
        except (TypeError, ValueError):
            return None

    def _build_description(self, vital: NormalizedVital, severity: Severity) -> str:
        """Build a human-readable anomaly description."""
        value_str = ", ".join(f"{k}={v}" for k, v in vital.value.items())
        return (
            f"{severity.value.upper()} anomaly: {vital.vital_type.value} "
            f"reading ({value_str} {vital.unit}) outside {severity.value} range"
        )

    def _check_thresholds_raw(self, vitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Check thresholds for raw dict-format vitals."""
        results = []
        for v in vitals:
            vital_type = v.get("vital_type", "")
            value = v.get("value", {})
            thresholds = CLINICAL_THRESHOLDS.get(vital_type)
            if not thresholds:
                continue
            severity = self._determine_severity(vital_type, value, thresholds)
            if severity:
                results.append({
                    "vital_type": vital_type,
                    "value": value,
                    "severity": severity.value,
                    "type": "threshold_breach",
                })
        return results
