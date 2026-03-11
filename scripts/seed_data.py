"""
Seed script for development data.

Populates the database with sample patients, providers, observations,
and conditions for testing the platform.
"""

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("healthos.seed")


SAMPLE_PATIENTS = [
    {
        "mrn": "MRN-001",
        "first_name": "Sarah",
        "last_name": "Johnson",
        "date_of_birth": date(1965, 3, 15),
        "sex": "female",
        "email": "sarah.johnson@example.com",
        "phone": "555-0101",
        "blood_type": "A+",
        "risk_score": 7.5,
        "risk_level": "HIGH",
    },
    {
        "mrn": "MRN-002",
        "first_name": "Michael",
        "last_name": "Chen",
        "date_of_birth": date(1978, 8, 22),
        "sex": "male",
        "email": "michael.chen@example.com",
        "phone": "555-0102",
        "blood_type": "O+",
        "risk_score": 3.2,
        "risk_level": "LOW",
    },
    {
        "mrn": "MRN-003",
        "first_name": "Maria",
        "last_name": "Garcia",
        "date_of_birth": date(1955, 11, 8),
        "sex": "female",
        "email": "maria.garcia@example.com",
        "phone": "555-0103",
        "blood_type": "B+",
        "risk_score": 8.9,
        "risk_level": "CRITICAL",
    },
    {
        "mrn": "MRN-004",
        "first_name": "James",
        "last_name": "Williams",
        "date_of_birth": date(1990, 1, 30),
        "sex": "male",
        "email": "james.williams@example.com",
        "phone": "555-0104",
        "blood_type": "AB+",
        "risk_score": 2.1,
        "risk_level": "LOW",
    },
    {
        "mrn": "MRN-005",
        "first_name": "Emily",
        "last_name": "Brown",
        "date_of_birth": date(1942, 6, 18),
        "sex": "female",
        "email": "emily.brown@example.com",
        "phone": "555-0105",
        "blood_type": "O-",
        "risk_score": 6.8,
        "risk_level": "HIGH",
    },
]

SAMPLE_PROVIDERS = [
    {
        "npi": "1234567890",
        "first_name": "Dr. Robert",
        "last_name": "Smith",
        "email": "robert.smith@healthos.example",
        "role": "physician",
        "specialty": "Internal Medicine",
        "department": "Primary Care",
    },
    {
        "npi": "1234567891",
        "first_name": "Dr. Lisa",
        "last_name": "Park",
        "email": "lisa.park@healthos.example",
        "role": "physician",
        "specialty": "Cardiology",
        "department": "Cardiology",
    },
    {
        "first_name": "Nancy",
        "last_name": "Rivera",
        "email": "nancy.rivera@healthos.example",
        "role": "nurse",
        "specialty": "Critical Care",
        "department": "ICU",
    },
    {
        "first_name": "Tom",
        "last_name": "Anderson",
        "email": "tom.anderson@healthos.example",
        "role": "care_coordinator",
        "department": "RPM",
    },
]

SAMPLE_VITALS = [
    ("8480-6", "Systolic Blood Pressure", 138, "mmHg"),
    ("8462-4", "Diastolic Blood Pressure", 88, "mmHg"),
    ("8867-4", "Heart Rate", 78, "bpm"),
    ("9279-1", "Respiratory Rate", 16, "/min"),
    ("8310-5", "Body Temperature", 37.0, "°C"),
    ("2708-6", "Oxygen Saturation", 97, "%"),
]


async def seed():
    from platform.config.database import get_db_context
    from shared.models.patient import Patient
    from shared.models.provider import Provider
    from shared.models.observation import Observation

    tenant_id = "default"

    async with get_db_context() as db:
        # Seed providers
        provider_ids = []
        for p_data in SAMPLE_PROVIDERS:
            provider = Provider(tenant_id=tenant_id, **p_data)
            db.add(provider)
            await db.flush()
            provider_ids.append(str(provider.id))
            logger.info("Created provider: %s %s", p_data["first_name"], p_data["last_name"])

        # Seed patients
        patient_ids = []
        for i, pt_data in enumerate(SAMPLE_PATIENTS):
            pt_data["primary_provider_id"] = provider_ids[i % len(provider_ids)]
            patient = Patient(tenant_id=tenant_id, **pt_data)
            db.add(patient)
            await db.flush()
            patient_ids.append(str(patient.id))
            logger.info("Created patient: %s %s (MRN: %s)", pt_data["first_name"], pt_data["last_name"], pt_data["mrn"])

        # Seed observations (last 7 days of vitals for each patient)
        now = datetime.now(timezone.utc)
        for pid in patient_ids:
            for day_offset in range(7):
                for loinc, display, base_val, unit in SAMPLE_VITALS:
                    # Add some variance
                    import random
                    variance = random.uniform(-5, 5) if isinstance(base_val, int) else random.uniform(-0.5, 0.5)
                    value = round(base_val + variance, 1)
                    obs = Observation(
                        tenant_id=tenant_id,
                        patient_id=pid,
                        category="vital-signs",
                        loinc_code=loinc,
                        display=display,
                        value_quantity=value,
                        value_unit=unit,
                        effective_datetime=now - timedelta(days=day_offset, hours=random.randint(0, 12)),
                        status="final",
                        data_source="device",
                    )
                    db.add(obs)

            logger.info("Created 7 days of vitals for patient %s", pid)

    logger.info("Seed complete: %d providers, %d patients, %d observation days",
                len(SAMPLE_PROVIDERS), len(SAMPLE_PATIENTS), 7)


if __name__ == "__main__":
    asyncio.run(seed())
