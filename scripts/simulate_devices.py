"""
Eminence HealthOS — Device Simulator
Generates realistic vital sign data for testing the RPM pipeline.
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


# Patient profiles for simulation
PATIENT_PROFILES = [
    {
        "name": "Healthy Adult",
        "heart_rate": (65, 80),
        "systolic": (110, 125),
        "diastolic": (70, 80),
        "glucose": (80, 110),
        "spo2": (96, 99),
        "temperature": (97.5, 98.8),
        "respiratory_rate": (14, 18),
    },
    {
        "name": "Hypertensive Patient",
        "heart_rate": (75, 95),
        "systolic": (140, 170),
        "diastolic": (90, 105),
        "glucose": (90, 130),
        "spo2": (94, 98),
        "temperature": (97.5, 99.0),
        "respiratory_rate": (15, 20),
    },
    {
        "name": "Diabetic Patient",
        "heart_rate": (70, 90),
        "systolic": (120, 140),
        "diastolic": (75, 88),
        "glucose": (140, 280),
        "spo2": (95, 98),
        "temperature": (97.5, 99.0),
        "respiratory_rate": (14, 19),
    },
    {
        "name": "Heart Failure Patient",
        "heart_rate": (85, 110),
        "systolic": (90, 115),
        "diastolic": (55, 70),
        "glucose": (85, 120),
        "spo2": (88, 94),
        "temperature": (97.0, 98.5),
        "respiratory_rate": (18, 26),
    },
    {
        "name": "COPD Patient",
        "heart_rate": (80, 100),
        "systolic": (115, 135),
        "diastolic": (70, 85),
        "glucose": (85, 120),
        "spo2": (86, 93),
        "temperature": (97.5, 99.5),
        "respiratory_rate": (18, 28),
    },
]


def generate_vital(
    patient_id: str,
    vital_type: str,
    profile: dict[str, Any],
    timestamp: datetime,
    anomaly_chance: float = 0.05,
) -> dict[str, Any]:
    """Generate a single vital reading with optional anomaly injection."""
    is_anomaly = random.random() < anomaly_chance

    if vital_type == "blood_pressure":
        sys_range = profile["systolic"]
        dia_range = profile["diastolic"]

        if is_anomaly:
            systolic = random.uniform(sys_range[1] + 20, sys_range[1] + 50)
            diastolic = random.uniform(dia_range[1] + 10, dia_range[1] + 30)
        else:
            systolic = random.uniform(*sys_range)
            diastolic = random.uniform(*dia_range)

        value = {"systolic": round(systolic, 1), "diastolic": round(diastolic, 1)}
        unit = "mmHg"
    elif vital_type == "heart_rate":
        rng = profile["heart_rate"]
        val = random.uniform(rng[1] + 30, rng[1] + 60) if is_anomaly else random.uniform(*rng)
        value = {"value": round(val, 1)}
        unit = "bpm"
    elif vital_type == "glucose":
        rng = profile["glucose"]
        val = random.uniform(rng[1] + 50, rng[1] + 150) if is_anomaly else random.uniform(*rng)
        value = {"value": round(val, 1)}
        unit = "mg/dL"
    elif vital_type == "spo2":
        rng = profile["spo2"]
        val = random.uniform(rng[0] - 10, rng[0] - 3) if is_anomaly else random.uniform(*rng)
        value = {"value": round(min(100, max(50, val)), 1)}
        unit = "%"
    elif vital_type == "temperature":
        rng = profile["temperature"]
        val = random.uniform(101.5, 104.0) if is_anomaly else random.uniform(*rng)
        value = {"value": round(val, 1)}
        unit = "°F"
    elif vital_type == "respiratory_rate":
        rng = profile["respiratory_rate"]
        val = random.uniform(rng[1] + 5, rng[1] + 15) if is_anomaly else random.uniform(*rng)
        value = {"value": round(val, 1)}
        unit = "breaths/min"
    else:
        value = {"value": random.uniform(60, 100)}
        unit = "unknown"

    return {
        "patient_id": patient_id,
        "device_id": f"sim-device-{vital_type[:3]}-{random.randint(100, 999)}",
        "vital_type": vital_type,
        "value": value,
        "unit": unit,
        "recorded_at": timestamp.isoformat(),
        "source": "simulator",
    }


def generate_patient_vitals(
    patient_id: str,
    profile: dict[str, Any],
    hours: int = 48,
    readings_per_hour: int = 1,
    anomaly_chance: float = 0.05,
) -> list[dict[str, Any]]:
    """Generate a time series of vitals for a patient."""
    vitals = []
    now = datetime.now(timezone.utc)
    vital_types = [
        "heart_rate",
        "blood_pressure",
        "glucose",
        "spo2",
        "temperature",
        "respiratory_rate",
    ]

    for hour_offset in range(hours, 0, -1):
        for _ in range(readings_per_hour):
            timestamp = now - timedelta(hours=hour_offset, minutes=random.randint(0, 59))
            for vt in vital_types:
                # Not every vital type is measured every interval
                if random.random() < 0.7:  # 70% chance of measurement
                    vitals.append(
                        generate_vital(patient_id, vt, profile, timestamp, anomaly_chance)
                    )

    return vitals


def generate_simulation_batch(
    num_patients: int = 5,
    hours: int = 48,
    anomaly_chance: float = 0.05,
) -> dict[str, list[dict[str, Any]]]:
    """Generate vitals for multiple simulated patients."""
    all_data = {}

    for i in range(num_patients):
        patient_id = str(uuid.uuid4())
        profile = PATIENT_PROFILES[i % len(PATIENT_PROFILES)]
        vitals = generate_patient_vitals(
            patient_id=patient_id,
            profile=profile,
            hours=hours,
            anomaly_chance=anomaly_chance,
        )
        all_data[patient_id] = vitals
        print(f"Generated {len(vitals)} vitals for {profile['name']} (ID: {patient_id[:8]}...)")

    total = sum(len(v) for v in all_data.values())
    print(f"\nTotal: {total} vital readings across {num_patients} patients")
    return all_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HealthOS Device Simulator")
    parser.add_argument("--patients", type=int, default=5, help="Number of patients")
    parser.add_argument("--hours", type=int, default=48, help="Hours of data to generate")
    parser.add_argument("--anomaly-rate", type=float, default=0.05, help="Anomaly injection rate")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()

    data = generate_simulation_batch(args.patients, args.hours, args.anomaly_rate)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved to {args.output}")
    else:
        print(json.dumps({"summary": {pid: len(v) for pid, v in data.items()}}, indent=2))
