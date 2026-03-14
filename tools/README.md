# HealthOS Developer Tools

## Device Simulator (`device_simulator.py`)

Generates realistic vital sign data for testing the RPM (Remote Patient Monitoring) pipeline. Simulates multiple patients with configurable medical profiles, publishing readings to Kafka and/or the REST API.

### Supported Vital Types

| Vital | Value Format | Unit | Valid Range |
|-------|-------------|------|-------------|
| `heart_rate` | `{"value": 72}` | bpm | 20 - 300 |
| `blood_pressure` | `{"systolic": 120, "diastolic": 80}` | mmHg | sys 40-300, dia 20-200 |
| `glucose` | `{"value": 95}` | mg/dL | 20 - 600 |
| `spo2` | `{"value": 97.5}` | % | 50 - 100 |
| `temperature` | `{"value": 98.6}` | F | 85 - 115 |
| `weight` | `{"value": 170.0}` | kg | 0.5 - 500 |
| `respiratory_rate` | `{"value": 16}` | breaths/min | 4 - 60 |

### Patient Profiles

- **normal** — Healthy baselines across all vitals
- **hypertensive** — Elevated blood pressure and heart rate
- **diabetic** — High and variable glucose, moderately elevated BP
- **cardiac** — Elevated heart rate, low SpO2, high respiratory rate
- **deteriorating** — Starts near-normal and gradually worsens over time (drift applied to all vitals each reading cycle)
- **mixed** — Assigns profiles round-robin across patients

### Usage

Run from the repository root:

```bash
# Stream mode: 5 mixed-profile patients, readings every 30s for 60 minutes, to the API
python -m tools.device_simulator

# Customize patients and profile
python -m tools.device_simulator --patients 10 --profile diabetic --mode stream --target api

# Batch mode: generate 200 historical readings per patient to Kafka
python -m tools.device_simulator --mode batch --batch-size 200 --target kafka

# Stream to both Kafka and API with 10-second intervals
python -m tools.device_simulator --profile cardiac --mode stream --interval 10 --target both

# Reproducible run with a fixed random seed
python -m tools.device_simulator --seed 42 --patients 3 --mode batch --batch-size 50

# Verbose output for debugging
python -m tools.device_simulator -v --patients 2 --interval 5 --duration 2
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--patients N` | 5 | Number of simulated patients |
| `--profile` | mixed | Patient profile: normal, hypertensive, diabetic, cardiac, deteriorating, mixed |
| `--mode` | stream | `stream` (real-time) or `batch` (historical) |
| `--interval SECS` | 30 | Seconds between reading cycles in stream mode |
| `--duration MINS` | 60 | How long to run in stream mode |
| `--batch-size N` | 100 | Readings per patient in batch mode |
| `--target` | api | Publishing target: `kafka`, `api`, or `both` |
| `--api-url URL` | http://localhost:4090 | Base URL for the API target |
| `--kafka-servers` | localhost:9092 | Kafka bootstrap servers |
| `--seed INT` | (random) | Random seed for reproducible data |
| `-v, --verbose` | off | Enable debug-level logging |

### Publishing Targets

**API mode** (`--target api`): Posts readings to `POST /api/v1/vitals/ingest` with the body:
```json
{
  "patient_id": "uuid",
  "vitals": [
    {
      "vital_type": "heart_rate",
      "value": {"value": 72},
      "device_id": "apple_watch_a1b2c3d4",
      "recorded_at": "2026-03-14T12:00:00+00:00",
      "source": "home_device",
      "unit": "bpm"
    }
  ]
}
```

**Kafka mode** (`--target kafka`): Publishes to topics `device.vitals.raw` and `healthos.vitals.ingested` using the standard `HealthOSEvent` envelope. Falls back to log-only mode if Kafka is unavailable.

### How It Works

1. On startup, the simulator creates N simulated patients, each assigned a profile and unique device IDs per vital type.
2. In **stream mode**, each cycle picks a random subset of 1-3 vital types per patient, generates readings with Gaussian noise, and publishes them. Cycles repeat at the configured interval until the duration elapses. Press Ctrl+C to stop early.
3. In **batch mode**, readings are generated with timestamps spread evenly over the past 7 days and published in chunks of 50.
4. Approximately 2% of readings include an injected anomaly (a spike or dip of 2.5-5x the standard deviation).
5. For `deteriorating` patients, each vital's mean drifts progressively with every reading, simulating gradual clinical decline.

### Prerequisites

- `httpx` (for API publishing): `pip install httpx`
- `aiokafka` (for Kafka publishing, optional): `pip install aiokafka`
