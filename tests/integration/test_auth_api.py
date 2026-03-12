"""
Integration tests for the Auth API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.conftest import auth_header


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/register
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, seed_org):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new.user@test.health",
            "password": "secure123",
            "full_name": "New User",
            "role": "clinician",
            "org_slug": "test-hospital",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new.user@test.health"
    assert body["role"] == "clinician"
    assert "id" in body


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, seed_users):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@test.health",
            "password": "another123",
            "full_name": "Duplicate",
            "role": "clinician",
            "org_slug": "test-hospital",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_nonexistent_org(client: AsyncClient, seed_org):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@test.health",
            "password": "secure123",
            "full_name": "Ghost",
            "role": "clinician",
            "org_slug": "nonexistent-org",
        },
    )
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/auth/login
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_login_valid_credentials(client: AsyncClient, seed_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.health", "password": "admin123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, seed_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.health", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient, seed_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.health", "password": "whatever"},
    )
    assert resp.status_code == 401
