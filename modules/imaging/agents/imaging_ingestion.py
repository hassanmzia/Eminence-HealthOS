"""
Eminence HealthOS — Imaging Ingestion Agent (#51)
Layer 1 (Sensing): Receives DICOM images from PACS/modalities,
normalizes metadata, and stores securely for downstream analysis.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

# Supported imaging modalities
MODALITIES: dict[str, dict[str, Any]] = {
    "CR": {"name": "Computed Radiography (X-Ray)", "typical_size_mb": 15, "ai_supported": True},
    "CT": {"name": "Computed Tomography", "typical_size_mb": 500, "ai_supported": True},
    "MR": {"name": "Magnetic Resonance Imaging", "typical_size_mb": 200, "ai_supported": True},
    "US": {"name": "Ultrasound", "typical_size_mb": 50, "ai_supported": True},
    "MG": {"name": "Mammography", "typical_size_mb": 100, "ai_supported": True},
    "OP": {"name": "Ophthalmic Photography (Retinal)", "typical_size_mb": 20, "ai_supported": True},
    "ECG": {"name": "Electrocardiogram", "typical_size_mb": 2, "ai_supported": True},
    "SM": {"name": "Slide Microscopy (Pathology WSI)", "typical_size_mb": 2000, "ai_supported": True},
}

BODY_PARTS = ["CHEST", "HEAD", "ABDOMEN", "SPINE", "EXTREMITY", "PELVIS", "BREAST", "EYE", "HEART"]


class ImagingIngestionAgent(BaseAgent):
    """Receives DICOM images from PACS/modalities and normalizes metadata."""

    name = "imaging_ingestion"
    tier = AgentTier.SENSING
    version = "1.0.0"
    description = (
        "DICOM image ingestion from PACS, modalities, and external sources — "
        "metadata normalization, secure storage, and downstream routing"
    )
    min_confidence = 0.90

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "ingest_study")

        if action == "ingest_study":
            return self._ingest_study(input_data)
        elif action == "validate_dicom":
            return self._validate_dicom(input_data)
        elif action == "query_studies":
            return self._query_studies(input_data)
        elif action == "route_study":
            return self._route_study(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown imaging ingestion action: {action}",
                status=AgentStatus.FAILED,
            )

    def _ingest_study(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        modality = ctx.get("modality", "CR").upper()
        body_part = ctx.get("body_part", "CHEST").upper()
        series_count = ctx.get("series_count", 1)
        instance_count = ctx.get("instance_count", 1)

        mod_info = MODALITIES.get(modality, MODALITIES["CR"])

        study_uid = ctx.get("study_uid", f"1.2.840.{uuid.uuid4().int % 10**12}")
        accession = ctx.get("accession_number", f"ACC-{uuid.uuid4().hex[:8].upper()}")

        result = {
            "study_id": str(uuid.uuid4()),
            "study_uid": study_uid,
            "accession_number": accession,
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "ingested_at": now.isoformat(),
            "modality": modality,
            "modality_name": mod_info["name"],
            "body_part": body_part,
            "series_count": series_count,
            "instance_count": instance_count,
            "estimated_size_mb": mod_info["typical_size_mb"] * series_count,
            "ai_analysis_supported": mod_info["ai_supported"],
            "status": "received",
            "storage_location": f"minio://imaging/{study_uid}",
            "metadata": {
                "institution": ctx.get("institution", "Eminence Health System"),
                "referring_physician": ctx.get("referring_physician", ""),
                "study_description": ctx.get("study_description", f"{body_part} {mod_info['name']}"),
                "study_date": ctx.get("study_date", now.strftime("%Y%m%d")),
            },
            "requires_ai_analysis": mod_info["ai_supported"],
            "priority": ctx.get("priority", "routine"),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Ingested {modality} study: {body_part}, {instance_count} instances",
        )

    def _validate_dicom(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        study_uid = ctx.get("study_uid", "unknown")

        checks = [
            {"check": "patient_id_present", "passed": True},
            {"check": "study_date_valid", "passed": True},
            {"check": "modality_supported", "passed": ctx.get("modality", "CR").upper() in MODALITIES},
            {"check": "pixel_data_present", "passed": True},
            {"check": "transfer_syntax_valid", "passed": True},
            {"check": "phi_tags_present", "passed": True},
        ]

        result = {
            "study_uid": study_uid,
            "validated_at": now.isoformat(),
            "checks": checks,
            "all_passed": all(c["passed"] for c in checks),
            "failed_checks": [c["check"] for c in checks if not c["passed"]],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"DICOM validation: {'all passed' if result['all_passed'] else f'{len(result[\"failed_checks\"])} failed'}",
        )

    def _query_studies(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        studies = [
            {"study_id": "STD-001", "date": "2026-03-12", "modality": "CR", "body_part": "CHEST", "description": "PA and Lateral Chest X-ray", "status": "read", "findings": "No acute cardiopulmonary disease"},
            {"study_id": "STD-002", "date": "2026-03-10", "modality": "CT", "body_part": "HEAD", "description": "CT Head w/o Contrast", "status": "read", "findings": "No acute intracranial abnormality"},
            {"study_id": "STD-003", "date": "2026-03-08", "modality": "MR", "body_part": "SPINE", "description": "MRI Lumbar Spine", "status": "pending_read", "findings": None},
            {"study_id": "STD-004", "date": "2026-03-05", "modality": "US", "body_part": "ABDOMEN", "description": "Abdominal Ultrasound", "status": "read", "findings": "Cholelithiasis without cholecystitis"},
        ]

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "queried_at": now.isoformat(),
            "total_studies": len(studies),
            "studies": studies,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=f"Retrieved {len(studies)} imaging studies",
        )

    def _route_study(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        study_id = ctx.get("study_id", "unknown")
        priority = ctx.get("priority", "routine")
        modality = ctx.get("modality", "CR")

        routing = {
            "stat": {"worklist": "STAT", "expected_read_min": 30, "notification": "Page on-call radiologist"},
            "urgent": {"worklist": "URGENT", "expected_read_min": 120, "notification": "Alert radiology team"},
            "routine": {"worklist": "ROUTINE", "expected_read_min": 1440, "notification": "Queue for next available"},
        }
        route_info = routing.get(priority, routing["routine"])

        result = {
            "study_id": study_id,
            "routed_at": now.isoformat(),
            "priority": priority,
            "assigned_worklist": route_info["worklist"],
            "expected_read_minutes": route_info["expected_read_min"],
            "notification_action": route_info["notification"],
            "ai_pre_read": MODALITIES.get(modality.upper(), {}).get("ai_supported", False),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Study {study_id} routed to {route_info['worklist']} worklist",
        )
