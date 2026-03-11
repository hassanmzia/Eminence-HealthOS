"""
Device Integration Agent — Tier 1 (Monitoring).

Manages incoming data streams from RPM devices (blood pressure cuffs,
glucose meters, pulse oximeters, smart watches). Validates, normalizes,
and routes device data into the ingestion pipeline.
"""

import logging
from datetime import datetime, timezone

from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.device_integration")

# Supported device types and their expected data formats
DEVICE_TYPES = {
    "blood_pressure_cuff": {
        "loinc_codes": ["8480-6", "8462-4"],
        "required_fields": ["systolic", "diastolic"],
    },
    "pulse_oximeter": {
        "loinc_codes": ["2708-6", "8867-4"],
        "required_fields": ["spo2"],
    },
    "glucose_meter": {
        "loinc_codes": ["2345-7"],
        "required_fields": ["glucose"],
    },
    "thermometer": {
        "loinc_codes": ["8310-5"],
        "required_fields": ["temperature"],
    },
    "weight_scale": {
        "loinc_codes": ["29463-7"],
        "required_fields": ["weight"],
    },
    "ecg_monitor": {
        "loinc_codes": ["8867-4"],
        "required_fields": ["heart_rate"],
    },
}


class DeviceIntegrationAgent(HealthOSAgent):
    """Validates and routes incoming RPM device data."""

    def __init__(self):
        super().__init__(
            name="device_integration",
            tier=AgentTier.MONITORING,
            description="Manages RPM device data ingestion, validation, and routing",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.DEVICE_INTEGRATION, AgentCapability.VITAL_MONITORING]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        device_type = data.get("device_type", "unknown")
        device_id = data.get("device_id", "unknown")
        readings = data.get("readings", {})

        # Validate device type
        if device_type not in DEVICE_TYPES:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="unsupported_device",
                rationale=f"Device type '{device_type}' not supported",
                confidence=1.0,
                data={"device_type": device_type, "device_id": device_id},
            )

        spec = DEVICE_TYPES[device_type]
        validation = self._validate_readings(readings, spec)

        if not validation["valid"]:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="invalid_data",
                rationale=f"Invalid device data: {validation['errors']}",
                confidence=0.95,
                data={"device_type": device_type, "errors": validation["errors"]},
            )

        # Normalize readings to LOINC-coded observations
        normalized = self._normalize_readings(device_type, readings)

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="device_data_accepted",
            rationale=f"Accepted {len(normalized)} readings from {device_type} ({device_id})",
            confidence=0.90,
            data={
                "device_type": device_type,
                "device_id": device_id,
                "observations": normalized,
                "reading_count": len(normalized),
            },
            feature_contributions=[
                {"feature": "device_type", "contribution": 0.3, "value": device_type},
                {"feature": "data_quality", "contribution": 0.4, "value": validation["quality_score"]},
                {"feature": "reading_count", "contribution": 0.3, "value": len(normalized)},
            ],
            downstream_agents=["vital_monitor"],
        )

    def _validate_readings(self, readings: dict, spec: dict) -> dict:
        errors = []
        for field in spec["required_fields"]:
            if field not in readings:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(readings[field], (int, float)):
                errors.append(f"Invalid type for {field}: expected numeric")

        quality_score = 1.0 - (len(errors) / max(len(spec["required_fields"]), 1))
        return {"valid": len(errors) == 0, "errors": errors, "quality_score": quality_score}

    def _normalize_readings(self, device_type: str, readings: dict) -> list:
        normalized = []
        field_to_loinc = {
            "systolic": ("8480-6", "Systolic Blood Pressure", "mmHg"),
            "diastolic": ("8462-4", "Diastolic Blood Pressure", "mmHg"),
            "spo2": ("2708-6", "Oxygen Saturation", "%"),
            "heart_rate": ("8867-4", "Heart Rate", "bpm"),
            "glucose": ("2345-7", "Glucose", "mg/dL"),
            "temperature": ("8310-5", "Body Temperature", "°C"),
            "weight": ("29463-7", "Body Weight", "kg"),
        }

        for field, value in readings.items():
            if field in field_to_loinc and isinstance(value, (int, float)):
                loinc, display, unit = field_to_loinc[field]
                normalized.append({
                    "loinc_code": loinc,
                    "display": display,
                    "value_quantity": value,
                    "value_unit": unit,
                    "data_source": "device",
                })

        return normalized
