"""
Eminence HealthOS — Adherence Monitoring Agent
Layer 2 (Interpretation): Tracks patient compliance with monitoring schedules
and care plan adherence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    AlertRequest,
    AlertType,
    NormalizedVital,
    PipelineState,
    Severity,
)


# Expected submission frequency per vital type (hours between readings)
EXPECTED_FREQUENCY: dict[str, int] = {
    "heart_rate": 4,
    "blood_pressure": 12,
    "glucose": 8,
    "spo2": 6,
    "weight": 24,
    "temperature": 12,
    "respiratory_rate": 8,
}


class AdherenceMonitoringAgent(BaseAgent):
    name = "adherence_monitoring"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Monitors patient adherence to vital sign submission schedules"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        vitals = input_data.context.get("normalized_vitals", [])
        adherence = self._compute_adherence_raw(vitals)

        return self.build_output(
            trace_id=input_data.trace_id,
            result=adherence,
            confidence=0.9,
            rationale=f"Overall adherence: {adherence.get('overall_rate', 0):.0%}",
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Check adherence and generate alerts for non-compliance."""
        adherence_data = self._compute_adherence(state.normalized_vitals)

        # Store adherence data in patient context
        state.patient_context["adherence"] = adherence_data

        # Generate alerts for poor adherence
        for vital_type, info in adherence_data.get("by_type", {}).items():
            if info["status"] == "non_compliant":
                state.alert_requests.append(
                    AlertRequest(
                        patient_id=state.patient_id,
                        org_id=state.org_id,
                        alert_type=AlertType.PATIENT_NOTIFICATION,
                        priority=Severity.MODERATE,
                        message=f"Patient has not submitted {vital_type} readings for "
                        f"{info['hours_since_last']:.0f} hours. "
                        f"Expected every {info['expected_hours']} hours.",
                    )
                )

        state.executed_agents.append(self.name)
        return state

    def _compute_adherence(self, vitals: list[NormalizedVital]) -> dict[str, Any]:
        """Compute adherence metrics from normalized vitals."""
        now = datetime.now(timezone.utc)
        by_type: dict[str, list[datetime]] = {}

        for v in vitals:
            vt = v.vital_type.value
            by_type.setdefault(vt, []).append(v.recorded_at)

        type_adherence: dict[str, dict[str, Any]] = {}
        compliant_count = 0
        total_types = 0

        for vital_type, expected_hours in EXPECTED_FREQUENCY.items():
            total_types += 1
            timestamps = sorted(by_type.get(vital_type, []))

            if not timestamps:
                type_adherence[vital_type] = {
                    "status": "no_data",
                    "last_reading": None,
                    "hours_since_last": None,
                    "expected_hours": expected_hours,
                    "submission_count": 0,
                    "compliance_rate": 0.0,
                }
                continue

            last_ts = timestamps[-1]
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)

            hours_since = (now - last_ts).total_seconds() / 3600

            is_compliant = hours_since <= expected_hours * 1.5
            if is_compliant:
                compliant_count += 1

            # Compute compliance rate over available data
            if len(timestamps) >= 2:
                total_span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
                expected_submissions = max(1, total_span / expected_hours)
                rate = min(1.0, len(timestamps) / expected_submissions)
            else:
                rate = 1.0 if is_compliant else 0.5

            type_adherence[vital_type] = {
                "status": "compliant" if is_compliant else "non_compliant",
                "last_reading": last_ts.isoformat(),
                "hours_since_last": round(hours_since, 1),
                "expected_hours": expected_hours,
                "submission_count": len(timestamps),
                "compliance_rate": round(rate, 2),
            }

        overall_rate = compliant_count / total_types if total_types > 0 else 0.0

        return {
            "overall_rate": round(overall_rate, 2),
            "compliant_types": compliant_count,
            "total_types": total_types,
            "by_type": type_adherence,
        }

    def _compute_adherence_raw(self, vitals: list[dict]) -> dict[str, Any]:
        """Compute adherence from raw dict-format vitals."""
        now = datetime.now(timezone.utc)
        by_type: dict[str, list[str]] = {}

        for v in vitals:
            vt = v.get("vital_type", "")
            ts = v.get("recorded_at", "")
            if vt and ts:
                by_type.setdefault(vt, []).append(ts)

        result = {"by_type": {}, "overall_rate": 0.0}
        compliant = 0
        total = 0

        for vt, expected in EXPECTED_FREQUENCY.items():
            total += 1
            timestamps = by_type.get(vt, [])
            if timestamps:
                compliant += 1
                result["by_type"][vt] = {
                    "submissions": len(timestamps),
                    "expected_hours": expected,
                    "status": "compliant",
                }
            else:
                result["by_type"][vt] = {
                    "submissions": 0,
                    "expected_hours": expected,
                    "status": "no_data",
                }

        result["overall_rate"] = round(compliant / total, 2) if total > 0 else 0.0
        return result
