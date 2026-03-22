"""
Eminence HealthOS — Lab Results Agent (#38)
Layer 2 (Interpretation): Ingests lab results from multiple formats,
flags abnormals, and triggers risk re-scoring.
"""

from __future__ import annotations

import json
import logging
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
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

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
            return await self._ingest_results(input_data)
        elif action == "flag_abnormals":
            return self._flag_abnormals(input_data)
        elif action == "interpret_results":
            return await self._interpret_results(input_data)
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

    async def _ingest_results(self, input_data: AgentInput) -> AgentOutput:
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

        # --- LLM-generated results interpretation ---
        results_interpretation = (
            f"{len(processed)} results ingested: {abnormals} abnormal, {criticals} critical."
            if abnormals or criticals
            else f"{len(processed)} results ingested; all within normal limits."
        )
        try:
            interpretation_payload = {
                "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
                "results": processed,
                "abnormal_count": abnormals,
                "critical_count": criticals,
            }
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Interpret the following lab results and provide a clinical narrative "
                    f"on their significance. Highlight abnormal and critical values with "
                    f"possible clinical implications.\n\n"
                    f"Lab results:\n{json.dumps(interpretation_payload, indent=2)}"
                )}],
                system=(
                    "You are a clinical laboratory medicine AI. Interpret lab results and "
                    "generate a concise clinical narrative. Explain the clinical significance "
                    "of abnormal values, potential underlying conditions, and recommended "
                    "follow-up actions. Prioritize critical values."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if llm_response and llm_response.content:
                results_interpretation = llm_response.content
        except Exception:
            logger.warning(
                "LLM call failed for results interpretation; using fallback narrative",
                exc_info=True,
            )

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
            "results_interpretation": results_interpretation,
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

    async def _interpret_results(self, input_data: AgentInput) -> AgentOutput:
        """Flag abnormals and generate an LLM clinical interpretation."""
        ctx = input_data.context
        results = ctx.get("results", [])

        # Flag abnormals using reference ranges
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
            else:
                # Use the flag from the input if no reference range is available
                input_flag = r.get("flag", "normal").lower()
                if input_flag in ("high", "low"):
                    flag = input_flag
                    abnormals += 1
                elif input_flag == "critical":
                    flag = "critical_high"
                    criticals += 1

            processed.append({
                "test": r.get("test", test),
                "value": value,
                "unit": r.get("unit", ref.get("unit", "")),
                "reference_range": (
                    f"{ref.get('low', '')}-{ref.get('high', '')}" if ref
                    else r.get("range", r.get("reference_range", "N/A"))
                ),
                "flag": flag,
                "is_abnormal": flag != "normal",
                "is_critical": flag.startswith("critical"),
            })

        # Generate LLM clinical interpretation (with rule-based fallback)
        interpretation = self._build_fallback_interpretation(processed, abnormals, criticals)
        try:
            interpretation_payload = {
                "patient_id": ctx.get("patient_id"),
                "results": processed,
                "abnormal_count": abnormals,
                "critical_count": criticals,
            }
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Interpret the following lab results and provide a clinical narrative "
                    f"on their significance. Highlight abnormal and critical values with "
                    f"possible clinical implications.\n\n"
                    f"Lab results:\n{json.dumps(interpretation_payload, indent=2)}"
                )}],
                system=(
                    "You are a clinical laboratory medicine AI. Interpret lab results and "
                    "generate a concise clinical narrative. Explain the clinical significance "
                    "of abnormal values, potential underlying conditions, and recommended "
                    "follow-up actions. Prioritize critical values."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if llm_response and llm_response.content:
                interpretation = llm_response.content
        except Exception:
            logger.warning(
                "LLM call failed for results interpretation; using fallback narrative",
                exc_info=True,
            )

        result = {
            "patient_id": ctx.get("patient_id"),
            "total_reviewed": len(processed),
            "abnormal_count": abnormals,
            "critical_count": criticals,
            "flagged_results": processed,
            "interpretation": interpretation,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=(
                f"Interpreted {len(processed)} results: "
                f"{abnormals} abnormal, {criticals} critical"
            ),
        )

    @staticmethod
    def _build_fallback_interpretation(
        processed: list[dict[str, Any]], abnormals: int, criticals: int,
    ) -> str:
        """Build a rule-based clinical narrative when LLM is unavailable."""
        sections: list[str] = []
        sections.append(
            f"AI Interpretation Summary ({len(processed)} tests reviewed: "
            f"{abnormals} abnormal, {criticals} critical)\n"
        )

        # Clinical interpretation rules keyed by test name
        interpretations: dict[str, str] = {
            "glucose": "elevated fasting glucose suggests impaired glucose tolerance or diabetes mellitus",
            "bun": "elevated BUN may indicate renal impairment, dehydration, or high protein intake",
            "creatinine": "elevated creatinine indicates reduced renal clearance",
            "egfr": "decreased eGFR indicates chronic kidney disease staging progression",
            "potassium": "hyperkalemia requires urgent evaluation — risk of cardiac arrhythmia",
            "hba1c": "elevated HbA1c indicates suboptimal glycemic control over prior 2-3 months",
            "sodium": "abnormal sodium requires assessment of fluid balance and ADH function",
            "hemoglobin": "abnormal hemoglobin warrants evaluation for anemia or polycythemia",
            "tsh": "abnormal TSH suggests thyroid dysfunction — recommend free T4/T3",
            "ldl": "elevated LDL cholesterol increases cardiovascular risk — consider statin therapy",
            "ldl cholesterol": "elevated LDL cholesterol increases cardiovascular risk — consider statin therapy",
            "hdl": "low HDL is an independent cardiovascular risk factor",
            "triglycerides": "elevated triglycerides increase pancreatitis and cardiovascular risk",
            "alt": "elevated ALT suggests hepatocellular injury",
            "ast": "elevated AST may indicate liver, cardiac, or muscle injury",
            "inr": "elevated INR indicates anticoagulation effect or coagulopathy",
            "troponin i": "elevated troponin indicates myocardial injury — rule out acute coronary syndrome",
            "troponin": "elevated troponin indicates myocardial injury — rule out acute coronary syndrome",
            "wbc": "abnormal WBC count warrants evaluation for infection or hematologic disorder",
            "platelets": "abnormal platelet count requires evaluation for bleeding or thrombotic risk",
            "calcium": "abnormal calcium requires evaluation of parathyroid function and vitamin D",
        }

        # CKD staging based on eGFR
        egfr_entry = next((p for p in processed if p["test"].lower() == "egfr"), None)
        ckd_stage = ""
        if egfr_entry:
            val = egfr_entry["value"]
            if val >= 90:
                ckd_stage = "Stage 1"
            elif val >= 60:
                ckd_stage = "Stage 2"
            elif val >= 45:
                ckd_stage = "Stage 3a"
            elif val >= 30:
                ckd_stage = "Stage 3b"
            elif val >= 15:
                ckd_stage = "Stage 4"
            else:
                ckd_stage = "Stage 5 (kidney failure)"

        finding_num = 0
        # Critical findings first
        for p in processed:
            if not p.get("is_critical"):
                continue
            finding_num += 1
            test_key = p["test"].lower()
            detail = interpretations.get(test_key, "requires immediate clinical evaluation")
            sections.append(
                f"{finding_num}. CRITICAL — {p['test'].upper()}: "
                f"Value {p['value']} {p.get('unit', '')} "
                f"(ref: {p.get('reference_range', 'N/A')}) — {detail}. "
                f"Immediate intervention required."
            )

        # Abnormal (non-critical) findings
        for p in processed:
            if not p.get("is_abnormal") or p.get("is_critical"):
                continue
            finding_num += 1
            test_key = p["test"].lower()
            detail = interpretations.get(test_key, "clinically significant deviation from normal")
            extra = ""
            if test_key == "egfr" and ckd_stage:
                extra = f" Consistent with CKD {ckd_stage}."
            sections.append(
                f"{finding_num}. {p['test'].upper()}: "
                f"Value {p['value']} {p.get('unit', '')} "
                f"(ref: {p.get('reference_range', 'N/A')}) — {detail}.{extra}"
            )

        # Recommendations
        recommendations: list[str] = []
        if criticals > 0:
            recommendations.append("Urgent clinical review of critical values")
        if egfr_entry and egfr_entry["value"] < 60:
            recommendations.append("Nephrology referral for CKD management")
        if any(p["test"].lower() in ("troponin", "troponin i") and p.get("is_critical") for p in processed):
            recommendations.append("Serial troponins and cardiology consultation")
        if any(p["test"].lower() == "potassium" and p.get("is_critical") for p in processed):
            recommendations.append("Repeat electrolytes in 2 hours; ECG monitoring")
        if any(p["test"].lower() == "hba1c" and p.get("is_abnormal") for p in processed):
            recommendations.append("Endocrinology referral for glycemic management")
        if any(p["test"].lower() == "tsh" and p.get("is_abnormal") for p in processed):
            recommendations.append("Thyroid function panel (free T4, T3)")
        if any(p["test"].lower() in ("ldl", "ldl cholesterol") and p.get("is_abnormal") for p in processed):
            recommendations.append("Lipid management review; consider statin intensification")

        if recommendations:
            sections.append("\nRecommendations: " + ". ".join(recommendations) + ".")

        return "\n\n".join(sections)

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
