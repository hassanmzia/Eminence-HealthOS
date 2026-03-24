"""
Eminence HealthOS — Create Superuser Script

Creates an admin user with full platform access.
Accepts credentials via environment variables or interactive prompts.

Usage:
  # Via docker compose
  docker compose exec api python scripts/create_superuser.py

  # With env vars (non-interactive)
  docker compose exec -e SUPERUSER_EMAIL=admin@example.com \
    -e SUPERUSER_PASSWORD=SecurePass123! \
    -e SUPERUSER_NAME="Platform Admin" \
    api python scripts/create_superuser.py

  # With custom org
  docker compose exec -e SUPERUSER_EMAIL=admin@example.com \
    -e SUPERUSER_PASSWORD=SecurePass123! \
    -e SUPERUSER_ORG=my-clinic \
    api python scripts/create_superuser.py
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from healthos_platform.database import get_db_context, get_engine
from healthos_platform.models import Base, Organization, User
from healthos_platform.security.auth import hash_password


async def create_superuser() -> None:
    # Ensure tables exist
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Collect credentials from env vars or interactive prompts
    email = os.environ.get("SUPERUSER_EMAIL")
    password = os.environ.get("SUPERUSER_PASSWORD")
    full_name = os.environ.get("SUPERUSER_NAME", "")
    org_slug = os.environ.get("SUPERUSER_ORG", "")

    interactive = not (email and password)

    if not email:
        email = input("Email: ").strip()
        if not email:
            print("Error: Email is required.")
            sys.exit(1)

    if not password:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Password (confirm): ")
        if password != password_confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)

    if not password:
        print("Error: Password is required.")
        sys.exit(1)

    if not full_name and interactive:
        full_name = input("Full name (optional): ").strip()

    if not full_name:
        full_name = "System Administrator"

    async with get_db_context() as db:
        # Find or create organization
        if org_slug:
            result = await db.execute(
                select(Organization).where(Organization.slug == org_slug)
            )
            org = result.scalar_one_or_none()
            if not org:
                print(f"Error: Organization '{org_slug}' not found.")
                sys.exit(1)
        else:
            # Use first available org, or create a default one
            result = await db.execute(select(Organization).limit(1))
            org = result.scalar_one_or_none()
            if not org:
                org = Organization(
                    name="Eminence Health",
                    slug="eminence-health",
                    tier="enterprise",
                    hipaa_baa_signed=True,
                    settings={
                        "features": ["rpm", "telehealth", "analytics"],
                        "ai_enabled": True,
                    },
                )
                db.add(org)
                await db.flush()
                print(f"Created organization: {org.name} ({org.slug})")

        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == email, User.org_id == org.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing user to admin
            existing.hashed_password = hash_password(password)
            existing.role = "admin"
            existing.full_name = full_name
            existing.is_active = True
            print(f"Updated existing user '{email}' to admin role.")
        else:
            user = User(
                org_id=org.id,
                email=email,
                hashed_password=hash_password(password),
                role="admin",
                full_name=full_name,
                is_active=True,
                email_verified=True,
            )
            db.add(user)
            print(f"Created superuser: {email}")

        print(f"  Role: admin (full platform access)")
        print(f"  Org:  {org.name} ({org.slug})")


if __name__ == "__main__":
    asyncio.run(create_superuser())
