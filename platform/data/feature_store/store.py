"""
Feature Store for HealthOS agents.

Provides pre-computed patient features for agent consumption.
Backed by Redis for hot features and PostgreSQL for historical.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("healthos.feature_store")


class FeatureStore:
    """
    Centralized feature store for agent input features.

    Features are organized by patient and feature group:
        - vitals: latest vital signs
        - labs: latest lab results
        - risk: computed risk scores
        - medications: active medications
        - demographics: patient demographics
        - utilization: encounter history stats
    """

    FEATURE_GROUPS = [
        "vitals", "labs", "risk", "medications",
        "demographics", "utilization", "devices",
    ]

    def __init__(self, redis=None):
        self._redis = redis

    def _key(self, patient_id: str, group: str, tenant_id: str = "default") -> str:
        return f"features:{tenant_id}:{patient_id}:{group}"

    async def get_features(
        self,
        patient_id: str,
        groups: Optional[list[str]] = None,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Retrieve features for a patient across specified groups."""
        groups = groups or self.FEATURE_GROUPS
        result = {}

        if not self._redis:
            return result

        for group in groups:
            key = self._key(patient_id, group, tenant_id)
            try:
                data = await self._redis.get(key)
                if data:
                    result[group] = json.loads(data)
            except Exception as e:
                logger.warning("Feature fetch failed for %s: %s", key, e)

        return result

    async def set_features(
        self,
        patient_id: str,
        group: str,
        features: dict,
        tenant_id: str = "default",
        ttl: int = 3600,
    ) -> None:
        """Store features for a patient in a specific group."""
        if not self._redis:
            return

        key = self._key(patient_id, group, tenant_id)
        features["_updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            await self._redis.set(key, json.dumps(features), ex=ttl)
        except Exception as e:
            logger.warning("Feature store failed for %s: %s", key, e)

    async def update_vitals(
        self,
        patient_id: str,
        loinc_code: str,
        value: float,
        unit: str,
        tenant_id: str = "default",
    ) -> None:
        """Update a single vital sign in the patient's vitals feature group."""
        features = await self.get_features(patient_id, ["vitals"], tenant_id)
        vitals = features.get("vitals", {})
        vitals[loinc_code] = {
            "value": value,
            "unit": unit,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.set_features(patient_id, "vitals", vitals, tenant_id)

    async def get_patient_snapshot(
        self,
        patient_id: str,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Get a full feature snapshot for agent consumption."""
        return await self.get_features(patient_id, tenant_id=tenant_id)

    async def invalidate(
        self,
        patient_id: str,
        group: Optional[str] = None,
        tenant_id: str = "default",
    ) -> None:
        """Invalidate cached features."""
        if not self._redis:
            return

        if group:
            await self._redis.delete(self._key(patient_id, group, tenant_id))
        else:
            for g in self.FEATURE_GROUPS:
                await self._redis.delete(self._key(patient_id, g, tenant_id))
