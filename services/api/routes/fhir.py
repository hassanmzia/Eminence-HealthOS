"""FHIR R4 endpoints for interoperability."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.config.database import get_db
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id
from shared.models.observation import Observation
from shared.models.patient import Patient
from shared.utils.fhir import to_fhir_observation, to_fhir_patient

logger = logging.getLogger("healthos.routes.fhir")
router = APIRouter()


@router.get("/Patient/{patient_id}")
async def get_fhir_patient(
    patient_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Return a patient as a FHIR R4 Patient resource."""
    result = await db.execute(
        select(Patient).where(
            Patient.id == str(patient_id),
            Patient.tenant_id == tenant_id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return to_fhir_patient(patient)


@router.get("/Patient/{patient_id}/Observation")
async def get_fhir_observations(
    patient_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Return a FHIR R4 Bundle of Observations for a patient."""
    result = await db.execute(
        select(Observation)
        .where(
            Observation.patient_id == str(patient_id),
            Observation.tenant_id == tenant_id,
        )
        .order_by(Observation.effective_datetime.desc())
        .limit(100)
    )
    observations = result.scalars().all()

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(observations),
        "entry": [
            {
                "resource": to_fhir_observation(obs),
                "fullUrl": f"Observation/{obs.id}",
            }
            for obs in observations
        ],
    }


@router.get("/Observation/{observation_id}")
async def get_fhir_observation(
    observation_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Return a single Observation as FHIR R4."""
    result = await db.execute(
        select(Observation).where(
            Observation.id == str(observation_id),
            Observation.tenant_id == tenant_id,
        )
    )
    obs = result.scalar_one_or_none()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return to_fhir_observation(obs)


@router.post("/Bundle")
async def ingest_fhir_bundle(
    bundle: dict,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Ingest a FHIR R4 Bundle."""
    if bundle.get("resourceType") != "Bundle":
        raise HTTPException(status_code=400, detail="Expected a FHIR Bundle resource")

    from healthos_platform.data.ingestion.pipeline import IngestionPipeline
    pipeline = IngestionPipeline()
    result = await pipeline.ingest_fhir_bundle(bundle, tenant_id)
    return result
