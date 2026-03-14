"""
Feature Store for HealthOS agents.

Provides pre-computed patient features for agent consumption.
Backed by Redis for hot features and PostgreSQL for historical.
"""

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select

logger = logging.getLogger("healthos.feature_store")

# ─── Vital-type configuration ────────────────────────────────────────────────
# Weights used in the vital instability index (higher = more clinically significant)
_VITAL_WEIGHTS: dict[str, float] = {
    "heart_rate": 1.0,
    "systolic_bp": 1.2,
    "diastolic_bp": 1.0,
    "respiratory_rate": 1.3,
    "spo2": 1.5,
    "temperature": 0.8,
}

# Expected readings per 24 h window (used for adherence scoring)
_EXPECTED_READINGS_PER_24H: dict[str, int] = {
    "heart_rate": 4,
    "systolic_bp": 3,
    "diastolic_bp": 3,
    "respiratory_rate": 4,
    "spo2": 4,
    "temperature": 2,
}


def _extract_numeric(value_field: Any) -> Optional[float]:
    """Extract a numeric value from the Vital.value JSONB column.

    The column stores data in several possible shapes:
        - ``{"value": 72.0}``
        - ``{"quantity": 72.0}``
        - a bare numeric stored as a JSON number
    Returns *None* when parsing fails.
    """
    if value_field is None:
        return None
    if isinstance(value_field, (int, float)):
        return float(value_field)
    if isinstance(value_field, dict):
        for key in ("value", "quantity", "valueQuantity"):
            v = value_field.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    try:
        return float(value_field)
    except (TypeError, ValueError):
        return None


def _linear_slope(values: list[float]) -> float:
    """Compute the slope of a simple OLS linear regression over evenly-spaced
    observations.  *values* are assumed to be ordered oldest-first.
    Returns 0.0 when there are fewer than 2 data-points.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


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

    def __init__(self, redis=None, db_session_factory=None):
        self._redis = redis
        self._db_session_factory = db_session_factory

    # ── helpers ────────────────────────────────────────────────────────────

    def _key(self, patient_id: str, group: str, tenant_id: str = "default") -> str:
        return f"features:{tenant_id}:{patient_id}:{group}"

    async def _get_db_context(self):
        """Return an async context-manager that yields an ``AsyncSession``.

        Prefers the injected *db_session_factory* (easier to test). Falls back
        to the global ``get_db_context`` from the database module.
        """
        if self._db_session_factory is not None:
            return self._db_session_factory()
        # Fall back to global helper
        from healthos_platform.database import get_db_context
        return get_db_context()

    # ── existing public API (unchanged) ───────────────────────────────────

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

    # =====================================================================
    # NEW: Computation Pipeline
    # =====================================================================

    async def compute_vitals_features(
        self,
        patient_id: str,
        tenant_id: str = "default",
        lookback_hours: int = 48,
        trend_window: int = 10,
    ) -> dict[str, Any]:
        """Compute aggregated vitals features from recent readings.

        For each *vital_type* present in the lookback window this returns:
            - ``latest``: most recent numeric value
            - ``mean``, ``std``, ``min``, ``max``: descriptive statistics
            - ``trend``: OLS slope over the last *trend_window* readings
            - ``count_24h``: number of readings in the most recent 24 hours
            - ``latest_recorded_at``: ISO timestamp of the newest reading
            - ``unit``: measurement unit (from the most recent reading)

        Returns a dict keyed by *vital_type*.
        """
        from healthos_platform.models import Vital

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=lookback_hours)
        cutoff_24h = now - timedelta(hours=24)

        features: dict[str, Any] = {}

        async with await self._get_db_context() as session:
            stmt = (
                select(Vital)
                .where(
                    Vital.patient_id == patient_id,
                    Vital.recorded_at >= cutoff,
                )
                .order_by(Vital.recorded_at.asc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        # Group rows by vital_type
        grouped: dict[str, list] = {}
        for row in rows:
            grouped.setdefault(row.vital_type, []).append(row)

        for vital_type, readings in grouped.items():
            numeric_values: list[float] = []
            count_24h = 0
            latest_row = readings[-1]  # already sorted asc

            for r in readings:
                v = _extract_numeric(r.value)
                if v is not None:
                    numeric_values.append(v)
                if r.recorded_at >= cutoff_24h:
                    count_24h += 1

            if not numeric_values:
                continue

            n = len(numeric_values)
            mean = sum(numeric_values) / n
            variance = sum((x - mean) ** 2 for x in numeric_values) / n if n > 1 else 0.0
            std = math.sqrt(variance)

            # Trend: slope over last *trend_window* readings
            trend_slice = numeric_values[-trend_window:]
            trend = _linear_slope(trend_slice)

            features[vital_type] = {
                "latest": numeric_values[-1],
                "mean": round(mean, 4),
                "std": round(std, 4),
                "min": min(numeric_values),
                "max": max(numeric_values),
                "trend": round(trend, 6),
                "count_24h": count_24h,
                "total_readings": n,
                "latest_recorded_at": latest_row.recorded_at.isoformat(),
                "unit": latest_row.unit,
            }

        return features

    async def compute_risk_features(
        self,
        patient_id: str,
        tenant_id: str = "default",
        vitals_features: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Compute derived risk features for a patient.

        Returns:
            - ``vital_instability_index``: weighted sum of absolute z-scores
              across vital types (higher = more unstable).
            - ``adherence_score``: percentage of expected readings actually
              received in the last 24 h (0.0 -- 1.0).
            - ``anomaly_count_7d``: number of anomaly records in the last 7
              days.
            - ``anomaly_severity_breakdown``: count per severity bucket.
        """
        from healthos_platform.models import Anomaly

        # -- 1. Vital instability index -----------------------------------
        if vitals_features is None:
            vitals_features = await self.compute_vitals_features(
                patient_id, tenant_id=tenant_id
            )

        weighted_z_sum = 0.0
        total_weight = 0.0
        for vital_type, stats in vitals_features.items():
            std = stats.get("std", 0.0)
            mean = stats.get("mean", 0.0)
            latest = stats.get("latest")
            if std and std > 0 and latest is not None and mean is not None:
                z_score = abs(latest - mean) / std
            else:
                z_score = 0.0
            weight = _VITAL_WEIGHTS.get(vital_type, 1.0)
            weighted_z_sum += z_score * weight
            total_weight += weight

        instability_index = round(weighted_z_sum / total_weight, 4) if total_weight else 0.0

        # -- 2. Adherence score -------------------------------------------
        total_expected = 0
        total_received = 0
        for vital_type, expected in _EXPECTED_READINGS_PER_24H.items():
            total_expected += expected
            received = vitals_features.get(vital_type, {}).get("count_24h", 0)
            # Cap at expected so over-reporting doesn't inflate the score
            total_received += min(received, expected)

        adherence_score = round(total_received / total_expected, 4) if total_expected else 0.0

        # -- 3. Anomaly frequency (last 7 days) --------------------------
        now = datetime.now(timezone.utc)
        cutoff_7d = now - timedelta(days=7)

        anomaly_count = 0
        severity_breakdown: dict[str, int] = {}

        async with await self._get_db_context() as session:
            stmt = (
                select(Anomaly)
                .where(
                    Anomaly.patient_id == patient_id,
                    Anomaly.created_at >= cutoff_7d,
                )
            )
            result = await session.execute(stmt)
            anomalies = result.scalars().all()

        for a in anomalies:
            anomaly_count += 1
            sev = a.severity or "unknown"
            severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

        return {
            "vital_instability_index": instability_index,
            "adherence_score": adherence_score,
            "anomaly_count_7d": anomaly_count,
            "anomaly_severity_breakdown": severity_breakdown,
        }

    async def compute_utilization_features(
        self,
        patient_id: str,
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        """Compute healthcare utilization statistics.

        Returns:
            - ``encounters_30d``, ``encounters_90d``, ``encounters_365d``:
              encounter counts in respective windows.
            - ``days_since_last_encounter``: calendar days (or *None* if no
              encounters found).
            - ``ed_visit_count_365d``: number of emergency-department
              encounters in the last year.
        """
        from healthos_platform.models import Encounter

        now = datetime.now(timezone.utc)
        cutoff_30 = now - timedelta(days=30)
        cutoff_90 = now - timedelta(days=90)
        cutoff_365 = now - timedelta(days=365)

        async with await self._get_db_context() as session:
            # Fetch all encounters in the last 365 days in one round-trip
            stmt = (
                select(Encounter)
                .where(
                    Encounter.patient_id == patient_id,
                    Encounter.created_at >= cutoff_365,
                )
                .order_by(Encounter.created_at.desc())
            )
            result = await session.execute(stmt)
            encounters = result.scalars().all()

        enc_30 = 0
        enc_90 = 0
        enc_365 = 0
        ed_count = 0
        latest_encounter_dt: Optional[datetime] = None

        for enc in encounters:
            ts = enc.started_at or enc.created_at
            enc_365 += 1
            if ts >= cutoff_90:
                enc_90 += 1
            if ts >= cutoff_30:
                enc_30 += 1
            # Track ED visits (common encounter_type values)
            if enc.encounter_type and enc.encounter_type.lower() in (
                "emergency", "ed", "emergency_department", "er",
            ):
                ed_count += 1
            # Track most recent encounter time
            if latest_encounter_dt is None or ts > latest_encounter_dt:
                latest_encounter_dt = ts

        days_since_last: Optional[float] = None
        if latest_encounter_dt is not None:
            delta = now - latest_encounter_dt
            days_since_last = round(delta.total_seconds() / 86400, 2)

        return {
            "encounters_30d": enc_30,
            "encounters_90d": enc_90,
            "encounters_365d": enc_365,
            "days_since_last_encounter": days_since_last,
            "ed_visit_count_365d": ed_count,
        }

    async def refresh_patient_features(
        self,
        patient_id: str,
        tenant_id: str = "default",
        ttl: int = 3600,
    ) -> dict[str, Any]:
        """Orchestrate full feature computation and cache refresh.

        Calls each ``compute_*`` method, stores the results in Redis, and
        returns the complete feature payload.
        """
        results: dict[str, Any] = {}

        # 1. Vitals features
        try:
            vitals_features = await self.compute_vitals_features(
                patient_id, tenant_id=tenant_id
            )
            results["vitals"] = vitals_features
            await self.set_features(patient_id, "vitals", vitals_features, tenant_id, ttl)
        except Exception as e:
            logger.error(
                "Failed to compute vitals features for %s: %s", patient_id, e
            )
            vitals_features = {}

        # 2. Risk features (pass pre-computed vitals to avoid double query)
        try:
            risk_features = await self.compute_risk_features(
                patient_id,
                tenant_id=tenant_id,
                vitals_features=vitals_features,
            )
            results["risk"] = risk_features
            await self.set_features(patient_id, "risk", risk_features, tenant_id, ttl)
        except Exception as e:
            logger.error(
                "Failed to compute risk features for %s: %s", patient_id, e
            )

        # 3. Utilization features
        try:
            util_features = await self.compute_utilization_features(
                patient_id, tenant_id=tenant_id
            )
            results["utilization"] = util_features
            await self.set_features(patient_id, "utilization", util_features, tenant_id, ttl)
        except Exception as e:
            logger.error(
                "Failed to compute utilization features for %s: %s",
                patient_id,
                e,
            )

        logger.info(
            "Refreshed features for patient %s (groups: %s)",
            patient_id,
            list(results.keys()),
        )
        return results
