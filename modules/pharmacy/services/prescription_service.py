"""Pharmacy prescription service layer."""

import logging
from typing import Optional

logger = logging.getLogger("healthos.pharmacy.prescription_service")


class PrescriptionService:
    """Business logic for prescription management."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._prescriptions: dict[str, dict] = {}

    async def create_prescription(self, data: dict) -> dict:
        """Create a new prescription."""
        rx_id = data.get("prescription_id", "")
        self._prescriptions[rx_id] = data
        logger.info("Created prescription %s", rx_id)
        return data

    async def get_prescription(self, rx_id: str) -> Optional[dict]:
        """Retrieve a prescription by ID."""
        return self._prescriptions.get(rx_id)

    async def transmit_prescription(self, rx_id: str, pharmacy_id: str) -> dict:
        """Transmit a prescription to a pharmacy via NCPDP SCRIPT."""
        rx = self._prescriptions.get(rx_id)
        if rx:
            rx["status"] = "transmitted"
            rx["pharmacy_id"] = pharmacy_id
        logger.info("Transmitted prescription %s to pharmacy %s", rx_id, pharmacy_id)
        return {"status": "transmitted", "prescription_id": rx_id}

    async def check_refill_eligibility(self, rx_id: str) -> dict:
        """Check if a prescription is eligible for refill."""
        rx = self._prescriptions.get(rx_id)
        remaining = rx.get("refills_remaining", 0) if rx else 0
        return {
            "eligible": remaining > 0,
            "refills_remaining": remaining,
            "prescription_id": rx_id,
        }
