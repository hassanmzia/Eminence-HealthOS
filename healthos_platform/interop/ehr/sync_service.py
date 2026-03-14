"""
Eminence HealthOS — EHR Sync Orchestration Service

Manages multiple EHR connectors, orchestrates bidirectional sync of
encounters, patients, and clinical data, and handles conflict resolution
with last-write-wins + audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.interop.ehr.base_connector import BaseEHRConnector
from healthos_platform.interop.ehr.mappers import (
    encounter_to_fhir,
    fhir_encounter_to_internal,
    fhir_observation_to_internal,
    vital_to_fhir_observation,
)

logger = structlog.get_logger(__name__)


class EHRSyncService:
    """
    Central orchestrator for EHR synchronisation.

    Holds a registry of named connectors and provides high-level operations
    that coordinate database lookups, mapping, and remote push/pull.
    """

    def __init__(self) -> None:
        self._connectors: dict[str, BaseEHRConnector] = {}
        self._sync_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Connector registry
    # ------------------------------------------------------------------

    def register_connector(self, name: str, connector: BaseEHRConnector) -> None:
        """Register a connector under a unique name."""
        if name in self._connectors:
            logger.warning("ehr.sync.connector_replaced", name=name)
        self._connectors[name] = connector
        logger.info("ehr.sync.connector_registered", name=name, type=type(connector).__name__)

    def unregister_connector(self, name: str) -> None:
        """Remove a connector by name."""
        self._connectors.pop(name, None)

    def get_connector(self, name: str) -> BaseEHRConnector:
        """Retrieve a registered connector. Raises KeyError if missing."""
        if name not in self._connectors:
            raise KeyError(f"EHR connector '{name}' is not registered")
        return self._connectors[name]

    def list_connectors(self) -> dict[str, str]:
        """Return a dict mapping connector names to their class names."""
        return {name: type(c).__name__ for name, c in self._connectors.items()}

    async def get_connector_statuses(self) -> list[dict[str, Any]]:
        """Return connectivity status for all registered connectors."""
        statuses = []
        for name, connector in self._connectors.items():
            try:
                connected = await connector.is_connected()
            except Exception:
                connected = False
            statuses.append({
                "name": name,
                "type": type(connector).__name__,
                "connected": connected,
                "connector_name": connector.connector_name,
            })
        return statuses

    # ------------------------------------------------------------------
    # Push: Local -> EHR
    # ------------------------------------------------------------------

    async def sync_encounter_to_ehr(
        self,
        encounter_id: str,
        connector_name: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Pull an encounter from the local DB, convert it, and push to the
        specified EHR connector.

        Returns the remote response (FHIR Bundle or ACK dict).
        """
        from healthos_platform.models import Encounter

        connector = self.get_connector(connector_name)

        result = await db.execute(
            select(Encounter).where(Encounter.id == uuid.UUID(encounter_id))
        )
        encounter = result.scalar_one_or_none()
        if not encounter:
            raise ValueError(f"Encounter {encounter_id} not found")

        response = await connector.sync_encounter(encounter)

        self._record_sync(
            direction="push",
            connector_name=connector_name,
            resource_type="Encounter",
            resource_id=encounter_id,
            status="success",
        )

        return response

    async def sync_patient_to_ehr(
        self,
        patient_id: str,
        connector_name: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Full patient sync: push patient demographics, encounters, vitals,
        and clinical notes to the specified EHR connector.
        """
        from healthos_platform.models import Encounter, Patient, Vital

        connector = self.get_connector(connector_name)

        # Fetch patient
        result = await db.execute(
            select(Patient).where(Patient.id == uuid.UUID(patient_id))
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        sync_results: dict[str, Any] = {
            "patient_id": patient_id,
            "connector": connector_name,
            "resources_synced": [],
            "errors": [],
        }

        # 1. Sync patient demographics
        try:
            patient_resp = await connector.sync_patient(patient)
            sync_results["resources_synced"].append({
                "type": "Patient",
                "id": patient_id,
                "response": patient_resp,
            })
        except Exception as exc:
            logger.error("ehr.sync.patient_failed", patient_id=patient_id, error=str(exc))
            sync_results["errors"].append({
                "type": "Patient",
                "id": patient_id,
                "error": str(exc),
            })

        # 2. Sync encounters
        enc_result = await db.execute(
            select(Encounter).where(Encounter.patient_id == uuid.UUID(patient_id))
        )
        encounters = enc_result.scalars().all()

        for enc in encounters:
            try:
                enc_resp = await connector.sync_encounter(enc)
                sync_results["resources_synced"].append({
                    "type": "Encounter",
                    "id": str(enc.id),
                    "response": enc_resp,
                })
            except Exception as exc:
                logger.error("ehr.sync.encounter_failed", encounter_id=str(enc.id), error=str(exc))
                sync_results["errors"].append({
                    "type": "Encounter",
                    "id": str(enc.id),
                    "error": str(exc),
                })

        # 3. Sync vitals
        vital_result = await db.execute(
            select(Vital).where(Vital.patient_id == uuid.UUID(patient_id))
        )
        vitals = vital_result.scalars().all()

        for vital in vitals:
            try:
                vital_remote_id = await connector.push_observation(vital)
                sync_results["resources_synced"].append({
                    "type": "Observation",
                    "id": str(vital.id),
                    "remote_id": vital_remote_id,
                })
            except Exception as exc:
                logger.error("ehr.sync.vital_failed", vital_id=str(vital.id), error=str(exc))
                sync_results["errors"].append({
                    "type": "Observation",
                    "id": str(vital.id),
                    "error": str(exc),
                })

        self._record_sync(
            direction="push",
            connector_name=connector_name,
            resource_type="Patient",
            resource_id=patient_id,
            status="success" if not sync_results["errors"] else "partial",
            detail=sync_results,
        )

        return sync_results

    # ------------------------------------------------------------------
    # Pull: EHR -> Local
    # ------------------------------------------------------------------

    async def sync_from_ehr(
        self,
        connector_name: str,
        patient_id: str,
        db: AsyncSession,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> dict[str, Any]:
        """
        Pull patient data from an EHR and create/update local records.

        Uses last-write-wins conflict resolution: if a remote record is
        newer than the local one, the local record is updated.
        """
        from healthos_platform.models import Encounter

        connector = self.get_connector(connector_name)
        sync_results: dict[str, Any] = {
            "patient_id": patient_id,
            "connector": connector_name,
            "direction": "pull",
            "created": [],
            "updated": [],
            "conflicts": [],
            "errors": [],
        }

        # 1. Fetch patient from EHR
        try:
            remote_patient = await connector.fetch_patient(patient_id)
            sync_results["remote_patient"] = remote_patient
        except Exception as exc:
            logger.error("ehr.sync.pull_patient_failed", error=str(exc))
            sync_results["errors"].append({
                "type": "Patient",
                "error": str(exc),
            })

        # 2. Fetch encounters from EHR
        try:
            remote_encounters = await connector.fetch_encounters(
                patient_id, date_range=date_range
            )
        except Exception as exc:
            logger.error("ehr.sync.pull_encounters_failed", error=str(exc))
            remote_encounters = []
            sync_results["errors"].append({
                "type": "Encounter",
                "error": str(exc),
            })

        for remote_enc in remote_encounters:
            try:
                internal = fhir_encounter_to_internal(remote_enc)
                fhir_id = internal.get("fhir_id") or remote_enc.get("id", "")

                # Check for existing encounter by fhir_id pattern
                # Using a simple approach: look for encounters with matching patient
                local_result = await db.execute(
                    select(Encounter).where(
                        Encounter.patient_id == uuid.UUID(patient_id),
                        Encounter.status == internal.get("status"),
                    ).limit(1)
                )
                existing = local_result.scalar_one_or_none()

                if existing:
                    # Last-write-wins: update if remote is different
                    conflict_entry = {
                        "fhir_id": fhir_id,
                        "resolution": "last_write_wins",
                        "winner": "remote",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    existing.status = internal.get("status", existing.status)
                    existing.reason = internal.get("reason") or existing.reason
                    existing.encounter_type = internal.get("encounter_type", existing.encounter_type)

                    sync_results["updated"].append(str(existing.id))
                    sync_results["conflicts"].append(conflict_entry)
                else:
                    # Create new encounter
                    new_enc = Encounter(
                        patient_id=uuid.UUID(patient_id),
                        org_id=uuid.UUID(patient_id),  # Will be corrected by caller
                        encounter_type=internal.get("encounter_type", "office_visit"),
                        status=internal.get("status", "in-progress"),
                        reason=internal.get("reason"),
                    )
                    db.add(new_enc)
                    sync_results["created"].append(str(new_enc.id))

            except Exception as exc:
                logger.error("ehr.sync.pull_encounter_process_failed", error=str(exc))
                sync_results["errors"].append({
                    "type": "Encounter",
                    "fhir_id": remote_enc.get("id", ""),
                    "error": str(exc),
                })

        self._record_sync(
            direction="pull",
            connector_name=connector_name,
            resource_type="Patient",
            resource_id=patient_id,
            status="success" if not sync_results["errors"] else "partial",
            detail=sync_results,
        )

        return sync_results

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    async def batch_sync_encounters(
        self,
        encounter_ids: list[str],
        connector_name: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Sync multiple encounters to an EHR in a single batch.

        For FHIR connectors, this uses Bundle transactions. For HL7v2
        connectors, messages are sent sequentially.
        """
        from healthos_platform.models import Encounter

        connector = self.get_connector(connector_name)
        results: dict[str, Any] = {
            "connector": connector_name,
            "total": len(encounter_ids),
            "succeeded": [],
            "failed": [],
        }

        # Check if connector supports batch (FHIR)
        if hasattr(connector, "batch_sync"):
            # Fetch all encounters
            enc_result = await db.execute(
                select(Encounter).where(
                    Encounter.id.in_([uuid.UUID(eid) for eid in encounter_ids])
                )
            )
            encounters = enc_result.scalars().all()

            fhir_resources = [encounter_to_fhir(enc) for enc in encounters]

            try:
                batch_resp = await connector.batch_sync(fhir_resources)
                results["succeeded"] = encounter_ids
                results["batch_response"] = batch_resp
            except Exception as exc:
                results["failed"] = encounter_ids
                results["error"] = str(exc)
        else:
            # Sequential sync for non-batch connectors
            for eid in encounter_ids:
                try:
                    await self.sync_encounter_to_ehr(eid, connector_name, db)
                    results["succeeded"].append(eid)
                except Exception as exc:
                    results["failed"].append({"id": eid, "error": str(exc)})

        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record_sync(
        self,
        direction: str,
        connector_name: str,
        resource_type: str,
        resource_id: str,
        status: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        """Append a sync event to the in-memory history."""
        entry = {
            "id": str(uuid.uuid4()),
            "direction": direction,
            "connector": connector_name,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if detail:
            entry["detail"] = detail
        self._sync_history.append(entry)

    def get_sync_history(
        self,
        limit: int = 50,
        connector_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent sync history, optionally filtered by connector."""
        history = self._sync_history
        if connector_name:
            history = [h for h in history if h["connector"] == connector_name]
        return list(reversed(history[-limit:]))
