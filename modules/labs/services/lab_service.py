"""Labs service layer."""

import logging
from typing import Optional

logger = logging.getLogger("healthos.labs.lab_service")


class LabService:
    """Business logic for lab order and result management."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._orders: dict[str, dict] = {}
        self._results: dict[str, list[dict]] = {}

    async def create_order(self, data: dict) -> dict:
        order_id = data.get("order_id", "")
        self._orders[order_id] = data
        logger.info("Created lab order %s", order_id)
        return data

    async def get_order(self, order_id: str) -> Optional[dict]:
        return self._orders.get(order_id)

    async def ingest_results(self, order_id: str, results: list[dict]) -> dict:
        self._results.setdefault(order_id, []).extend(results)
        logger.info("Ingested %d results for order %s", len(results), order_id)
        return {"order_id": order_id, "results_count": len(results)}

    async def get_patient_results(self, patient_id: str) -> list[dict]:
        all_results = []
        for order_id, results in self._results.items():
            order = self._orders.get(order_id, {})
            if str(order.get("patient_id")) == patient_id:
                all_results.extend(results)
        return all_results

    async def evaluate_critical(self, result: dict) -> dict:
        """Evaluate if a lab result is a critical value."""
        value = float(result.get("value", 0))
        ref_high = float(result.get("reference_high", 999))
        ref_low = float(result.get("reference_low", 0))
        is_critical = value > ref_high * 1.5 or value < ref_low * 0.5
        return {"is_critical": is_critical, "value": value, "severity": "critical" if is_critical else "normal"}
