"""Digital Twin service layer."""

import logging
from typing import Optional

logger = logging.getLogger("healthos.digital_twin.twin_service")


class TwinService:
    """Business logic for patient digital twin management."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._twins: dict[str, dict] = {}

    async def build_twin(self, patient_id: str, data: dict) -> dict:
        twin_id = data.get("twin_id", "")
        twin = {"twin_id": twin_id, "patient_id": patient_id, "status": "active", **data}
        self._twins[twin_id] = twin
        logger.info("Built digital twin %s for patient %s", twin_id, patient_id)
        return twin

    async def get_twin(self, twin_id: str) -> Optional[dict]:
        return self._twins.get(twin_id)

    async def get_twin_by_patient(self, patient_id: str) -> Optional[dict]:
        for twin in self._twins.values():
            if str(twin.get("patient_id")) == patient_id:
                return twin
        return None

    async def update_twin(self, twin_id: str, data: dict) -> Optional[dict]:
        twin = self._twins.get(twin_id)
        if twin:
            twin.update(data)
        return twin

    async def simulate_scenario(self, twin_id: str, scenario: dict) -> dict:
        return {
            "twin_id": twin_id,
            "scenario_type": scenario.get("scenario_type", "unknown"),
            "projected_outcome": {"health_score_change": 5.2, "risk_reduction": 0.15},
            "confidence": 0.78,
        }

    async def forecast_trajectory(self, twin_id: str, metrics: list[str], months: int) -> dict:
        return {
            "twin_id": twin_id,
            "horizon_months": months,
            "projections": {m: {"trend": "stable", "confidence": 0.8} for m in metrics},
        }
