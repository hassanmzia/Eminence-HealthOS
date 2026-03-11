"""
Data ingestion pipeline for HealthOS.

Handles ingestion of vitals from devices, lab results from interfaces,
and FHIR bundles from EHR systems. Routes data to the feature store
and event bus.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("healthos.ingestion")


class IngestionPipeline:
    """Coordinates data ingestion from multiple sources."""

    def __init__(self, feature_store=None, event_producer=None):
        self._feature_store = feature_store
        self._event_producer = event_producer

    async def ingest_vital(
        self,
        patient_id: str,
        loinc_code: str,
        value: float,
        unit: str,
        tenant_id: str = "default",
        device_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> dict:
        """Ingest a single vital sign reading."""
        timestamp = timestamp or datetime.now(timezone.utc)

        # Store observation in database
        observation_data = {
            "patient_id": patient_id,
            "loinc_code": loinc_code,
            "value_quantity": value,
            "value_unit": unit,
            "category": "vital-signs",
            "data_source": "device" if device_id else "manual",
            "device_id": device_id,
            "effective_datetime": timestamp.isoformat(),
            "status": "final",
        }

        try:
            from healthos_platform.config.database import get_db_context
            from shared.models.observation import Observation

            async with get_db_context() as db:
                obs = Observation(
                    tenant_id=tenant_id,
                    patient_id=patient_id,
                    loinc_code=loinc_code,
                    display=self._get_display_name(loinc_code),
                    value_quantity=value,
                    value_unit=unit,
                    category="vital-signs",
                    data_source="device" if device_id else "manual",
                    device_id=device_id,
                    effective_datetime=timestamp,
                    status="final",
                )
                db.add(obs)
                await db.flush()
                observation_data["id"] = str(obs.id)
        except Exception as e:
            logger.error("Failed to persist observation: %s", e)

        # Update feature store
        if self._feature_store:
            await self._feature_store.update_vitals(
                patient_id, loinc_code, value, unit, tenant_id
            )

        # Publish event
        if self._event_producer:
            from shared.events.bus import HealthOSEvent, Topics
            await self._event_producer.publish(
                Topics.VITALS_INGEST,
                HealthOSEvent(
                    event_type="vital.recorded",
                    payload=observation_data,
                    tenant_id=tenant_id,
                    patient_id=patient_id,
                ),
            )

        return observation_data

    async def ingest_lab_result(
        self,
        patient_id: str,
        loinc_code: str,
        value: float,
        unit: str,
        tenant_id: str = "default",
        reference_low: Optional[float] = None,
        reference_high: Optional[float] = None,
    ) -> dict:
        """Ingest a lab result."""
        result_data = {
            "patient_id": patient_id,
            "loinc_code": loinc_code,
            "value_quantity": value,
            "value_unit": unit,
            "category": "laboratory",
            "reference_low": reference_low,
            "reference_high": reference_high,
        }

        try:
            from healthos_platform.config.database import get_db_context
            from shared.models.observation import Observation

            async with get_db_context() as db:
                obs = Observation(
                    tenant_id=tenant_id,
                    patient_id=patient_id,
                    loinc_code=loinc_code,
                    display=self._get_display_name(loinc_code),
                    value_quantity=value,
                    value_unit=unit,
                    category="laboratory",
                    data_source="lab_interface",
                    reference_low=reference_low,
                    reference_high=reference_high,
                    effective_datetime=datetime.now(timezone.utc),
                    status="final",
                )
                db.add(obs)
                await db.flush()
                result_data["id"] = str(obs.id)
        except Exception as e:
            logger.error("Failed to persist lab result: %s", e)

        if self._event_producer:
            from shared.events.bus import HealthOSEvent, Topics
            await self._event_producer.publish(
                Topics.LABS_INGEST,
                HealthOSEvent(
                    event_type="lab.result_received",
                    payload=result_data,
                    tenant_id=tenant_id,
                    patient_id=patient_id,
                ),
            )

        return result_data

    async def ingest_fhir_bundle(
        self,
        bundle: dict,
        tenant_id: str = "default",
    ) -> dict:
        """Ingest a FHIR R4 Bundle resource."""
        results = {"processed": 0, "errors": 0, "resources": []}
        entries = bundle.get("entry", [])

        for entry in entries:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")

            try:
                if resource_type == "Patient":
                    from shared.utils.fhir import from_fhir_patient
                    patient_data = from_fhir_patient(resource)
                    results["resources"].append({"type": "Patient", "status": "processed"})

                elif resource_type == "Observation":
                    # Extract and ingest observation
                    coding = resource.get("code", {}).get("coding", [{}])[0]
                    value_qty = resource.get("valueQuantity", {})
                    subject = resource.get("subject", {}).get("reference", "")
                    patient_id = subject.replace("Patient/", "")

                    if value_qty.get("value") is not None:
                        await self.ingest_vital(
                            patient_id=patient_id,
                            loinc_code=coding.get("code", ""),
                            value=value_qty["value"],
                            unit=value_qty.get("unit", ""),
                            tenant_id=tenant_id,
                        )
                    results["resources"].append({"type": "Observation", "status": "processed"})

                results["processed"] += 1

            except Exception as e:
                results["errors"] += 1
                results["resources"].append({
                    "type": resource_type,
                    "status": "error",
                    "error": str(e),
                })

        return results

    def _get_display_name(self, loinc_code: str) -> str:
        display_names = {
            "8480-6": "Systolic Blood Pressure",
            "8462-4": "Diastolic Blood Pressure",
            "8867-4": "Heart Rate",
            "9279-1": "Respiratory Rate",
            "8310-5": "Body Temperature",
            "2708-6": "Oxygen Saturation",
            "29463-7": "Body Weight",
            "39156-5": "BMI",
            "2345-7": "Glucose",
            "2160-0": "Creatinine",
            "4548-4": "HbA1c",
            "718-7": "Hemoglobin",
            "6690-2": "WBC",
        }
        return display_names.get(loinc_code, f"Observation ({loinc_code})")
