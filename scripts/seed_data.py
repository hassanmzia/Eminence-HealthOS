"""
Eminence HealthOS — Database Seed Script
Populates the database with sample organizations, users, and patients.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from platform.config import get_settings
from platform.database import get_db_context, get_engine
from platform.models import Base, Organization, Patient, User
from platform.security.auth import hash_password


async def seed() -> None:
    """Seed the database with sample data."""
    # Create all tables
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_db_context() as db:
        # ── Organization ─────────────────────────────────────────────────
        org = Organization(
            name="Eminence Health Demo",
            slug="eminence-demo",
            tier="enterprise",
            hipaa_baa_signed=True,
            settings={
                "features": ["rpm", "telehealth", "analytics"],
                "max_patients": 10000,
                "ai_enabled": True,
            },
        )
        db.add(org)
        await db.flush()

        # ── Users ────────────────────────────────────────────────────────
        users = [
            User(
                org_id=org.id,
                email="admin@eminence.health",
                hashed_password=hash_password("admin123"),
                role="admin",
                full_name="System Administrator",
            ),
            User(
                org_id=org.id,
                email="dr.smith@eminence.health",
                hashed_password=hash_password("doctor123"),
                role="clinician",
                full_name="Dr. Sarah Smith",
                profile={"specialty": "cardiology", "npi": "1234567890"},
            ),
            User(
                org_id=org.id,
                email="nurse.jones@eminence.health",
                hashed_password=hash_password("nurse123"),
                role="nurse",
                full_name="Nurse Mike Jones",
            ),
            User(
                org_id=org.id,
                email="cm.wilson@eminence.health",
                hashed_password=hash_password("caremanager123"),
                role="care_manager",
                full_name="Carol Wilson, RN",
            ),
        ]
        for u in users:
            db.add(u)
        await db.flush()

        # ── Patients ─────────────────────────────────────────────────────
        patients = [
            Patient(
                org_id=org.id,
                mrn="MRN001",
                demographics={
                    "name": "John Williams",
                    "dob": "1955-03-15",
                    "gender": "male",
                    "contact": {"phone": "555-0101", "email": "john.w@email.com"},
                },
                conditions=[
                    {"code": "I10", "display": "Essential hypertension", "onset": "2018-06-01"},
                    {"code": "E11", "display": "Type 2 diabetes", "onset": "2020-01-15"},
                ],
                medications=[
                    {"name": "Lisinopril", "dose": "20mg", "frequency": "daily"},
                    {"name": "Metformin", "dose": "1000mg", "frequency": "twice daily"},
                ],
                risk_level="high",
                care_team=[{"user_id": str(users[1].id), "role": "primary_physician"}],
            ),
            Patient(
                org_id=org.id,
                mrn="MRN002",
                demographics={
                    "name": "Maria Garcia",
                    "dob": "1968-09-22",
                    "gender": "female",
                    "contact": {"phone": "555-0102", "email": "maria.g@email.com"},
                },
                conditions=[
                    {"code": "I50.9", "display": "Heart failure, unspecified", "onset": "2022-03-10"},
                ],
                medications=[
                    {"name": "Carvedilol", "dose": "25mg", "frequency": "twice daily"},
                    {"name": "Furosemide", "dose": "40mg", "frequency": "daily"},
                ],
                risk_level="critical",
                care_team=[{"user_id": str(users[1].id), "role": "primary_physician"}],
            ),
            Patient(
                org_id=org.id,
                mrn="MRN003",
                demographics={
                    "name": "Robert Chen",
                    "dob": "1975-12-08",
                    "gender": "male",
                    "contact": {"phone": "555-0103", "email": "robert.c@email.com"},
                },
                conditions=[
                    {"code": "J44.1", "display": "COPD with acute exacerbation", "onset": "2019-11-20"},
                ],
                medications=[
                    {"name": "Tiotropium", "dose": "18mcg", "frequency": "daily"},
                    {"name": "Albuterol", "dose": "2 puffs", "frequency": "as needed"},
                ],
                risk_level="moderate",
                care_team=[{"user_id": str(users[1].id), "role": "primary_physician"}],
            ),
            Patient(
                org_id=org.id,
                mrn="MRN004",
                demographics={
                    "name": "Lisa Thompson",
                    "dob": "1990-05-30",
                    "gender": "female",
                    "contact": {"phone": "555-0104", "email": "lisa.t@email.com"},
                },
                conditions=[],
                medications=[],
                risk_level="low",
                care_team=[],
            ),
            Patient(
                org_id=org.id,
                mrn="MRN005",
                demographics={
                    "name": "James Brown",
                    "dob": "1948-01-12",
                    "gender": "male",
                    "contact": {"phone": "555-0105", "email": "james.b@email.com"},
                },
                conditions=[
                    {"code": "I10", "display": "Essential hypertension", "onset": "2010-03-01"},
                    {"code": "E11", "display": "Type 2 diabetes", "onset": "2015-08-20"},
                    {"code": "N18.3", "display": "CKD stage 3", "onset": "2021-06-15"},
                ],
                medications=[
                    {"name": "Amlodipine", "dose": "10mg", "frequency": "daily"},
                    {"name": "Insulin Glargine", "dose": "30 units", "frequency": "bedtime"},
                    {"name": "Losartan", "dose": "50mg", "frequency": "daily"},
                ],
                risk_level="high",
                care_team=[{"user_id": str(users[1].id), "role": "primary_physician"}],
            ),
        ]
        for p in patients:
            db.add(p)

    print("Database seeded successfully!")
    print(f"  Organization: {org.name} ({org.slug})")
    print(f"  Users: {len(users)}")
    print(f"  Patients: {len(patients)}")


if __name__ == "__main__":
    asyncio.run(seed())
