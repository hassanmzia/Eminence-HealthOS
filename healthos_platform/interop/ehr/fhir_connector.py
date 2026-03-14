"""
Eminence HealthOS — FHIR R4 EHR Connector

Implements ``BaseEHRConnector`` for systems exposing a FHIR R4 REST API,
with SMART on FHIR client-credentials authentication, httpx async transport,
and FHIR Bundle transaction support.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from healthos_platform.interop.ehr.base_connector import (
    BaseEHRConnector,
    audit_sync,
    ehr_retry,
)
from healthos_platform.interop.ehr.mappers import (
    clinical_note_to_fhir,
    encounter_to_fhir,
    vital_to_fhir_observation,
)

logger = structlog.get_logger(__name__)


class FHIRConnector(BaseEHRConnector):
    """
    FHIR R4 connector using httpx async client.

    Parameters
    ----------
    base_url:
        The FHIR server root (e.g. ``https://ehr.example.com/fhir``).
    auth_config:
        Dict with SMART on FHIR client-credentials fields::

            {
                "token_url": "https://ehr.example.com/auth/token",
                "client_id": "...",
                "client_secret": "...",
                "scope": "system/*.read system/*.write",  # optional
            }

        If ``None``, no authentication is applied (useful for open sandboxes).
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        auth_config: dict[str, str] | None = None,
        timeout: float = 30.0,
        connector_name: str = "fhir-r4",
    ) -> None:
        super().__init__(connector_name=connector_name)
        self.base_url = base_url.rstrip("/")
        self.auth_config = auth_config or {}
        self.timeout = timeout

        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the httpx client and obtain an access token if configured."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            },
        )
        if self.auth_config.get("token_url"):
            await self._refresh_token()
        logger.info("fhir.connected", base_url=self.base_url)

    async def disconnect(self) -> None:
        """Close the httpx client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._access_token = None
        logger.info("fhir.disconnected", base_url=self.base_url)

    async def is_connected(self) -> bool:
        """Check whether the client is open and the token is valid."""
        if self._client is None or self._client.is_closed:
            return False
        # Quick metadata check
        try:
            resp = await self._client.get("/metadata", headers=self._auth_headers())
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Encounter sync
    # ------------------------------------------------------------------

    @audit_sync("sync_encounter")
    @ehr_retry()
    async def sync_encounter(self, encounter: Any) -> dict:
        """Push an internal Encounter to the FHIR server as a Bundle transaction."""
        fhir_resource = encounter_to_fhir(encounter)
        bundle = self._wrap_in_bundle([fhir_resource])
        return await self._post_bundle(bundle)

    @audit_sync("fetch_encounters")
    @ehr_retry()
    async def fetch_encounters(
        self,
        patient_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> list[dict]:
        """Search for encounters on the remote FHIR server."""
        params: dict[str, str] = {"subject": f"Patient/{patient_id}"}
        if date_range:
            start, end = date_range
            params["date"] = f"ge{start.isoformat()}"
            params["date"] = f"le{end.isoformat()}"

        resp = await self._get("/Encounter", params=params)
        bundle = resp.json()
        return [
            entry["resource"]
            for entry in bundle.get("entry", [])
            if entry.get("resource", {}).get("resourceType") == "Encounter"
        ]

    # ------------------------------------------------------------------
    # Patient sync
    # ------------------------------------------------------------------

    @audit_sync("sync_patient")
    @ehr_retry()
    async def sync_patient(self, patient: Any) -> dict:
        """Push an internal Patient record to the FHIR server."""
        resource = self._patient_to_fhir(patient)
        fhir_id = getattr(patient, "fhir_id", None)

        if fhir_id:
            # Update existing
            resp = await self._put(f"/Patient/{fhir_id}", resource)
        else:
            # Create new
            resp = await self._post("/Patient", resource)

        return resp.json()

    @audit_sync("fetch_patient")
    @ehr_retry()
    async def fetch_patient(self, patient_id: str) -> dict:
        """Fetch a single Patient resource from the FHIR server."""
        resp = await self._get(f"/Patient/{patient_id}")
        return resp.json()

    # ------------------------------------------------------------------
    # Clinical data push
    # ------------------------------------------------------------------

    @audit_sync("push_clinical_note")
    @ehr_retry()
    async def push_clinical_note(self, note: Any) -> str:
        """Push a ClinicalNote as a FHIR DocumentReference."""
        resource = clinical_note_to_fhir(note)
        resp = await self._post("/DocumentReference", resource)
        result = resp.json()
        return result.get("id", "")

    @audit_sync("push_observation")
    @ehr_retry()
    async def push_observation(self, observation: Any) -> str:
        """Push a vital/observation as a FHIR Observation resource."""
        resource = vital_to_fhir_observation(observation)
        resp = await self._post("/Observation", resource)
        result = resp.json()
        return result.get("id", "")

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    @audit_sync("batch_sync")
    @ehr_retry()
    async def batch_sync(self, resources: list[dict]) -> dict:
        """
        Push multiple resources in a single FHIR Bundle transaction.

        Each resource dict must include ``resourceType`` and ``id``.
        """
        bundle = self._wrap_in_bundle(resources)
        return await self._post_bundle(bundle)

    # ------------------------------------------------------------------
    # SMART on FHIR auth
    # ------------------------------------------------------------------

    async def _refresh_token(self) -> None:
        """Obtain or refresh an access token using SMART client credentials."""
        token_url = self.auth_config["token_url"]
        client_id = self.auth_config["client_id"]
        client_secret = self.auth_config["client_secret"]
        scope = self.auth_config.get("scope", "system/*.read system/*.write")

        async with httpx.AsyncClient(timeout=self.timeout) as auth_client:
            resp = await auth_client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            token_data = resp.json()

        self._access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        # Refresh 60s early to avoid edge-case expiration
        self._token_expires_at = time.monotonic() + expires_in - 60

        logger.info("fhir.token_refreshed", expires_in=expires_in)

    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header if a token is available."""
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    async def _ensure_token(self) -> None:
        """Refresh the token if it has expired."""
        if self.auth_config.get("token_url") and time.monotonic() >= self._token_expires_at:
            await self._refresh_token()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        assert self._client is not None, "Connector not connected. Call connect() first."
        await self._ensure_token()
        resp = await self._client.get(path, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        return resp

    async def _post(self, path: str, resource: dict) -> httpx.Response:
        assert self._client is not None, "Connector not connected. Call connect() first."
        await self._ensure_token()
        resp = await self._client.post(path, json=resource, headers=self._auth_headers())
        resp.raise_for_status()
        return resp

    async def _put(self, path: str, resource: dict) -> httpx.Response:
        assert self._client is not None, "Connector not connected. Call connect() first."
        await self._ensure_token()
        resp = await self._client.put(path, json=resource, headers=self._auth_headers())
        resp.raise_for_status()
        return resp

    async def _post_bundle(self, bundle: dict) -> dict:
        """POST a FHIR Bundle to the server root."""
        assert self._client is not None, "Connector not connected. Call connect() first."
        await self._ensure_token()
        resp = await self._client.post("/", json=bundle, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # FHIR helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap_in_bundle(resources: list[dict]) -> dict:
        """Wrap a list of FHIR resources in a Bundle transaction."""
        entries = []
        for res in resources:
            resource_type = res.get("resourceType", "Resource")
            resource_id = res.get("id", "")

            method = "PUT" if resource_id else "POST"
            url = f"{resource_type}/{resource_id}" if resource_id else resource_type

            entries.append({
                "resource": res,
                "request": {
                    "method": method,
                    "url": url,
                },
            })

        return {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": entries,
        }

    @staticmethod
    def _patient_to_fhir(patient: Any) -> dict[str, Any]:
        """
        Convert an internal Patient model to a FHIR R4 Patient resource.

        Supports both the main ``healthos_platform.models.Patient`` (JSONB
        demographics) and ``shared.models.patient.Patient`` (discrete columns).
        """
        patient_id = str(getattr(patient, "id", ""))
        fhir_id = getattr(patient, "fhir_id", None)

        # Detect model type
        demographics = getattr(patient, "demographics", None)

        if demographics and isinstance(demographics, dict):
            # JSONB-based patient (healthos_platform.models.Patient)
            name_str = demographics.get("name", "")
            parts = name_str.split(" ", 1)
            given = parts[0] if parts else ""
            family = parts[1] if len(parts) > 1 else given
            gender = demographics.get("gender", "unknown")
            dob = demographics.get("dob", "")
            contact = demographics.get("contact", {})
            phone = contact.get("phone", "")
            email = contact.get("email", "")
        else:
            # Discrete-column patient (shared.models.patient.Patient)
            given = getattr(patient, "first_name", "")
            family = getattr(patient, "last_name", "")
            gender = getattr(patient, "sex", "unknown")
            dob_val = getattr(patient, "date_of_birth", None)
            dob = dob_val.isoformat() if dob_val else ""
            phone = getattr(patient, "phone", "") or ""
            email = getattr(patient, "email", "") or ""

        resource: dict[str, Any] = {
            "resourceType": "Patient",
            "active": True,
            "name": [
                {
                    "use": "official",
                    "family": family,
                    "given": [given] if given else [],
                }
            ],
            "gender": gender,
            "birthDate": dob,
        }

        if fhir_id:
            resource["id"] = fhir_id
        elif patient_id:
            resource["id"] = patient_id

        mrn = getattr(patient, "mrn", None)
        if mrn:
            resource["identifier"] = [
                {
                    "use": "usual",
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                "code": "MR",
                            }
                        ]
                    },
                    "value": mrn,
                }
            ]

        telecom: list[dict[str, str]] = []
        if phone:
            telecom.append({"system": "phone", "value": phone, "use": "mobile"})
        if email:
            telecom.append({"system": "email", "value": email})
        if telecom:
            resource["telecom"] = telecom

        return resource
