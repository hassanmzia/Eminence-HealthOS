"""Imaging service layer."""

import logging
from typing import Optional

logger = logging.getLogger("healthos.imaging.imaging_service")


class ImagingService:
    """Business logic for imaging studies and radiology workflows."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._studies: dict[str, dict] = {}

    async def ingest_study(self, data: dict) -> dict:
        study_id = data.get("study_id", "")
        self._studies[study_id] = {**data, "status": "received"}
        logger.info("Ingested imaging study %s", study_id)
        return self._studies[study_id]

    async def get_study(self, study_id: str) -> Optional[dict]:
        return self._studies.get(study_id)

    async def get_patient_studies(self, patient_id: str) -> list[dict]:
        return [s for s in self._studies.values() if str(s.get("patient_id")) == patient_id]

    async def assign_study(self, study_id: str, radiologist_id: str) -> dict:
        study = self._studies.get(study_id, {})
        study["assigned_to"] = radiologist_id
        study["status"] = "assigned"
        return study

    async def get_worklist(self, tenant_id: str) -> list[dict]:
        return [s for s in self._studies.values()
                if s.get("status") in ("received", "assigned")]

    async def check_sla(self, tenant_id: str) -> dict:
        return {"total_studies": len(self._studies), "within_sla": len(self._studies), "breached": 0}
