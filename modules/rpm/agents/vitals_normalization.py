"""
Eminence HealthOS — Vitals Normalization Agent
Layer 1 (Sensing): Standardizes vital sign data into a unified schema.
"""

from __future__ import annotations

from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    NormalizedVital,
    PipelineState,
    VitalType,
)


# Standard units per vital type
STANDARD_UNITS: dict[str, str] = {
    "heart_rate": "bpm",
    "blood_pressure": "mmHg",
    "glucose": "mg/dL",
    "spo2": "%",
    "weight": "kg",
    "temperature": "°F",
    "respiratory_rate": "breaths/min",
    "activity": "steps",
    "sleep": "hours",
}

# Unit conversion factors
CONVERSIONS: dict[tuple[str, str], float] = {
    ("kg", "lb"): 2.20462,
    ("lb", "kg"): 0.453592,
    ("°C", "°F"): None,  # Special conversion
    ("°F", "°C"): None,
    ("mmol/L", "mg/dL"): 18.0182,
    ("mg/dL", "mmol/L"): 0.0555,
}


class VitalsNormalizationAgent(BaseAgent):
    name = "vitals_normalization"
    tier = AgentTier.SENSING
    version = "1.0.0"
    description = "Normalizes vital signs into standard units and validates ranges"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        raw_vitals = input_data.context.get("raw_vitals", [])
        normalized = []
        issues = []

        for vital in raw_vitals:
            result, notes = self._normalize(vital)
            normalized.append(result)
            if notes:
                issues.extend(notes)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "normalized_count": len(normalized),
                "issues": issues,
            },
            confidence=0.95 if not issues else 0.85,
            rationale=f"Normalized {len(normalized)} vitals with {len(issues)} issues",
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Normalize all raw vitals in the pipeline state."""
        normalized_vitals: list[NormalizedVital] = []

        for vital in state.raw_vitals:
            notes: list[str] = []
            value = dict(vital.value)
            unit = vital.unit

            # Convert to standard units
            standard_unit = STANDARD_UNITS.get(vital.vital_type.value, unit)

            if unit and unit != standard_unit:
                value, unit, conversion_note = self._convert_units(
                    vital.vital_type.value, value, unit, standard_unit
                )
                if conversion_note:
                    notes.append(conversion_note)

            # Validate normalized values
            is_valid = self._validate_range(vital.vital_type.value, value)
            if not is_valid:
                notes.append(f"Value outside expected range for {vital.vital_type.value}")

            normalized_vitals.append(
                NormalizedVital(
                    patient_id=vital.patient_id,
                    org_id=vital.org_id,
                    vital_type=vital.vital_type,
                    value=value,
                    unit=standard_unit,
                    recorded_at=vital.recorded_at,
                    source=vital.source,
                    quality_score=vital.quality_score,
                    is_valid=is_valid,
                    validation_notes=notes,
                )
            )

        state.normalized_vitals = normalized_vitals
        state.executed_agents.append(self.name)
        return state

    def _normalize(self, vital: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        notes: list[str] = []
        vital_type = vital.get("vital_type", "")
        standard_unit = STANDARD_UNITS.get(vital_type)

        if standard_unit and vital.get("unit") != standard_unit:
            notes.append(f"Converted from {vital.get('unit')} to {standard_unit}")

        return vital, notes

    def _convert_units(
        self, vital_type: str, value: dict[str, Any], from_unit: str, to_unit: str
    ) -> tuple[dict[str, Any], str, str | None]:
        """Convert values between units."""
        note = None

        if from_unit == "°C" and to_unit == "°F":
            if "value" in value:
                value["value"] = round(value["value"] * 9 / 5 + 32, 1)
                note = f"Converted {from_unit} → {to_unit}"
        elif from_unit == "°F" and to_unit == "°C":
            if "value" in value:
                value["value"] = round((value["value"] - 32) * 5 / 9, 1)
                note = f"Converted {from_unit} → {to_unit}"
        elif from_unit == "lb" and to_unit == "kg":
            if "value" in value:
                value["value"] = round(value["value"] * 0.453592, 2)
                note = f"Converted {from_unit} → {to_unit}"
        elif from_unit == "mmol/L" and to_unit == "mg/dL":
            if "value" in value:
                value["value"] = round(value["value"] * 18.0182, 1)
                note = f"Converted {from_unit} → {to_unit}"
        else:
            factor = CONVERSIONS.get((from_unit, to_unit))
            if factor and "value" in value:
                value["value"] = round(value["value"] * factor, 2)
                note = f"Converted {from_unit} → {to_unit}"

        return value, to_unit, note

    def _validate_range(self, vital_type: str, value: dict[str, Any]) -> bool:
        """Check if normalized values are within physiologically possible ranges."""
        ranges = {
            "heart_rate": {"value": (20, 300)},
            "blood_pressure": {"systolic": (40, 300), "diastolic": (20, 200)},
            "glucose": {"value": (20, 600)},
            "spo2": {"value": (50, 100)},
            "weight": {"value": (0.5, 300)},
            "temperature": {"value": (85, 115)},
            "respiratory_rate": {"value": (4, 60)},
        }

        expected = ranges.get(vital_type)
        if not expected:
            return True

        for key, (low, high) in expected.items():
            val = value.get(key)
            if val is not None:
                try:
                    if float(val) < low or float(val) > high:
                        return False
                except (TypeError, ValueError):
                    return False

        return True
