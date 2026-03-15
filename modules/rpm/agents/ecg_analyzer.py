"""
ECG Analyzer Agent — Tier 2 (Diagnostic / Interpretation).

Analyzes ECG report text to detect STEMI, ST depression, AFib,
QT prolongation, and T-wave changes using rule-based regex extraction.
Triggers emergency protocols for STEMI findings.

Adapted from InHealth ecg_agent (Tier 2 Diagnostic).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.ecg_analyzer")

# LOINC / SNOMED codes for ECG
LOINC_ECG_REPORT = "11524-6"
SNOMED_STEMI = "57054005"
SNOMED_AFIB = "49436004"

# ECG thresholds
QTC_PROLONGED_MS = 470
ST_ELEVATION_MV = 0.1
QRS_WIDE_MS = 120


class ECGAnalyzerAgent(HealthOSAgent):
    """ECG analysis and critical cardiac event detection."""

    def __init__(self) -> None:
        super().__init__(
            name="ecg_analyzer",
            tier=AgentTier.DIAGNOSTIC,
            description=(
                "Analyzes ECG reports for STEMI, NSTEMI, AFib, QT prolongation, "
                "and T-wave changes with lead-level explainability"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.ANOMALY_DETECTION, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        report_text: str = data.get("ecg_report_text", "")
        report_id: str = data.get("report_id", "")
        report_date: str = data.get("report_date", "")

        if not report_text:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_ecg_data",
                rationale="No ECG report text provided",
                confidence=1.0,
            )

        # NLP-based ECG feature extraction
        ecg_features = self._extract_ecg_features(report_text)

        alerts: list[dict[str, Any]] = []
        severity = "LOW"
        emergency = False
        critical_findings: list[str] = []

        # STEMI detection
        if ecg_features.get("st_elevation"):
            emergency = True
            severity = "EMERGENCY"
            stemi_details = ecg_features["st_elevation"]
            critical_findings.append("STEMI pattern")
            alerts.append({
                "severity": "EMERGENCY",
                "message": (
                    f"STEMI DETECTED: ST elevation in leads {stemi_details.get('leads', [])}. "
                    "Activate STEMI protocol. Target door-to-balloon <= 90 min (AHA/ACC 2022)."
                ),
            })

        # ST depression / NSTEMI
        elif ecg_features.get("st_depression"):
            severity = "HIGH"
            critical_findings.append("ST depression (possible NSTEMI/UA)")
            alerts.append({
                "severity": "HIGH",
                "message": (
                    f"ST depression detected in leads {ecg_features['st_depression'].get('leads', [])}. "
                    "Possible NSTEMI/UA. Serial troponins required."
                ),
            })

        # AFib
        if ecg_features.get("afib"):
            if severity not in ("EMERGENCY",):
                severity = "HIGH"
            critical_findings.append("Atrial Fibrillation")
            alerts.append({
                "severity": "HIGH",
                "message": (
                    "Atrial Fibrillation detected. Calculate CHA2DS2-VASc score. "
                    "Rate/rhythm control and anticoagulation per ESC 2023."
                ),
            })

        # QT prolongation
        if ecg_features.get("qt_prolonged"):
            qt_ms = ecg_features["qt_prolonged"].get("qtc_ms", 0)
            if qt_ms and qt_ms > 500:
                emergency = True
                severity = "EMERGENCY"
                critical_findings.append("Critical QTc prolongation (>500ms)")
            alerts.append({
                "severity": "EMERGENCY" if qt_ms and qt_ms > 500 else "HIGH",
                "message": (
                    f"QTc prolongation: {qt_ms}ms (threshold: {QTC_PROLONGED_MS}ms). "
                    "Risk of Torsades de Pointes. Review QT-prolonging medications."
                ),
            })

        # T-wave changes
        if ecg_features.get("t_wave_changes"):
            alerts.append({
                "severity": "LOW",
                "message": (
                    f"T-wave abnormalities: {ecg_features['t_wave_changes'].get('description', '')}. "
                    "Correlate with clinical presentation."
                ),
            })

        recommendations = self._generate_recommendations(ecg_features, critical_findings)

        # LLM interpretation
        ecg_interpretation = None
        try:
            prompt = (
                f"ECG report:\n\n{report_text}\n\n"
                f"Extracted features: {json.dumps(ecg_features, default=str)}\n"
                f"Critical findings: {critical_findings}\n\n"
                "Provide:\n"
                "1. Detailed ECG interpretation with lead-by-lead analysis\n"
                "2. Specific ECG criteria that triggered each finding (explainability)\n"
                "3. Differential diagnosis ranked by probability\n"
                "4. Immediate management steps per AHA/ACC/ESC guidelines\n"
                "5. Additional workup needed"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a cardiology-trained ECG interpretation narrator. "
                    "Reference AHA/ACC STEMI 2022 and ESC AFib 2023 guidelines."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            ecg_interpretation = resp.content
        except Exception:
            logger.warning("LLM ECG interpretation failed; continuing without it")

        rationale_parts = []
        if critical_findings:
            rationale_parts.append(f"Critical: {', '.join(critical_findings)}")
        else:
            rationale_parts.append("No critical ECG findings")

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="ecg_assessment",
            rationale="; ".join(rationale_parts),
            confidence=0.85,
            data={
                "severity": severity,
                "report_id": report_id,
                "ecg_features": ecg_features,
                "critical_findings": critical_findings,
                "ecg_interpretation": ecg_interpretation,
                "report_date": report_date,
                "alerts": alerts,
                "recommendations": recommendations,
            },
            requires_hitl=emergency,
            hitl_reason="Critical ECG finding requires immediate clinical review" if emergency else None,
        )

    # -- ECG feature extraction (preserved from source) ---------------------------

    def _extract_ecg_features(self, text: str) -> dict[str, Any]:
        text_lower = text.lower()
        features: dict[str, Any] = {}

        # ST elevation patterns
        st_elev_patterns = [
            r"st[\s-]*elevation",
            r"st[\s-]*segment[\s-]*elevation",
            r"stemi",
            r"acute[\s-]*mi",
            r"current[\s-]*of[\s-]*injury",
        ]
        if any(re.search(p, text_lower) for p in st_elev_patterns):
            lead_match = re.findall(r"\b(I{1,3}|a[VF]{1,2}|V[1-6])\b", text, re.IGNORECASE)
            features["st_elevation"] = {
                "detected": True,
                "leads": list(set(lead_match[:6])),
                "trigger_patterns": [p for p in st_elev_patterns if re.search(p, text_lower)],
            }

        # ST depression
        if re.search(r"st[\s-]*depression|st[\s-]*segment[\s-]*depression|subendocardial", text_lower):
            lead_match = re.findall(r"\b(I{1,3}|a[VF]{1,2}|V[1-6])\b", text, re.IGNORECASE)
            features["st_depression"] = {
                "detected": True,
                "leads": list(set(lead_match[:6])),
            }

        # AFib
        if re.search(r"atrial[\s-]*fibrillation|a[\s-]*fib|irregular[\s-]*rhythm|absent[\s-]*p[\s-]*wave", text_lower):
            features["afib"] = {
                "detected": True,
                "description": "Irregularly irregular rhythm without discernible P-waves",
            }

        # QT prolongation
        qtc_match = re.search(r"qtc?\s*[=:]\s*(\d{3,4})", text_lower)
        if qtc_match:
            qtc_ms = int(qtc_match.group(1))
            if qtc_ms > QTC_PROLONGED_MS:
                features["qt_prolonged"] = {
                    "detected": True,
                    "qtc_ms": qtc_ms,
                    "threshold_ms": QTC_PROLONGED_MS,
                }
        elif re.search(r"qt[\s-]*prolongation|prolonged[\s-]*qt", text_lower):
            features["qt_prolonged"] = {"detected": True, "qtc_ms": None}

        # T-wave changes
        if re.search(r"t[\s-]*wave[\s-]*(inversion|flattening|changes|abnormal)", text_lower):
            t_match = re.search(r"t[\s-]*wave[\s-]*(inversion|flattening|changes|abnormal)", text_lower)
            features["t_wave_changes"] = {
                "detected": True,
                "description": t_match.group(0) if t_match else "T-wave abnormality",
            }

        return features

    def _generate_recommendations(
        self, features: dict[str, Any], critical_findings: list[str],
    ) -> list[str]:
        recs: list[str] = []
        if features.get("st_elevation"):
            recs.append(
                "STEMI: Activate cath lab. Dual antiplatelet therapy (aspirin 325mg + P2Y12 inhibitor). "
                "Primary PCI target <= 90 min (AHA/ACC 2022)."
            )
        if features.get("st_depression"):
            recs.append(
                "NSTEMI/UA: Serial troponins q3-6h. Anticoagulation (heparin/enoxaparin). "
                "Risk stratify with GRACE score. Early invasive strategy if high-risk."
            )
        if features.get("afib"):
            recs.append(
                "AFib: Rate control (beta-blocker or CCB). Anticoagulation if CHA2DS2-VASc >= 2 (men) "
                "or >= 3 (women) - DOAC preferred (ESC 2023)."
            )
        if features.get("qt_prolonged"):
            recs.append(
                "QTc prolongation: Discontinue/reduce QT-prolonging drugs. "
                "Correct electrolytes (K+, Mg2+). Cardiology/EP consult if >500ms."
            )
        return recs
