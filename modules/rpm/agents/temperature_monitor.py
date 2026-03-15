"""
Temperature Monitor Agent — Tier 1 (Monitoring).

Monitors body temperature from vitals data, detects fever and hypothermia,
cross-references with lab markers (WBC, CRP) for infection risk assessment,
and performs sepsis screening via SIRS criteria.

Adapted from InHealth temperature_agent (Tier 1 Monitoring).
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

logger = logging.getLogger("healthos.agent.temperature_monitor")

# LOINC codes
LOINC_TEMP = "8310-5"
LOINC_WBC = "6690-2"
LOINC_CRP = "1988-5"
LOINC_PROCALCITONIN = "33959-8"

# Clinical thresholds (Celsius)
TEMP_HYPOTHERMIA_CRITICAL = 35.0
TEMP_HYPOTHERMIA = 35.5
TEMP_FEVER = 38.0
TEMP_HIGH_FEVER = 39.5
TEMP_CRITICAL = 41.0

# Lab thresholds
WBC_HIGH = 11.0  # x10^9/L
WBC_LOW = 4.0
CRP_ELEVATED = 10.0  # mg/L
CRP_HIGH = 100.0


class TemperatureMonitorAgent(HealthOSAgent):
    """Temperature monitoring and infection risk assessment."""

    def __init__(self) -> None:
        super().__init__(
            name="temperature_monitor",
            tier=AgentTier.MONITORING,
            description=(
                "Monitors body temperature, detects fever/hypothermia, "
                "cross-references WBC/CRP for infection risk, and screens for sepsis (SIRS)"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.VITAL_MONITORING, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        current_temp: Optional[float] = data.get("temperature")
        current_wbc: Optional[float] = data.get("wbc")
        current_crp: Optional[float] = data.get("crp")
        temp_history: list[float] = data.get("temp_history", [])
        conditions: list[str] = data.get("conditions", [])
        medications: list[str] = data.get("medications", [])
        allergies: list[str] = data.get("allergies", [])

        if current_temp is None:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_temperature_data",
                rationale="No temperature reading provided",
                confidence=1.0,
            )

        alerts: list[dict[str, Any]] = []
        severity = "LOW"
        emergency = False

        # -- Temperature classification --
        if current_temp >= TEMP_CRITICAL:
            emergency = True
            severity = "EMERGENCY"
            alerts.append({
                "severity": "EMERGENCY",
                "message": (
                    f"HYPERPYREXIA: Temperature {current_temp:.1f} C "
                    f"(>= {TEMP_CRITICAL} C). Life-threatening. Immediate cooling required."
                ),
            })
        elif current_temp >= TEMP_HIGH_FEVER:
            severity = "HIGH"
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"High fever: {current_temp:.1f} C. "
                    "Infectious etiology likely. Blood cultures and broad-spectrum coverage may be needed."
                ),
            })
        elif current_temp >= TEMP_FEVER:
            severity = "MEDIUM"
            alerts.append({
                "severity": "MEDIUM",
                "message": f"Fever detected: {current_temp:.1f} C (>= {TEMP_FEVER} C). Monitor and evaluate source.",
            })
        elif current_temp <= TEMP_HYPOTHERMIA_CRITICAL:
            emergency = True
            severity = "EMERGENCY"
            alerts.append({
                "severity": "EMERGENCY",
                "message": (
                    f"CRITICAL HYPOTHERMIA: Temperature {current_temp:.1f} C "
                    f"(< {TEMP_HYPOTHERMIA_CRITICAL} C). Risk of cardiac arrest."
                ),
            })
        elif current_temp <= TEMP_HYPOTHERMIA:
            severity = "HIGH"
            alerts.append({
                "severity": "HIGH",
                "message": f"Hypothermia: Temperature {current_temp:.1f} C. Warming measures required.",
            })

        # -- Infection risk --
        infection_risk = self._assess_infection_risk(current_temp, current_wbc, current_crp)
        if infection_risk["level"] in ("HIGH", "CRITICAL"):
            if infection_risk["level"] == "CRITICAL":
                emergency = True
                severity = "EMERGENCY"
            alerts.append({
                "severity": "HIGH" if infection_risk["level"] == "HIGH" else "EMERGENCY",
                "message": f"Infection risk {infection_risk['level']}: {infection_risk['rationale']}",
            })

        # -- Sepsis screening (SIRS) --
        sirs_criteria_met = self._check_sirs(current_temp, current_wbc)
        if sirs_criteria_met >= 2:
            emergency = True
            severity = "EMERGENCY"
            alerts.append({
                "severity": "EMERGENCY",
                "message": (
                    f"SEPSIS SCREEN POSITIVE: {sirs_criteria_met}/4 SIRS criteria met. "
                    "Evaluate for sepsis (Surviving Sepsis Campaign 2021)."
                ),
            })

        # -- Clinical flags --
        patient_clinical = self._build_clinical_flags(conditions, medications, allergies)

        # -- Recommendations --
        recommendations = self._generate_recommendations(
            current_temp, infection_risk, sirs_criteria_met, patient_clinical,
        )

        # -- LLM narrative --
        clinical_assessment = None
        try:
            prompt = (
                f"Patient temperature and infection markers:\n"
                f"  Temperature: {current_temp} C\n"
                f"  WBC: {current_wbc} x10^9/L (normal: 4.0-11.0)\n"
                f"  CRP: {current_crp} mg/L (normal: < 10)\n"
                f"  SIRS criteria met: {sirs_criteria_met}/4\n"
                f"  Infection risk: {infection_risk}\n"
                f"  Clinical flags: {json.dumps(patient_clinical)}\n\n"
                "Provide:\n"
                "1. Most likely infectious source\n"
                "2. Workup recommendations\n"
                "3. Empiric treatment consideration (check allergies/contraindications)\n"
                "4. Monitoring plan personalized to comorbidities\n"
                "5. Contraindication warnings based on current medications"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical temperature and infection monitoring narrator. "
                    "Reference Surviving Sepsis Campaign 2021 and IDSA fever management guidelines."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            clinical_assessment = resp.content
        except Exception:
            logger.warning("LLM temperature assessment generation failed; continuing without it")

        rationale_parts = [f"Temperature {current_temp:.1f} C"]
        if current_wbc is not None:
            rationale_parts.append(f"WBC {current_wbc}")
        if current_crp is not None:
            rationale_parts.append(f"CRP {current_crp}")
        if sirs_criteria_met >= 2:
            rationale_parts.append(f"SIRS {sirs_criteria_met}/4")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="temperature_assessment",
            rationale="; ".join(rationale_parts),
            confidence=0.90,
            data={
                "severity": severity,
                "temperature_celsius": current_temp,
                "temperature_fahrenheit": round(current_temp * 9 / 5 + 32, 1),
                "wbc": current_wbc,
                "crp_mgL": current_crp,
                "sirs_criteria_met": sirs_criteria_met,
                "infection_risk": infection_risk,
                "clinical_assessment": clinical_assessment,
                "alerts": alerts,
                "recommendations": recommendations,
            },
            requires_hitl=emergency,
            hitl_reason="Emergency temperature finding requires immediate review" if emergency else None,
        )

    # -- Medical logic (preserved from source) ------------------------------------

    def _assess_infection_risk(
        self, temp: Optional[float], wbc: Optional[float], crp: Optional[float],
    ) -> dict[str, Any]:
        score = 0
        reasons: list[str] = []
        if temp and temp >= TEMP_FEVER:
            score += 2
            reasons.append(f"Fever {temp:.1f} C")
        if wbc and wbc > WBC_HIGH:
            score += 2
            reasons.append(f"Leukocytosis WBC {wbc:.1f}")
        elif wbc and wbc < WBC_LOW:
            score += 1
            reasons.append(f"Leukopenia WBC {wbc:.1f} (immunocompromised)")
        if crp and crp >= CRP_HIGH:
            score += 2
            reasons.append(f"Markedly elevated CRP {crp:.1f} mg/L")
        elif crp and crp >= CRP_ELEVATED:
            score += 1
            reasons.append(f"Elevated CRP {crp:.1f} mg/L")

        if score >= 4:
            level = "CRITICAL"
        elif score >= 2:
            level = "HIGH"
        elif score >= 1:
            level = "MEDIUM"
        else:
            level = "LOW"
        return {
            "level": level,
            "score": score,
            "rationale": "; ".join(reasons) if reasons else "No significant infection markers",
        }

    def _check_sirs(self, temp: Optional[float], wbc: Optional[float]) -> int:
        count = 0
        if temp and (temp > 38.0 or temp < 36.0):
            count += 1
        if wbc and (wbc > 12.0 or wbc < 4.0):
            count += 1
        return count

    def _build_clinical_flags(
        self, conditions: list[str], medications: list[str], allergies: list[str],
    ) -> dict[str, Any]:
        cond_lower = [c.lower() for c in conditions]
        med_lower = [m.lower() for m in medications]
        allergy_lower = [a.lower() for a in allergies]

        has_ckd = any(k in t for t in cond_lower for k in ["chronic kidney", "ckd", "renal failure"])
        has_liver = any(k in t for t in cond_lower for k in ["cirrhosis", "hepatic", "liver disease"])
        has_hf = any(k in t for t in cond_lower for k in ["heart failure", "chf", "cardiomyopathy"])
        is_immunocompromised = any(
            k in t for t in cond_lower
            for k in ["hiv", "immunodeficiency", "transplant", "leukemia", "lymphoma"]
        )
        on_anticoagulants = any(
            k in t for t in med_lower
            for k in ["warfarin", "heparin", "enoxaparin", "rivaroxaban", "apixaban", "dabigatran"]
        )
        nsaid_allergy = any(k in t for t in allergy_lower for k in ["nsaid", "ibuprofen", "naproxen"])
        acetaminophen_allergy = any(k in t for t in allergy_lower for k in ["acetaminophen", "paracetamol"])
        penicillin_allergy = any(k in t for t in allergy_lower for k in ["penicillin", "amoxicillin"])
        sulfa_allergy = any(k in t for t in allergy_lower for k in ["sulfa", "sulfamethoxazole"])

        return {
            "has_ckd": has_ckd,
            "has_liver_disease": has_liver,
            "has_heart_failure": has_hf,
            "is_immunocompromised": is_immunocompromised,
            "on_anticoagulants": on_anticoagulants,
            "nsaid_allergy": nsaid_allergy,
            "acetaminophen_allergy": acetaminophen_allergy,
            "penicillin_allergy": penicillin_allergy,
            "sulfa_allergy": sulfa_allergy,
        }

    def _generate_recommendations(
        self,
        temp: Optional[float],
        infection_risk: dict[str, Any],
        sirs: int,
        pc: dict[str, Any],
    ) -> list[str]:
        recs: list[str] = []
        if temp and temp >= TEMP_FEVER:
            if pc.get("acetaminophen_allergy"):
                if not pc.get("nsaid_allergy") and not pc.get("has_ckd") and not pc.get("on_anticoagulants"):
                    recs.append("Fever management: Ibuprofen 400mg q6h PRN (acetaminophen allergy). Adequate hydration.")
                else:
                    recs.append("Fever management: Physical cooling measures. Both acetaminophen and NSAIDs contraindicated.")
            elif pc.get("has_liver_disease"):
                recs.append("Fever management: Acetaminophen 500mg q8h PRN (REDUCED DOSE - liver disease). Max 2g/day.")
            else:
                contraindications = []
                if pc.get("has_ckd"):
                    contraindications.append("CKD")
                if pc.get("on_anticoagulants"):
                    contraindications.append("anticoagulant therapy")
                if pc.get("nsaid_allergy"):
                    contraindications.append("NSAID allergy")
                nsaid_warning = (
                    f" AVOID NSAIDs ({', '.join(contraindications)})."
                    if contraindications
                    else " Avoid NSAIDs if CKD, GI risk, or anticoagulant use."
                )
                recs.append(f"Fever management: Acetaminophen 650mg q6h PRN.{nsaid_warning} Adequate hydration.")
            recs.append("Workup: Blood cultures x2, CBC, BMP, UA/UC, chest X-ray if respiratory symptoms.")
            if pc.get("is_immunocompromised"):
                recs.append(
                    "IMMUNOCOMPROMISED PATIENT: Lower threshold for empiric antibiotics. "
                    "Consider fungal and atypical infections. ID consultation recommended."
                )

        if sirs >= 2:
            if pc.get("has_heart_failure"):
                recs.append(
                    "SEPSIS BUNDLE (HF-ADAPTED): Cautious IV crystalloid 10-15 mL/kg. "
                    "Reassess after each 250mL bolus. Broad-spectrum antibiotics within 1 hour."
                )
            else:
                recs.append(
                    "SEPSIS BUNDLE: 30 mL/kg IV crystalloid within 3 hours. "
                    "Broad-spectrum antibiotics within 1 hour. Serial lactate (SSC 2021)."
                )
            allergy_warnings = []
            if pc.get("penicillin_allergy"):
                allergy_warnings.append("PENICILLIN ALLERGY - avoid beta-lactams")
            if pc.get("sulfa_allergy"):
                allergy_warnings.append("SULFA ALLERGY - avoid TMP-SMX")
            if allergy_warnings:
                recs.append(f"ALLERGY ALERT for empiric antibiotics: {'; '.join(allergy_warnings)}.")
            if pc.get("has_ckd"):
                recs.append("RENAL DOSING REQUIRED: Adjust antibiotic doses for renal function.")

        if infection_risk.get("level") in ("HIGH", "CRITICAL"):
            recs.append("Infectious disease consultation recommended. Consider procalcitonin-guided therapy.")

        return recs
