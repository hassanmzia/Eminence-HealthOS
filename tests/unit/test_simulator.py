"""
Eminence HealthOS — Device Simulator Tests
"""

from __future__ import annotations

from datetime import datetime, timezone

from scripts.simulate_devices import (
    PATIENT_PROFILES,
    generate_patient_vitals,
    generate_simulation_batch,
    generate_vital,
)


def test_generate_single_vital():
    vital = generate_vital(
        patient_id="test-123",
        vital_type="heart_rate",
        profile=PATIENT_PROFILES[0],
        timestamp=datetime.now(timezone.utc),
        anomaly_chance=0.0,
    )
    assert vital["vital_type"] == "heart_rate"
    assert "value" in vital["value"]
    assert vital["source"] == "simulator"


def test_generate_blood_pressure():
    vital = generate_vital(
        patient_id="test-123",
        vital_type="blood_pressure",
        profile=PATIENT_PROFILES[0],
        timestamp=datetime.now(timezone.utc),
        anomaly_chance=0.0,
    )
    assert "systolic" in vital["value"]
    assert "diastolic" in vital["value"]
    assert vital["unit"] == "mmHg"


def test_generate_patient_vitals():
    vitals = generate_patient_vitals(
        patient_id="test-123",
        profile=PATIENT_PROFILES[0],
        hours=24,
        readings_per_hour=1,
        anomaly_chance=0.0,
    )
    assert len(vitals) > 0
    vital_types = set(v["vital_type"] for v in vitals)
    assert "heart_rate" in vital_types


def test_generate_simulation_batch():
    batch = generate_simulation_batch(num_patients=2, hours=6, anomaly_chance=0.0)
    assert len(batch) == 2
    for patient_id, vitals in batch.items():
        assert len(vitals) > 0


def test_anomaly_injection():
    """Test that anomalies are injected at the expected rate."""
    vital = generate_vital(
        patient_id="test-123",
        vital_type="heart_rate",
        profile=PATIENT_PROFILES[0],
        timestamp=datetime.now(timezone.utc),
        anomaly_chance=1.0,  # Force anomaly
    )
    # Anomalous heart rate should be above normal range
    assert vital["value"]["value"] > PATIENT_PROFILES[0]["heart_rate"][1]
