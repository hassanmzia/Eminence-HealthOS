"""
Eminence HealthOS — EHR Sync API Routes

Exposes endpoints for triggering EHR synchronisation, listing connector
status, and testing connectivity.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.database import get_db
from healthos_platform.security.rbac import Permission

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ehr", tags=["EHR Sync"])


# ---------------------------------------------------------------------------
# Singleton sync service — lazily initialised on first use
# ---------------------------------------------------------------------------

_sync_service = None


def _get_sync_service():
    """Return the global EHRSyncService instance (lazy init)."""
    global _sync_service
    if _sync_service is None:
        from healthos_platform.interop.ehr.sync_service import EHRSyncService
        _sync_service = EHRSyncService()
    return _sync_service


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ConnectorTestRequest(BaseModel):
    """Request body for testing connector connectivity."""
    connector_type: str = Field(
        ...,
        description="Type of connector: 'fhir' or 'hl7v2'",
        examples=["fhir"],
    )
    # FHIR fields
    base_url: str | None = Field(None, description="FHIR server base URL")
    auth_config: dict[str, str] | None = Field(
        None,
        description="SMART on FHIR auth config with token_url, client_id, client_secret",
    )
    # HL7v2 fields
    host: str | None = Field(None, description="HL7v2 listener host")
    port: int | None = Field(None, description="HL7v2 listener port")


class ConnectorRegisterRequest(BaseModel):
    """Request body for registering a new connector."""
    name: str = Field(..., description="Unique connector name")
    connector_type: str = Field(..., description="'fhir' or 'hl7v2'")
    # FHIR
    base_url: str | None = None
    auth_config: dict[str, str] | None = None
    # HL7v2
    host: str | None = None
    port: int | None = None
    sending_app: str = "HealthOS"
    sending_facility: str = "HealthOS"
    receiving_app: str = ""
    receiving_facility: str = ""


class SyncEncounterRequest(BaseModel):
    """Optional request body for encounter sync."""
    connector_name: str = Field("default", description="Registered connector name")


class BatchSyncRequest(BaseModel):
    """Request body for batch encounter sync."""
    encounter_ids: list[str] = Field(..., description="List of encounter UUIDs")
    connector_name: str = Field("default", description="Registered connector name")


class PatientSyncRequest(BaseModel):
    """Optional request body for patient sync."""
    connector_name: str = Field("default", description="Registered connector name")
    direction: str = Field("push", description="'push' (local->EHR) or 'pull' (EHR->local)")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/connectors", response_model=dict)
async def list_connectors(
    ctx: TenantContext = Depends(get_current_user),
) -> dict[str, Any]:
    """List all registered EHR connectors and their current status."""
    ctx.require_permission(Permission.ENCOUNTERS_READ)
    svc = _get_sync_service()
    statuses = await svc.get_connector_statuses()
    return {
        "connectors": statuses,
        "total": len(statuses),
    }


@router.post("/connectors/register", response_model=dict)
async def register_connector(
    body: ConnectorRegisterRequest,
    ctx: TenantContext = Depends(get_current_user),
) -> dict[str, Any]:
    """Register a new EHR connector."""
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)
    svc = _get_sync_service()

    if body.connector_type == "fhir":
        if not body.base_url:
            raise HTTPException(status_code=400, detail="base_url is required for FHIR connectors")
        from healthos_platform.interop.ehr.fhir_connector import FHIRConnector
        connector = FHIRConnector(
            base_url=body.base_url,
            auth_config=body.auth_config,
            connector_name=body.name,
        )
    elif body.connector_type == "hl7v2":
        if not body.host or not body.port:
            raise HTTPException(status_code=400, detail="host and port are required for HL7v2 connectors")
        from healthos_platform.interop.ehr.hl7v2_connector import HL7v2Connector
        connector = HL7v2Connector(
            host=body.host,
            port=body.port,
            sending_app=body.sending_app,
            sending_facility=body.sending_facility,
            receiving_app=body.receiving_app,
            receiving_facility=body.receiving_facility,
            connector_name=body.name,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown connector type: {body.connector_type}")

    svc.register_connector(body.name, connector)

    return {
        "status": "registered",
        "name": body.name,
        "type": body.connector_type,
    }


@router.post("/connectors/test", response_model=dict)
async def test_connectivity(
    body: ConnectorTestRequest,
    ctx: TenantContext = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Test connectivity to an EHR system without persisting the connector.

    Creates a temporary connector, attempts to connect, checks status,
    and then disconnects.
    """
    ctx.require_permission(Permission.ENCOUNTERS_READ)

    if body.connector_type == "fhir":
        if not body.base_url:
            raise HTTPException(status_code=400, detail="base_url is required for FHIR test")
        from healthos_platform.interop.ehr.fhir_connector import FHIRConnector
        connector = FHIRConnector(
            base_url=body.base_url,
            auth_config=body.auth_config,
            connector_name="test-fhir",
        )
    elif body.connector_type == "hl7v2":
        if not body.host or not body.port:
            raise HTTPException(status_code=400, detail="host and port are required for HL7v2 test")
        from healthos_platform.interop.ehr.hl7v2_connector import HL7v2Connector
        connector = HL7v2Connector(
            host=body.host,
            port=body.port,
            connector_name="test-hl7v2",
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown connector type: {body.connector_type}")

    try:
        await connector.connect()
        connected = await connector.is_connected()
        await connector.disconnect()
        return {
            "status": "ok" if connected else "unreachable",
            "connected": connected,
            "connector_type": body.connector_type,
        }
    except Exception as exc:
        logger.error("ehr.test_connectivity_failed", error=str(exc))
        try:
            await connector.disconnect()
        except Exception:
            pass
        return {
            "status": "error",
            "connected": False,
            "connector_type": body.connector_type,
            "error": str(exc),
        }


@router.post("/sync/encounter/{encounter_id}", response_model=dict)
async def sync_encounter(
    encounter_id: uuid.UUID,
    body: SyncEncounterRequest | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Sync a single encounter to the configured EHR system.

    Pulls the encounter from the local database, maps it to the
    connector's wire format, and pushes it to the remote EHR.
    """
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)
    svc = _get_sync_service()
    connector_name = body.connector_name if body else "default"

    try:
        result = await svc.sync_encounter_to_ehr(
            encounter_id=str(encounter_id),
            connector_name=connector_name,
            db=db,
        )
        return {
            "status": "synced",
            "encounter_id": str(encounter_id),
            "connector": connector_name,
            "response": result,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("ehr.sync_encounter_failed", encounter_id=str(encounter_id), error=str(exc))
        raise HTTPException(status_code=502, detail=f"EHR sync failed: {exc}")


@router.post("/sync/encounter/batch", response_model=dict)
async def batch_sync_encounters(
    body: BatchSyncRequest,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Sync multiple encounters in a single batch operation."""
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)
    svc = _get_sync_service()

    try:
        result = await svc.batch_sync_encounters(
            encounter_ids=body.encounter_ids,
            connector_name=body.connector_name,
            db=db,
        )
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("ehr.batch_sync_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Batch sync failed: {exc}")


@router.post("/sync/patient/{patient_id}", response_model=dict)
async def sync_patient(
    patient_id: uuid.UUID,
    body: PatientSyncRequest | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Full patient sync — push all patient data (demographics, encounters,
    vitals) to the configured EHR, or pull from the EHR into the local DB.
    """
    ctx.require_permission(Permission.PATIENT_WRITE)
    svc = _get_sync_service()
    connector_name = body.connector_name if body else "default"
    direction = body.direction if body else "push"

    try:
        if direction == "push":
            result = await svc.sync_patient_to_ehr(
                patient_id=str(patient_id),
                connector_name=connector_name,
                db=db,
            )
        elif direction == "pull":
            result = await svc.sync_from_ehr(
                connector_name=connector_name,
                patient_id=str(patient_id),
                db=db,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid direction: {direction}")

        return {
            "status": "synced",
            "patient_id": str(patient_id),
            "direction": direction,
            "connector": connector_name,
            "result": result,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ehr.sync_patient_failed", patient_id=str(patient_id), error=str(exc))
        raise HTTPException(status_code=502, detail=f"Patient sync failed: {exc}")


@router.get("/sync/history", response_model=dict)
async def get_sync_history(
    connector: str | None = Query(None, description="Filter by connector name"),
    limit: int = Query(50, ge=1, le=500),
    ctx: TenantContext = Depends(get_current_user),
) -> dict[str, Any]:
    """Return recent sync history entries."""
    ctx.require_permission(Permission.ENCOUNTERS_READ)
    svc = _get_sync_service()
    history = svc.get_sync_history(limit=limit, connector_name=connector)
    return {
        "history": history,
        "total": len(history),
    }
