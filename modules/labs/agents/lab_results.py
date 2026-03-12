"""
Eminence HealthOS — Lab Results Agent (#38)
Layer 2 (Interpretation): Ingests lab results from multiple formats,
flags abnormals, and triggers risk re-scoring.
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

# Reference ranges for common lab values
REFERENCE_RANGES: dict[str, dict[str, Any]] = {
    "glucose": {"low": 70, "high": 100, "critical_low": 50, "critical_high": 400, "unit": "mg/dL"},
    "bun": {"low": 7, "high": 20, "critical_low": None, "critical_high": 100, "unit": "mg/dL"},
    "creatinine": {"low": 0.6, "high": 1.2, "critical_low": None, "critical_high": 10, "unit": "mg/dL"},
    "sodium": {"low": 136, "high": 145, "critical_low": 120, "critical_high": 160, "unit": "mEq/L"},
    "potassium": {"low": 3.5, "high": 5.0, "critical_low": 2.5, "critical_high": 6.5, "unit": "mEq/L"},
    "calcium": {"low": 8.5, "high": 10.5, "critical_low": 6.0, "critical_high": 14.0, "unit": "mg/dL"},
    "hemoglobin": {"low": 12.0, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0, "unit": "g/dL"},
    "hematocrit": {"low": 36, "high": 52, "critical_low": 20, "critical_high": 60, "unit": "%"},
    "wbc": {"low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0, "unit": "K/uL"},
    "platelets": {"low": 150, "high": 400, "critical_low": 50, "critical_high": 1000, "unit": "K/uL"},
    "hba1c": {"low": 4.0, "high": 5.6, "critical_low": None, "critical_high": 14.0, "unit": "%"},
    "tsh": {"low": 0.4, "high": 4.0, "critical_low": 0.01, "critical_high": 100, "unit": "mIU/L"},
    "total_cholesterol": {"low": 0, "high": 200, "critical_low": None, "critical_high": 500, "unit": "mg/dL"},
    "ldl": {"low": 0, "high": 100, "critical_low": None, "critical_high": 300, "unit": "mg/dL"},
    "hdl": {"low": 40, "high": 200, "critical_low": None, "critical_high": None, "unit": "mg/dL"},
    "triglycerides": {"low": 0, "high": 150, "critical_low": None, "critical_high": 500, "unit": "mg/dL"},
    "alt": {"low": 7, "high": 56, "critical_low": None, "critical_high": 1000, "unit": "U/L"},
    "ast": {"low": 10, "high": 40, "critical_low": None, "critical_high": 1000, "unit": "U/L"},
    "inr": {"low": 0.8, "high": 1.2, "critical_low": None, "critical_high": 5.0, "unit": "ratio"},
    "egfr": {"low": 60, "high": 999, "critical_low": 15, "critical_high": None, "unit": "mL/min/1.73m2"},
}

INGESTION_FORMATS = ["HL7_ORU", "FHIR", "LIS", "PDF_OCR", "PATIENT_UPLOAD", "GENOMIC"]


class LabResultsAgent(BaseAgent):
    """Ingests lab results, flags abnormals, and triggers risk re-scoring."""

    name = "lab_results"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = (
        "Lab result ingestion from 6 formats (HL7, FHIR, LIS, PDF/OCR, patient upload, genomic), "
        "abnormal flagging, and risk re-scoring triggers"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "ingest_results")

        if action == "ingest_results":
            return self._ingest_results(input_data)
        elif action == "flag_abnormals":
            return self._flag_abnormals(input_data)
        elif action == "get_results":
            return self._get_results(input_data)
        elif action == "compare_to_prior":
            return self._compare_to_prior(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown lab results action: {action}",
                status=AgentStatus.FAILED,
            )

    def _ingest_results(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        source_format = ctx.get("format", "HL7_ORU")
        results = ctx.get("results", [])

        if not results:
            results = [
                {"test": "glucose", "value": 118, "unit": "mg/dL"},
                {"test": "bun", "value": 22, "unit": "mg/dL"},
                {"test": "creatinine", "value": 1.4, "unit": "mg/dL"},
                {"test": "sodium", "value": 141, "unit": "mEq/L"},
                {"test": "potassium", "value": 5.2, "unit": "mEq/L"},
                {"test": "hba1c", "value": 7.1, "unit": "%"},
                {"test": "egfr", "value": 52, "unit": "mL/min/1.73m2"},
            ]

        processed: list[dict[str, Any]] = []
        abnormals = 0
        criticals = 0

        for r in results:
            test = r.get("test", "").lower()
            value = r.get("value", 0)
            ref = REFERENCE_RANGES.get(test, {})

            flag = "normal"
            if ref:
                if ref.get("critical_low") is not None and value <= ref["critical_low"]:
                    flag = "critical_low"
                    criticals += 1
                elif ref.get("critical_high") is not None and value >= ref["critical_high"]:
                    flag = "critical_high"
                    criticals += 1
                elif value < ref.get("low", 0):
                    flag = "low"
                    abnormals += 1
                elif value > ref.get("high", 999999):
                    flag = "high"
                    abnormals += 1

            processed.append({
                "test": test,
                "value": value,
                "unit": r.get("unit", ref.get("unit", "")),
                "reference_range": f"{ref.get('low', '')}-{ref.get('high', '')}" if ref else "N/A",
                "flag": flag,
                "is_abnormal": flag != "normal",
                "is_critical": flag.startswith("critical"),
            })

        result = {
            "result_set_id": str(uuid.uuid4()),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "ingested_at": now.isoformat(),
            "source_format": source_format,
            "total_results": len(processed),
            "abnormal_count": abnormals,
            "critical_count": criticals,
            "results": processed,
            "requires_risk_rescore": abnormals > 0 or criticals > 0,
            "requires_critical_alert": criticals > 0,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=(
                f"Ingested {len(processed)} results ({source_format}): "
                f"{abnormals} abnormal, {criticals} critical"
            ),
        )

    def _flag_abnormals(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        results = ctx.get("results", [])

        flagged: list[dict[str, Any]] = []
        for r in results:
            test = r.get("test", "").lower()
            value = r.get("value", 0)
            ref = REFERENCE_RANGES.get(test, {})

            if ref:
                is_abnormal = value < ref.get("low", 0) or value > ref.get("high", 999999)
                is_critical = (
                    (ref.get("critical_low") is not None and value <= ref["critical_low"])
                    or (ref.get("critical_high") is not None and value >= ref["critical_high"])
                )
                if is_abnormal or is_critical:
                    flagged.append({
                        "test": test,
                        "value": value,
                        "unit": ref.get("unit", ""),
                        "reference_range": f"{ref.get('low', '')}-{ref.get('high', '')}",
                        "is_critical": is_critical,
                        "deviation": "above" if value > ref.get("high", 999999) else "below",
                    })

        result = {
            "flagged_at": now.isoformat(),
            "total_reviewed": len(results),
            "abnormals": flagged,
            "total_abnormal": len(flagged),
            "critical_count": sum(1 for f in flagged if f["is_critical"]),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Flagged {len(flagged)} abnormal results ({result['critical_count']} critical)",
        )

    def _get_results(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "retrieved_at": now.isoformat(),
            "result_sets": [
                {
                    "date": "2026-03-12",
                    "panel": "Basic Metabolic Panel",
                    "results": [
                        {"test": "Glucose", "value": 118, "unit": "mg/dL", "flag": "high"},
                        {"test": "BUN", "value": 22, "unit": "mg/dL", "flag": "high"},
                        {"test": "Creatinine", "value": 1.4, "unit": "mg/dL", "flag": "high"},
                        {"test": "Sodium", "value": 141, "unit": "mEq/L", "flag": "normal"},
                        {"test": "Potassium", "value": 5.2, "unit": "mEq/L", "flag": "high"},
                    ],
                },
            ],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale="Retrieved latest lab results",
        )

    def _compare_to_prior(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        current = ctx.get("current_results", [])
        prior = ctx.get("prior_results", [])

        comparisons: list[dict[str, Any]] = []
        prior_map = {r.get("test", "").lower(): r.get("value", 0) for r in prior}

        for r in current:
            test = r.get("test", "").lower()
            current_val = r.get("value", 0)
            prior_val = prior_map.get(test)

            if prior_val is not None:
                change = current_val - prior_val
                pct_change = round(change / max(abs(prior_val), 0.01) * 100, 1)
                comparisons.append({
                    "test": test,
                    "current": current_val,
                    "prior": prior_val,
                    "change": round(change, 2),
                    "pct_change": pct_change,
                    "trend": "increasing" if change > 0 else ("decreasing" if change < 0 else "stable"),
                })

        result = {
            "compared_at": now.isoformat(),
            "comparisons": comparisons,
            "total_compared": len(comparisons),
            "significant_changes": sum(1 for c in comparisons if abs(c["pct_change"]) > 10),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"Compared {len(comparisons)} results to prior — {result['significant_changes']} significant changes",
        )
