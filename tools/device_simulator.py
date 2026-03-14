#!/usr/bin/env python3
"""
Eminence HealthOS — RPM Device Simulator
Generates realistic vital sign data for testing the RPM pipeline.

Supports multiple device types, patient profiles, Kafka publishing,
and direct API ingestion. Includes noise, anomalies, and gradual trends.

Usage:
    python -m tools.device_simulator --patients 5 --profile mixed --mode stream --target api
    python -m tools.device_simulator --mode batch --batch-size 200 --target kafka
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("device_simulator")

# ---------------------------------------------------------------------------
# Constants aligned with healthos_platform/agents/types.py
# ---------------------------------------------------------------------------

VITAL_TYPES = [
    "heart_rate",
    "blood_pressure",
    "glucose",
    "spo2",
    "temperature",
    "weight",
    "respiratory_rate",
]

UNITS = {
    "heart_rate": "bpm",
    "blood_pressure": "mmHg",
    "glucose": "mg/dL",
    "spo2": "%",
    "temperature": "F",
    "weight": "kg",
    "respiratory_rate": "breaths/min",
}

# Kafka topic for raw device vitals
KAFKA_TOPIC = "device.vitals.raw"

# Also support the platform topic used by the existing Kafka service
KAFKA_TOPIC_PLATFORM = "healthos.vitals.ingested"


# ---------------------------------------------------------------------------
# Patient profiles
# ---------------------------------------------------------------------------


class ProfileType(str, Enum):
    NORMAL = "normal"
    HYPERTENSIVE = "hypertensive"
    DIABETIC = "diabetic"
    CARDIAC = "cardiac"
    DETERIORATING = "deteriorating"


# Each profile defines baselines and standard deviations for each vital type.
# Format: {vital_type: {param: (mean, stddev)}}
PROFILE_BASELINES: dict[str, dict[str, dict[str, tuple[float, float]]]] = {
    "normal": {
        "heart_rate": {"value": (72, 6)},
        "blood_pressure": {"systolic": (118, 8), "diastolic": (76, 5)},
        "glucose": {"value": (95, 8)},
        "spo2": {"value": (97.5, 0.8)},
        "temperature": {"value": (98.6, 0.3)},
        "weight": {"value": (170, 2)},
        "respiratory_rate": {"value": (16, 2)},
    },
    "hypertensive": {
        "heart_rate": {"value": (82, 8)},
        "blood_pressure": {"systolic": (155, 12), "diastolic": (98, 8)},
        "glucose": {"value": (105, 12)},
        "spo2": {"value": (96.5, 1.0)},
        "temperature": {"value": (98.6, 0.3)},
        "weight": {"value": (210, 3)},
        "respiratory_rate": {"value": (18, 2)},
    },
    "diabetic": {
        "heart_rate": {"value": (78, 7)},
        "blood_pressure": {"systolic": (135, 10), "diastolic": (88, 6)},
        "glucose": {"value": (180, 40)},
        "spo2": {"value": (96.0, 1.2)},
        "temperature": {"value": (98.4, 0.4)},
        "weight": {"value": (195, 3)},
        "respiratory_rate": {"value": (17, 2)},
    },
    "cardiac": {
        "heart_rate": {"value": (90, 15)},
        "blood_pressure": {"systolic": (140, 15), "diastolic": (85, 10)},
        "glucose": {"value": (110, 15)},
        "spo2": {"value": (93.0, 2.0)},
        "temperature": {"value": (98.5, 0.4)},
        "weight": {"value": (185, 4)},
        "respiratory_rate": {"value": (22, 4)},
    },
    "deteriorating": {
        "heart_rate": {"value": (80, 8)},
        "blood_pressure": {"systolic": (130, 10), "diastolic": (85, 7)},
        "glucose": {"value": (120, 15)},
        "spo2": {"value": (95.5, 1.5)},
        "temperature": {"value": (98.8, 0.5)},
        "weight": {"value": (180, 2)},
        "respiratory_rate": {"value": (18, 2)},
    },
}

# Deterioration drift per reading (additive shift to the mean over time)
DETERIORATION_DRIFT = {
    "heart_rate": {"value": 0.15},
    "blood_pressure": {"systolic": 0.25, "diastolic": 0.15},
    "glucose": {"value": 0.3},
    "spo2": {"value": -0.04},
    "temperature": {"value": 0.008},
    "weight": {"value": 0.02},
    "respiratory_rate": {"value": 0.06},
}

# Device source types per vital
DEVICE_SOURCES = {
    "heart_rate": ["apple_watch", "fitbit", "withings_scanwatch", "garmin_venu"],
    "blood_pressure": ["omron_bp7250", "withings_bpm_connect", "qardio_arm"],
    "glucose": ["dexcom_g7", "freestyle_libre_3", "contour_next_one"],
    "spo2": ["masimo_mightysat", "apple_watch", "withings_scanwatch"],
    "temperature": ["withings_thermo", "kinsa_smart_stick", "braun_thermoscan"],
    "weight": ["withings_body_plus", "fitbit_aria_air", "renpho_smart_scale"],
    "respiratory_rate": ["apple_watch", "withings_sleep_analyzer", "garmin_venu"],
}

# Anomaly probability per reading (approx 2%)
ANOMALY_PROBABILITY = 0.02


# ---------------------------------------------------------------------------
# Simulated patient
# ---------------------------------------------------------------------------


@dataclass
class SimulatedPatient:
    patient_id: str
    org_id: str
    profile: str
    device_ids: dict[str, str] = field(default_factory=dict)
    reading_count: int = 0
    # Per-vital cumulative drift (for deteriorating profile)
    drift: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Assign a unique device_id per vital type
        for vt in VITAL_TYPES:
            source = random.choice(DEVICE_SOURCES[vt])
            self.device_ids[vt] = f"{source}_{self.patient_id[:8]}"
        # Init drift accumulators
        for vt in VITAL_TYPES:
            self.drift[vt] = {k: 0.0 for k in PROFILE_BASELINES[self.profile][vt]}

    def generate_reading(self, vital_type: str) -> dict[str, Any]:
        """Generate a single vital reading with realistic noise and optional anomaly."""
        baselines = PROFILE_BASELINES[self.profile][vital_type]
        value: dict[str, Any] = {}

        for param, (mean, stddev) in baselines.items():
            # Apply drift for deteriorating patients
            drift_val = self.drift[vital_type].get(param, 0.0)
            effective_mean = mean + drift_val

            # Generate base value with Gaussian noise
            v = random.gauss(effective_mean, stddev)

            # Occasional anomaly: spike or dip
            if random.random() < ANOMALY_PROBABILITY:
                direction = random.choice([-1, 1])
                magnitude = random.uniform(2.5, 5.0) * stddev
                v += direction * magnitude
                logger.debug(
                    "Anomaly injected: %s.%s = %.2f for patient %s",
                    vital_type,
                    param,
                    v,
                    self.patient_id[:8],
                )

            # Clamp to valid ranges (from device_ingestion.py)
            v = self._clamp(vital_type, param, v)

            # Round appropriately
            if vital_type == "spo2":
                v = round(v, 1)
            elif vital_type == "temperature":
                v = round(v, 1)
            elif vital_type == "weight":
                v = round(v, 1)
            elif vital_type in ("heart_rate", "respiratory_rate"):
                v = round(v)
            elif vital_type == "blood_pressure":
                v = round(v)
            elif vital_type == "glucose":
                v = round(v)
            else:
                v = round(v, 2)

            value[param] = v

        # Update drift for deteriorating profile
        if self.profile == "deteriorating":
            for param in baselines:
                drift_delta = DETERIORATION_DRIFT.get(vital_type, {}).get(param, 0.0)
                self.drift[vital_type][param] += drift_delta

        self.reading_count += 1

        now = datetime.now(timezone.utc)
        return {
            "vital_type": vital_type,
            "value": value,
            "device_id": self.device_ids[vital_type],
            "recorded_at": now.isoformat(),
            "source": "home_device",
            "unit": UNITS[vital_type],
            "patient_id": self.patient_id,
            "org_id": self.org_id,
        }

    @staticmethod
    def _clamp(vital_type: str, param: str, value: float) -> float:
        """Clamp value to the valid range defined in device_ingestion.py."""
        ranges = {
            "heart_rate": {"value": (20, 300)},
            "blood_pressure": {"systolic": (40, 300), "diastolic": (20, 200)},
            "glucose": {"value": (20, 600)},
            "spo2": {"value": (50, 100)},
            "weight": {"value": (0.5, 500)},
            "temperature": {"value": (85, 115)},
            "respiratory_rate": {"value": (4, 60)},
        }
        bounds = ranges.get(vital_type, {}).get(param)
        if bounds:
            return max(bounds[0], min(bounds[1], value))
        return value


# ---------------------------------------------------------------------------
# Publishers
# ---------------------------------------------------------------------------


class KafkaPublisher:
    """Publishes readings to Kafka using aiokafka (or logs if unavailable)."""

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        self._servers = bootstrap_servers
        self._producer = None

    async def start(self) -> None:
        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            await self._producer.start()
            logger.info("Kafka producer connected to %s", self._servers)
        except Exception as exc:
            logger.warning(
                "Kafka unavailable (%s) — falling back to log-only mode", exc
            )
            self._producer = None

    async def publish(self, reading: dict[str, Any]) -> None:
        envelope = {
            "event_id": str(uuid.uuid4()),
            "event_type": "vitals.raw",
            "source": f"device:{reading.get('device_id', 'unknown')}",
            "org_id": reading.get("org_id", ""),
            "patient_id": reading.get("patient_id", ""),
            "timestamp": reading.get("recorded_at", datetime.now(timezone.utc).isoformat()),
            "payload": {
                "vital_type": reading["vital_type"],
                "value": reading["value"],
                "device_id": reading.get("device_id"),
                "recorded_at": reading["recorded_at"],
                "source": reading.get("source", "home_device"),
                "unit": reading.get("unit", ""),
            },
        }
        if self._producer:
            key = reading.get("patient_id", "")
            await self._producer.send_and_wait(KAFKA_TOPIC, value=envelope, key=key)
            # Also publish to the platform topic for the existing consumer
            await self._producer.send_and_wait(KAFKA_TOPIC_PLATFORM, value=envelope, key=key)
        else:
            logger.info(
                "[kafka-dry] %s | %s | %s",
                reading["vital_type"],
                json.dumps(reading["value"]),
                reading.get("patient_id", "?")[:8],
            )

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")


class ApiPublisher:
    """Publishes readings to the HealthOS REST API."""

    def __init__(self, base_url: str = "http://localhost:4090") -> None:
        self._base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(10.0),
        )
        logger.info("API publisher targeting %s", self._base_url)

    async def publish(self, reading: dict[str, Any]) -> None:
        if self._client is None:
            return

        patient_id = reading.get("patient_id", "")
        payload = {
            "vital_type": reading["vital_type"],
            "value": reading["value"],
            "device_id": reading.get("device_id"),
            "recorded_at": reading["recorded_at"],
            "source": reading.get("source", "home_device"),
            "unit": reading.get("unit", ""),
        }

        try:
            resp = await self._client.post(
                f"/api/v1/vitals/ingest",
                json={
                    "patient_id": patient_id,
                    "vitals": [payload],
                },
            )
            if resp.status_code < 300:
                logger.debug(
                    "[api] OK %d | %s | %s",
                    resp.status_code,
                    reading["vital_type"],
                    patient_id[:8],
                )
            else:
                logger.warning(
                    "[api] %d | %s | %s | %s",
                    resp.status_code,
                    reading["vital_type"],
                    patient_id[:8],
                    resp.text[:120],
                )
        except httpx.RequestError as exc:
            logger.warning("[api] request failed: %s", exc)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            logger.info("API publisher closed")


# ---------------------------------------------------------------------------
# Simulator orchestrator
# ---------------------------------------------------------------------------


class DeviceSimulator:
    """Orchestrates simulated patients and publishing targets."""

    def __init__(
        self,
        num_patients: int = 5,
        profile: str = "mixed",
        mode: str = "stream",
        interval: float = 30.0,
        duration: float = 60.0,
        batch_size: int = 100,
        targets: list[str] | None = None,
        api_url: str = "http://localhost:4090",
        kafka_servers: str = "localhost:9092",
    ) -> None:
        self.mode = mode
        self.interval = interval
        self.duration = duration
        self.batch_size = batch_size
        self.api_url = api_url
        self.kafka_servers = kafka_servers
        self._targets = targets or ["api"]
        self._publishers: list[KafkaPublisher | ApiPublisher] = []
        self._patients: list[SimulatedPatient] = []
        self._running = False
        self._stats = {"published": 0, "errors": 0}

        # Create patients
        org_id = str(uuid.uuid4())
        profiles = self._assign_profiles(num_patients, profile)
        for i, p in enumerate(profiles):
            self._patients.append(
                SimulatedPatient(
                    patient_id=str(uuid.uuid4()),
                    org_id=org_id,
                    profile=p,
                )
            )
        logger.info(
            "Created %d patients (org=%s) with profiles: %s",
            num_patients,
            org_id[:8],
            [pt.profile for pt in self._patients],
        )

    @staticmethod
    def _assign_profiles(n: int, profile: str) -> list[str]:
        if profile == "mixed":
            all_profiles = [p.value for p in ProfileType]
            return [all_profiles[i % len(all_profiles)] for i in range(n)]
        return [profile] * n

    async def start(self) -> None:
        """Initialize publishers."""
        if "kafka" in self._targets or "both" in self._targets:
            kp = KafkaPublisher(self.kafka_servers)
            await kp.start()
            self._publishers.append(kp)

        if "api" in self._targets or "both" in self._targets:
            ap = ApiPublisher(self.api_url)
            await ap.start()
            self._publishers.append(ap)

        if not self._publishers:
            logger.warning("No publishers configured — readings will be logged only")

    async def stop(self) -> None:
        """Shut down publishers."""
        for pub in self._publishers:
            await pub.stop()
        logger.info(
            "Simulator stopped. Published %d readings (%d errors)",
            self._stats["published"],
            self._stats["errors"],
        )

    async def run(self) -> None:
        """Run the simulator in the configured mode."""
        await self.start()
        self._running = True

        try:
            if self.mode == "stream":
                await self._run_stream()
            else:
                await self._run_batch()
        finally:
            await self.stop()

    async def _run_stream(self) -> None:
        """Stream readings at the configured interval until duration elapses."""
        end_time = time.monotonic() + (self.duration * 60)
        cycle = 0

        logger.info(
            "Streaming mode: interval=%.1fs, duration=%.0fmin, patients=%d",
            self.interval,
            self.duration,
            len(self._patients),
        )

        while self._running and time.monotonic() < end_time:
            cycle += 1
            # Each cycle, pick a random subset of vital types per patient
            # (patients don't measure everything every interval)
            tasks = []
            for patient in self._patients:
                num_vitals = random.randint(1, 3)
                chosen_vitals = random.sample(VITAL_TYPES, num_vitals)
                for vt in chosen_vitals:
                    reading = patient.generate_reading(vt)
                    tasks.append(self._publish(reading))

            await asyncio.gather(*tasks, return_exceptions=True)

            elapsed = (self.duration * 60) - (end_time - time.monotonic())
            remaining = end_time - time.monotonic()
            logger.info(
                "Cycle %d complete | readings=%d | elapsed=%.0fs | remaining=%.0fs",
                cycle,
                self._stats["published"],
                elapsed,
                max(0, remaining),
            )

            if self._running and time.monotonic() < end_time:
                await asyncio.sleep(self.interval)

    async def _run_batch(self) -> None:
        """Generate a batch of historical readings per patient."""
        logger.info(
            "Batch mode: %d readings/patient, %d patients = %d total",
            self.batch_size,
            len(self._patients),
            self.batch_size * len(self._patients),
        )

        now = datetime.now(timezone.utc)
        tasks = []

        for patient in self._patients:
            for i in range(self.batch_size):
                # Space readings evenly over the past 7 days
                offset_minutes = (self.batch_size - i) * (7 * 24 * 60 / self.batch_size)
                ts = now - timedelta(minutes=offset_minutes)

                vt = random.choice(VITAL_TYPES)
                reading = patient.generate_reading(vt)
                reading["recorded_at"] = ts.isoformat()
                tasks.append(self._publish(reading))

                # Flush in chunks to avoid overwhelming the target
                if len(tasks) >= 50:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Batch complete: %d readings published", self._stats["published"])

    async def _publish(self, reading: dict[str, Any]) -> None:
        """Publish a single reading to all configured targets."""
        for pub in self._publishers:
            try:
                await pub.publish(reading)
                self._stats["published"] += 1
            except Exception as exc:
                self._stats["errors"] += 1
                logger.error("Publish error: %s", exc)

    def request_stop(self) -> None:
        """Signal the simulator to stop gracefully."""
        logger.info("Stop requested — finishing current cycle...")
        self._running = False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="device_simulator",
        description="HealthOS RPM Device Simulator — generates realistic vital sign data for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # Stream 5 mixed-profile patients to the API for 30 minutes
  python -m tools.device_simulator --patients 5 --profile mixed --mode stream --duration 30 --target api

  # Batch-generate 200 readings/patient for 10 diabetic patients to Kafka
  python -m tools.device_simulator --patients 10 --profile diabetic --mode batch --batch-size 200 --target kafka

  # Stream cardiac patients with 10-second intervals to both Kafka and API
  python -m tools.device_simulator --profile cardiac --mode stream --interval 10 --target both
""",
    )

    parser.add_argument(
        "--patients",
        type=int,
        default=5,
        metavar="N",
        help="Number of simulated patients (default: 5)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="mixed",
        choices=["normal", "hypertensive", "diabetic", "cardiac", "deteriorating", "mixed"],
        help="Patient profile type (default: mixed)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="stream",
        choices=["stream", "batch"],
        help="Simulator mode (default: stream)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30,
        metavar="SECS",
        help="Seconds between reading cycles in stream mode (default: 30)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60,
        metavar="MINS",
        help="Duration in minutes for stream mode (default: 60)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        metavar="N",
        help="Readings per patient in batch mode (default: 100)",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="api",
        choices=["kafka", "api", "both"],
        help="Publishing target (default: api)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:4090",
        metavar="URL",
        help="Base URL for API target (default: http://localhost:4090)",
    )
    parser.add_argument(
        "--kafka-servers",
        type=str,
        default="localhost:9092",
        metavar="HOST:PORT",
        help="Kafka bootstrap servers (default: localhost:9092)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="INT",
        help="Random seed for reproducible runs",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.seed is not None:
        random.seed(args.seed)
        logger.info("Random seed set to %d", args.seed)

    simulator = DeviceSimulator(
        num_patients=args.patients,
        profile=args.profile,
        mode=args.mode,
        interval=args.interval,
        duration=args.duration,
        batch_size=args.batch_size,
        targets=[args.target],
        api_url=args.api_url,
        kafka_servers=args.kafka_servers,
    )

    # Handle Ctrl+C for graceful shutdown
    loop = asyncio.new_event_loop()

    def _signal_handler(sig: int, frame: Any) -> None:
        simulator.request_stop()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        loop.run_until_complete(simulator.run())
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down")
        loop.run_until_complete(simulator.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
