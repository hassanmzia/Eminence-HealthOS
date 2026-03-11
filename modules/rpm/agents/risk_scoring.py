"""
Eminence HealthOS — Risk Scoring Agent
Layer 3 (Decisioning): Computes patient deterioration risk scores using
weighted clinical factors and optional ML models.
"""

from __future__ import annotations

import math
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
    AnomalyDetection,
    NormalizedVital,
    PipelineState,
    RiskAssessment,
    Severity,
)


# Weighted risk factors for rule-based scoring
RISK_WEIGHTS: dict[str, float] = {
    "critical_anomaly": 0.35,
    "high_anomaly": 0.20,
    "moderate_anomaly": 0.10,
    "vital_trend_declining": 0.15,
    "multiple_vital_types_abnormal": 0.10,
    "comorbidity_count": 0.05,
    "age_factor": 0.05,
}

# Clinical risk modifiers per vital type
VITAL_RISK_WEIGHTS: dict[str, float] = {
    "heart_rate": 0.20,
    "blood_pressure": 0.25,
    "glucose": 0.15,
    "spo2": 0.25,
    "temperature": 0.10,
    "respiratory_rate": 0.20,
}


class RiskScoringAgent(BaseAgent):
    name = "risk_scoring"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Computes patient deterioration risk from vitals, anomalies, and clinical context"
    min_confidence = 0.7

    async def process(self, input_data: AgentInput) -> AgentOutput:
        anomalies = input_data.context.get("anomalies", [])
        vitals = input_data.context.get("normalized_vitals", [])

        score, factors = self._compute_score_raw(anomalies, vitals)
        risk_level = self._score_to_level(score)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "score": round(score, 4),
                "risk_level": risk_level.value,
                "factors": factors,
            },
            confidence=0.85,
            rationale=f"Risk score {score:.2f} ({risk_level.value}) based on {len(factors)} factors",
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Compute risk from pipeline state anomalies and vitals."""
        score, factors = self._compute_score(state.anomalies, state.normalized_vitals, state)
        risk_level = self._score_to_level(score)

        recommendations = self._generate_recommendations(score, risk_level, factors)

        assessment = RiskAssessment(
            patient_id=state.patient_id,
            org_id=state.org_id,
            score_type="deterioration",
            score=round(score, 4),
            risk_level=risk_level,
            contributing_factors=factors,
            model_version=self.version,
            recommendations=recommendations,
        )

        state.risk_assessments.append(assessment)
        state.executed_agents.append(self.name)
        return state

    def _compute_score(
        self,
        anomalies: list[AnomalyDetection],
        vitals: list[NormalizedVital],
        state: PipelineState,
    ) -> tuple[float, list[dict[str, Any]]]:
        """Compute weighted risk score from anomalies and clinical context."""
        score = 0.0
        factors: list[dict[str, Any]] = []

        # Factor 1: Anomaly severity
        critical_count = sum(1 for a in anomalies if a.severity == Severity.CRITICAL)
        high_count = sum(1 for a in anomalies if a.severity == Severity.HIGH)
        moderate_count = sum(1 for a in anomalies if a.severity == Severity.MODERATE)

        if critical_count > 0:
            contrib = min(1.0, critical_count * 0.5) * RISK_WEIGHTS["critical_anomaly"]
            score += contrib
            factors.append({
                "factor": "critical_anomalies",
                "count": critical_count,
                "weight": RISK_WEIGHTS["critical_anomaly"],
                "contribution": round(contrib, 4),
            })

        if high_count > 0:
            contrib = min(1.0, high_count * 0.4) * RISK_WEIGHTS["high_anomaly"]
            score += contrib
            factors.append({
                "factor": "high_anomalies",
                "count": high_count,
                "weight": RISK_WEIGHTS["high_anomaly"],
                "contribution": round(contrib, 4),
            })

        if moderate_count > 0:
            contrib = min(1.0, moderate_count * 0.3) * RISK_WEIGHTS["moderate_anomaly"]
            score += contrib
            factors.append({
                "factor": "moderate_anomalies",
                "count": moderate_count,
                "weight": RISK_WEIGHTS["moderate_anomaly"],
                "contribution": round(contrib, 4),
            })

        # Factor 2: Multiple vital types affected
        affected_types = set(a.vital_type.value for a in anomalies)
        if len(affected_types) > 1:
            contrib = min(1.0, len(affected_types) / 4) * RISK_WEIGHTS["multiple_vital_types_abnormal"]
            score += contrib
            factors.append({
                "factor": "multiple_vital_types_abnormal",
                "types": list(affected_types),
                "weight": RISK_WEIGHTS["multiple_vital_types_abnormal"],
                "contribution": round(contrib, 4),
            })

        # Factor 3: Patient comorbidities (from context)
        conditions = state.patient_context.get("conditions", [])
        if conditions:
            contrib = min(1.0, len(conditions) / 5) * RISK_WEIGHTS["comorbidity_count"]
            score += contrib
            factors.append({
                "factor": "comorbidities",
                "count": len(conditions),
                "weight": RISK_WEIGHTS["comorbidity_count"],
                "contribution": round(contrib, 4),
            })

        return min(1.0, score), factors

    def _compute_score_raw(
        self, anomalies: list[dict], vitals: list[dict]
    ) -> tuple[float, list[dict[str, Any]]]:
        """Compute score from raw dict data."""
        score = 0.0
        factors: list[dict[str, Any]] = []

        severity_counts: dict[str, int] = {}
        for a in anomalies:
            sev = a.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        for sev, count in severity_counts.items():
            weight_key = f"{sev}_anomaly"
            weight = RISK_WEIGHTS.get(weight_key, 0.05)
            contrib = min(1.0, count * 0.4) * weight
            score += contrib
            factors.append({"factor": weight_key, "count": count, "contribution": round(contrib, 4)})

        return min(1.0, score), factors

    def _score_to_level(self, score: float) -> Severity:
        if score >= 0.75:
            return Severity.CRITICAL
        elif score >= 0.5:
            return Severity.HIGH
        elif score >= 0.25:
            return Severity.MODERATE
        return Severity.LOW

    def _generate_recommendations(
        self, score: float, risk_level: Severity, factors: list[dict[str, Any]]
    ) -> list[str]:
        """Generate clinical action recommendations based on risk."""
        recommendations = []

        if risk_level == Severity.CRITICAL:
            recommendations.extend([
                "Immediate clinical review recommended",
                "Consider initiating telehealth encounter",
                "Notify assigned care team",
            ])
        elif risk_level == Severity.HIGH:
            recommendations.extend([
                "Schedule clinical review within 4 hours",
                "Increase monitoring frequency",
                "Review current medications",
            ])
        elif risk_level == Severity.MODERATE:
            recommendations.extend([
                "Continue standard monitoring",
                "Schedule follow-up within 24 hours",
            ])
        else:
            recommendations.append("Maintain current care plan")

        return recommendations
