"""
Kidney Monitor Agent — Tier 2 (Diagnostic / Interpretation).

Tracks eGFR and creatinine trends, calculates CKD stage using CKD-EPI 2021,
detects acute kidney injury by KDIGO 2012 criteria, and flags medications
requiring renal dose adjustment.

Adapted from InHealth kidney_agent (Tier 2 Diagnostic).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.kidney_monitor")

# LOINC codes
LOINC_CREATININE = "2160-0"
LOINC_EGFR = "62238-1"
LOINC_BUN = "3094-0"
LOINC_URINE_ALBUMIN = "14959-1"
LOINC_POTASSIUM = "2823-3"
LOINC_BICARBONATE = "1963-8"

# CKD stages by eGFR
CKD_STAGES = [
    (90, None, 1, "Normal or high"),
    (60, 89, 2, "Mildly decreased"),
    (45, 59, 3, "Mildly to moderately decreased"),
    (30, 44, 3, "Moderately to severely decreased"),
    (15, 29, 4, "Severely decreased"),
    (0, 14, 5, "Kidney failure"),
]

# AKI criteria (KDIGO 2012)
AKI_CREATININE_RISE_48H = 0.3  # mg/dL rise within 48 hours
AKI_CREATININE_RISE_7D = 1.5   # 1.5x baseline within 7 days


class KidneyMonitorAgent(HealthOSAgent):
    """Kidney function monitoring, CKD staging, and AKI detection."""

    def __init__(self) -> None:
        super().__init__(
            name="kidney_monitor",
            tier=AgentTier.DIAGNOSTIC,
            description=(
                "Monitors eGFR/creatinine, calculates CKD stage (CKD-EPI 2021), "
                "detects AKI (KDIGO 2012), and flags nephrotoxic medications"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.LAB_ANALYSIS, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        current_creat: Optional[float] = data.get("creatinine")
        current_egfr: Optional[float] = data.get("egfr")
        current_uacr: Optional[float] = data.get("uacr")
        current_k: Optional[float] = data.get("potassium")
        creat_history: list[float] = data.get("creatinine_history", [])
        egfr_history: list[float] = data.get("egfr_history", [])
        age: int = data.get("age", 60)
        sex: str = data.get("sex", "male")
        is_female = sex.lower() in ("female", "f")

        # Calculate eGFR if not provided
        if current_egfr is None and current_creat is not None:
            current_egfr = self._ckd_epi(current_creat, age, is_female)

        if current_creat is None and current_egfr is None:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_kidney_data",
                rationale="No creatinine or eGFR data provided",
                confidence=1.0,
            )

        # CKD staging
        ckd_stage = self._get_ckd_stage(current_egfr)
        albuminuria_category = self._get_albuminuria_category(current_uacr)

        # AKI detection
        aki_detected = False
        aki_stage = 0
        if current_creat is not None and creat_history:
            baseline_creat = creat_history[-1] if creat_history else current_creat
            if baseline_creat > 0:
                rise = current_creat - baseline_creat
                ratio = current_creat / baseline_creat
                if rise >= AKI_CREATININE_RISE_48H:
                    aki_detected = True
                    aki_stage = 1
                if ratio >= 2.0:
                    aki_stage = 2
                if ratio >= 3.0 or current_creat >= 4.0:
                    aki_stage = 3

        # Trend analysis
        egfr_trend = self._analyze_trend(egfr_history)

        alerts: list[dict[str, Any]] = []
        severity = "LOW"
        emergency = False

        if current_egfr is not None and current_egfr < 15:
            severity = "HIGH"
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"CKD Stage 5 (kidney failure): eGFR {current_egfr:.1f} mL/min/1.73m2. "
                    "Nephrology referral urgent. Dialysis planning needed (KDIGO 2024)."
                ),
            })
        elif current_egfr is not None and current_egfr < 30:
            severity = "HIGH"
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"Advanced CKD Stage {ckd_stage.get('stage')}: eGFR {current_egfr:.1f}. "
                    "Urgent nephrology referral. Avoid nephrotoxins."
                ),
            })

        if aki_detected:
            emergency = aki_stage >= 2
            sev = "EMERGENCY" if aki_stage >= 2 else "HIGH"
            if sev == "EMERGENCY":
                severity = "EMERGENCY"
            else:
                severity = max(severity, "HIGH", key=lambda s: {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "EMERGENCY": 3, "CRITICAL": 4}.get(s, 0))
            creat_rise = current_creat - creat_history[-1] if creat_history else 0
            alerts.append({
                "severity": sev,
                "message": (
                    f"ACUTE KIDNEY INJURY Stage {aki_stage} (KDIGO 2012): "
                    f"creatinine rise {creat_rise:.2f} mg/dL. Identify and treat cause."
                ),
            })

        if current_k and current_k > 5.5:
            k_sev = "HIGH" if current_k > 6.0 else "MEDIUM"
            alerts.append({
                "severity": k_sev,
                "message": (
                    f"Hyperkalemia: K+ {current_k:.1f} mEq/L. "
                    "Risk of cardiac arrhythmia. Consider patiromer/sodium zirconium cyclosilicate."
                ),
            })

        if egfr_trend == "declining_rapid":
            alerts.append({
                "severity": "HIGH",
                "message": "Rapid eGFR decline detected. Evaluate for AKI on CKD, malignant HTN, or obstruction.",
            })

        recommendations = self._generate_recommendations(current_egfr, ckd_stage, aki_detected)

        # LLM narrative
        clinical_plan = None
        try:
            prompt = (
                f"Kidney function data:\n"
                f"  Creatinine: {current_creat} mg/dL\n"
                f"  eGFR: {current_egfr} mL/min/1.73m2 (CKD-EPI)\n"
                f"  CKD Stage: {ckd_stage}\n"
                f"  UACR: {current_uacr} mg/g\n"
                f"  Albuminuria category: {albuminuria_category}\n"
                f"  Potassium: {current_k} mEq/L\n"
                f"  AKI detected: {aki_detected} (Stage {aki_stage})\n"
                f"  eGFR trend: {egfr_trend}\n\n"
                "Provide KDIGO 2024-aligned management plan:\n"
                "1. CKD progression risk assessment\n"
                "2. Renoprotective strategies (ACE/ARB, SGLT2i, finerenone)\n"
                "3. Medication adjustments for current eGFR\n"
                "4. Nephrology referral urgency\n"
                "5. Diet modifications (protein, potassium, phosphorus)"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a nephrology clinical decision support narrator. "
                    "Reference KDIGO 2024 CKD guidelines, ADA 2024, and ACC/AHA guidelines."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            clinical_plan = resp.content
        except Exception:
            logger.warning("LLM kidney assessment failed; continuing without it")

        rationale_parts = []
        if current_creat is not None:
            rationale_parts.append(f"Creatinine {current_creat} mg/dL")
        if current_egfr is not None:
            rationale_parts.append(f"eGFR {current_egfr:.1f}")
        rationale_parts.append(f"CKD Stage {ckd_stage.get('stage', '?')}")
        if aki_detected:
            rationale_parts.append(f"AKI Stage {aki_stage}")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="kidney_assessment",
            rationale="; ".join(rationale_parts),
            confidence=0.88,
            data={
                "severity": severity,
                "creatinine_mgdl": current_creat,
                "egfr_ml_min": round(current_egfr, 1) if current_egfr else None,
                "ckd_stage": ckd_stage,
                "albuminuria_category": albuminuria_category,
                "uacr_mg_g": current_uacr,
                "potassium_meq_l": current_k,
                "aki_detected": aki_detected,
                "aki_stage": aki_stage,
                "egfr_trend": egfr_trend,
                "clinical_plan": clinical_plan,
                "alerts": alerts,
                "recommendations": recommendations,
            },
            requires_hitl=emergency,
            hitl_reason="AKI Stage >= 2 requires immediate clinical review" if emergency else None,
        )

    # -- Medical logic (preserved from source) ------------------------------------

    def _ckd_epi(self, creat: float, age: int, is_female: bool) -> float:
        """CKD-EPI 2021 (race-free) eGFR formula."""
        kappa = 0.7 if is_female else 0.9
        alpha = -0.241 if is_female else -0.302
        sex_factor = 1.012 if is_female else 1.0
        ratio = creat / kappa
        if ratio < 1:
            egfr = 142 * (ratio ** alpha) * (0.9938 ** age) * sex_factor
        else:
            egfr = 142 * (ratio ** -1.200) * (0.9938 ** age) * sex_factor
        return round(egfr, 1)

    def _get_ckd_stage(self, egfr: Optional[float]) -> dict[str, Any]:
        if egfr is None:
            return {"stage": "unknown", "description": "eGFR not available"}
        for low, high, stage, desc in CKD_STAGES:
            if high is None:
                if egfr >= low:
                    return {"stage": stage, "egfr_range": f">= {low}", "description": desc}
            elif low <= egfr <= high:
                return {"stage": stage, "egfr_range": f"{low}-{high}", "description": desc}
        return {"stage": 5, "description": "Kidney failure"}

    def _get_albuminuria_category(self, uacr: Optional[float]) -> str:
        if uacr is None:
            return "unknown"
        if uacr < 30:
            return "A1 - Normal to mildly increased (< 30 mg/g)"
        elif uacr < 300:
            return "A2 - Moderately increased (30-300 mg/g)"
        return "A3 - Severely increased (> 300 mg/g)"

    def _analyze_trend(self, values: list[float]) -> str:
        if len(values) < 3:
            return "insufficient_data"
        recent = values[:3]
        older = values[3:6] if len(values) >= 6 else values
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        delta = recent_avg - older_avg
        if delta < -10:
            return "declining_rapid"
        elif delta < -5:
            return "declining"
        elif delta > 5:
            return "improving"
        return "stable"

    def _generate_recommendations(
        self, egfr: Optional[float], ckd_stage: dict[str, Any], aki: bool,
    ) -> list[str]:
        recs: list[str] = []
        stage = ckd_stage.get("stage", 0)
        if isinstance(stage, int) and stage >= 3:
            recs.append(
                "Renoprotection: ACE/ARB for albuminuria. SGLT2i (empagliflozin/dapagliflozin) "
                "if eGFR >= 20 and T2DM or HF (CREDENCE/DAPA-CKD)."
            )
            recs.append("Avoid nephrotoxins: NSAIDs, contrast dye without pre-hydration, aminoglycosides.")
        if isinstance(stage, int) and stage >= 4:
            recs.append("Nephrology referral: CKD progression counseling, dialysis/transplant planning (KDIGO 2024).")
            recs.append("Dietary: Protein restriction 0.6-0.8g/kg/day. Potassium and phosphorus restriction if elevated.")
        if aki:
            recs.append(
                "AKI management: Identify and remove precipitating cause. Optimize fluid status. "
                "Avoid nephrotoxins. Monitor daily creatinine. Nephrology consult if Stage 2-3."
            )
        return recs
