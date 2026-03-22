from fastapi import FastAPI, Header, HTTPException
import httpx
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP FHIR Writeback Adapter")

FHIR_BASE = os.getenv("FHIR_BASE", "http://hapi-fhir:8080/fhir")
FHIR_AUTH_HEADER = os.getenv("FHIR_AUTH_HEADER", "")


@app.get("/health")
async def health():
    return {"status": "healthy", "server": "mcp-fhir-adapter"}


def _get_headers():
    headers = {"Content-Type": "application/fhir+json"}
    if FHIR_AUTH_HEADER:
        headers["Authorization"] = FHIR_AUTH_HEADER
    return headers


async def _ensure_patient(patient_id: str) -> dict:
    """Internal helper to ensure patient exists in FHIR."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{FHIR_BASE}/Patient/{patient_id}", headers=_get_headers())
        logger.info(f"Patient check for {patient_id}: {r.status_code}")

        if r.status_code == 404:
            patient_resource = {
                "resourceType": "Patient",
                "id": patient_id,
                "identifier": [{"system": "urn:demo:patient", "value": patient_id}],
                "name": [{"family": "Demo", "given": ["Patient"]}],
                "active": True
            }
            create_resp = await client.put(
                f"{FHIR_BASE}/Patient/{patient_id}",
                json=patient_resource,
                headers=_get_headers()
            )
            logger.info(f"Patient create for {patient_id}: {create_resp.status_code}")
            if create_resp.status_code >= 300:
                logger.error(f"Failed to create patient: {create_resp.text}")
                raise HTTPException(
                    status_code=502,
                    detail={"error": "Failed to create patient", "fhir_status": create_resp.status_code, "body": create_resp.text}
                )
            return {"patient_id": patient_id, "created": True}

        return {"patient_id": patient_id, "created": False}


async def _ensure_device(device_id: str) -> dict:
    """Internal helper to ensure device exists in FHIR."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{FHIR_BASE}/Device/{device_id}", headers=_get_headers())
        logger.info(f"Device check for {device_id}: {r.status_code}")

        if r.status_code == 404:
            device_resource = {
                "resourceType": "Device",
                "id": device_id,
                "identifier": [{"system": "urn:demo:device", "value": device_id}],
                "status": "active",
                "deviceName": [{"name": f"Device {device_id}", "type": "user-friendly-name"}]
            }
            create_resp = await client.put(
                f"{FHIR_BASE}/Device/{device_id}",
                json=device_resource,
                headers=_get_headers()
            )
            logger.info(f"Device create for {device_id}: {create_resp.status_code}")
            if create_resp.status_code >= 300:
                logger.error(f"Failed to create device: {create_resp.text}")
                raise HTTPException(
                    status_code=502,
                    detail={"error": "Failed to create device", "fhir_status": create_resp.status_code, "body": create_resp.text}
                )
            return {"device_id": device_id, "created": True}

        return {"device_id": device_id, "created": False}


@app.post("/tools/resolve_patient_encounter")
async def resolve_patient_encounter(payload: dict, authorization: str | None = Header(default=None)):
    """Resolve or create a patient based on facility/device context."""
    facility_id = payload.get("facility_id", "facility1")
    device_id = payload.get("device_id", "deviceX")

    patient_id = f"patient-{device_id}"

    logger.info(f"resolve_patient_encounter: facility={facility_id}, device={device_id}, patient_id={patient_id}")

    await _ensure_patient(patient_id)
    return {"patient_id": patient_id, "encounter_id": None}


@app.post("/tools/ensure_patient_exists")
async def ensure_patient_exists(payload: dict, authorization: str | None = Header(default=None)):
    """Ensure a patient exists in FHIR. Creates if not found."""
    patient_id = payload.get("patient_id", "demo-patient")
    return await _ensure_patient(patient_id)


@app.post("/tools/write_fhir_observation")
async def write_fhir_observation(payload: dict, authorization: str | None = Header(default=None)):
    obs = payload.get("observation")
    if not isinstance(obs, dict) or obs.get("resourceType") != "Observation":
        raise HTTPException(status_code=400, detail="Invalid Observation payload")

    # Extract and ensure patient exists
    subject_ref = obs.get("subject", {}).get("reference", "")
    logger.info(f"write_fhir_observation: subject_ref={subject_ref}")

    if subject_ref.startswith("Patient/"):
        patient_id = subject_ref.replace("Patient/", "")
        logger.info(f"Ensuring patient exists: {patient_id}")
        try:
            await _ensure_patient(patient_id)
        except Exception as e:
            logger.error(f"Failed to ensure patient: {e}")
            raise

    # Extract and ensure device exists
    device_ref = obs.get("device", {}).get("reference", "")
    if device_ref.startswith("Device/"):
        device_id = device_ref.replace("Device/", "")
        logger.info(f"Ensuring device exists: {device_id}")
        try:
            await _ensure_device(device_id)
        except Exception as e:
            logger.error(f"Failed to ensure device: {e}")
            raise

    async with httpx.AsyncClient(timeout=30) as client:
        logger.info(f"Posting observation to FHIR: {FHIR_BASE}/Observation")
        r = await client.post(f"{FHIR_BASE}/Observation", json=obs, headers=_get_headers())
        logger.info(f"FHIR response: {r.status_code}")

        if r.status_code >= 300:
            logger.error(f"FHIR error: {r.text}")
            raise HTTPException(status_code=502, detail={"fhir_status": r.status_code, "body": r.text})

        body = r.json()
        obs_id = body.get("id")
        logger.info(f"Created observation: {obs_id}")

    return {"status": "ok", "observation_id": obs_id, "warnings": []}
