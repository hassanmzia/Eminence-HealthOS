"""
Eminence HealthOS — Device Ingestion Agent
Layer 1 (Sensing): Collects and validates data from medical devices (wearables, home monitors).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from platform.agents.base import BaseAgent
from platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    PipelineState,
    VitalReading,
    VitalType,
)


# Valid ranges for data quality scoring
VALID_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "heart_rate": {"value": (20, 300)},
    "blood_pressure": {"systolic": (40, 300), "diastolic": (20, 200)},
    "glucose": {"value": (20, 600)},
    "spo2": {"value": (50, 100)},
    "weight": {"value": (0.5, 500)},
    "temperature": {"value": (85, 115)},  # Fahrenheit
    "respiratory_rate": {"value": (4, 60)},
}


class DeviceIngestionAgent(BaseAgent):
    name = "device_ingestion"
    tier = AgentTier.SENSING
    version = "1.0.0"
    description = "Collects, validates, and quality-scores data from medical devices"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        raw_readings = input_data.context.get("raw_vitals", [])

        if not raw_readings:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"ingested": 0, "rejected": 0},
                confidence=1.0,
                rationale="No vital readings to ingest",
            )

        ingested = []
        rejected = []

        for reading in raw_readings:
            quality = self._score_quality(reading)

            if quality < 0.3:
                rejected.append({
                    "reading": reading,
                    "quality": quality,
                    "reason": "Quality score below threshold",
                })
                continue

            reading["quality_score"] = quality
            ingested.append(reading)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "ingested": len(ingested),
                "rejected": len(rejected),
                "readings": ingested,
                "rejections": rejected,
            },
            confidence=0.95 if not rejected else 0.8,
            rationale=f"Ingested {len(ingested)} readings, rejected {len(rejected)}",
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Specialized pipeline handler that populates raw_vitals."""
        raw_data = state.patient_context.get("raw_vitals", [])
        vitals: list[VitalReading] = []

        for rd in raw_data:
            try:
                vital = VitalReading(
                    patient_id=state.patient_id,
                    org_id=state.org_id,
                    device_id=rd.get("device_id"),
                    vital_type=VitalType(rd["vital_type"]),
                    value=rd["value"],
                    unit=rd.get("unit", ""),
                    recorded_at=datetime.fromisoformat(rd["recorded_at"])
                    if isinstance(rd["recorded_at"], str)
                    else rd["recorded_at"],
                    source=rd.get("source", "wearable"),
                    quality_score=self._score_quality(rd),
                )
                vitals.append(vital)
            except (KeyError, ValueError):
                continue

        state.raw_vitals = vitals
        state.executed_agents.append(self.name)
        return state

    def _score_quality(self, reading: dict[str, Any]) -> float:
        """Score the quality of a vital reading (0.0 to 1.0)."""
        score = 1.0
        vital_type = reading.get("vital_type", "")
        value = reading.get("value", {})

        # Check if vital type is recognized
        ranges = VALID_RANGES.get(vital_type)
        if not ranges:
            return 0.7  # Unknown type, moderate quality

        # Check value ranges
        for key, (low, high) in ranges.items():
            val = value.get(key) if isinstance(value, dict) else value
            if val is None:
                score -= 0.3
                continue
            try:
                val = float(val)
                if val < low or val > high:
                    score -= 0.4
                elif val < low * 1.1 or val > high * 0.9:
                    score -= 0.1  # Near boundary
            except (TypeError, ValueError):
                score -= 0.5

        # Check timestamp freshness
        recorded_at = reading.get("recorded_at")
        if recorded_at:
            try:
                if isinstance(recorded_at, str):
                    ts = datetime.fromisoformat(recorded_at)
                else:
                    ts = recorded_at
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if age_hours > 24:
                    score -= 0.2
            except (ValueError, TypeError):
                score -= 0.1

        return max(0.0, min(1.0, score))
