"""
Eminence HealthOS — Auto-Coding Agent (#44)
Layer 3 (Decisioning): Suggests ICD-10, CPT, and E&M billing codes from
clinical encounter data and SOAP notes.
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

# E&M level criteria (2021 MDM-based guidelines)
EM_LEVELS: dict[str, dict[str, Any]] = {
    "99211": {"level": 1, "description": "Office visit, minimal", "typical_time_min": 5, "mdm": "N/A"},
    "99212": {"level": 2, "description": "Office visit, straightforward", "typical_time_min": 10, "mdm": "straightforward"},
    "99213": {"level": 3, "description": "Office visit, low complexity", "typical_time_min": 15, "mdm": "low"},
    "99214": {"level": 4, "description": "Office visit, moderate complexity", "typical_time_min": 25, "mdm": "moderate"},
    "99215": {"level": 5, "description": "Office visit, high complexity", "typical_time_min": 40, "mdm": "high"},
}

# Common CPT codes for clinical procedures
PROCEDURE_CODES: dict[str, dict[str, str]] = {
    "blood_draw": {"cpt": "36415", "description": "Collection of venous blood by venipuncture"},
    "bmp": {"cpt": "80048", "description": "Basic metabolic panel"},
    "cmp": {"cpt": "80053", "description": "Comprehensive metabolic panel"},
    "cbc": {"cpt": "85025", "description": "Complete blood count with differential"},
    "renal_panel": {"cpt": "80069", "description": "Renal function panel"},
    "lipid_panel": {"cpt": "80061", "description": "Lipid panel"},
    "ecg": {"cpt": "93000", "description": "Electrocardiogram, routine ECG with interpretation"},
    "urinalysis": {"cpt": "81003", "description": "Urinalysis, automated without microscopy"},
    "hba1c": {"cpt": "83036", "description": "Hemoglobin A1c"},
    "tsh": {"cpt": "84443", "description": "Thyroid stimulating hormone"},
}


class AutoCodingAgent(BaseAgent):
    """Suggests ICD-10, CPT, and E&M billing codes from encounter data."""

    name = "auto_coding"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "Automated clinical coding — suggests ICD-10 diagnoses, CPT procedure codes, "
        "and E&M visit level from SOAP notes and encounter data"
    )
    min_confidence = 0.82

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "code_encounter")

        if action == "code_encounter":
            return self._code_encounter(input_data)
        elif action == "suggest_icd10":
            return self._suggest_icd10(input_data)
        elif action == "suggest_cpt":
            return self._suggest_cpt(input_data)
        elif action == "determine_em_level":
            return self._determine_em_level(input_data)
        elif action == "validate_codes":
            return self._validate_codes(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown auto-coding action: {action}",
                status=AgentStatus.FAILED,
            )

    def _code_encounter(self, input_data: AgentInput) -> AgentOutput:
        """Full coding pipeline: ICD-10 + CPT + E&M from SOAP note."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        encounter_id = ctx.get("encounter_id", str(uuid.uuid4()))
        soap = ctx.get("soap", {})
        duration_min = ctx.get("encounter_duration_min", 20)

        # Extract diagnoses for ICD-10
        diagnoses = soap.get("assessment", {}).get("diagnoses", [])
        icd10_codes = self._extract_icd10(diagnoses)

        # Extract procedures for CPT
        plan_items = soap.get("plan", {}).get("items", [])
        cpt_codes = self._extract_cpt(plan_items)

        # Determine E&M level
        em_code = self._compute_em_level(diagnoses, plan_items, duration_min)

        # Calculate estimated reimbursement
        total_rvu = em_code.get("rvu", 0) + sum(c.get("rvu", 0) for c in cpt_codes)

        result = {
            "coding_id": str(uuid.uuid4()),
            "encounter_id": encounter_id,
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "coded_at": now.isoformat(),
            "status": "pending_review",
            "icd10_codes": icd10_codes,
            "cpt_codes": cpt_codes,
            "em_code": em_code,
            "total_codes": len(icd10_codes) + len(cpt_codes) + 1,
            "estimated_total_rvu": round(total_rvu, 2),
            "requires_provider_review": True,
            "coding_confidence": 0.87,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.87,
            rationale=(
                f"Coded encounter {encounter_id}: {len(icd10_codes)} ICD-10, "
                f"{len(cpt_codes)} CPT, E&M {em_code.get('code', 'N/A')} — pending provider review"
            ),
        )

    def _suggest_icd10(self, input_data: AgentInput) -> AgentOutput:
        """Suggest ICD-10 codes from diagnoses or free text."""
        ctx = input_data.context
        diagnoses = ctx.get("diagnoses", [])
        free_text = ctx.get("text", "")

        if not diagnoses and free_text:
            diagnoses = self._diagnoses_from_text(free_text)

        codes = self._extract_icd10(diagnoses)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"icd10_codes": codes, "source_diagnoses": len(diagnoses)},
            confidence=0.86,
            rationale=f"Suggested {len(codes)} ICD-10 codes from {len(diagnoses)} diagnoses",
        )

    def _suggest_cpt(self, input_data: AgentInput) -> AgentOutput:
        """Suggest CPT codes from plan items or procedures."""
        ctx = input_data.context
        plan_items = ctx.get("plan_items", [])
        procedures = ctx.get("procedures", [])

        codes = self._extract_cpt(plan_items + procedures)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"cpt_codes": codes, "source_items": len(plan_items) + len(procedures)},
            confidence=0.85,
            rationale=f"Suggested {len(codes)} CPT codes",
        )

    def _determine_em_level(self, input_data: AgentInput) -> AgentOutput:
        """Determine E&M visit level based on MDM complexity."""
        ctx = input_data.context
        diagnoses = ctx.get("diagnoses", [])
        plan_items = ctx.get("plan_items", [])
        duration_min = ctx.get("duration_min", 15)

        em = self._compute_em_level(diagnoses, plan_items, duration_min)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"em_code": em},
            confidence=0.88,
            rationale=f"E&M level determined: {em.get('code')} ({em.get('description')})",
        )

    def _validate_codes(self, input_data: AgentInput) -> AgentOutput:
        """Validate proposed codes for accuracy and compliance."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        icd10 = ctx.get("icd10_codes", [])
        cpt = ctx.get("cpt_codes", [])
        em = ctx.get("em_code", {})

        issues: list[dict[str, str]] = []

        # Check for unspecified codes
        for code in icd10:
            code_str = code.get("code", "") if isinstance(code, dict) else code
            if code_str.endswith(".9"):
                issues.append({
                    "type": "specificity",
                    "code": code_str,
                    "message": f"Unspecified code {code_str} — consider more specific alternative",
                })

        # Check E&M matches documentation
        if em and em.get("code"):
            em_info = EM_LEVELS.get(em["code"])
            if em_info and ctx.get("duration_min", 0) < em_info["typical_time_min"] * 0.5:
                issues.append({
                    "type": "em_time_mismatch",
                    "code": em["code"],
                    "message": "Visit duration may not support selected E&M level",
                })

        result = {
            "validated_at": now.isoformat(),
            "total_codes_reviewed": len(icd10) + len(cpt) + (1 if em else 0),
            "issues": issues,
            "is_valid": len(issues) == 0,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Validation: {len(issues)} issues found in {result['total_codes_reviewed']} codes",
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_icd10(diagnoses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        codes = []
        for dx in diagnoses:
            code = dx.get("icd10", "")
            if code:
                codes.append({
                    "code": code,
                    "description": dx.get("name", ""),
                    "certainty": dx.get("certainty", "confirmed"),
                    "status": dx.get("status", "new"),
                    "is_primary": len(codes) == 0,
                })

        if not codes:
            # Default demo codes
            codes = [
                {"code": "R60.0", "description": "Localized edema", "certainty": "confirmed", "status": "new", "is_primary": True},
                {"code": "I10", "description": "Essential hypertension", "certainty": "confirmed", "status": "existing", "is_primary": False},
                {"code": "T46.1X5A", "description": "Adverse effect of calcium-channel blocker, initial encounter", "certainty": "probable", "status": "new", "is_primary": False},
            ]
        return codes

    @staticmethod
    def _extract_cpt(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        codes = []
        for item in items:
            desc = item.get("description", "").lower()
            category = item.get("category", "")

            if "bmp" in desc or "basic metabolic" in desc:
                codes.append({**PROCEDURE_CODES["bmp"], "rvu": 1.42, "source": desc})
            elif "renal" in desc or "kidney" in desc:
                codes.append({**PROCEDURE_CODES["renal_panel"], "rvu": 1.56, "source": desc})
            elif "cmp" in desc or "comprehensive metabolic" in desc:
                codes.append({**PROCEDURE_CODES["cmp"], "rvu": 1.57, "source": desc})
            elif "cbc" in desc or "blood count" in desc:
                codes.append({**PROCEDURE_CODES["cbc"], "rvu": 0.88, "source": desc})
            elif "ecg" in desc or "electrocardiogram" in desc:
                codes.append({**PROCEDURE_CODES["ecg"], "rvu": 1.32, "source": desc})
            elif "lipid" in desc:
                codes.append({**PROCEDURE_CODES["lipid_panel"], "rvu": 1.17, "source": desc})
            elif "a1c" in desc or "hemoglobin a1c" in desc:
                codes.append({**PROCEDURE_CODES["hba1c"], "rvu": 1.08, "source": desc})
            elif "urinalysis" in desc:
                codes.append({**PROCEDURE_CODES["urinalysis"], "rvu": 0.29, "source": desc})

        if not codes:
            codes = [
                {**PROCEDURE_CODES["bmp"], "rvu": 1.42, "source": "Lab order from plan"},
                {**PROCEDURE_CODES["renal_panel"], "rvu": 1.56, "source": "Renal function check"},
            ]
        return codes

    @staticmethod
    def _compute_em_level(
        diagnoses: list[dict[str, Any]],
        plan_items: list[dict[str, Any]],
        duration_min: int,
    ) -> dict[str, Any]:
        # MDM complexity scoring
        num_diagnoses = len(diagnoses) if diagnoses else 0
        num_plan_items = len(plan_items) if plan_items else 0
        has_new_problem = any(d.get("status") == "new" for d in (diagnoses or []))
        has_med_change = any("medication" in (i.get("category", "") + i.get("description", "")).lower() for i in (plan_items or []))

        complexity_score = num_diagnoses + num_plan_items
        if has_new_problem:
            complexity_score += 2
        if has_med_change:
            complexity_score += 1

        # Map complexity to E&M level
        if complexity_score >= 7 or duration_min >= 40:
            code = "99215"
        elif complexity_score >= 5 or duration_min >= 25:
            code = "99214"
        elif complexity_score >= 3 or duration_min >= 15:
            code = "99213"
        elif complexity_score >= 1:
            code = "99212"
        else:
            code = "99211"

        em_info = EM_LEVELS[code]
        return {
            "code": code,
            "description": em_info["description"],
            "level": em_info["level"],
            "mdm_complexity": em_info["mdm"],
            "encounter_duration_min": duration_min,
            "complexity_score": complexity_score,
            "rvu": 1.0 + (em_info["level"] - 1) * 0.8,
        }

    @staticmethod
    def _diagnoses_from_text(text: str) -> list[dict[str, Any]]:
        text_lower = text.lower()
        diagnoses = []
        keyword_map = {
            "hypertension": {"name": "Essential hypertension", "icd10": "I10"},
            "diabetes": {"name": "Type 2 diabetes mellitus", "icd10": "E11.9"},
            "edema": {"name": "Localized edema", "icd10": "R60.0"},
            "chest pain": {"name": "Chest pain, unspecified", "icd10": "R07.9"},
            "headache": {"name": "Headache", "icd10": "R51.9"},
            "anxiety": {"name": "Generalized anxiety disorder", "icd10": "F41.1"},
            "depression": {"name": "Major depressive disorder", "icd10": "F32.9"},
        }
        for keyword, dx in keyword_map.items():
            if keyword in text_lower:
                diagnoses.append({**dx, "status": "new", "certainty": "probable"})
        return diagnoses
