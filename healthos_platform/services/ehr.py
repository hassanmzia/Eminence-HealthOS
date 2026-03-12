"""
Eminence HealthOS — EHR Connector Framework
Provides standardized interfaces for Epic, Cerner, and Allscripts integrations
using FHIR R4 and proprietary APIs.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from healthos_platform.config import get_settings

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# Base EHR Connector
# ═══════════════════════════════════════════════════════════════════════════════


class EHRConnector(ABC):
    """Abstract base for EHR system connectors."""

    name: str = "base"
    fhir_version: str = "R4"

    def __init__(self, base_url: str, client_id: str, client_secret: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._log = logger.bind(ehr=self.name)

    @abstractmethod
    async def authenticate(self) -> str:
        """Obtain an access token from the EHR system."""
        ...

    async def _get_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expires_at and now < self._token_expires_at:
            return self._access_token
        self._access_token = await self.authenticate()
        return self._access_token

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Make an authenticated request to the EHR system."""
        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }
        headers.update(kwargs.pop("headers", {}))

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()

    # ── FHIR R4 Operations ────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> dict[str, Any]:
        """Fetch a FHIR Patient resource."""
        return await self._request("GET", f"/fhir/r4/Patient/{patient_id}")

    async def search_patients(self, **params) -> dict[str, Any]:
        """Search for FHIR Patient resources."""
        return await self._request("GET", "/fhir/r4/Patient", params=params)

    async def get_observations(self, patient_id: str, category: str = "vital-signs") -> dict[str, Any]:
        """Fetch FHIR Observation resources for a patient."""
        return await self._request(
            "GET",
            "/fhir/r4/Observation",
            params={"patient": patient_id, "category": category, "_sort": "-date", "_count": 100},
        )

    async def get_conditions(self, patient_id: str) -> dict[str, Any]:
        """Fetch FHIR Condition resources for a patient."""
        return await self._request(
            "GET",
            "/fhir/r4/Condition",
            params={"patient": patient_id, "clinical-status": "active"},
        )

    async def get_medications(self, patient_id: str) -> dict[str, Any]:
        """Fetch FHIR MedicationRequest resources for a patient."""
        return await self._request(
            "GET",
            "/fhir/r4/MedicationRequest",
            params={"patient": patient_id, "status": "active"},
        )

    async def get_encounters(self, patient_id: str) -> dict[str, Any]:
        """Fetch FHIR Encounter resources for a patient."""
        return await self._request(
            "GET",
            "/fhir/r4/Encounter",
            params={"patient": patient_id, "_sort": "-date", "_count": 20},
        )

    async def get_allergies(self, patient_id: str) -> dict[str, Any]:
        """Fetch FHIR AllergyIntolerance resources for a patient."""
        return await self._request(
            "GET",
            "/fhir/r4/AllergyIntolerance",
            params={"patient": patient_id, "clinical-status": "active"},
        )

    async def create_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Create a FHIR Observation resource (e.g., vitals)."""
        return await self._request("POST", "/fhir/r4/Observation", json=observation)

    # ── Batch Sync ────────────────────────────────────────────────────────

    async def sync_patient_data(self, patient_id: str) -> dict[str, Any]:
        """Pull full patient record from EHR system."""
        self._log.info("ehr.sync.start", patient_id=patient_id)

        patient = await self.get_patient(patient_id)
        observations = await self.get_observations(patient_id)
        conditions = await self.get_conditions(patient_id)
        medications = await self.get_medications(patient_id)
        encounters = await self.get_encounters(patient_id)
        allergies = await self.get_allergies(patient_id)

        self._log.info("ehr.sync.complete", patient_id=patient_id)

        return {
            "patient": patient,
            "observations": observations,
            "conditions": conditions,
            "medications": medications,
            "encounters": encounters,
            "allergies": allergies,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Epic Connector
# ═══════════════════════════════════════════════════════════════════════════════


class EpicConnector(EHRConnector):
    """
    Epic EHR connector using SMART on FHIR / Epic FHIR R4 APIs.
    Supports Epic's OAuth 2.0 backend services authorization.
    """

    name = "epic"

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str = "",
        private_key_path: str = "",
    ) -> None:
        super().__init__(base_url, client_id, client_secret)
        self.private_key_path = private_key_path

    async def authenticate(self) -> str:
        """
        Authenticate using Epic's Backend Services (JWT assertion).
        Epic uses SMART Backend Services authorization with signed JWTs.
        """
        from datetime import timedelta
        from jose import jwt as jose_jwt

        now = datetime.now(timezone.utc)
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": f"{self.base_url}/oauth2/token",
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        }

        # Load private key for JWT signing
        if self.private_key_path:
            with open(self.private_key_path) as f:
                private_key = f.read()
        else:
            private_key = self.client_secret

        assertion = jose_jwt.encode(claims, private_key, algorithm="RS384")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                    "client_assertion": assertion,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        self._token_expires_at = now + timedelta(seconds=data.get("expires_in", 300))
        self._log.info("epic.authenticated", expires_in=data.get("expires_in"))
        return data["access_token"]

    async def get_schedule(self, provider_id: str, date: str) -> dict[str, Any]:
        """Epic-specific: Get provider schedule."""
        return await self._request(
            "GET",
            "/fhir/r4/Schedule",
            params={"actor": f"Practitioner/{provider_id}", "date": date},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Cerner Connector
# ═══════════════════════════════════════════════════════════════════════════════


class CernerConnector(EHRConnector):
    """
    Oracle Cerner (now Oracle Health) connector using FHIR R4 APIs.
    Uses OAuth 2.0 client credentials flow.
    """

    name = "cerner"

    def __init__(self, base_url: str, client_id: str, client_secret: str, tenant_id: str = "") -> None:
        super().__init__(base_url, client_id, client_secret)
        self.tenant_id = tenant_id

    async def authenticate(self) -> str:
        """Authenticate using OAuth 2.0 client credentials."""
        from datetime import timedelta

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "system/*.read",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        now = datetime.now(timezone.utc)
        self._token_expires_at = now + timedelta(seconds=data.get("expires_in", 300))
        self._log.info("cerner.authenticated", expires_in=data.get("expires_in"))
        return data["access_token"]

    async def get_care_plan(self, patient_id: str) -> dict[str, Any]:
        """Cerner-specific: Get FHIR CarePlan resources."""
        return await self._request(
            "GET",
            "/fhir/r4/CarePlan",
            params={"patient": patient_id, "status": "active"},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Allscripts Connector
# ═══════════════════════════════════════════════════════════════════════════════


class AllscriptsConnector(EHRConnector):
    """
    Allscripts EHR connector. Uses Allscripts Unity API with FHIR facade.
    """

    name = "allscripts"

    async def authenticate(self) -> str:
        """Authenticate using Allscripts Unity token service."""
        from datetime import timedelta

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/unity/unityservice.svc/json/GetToken",
                json={
                    "Username": self.client_id,
                    "Password": self.client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        now = datetime.now(timezone.utc)
        self._token_expires_at = now + timedelta(hours=1)
        self._log.info("allscripts.authenticated")
        return data.get("Token", "")


# ═══════════════════════════════════════════════════════════════════════════════
# EHR Registry
# ═══════════════════════════════════════════════════════════════════════════════


class EHRRegistry:
    """Registry of configured EHR connectors per organization."""

    def __init__(self) -> None:
        self._connectors: dict[str, EHRConnector] = {}

    def register(self, org_id: str, connector: EHRConnector) -> None:
        """Register an EHR connector for an organization."""
        self._connectors[org_id] = connector
        logger.info("ehr.registered", org_id=org_id, ehr=connector.name)

    def get(self, org_id: str) -> EHRConnector | None:
        """Get the EHR connector for an organization."""
        return self._connectors.get(org_id)

    def list_connectors(self) -> list[dict[str, str]]:
        """List all registered EHR connectors."""
        return [
            {"org_id": org_id, "ehr": conn.name, "base_url": conn.base_url}
            for org_id, conn in self._connectors.items()
        ]


# Module-level registry
ehr_registry = EHRRegistry()
