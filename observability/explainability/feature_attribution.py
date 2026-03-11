"""
Feature Attribution Engine for HealthOS Agent Explainability.

Provides SHAP-style feature importance analysis for agent decisions,
including per-domain contribution breakdown, counterfactual analysis,
and natural language explanation generation.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("healthos.observability.explainability")


@dataclass
class FeatureContribution:
    """A single feature's contribution to a decision."""
    feature: str
    value: float          # Raw feature value
    contribution: float   # Contribution to final score (positive = risk-increasing)
    direction: str        # "positive" (protective) or "negative" (risk-increasing)
    baseline: float = 0.0  # Population baseline for this feature
    percentile: float = None  # Where this patient falls in population distribution
    category: str = ""    # Feature category (vitals, labs, demographics, sdoh, etc.)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "feature": self.feature,
            "value": self.value,
            "contribution": round(self.contribution, 4),
            "direction": self.direction,
        }
        if self.baseline:
            d["baseline"] = round(self.baseline, 4)
        if self.percentile is not None:
            d["percentile"] = round(self.percentile, 2)
        if self.category:
            d["category"] = self.category
        return d


@dataclass
class AttributionResult:
    """Complete attribution analysis for a single agent decision."""
    agent_name: str
    patient_id: str
    decision: str
    final_score: float
    risk_level: str
    contributions: List[FeatureContribution]
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    top_drivers: List[str] = field(default_factory=list)
    counterfactual_analysis: List[Dict] = field(default_factory=list)
    natural_language_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "patient_id": self.patient_id,
            "decision": self.decision,
            "final_score": round(self.final_score, 4),
            "risk_level": self.risk_level,
            "contributions": [c.to_dict() for c in self.contributions],
            "confidence_interval": [round(v, 4) for v in self.confidence_interval],
            "top_drivers": self.top_drivers,
            "counterfactual_analysis": self.counterfactual_analysis,
            "natural_language_explanation": self.natural_language_explanation,
        }


class FeatureAttributionEngine:
    """
    Computes feature-level attributions for agent decisions.

    Supports three modes:
    1. Weighted contribution (for ensemble/rule-based agents)
    2. Permutation importance (for ML model agents)
    3. Counterfactual analysis (what would change the decision?)
    """

    # Population baselines for common clinical features
    CLINICAL_BASELINES = {
        "systolic_bp": {"mean": 120.0, "std": 15.0, "unit": "mmHg"},
        "diastolic_bp": {"mean": 80.0, "std": 10.0, "unit": "mmHg"},
        "heart_rate": {"mean": 72.0, "std": 12.0, "unit": "bpm"},
        "spo2": {"mean": 97.0, "std": 1.5, "unit": "%"},
        "temperature": {"mean": 98.6, "std": 0.5, "unit": "F"},
        "glucose": {"mean": 100.0, "std": 25.0, "unit": "mg/dL"},
        "a1c": {"mean": 5.7, "std": 0.8, "unit": "%"},
        "egfr": {"mean": 90.0, "std": 20.0, "unit": "mL/min"},
        "creatinine": {"mean": 1.0, "std": 0.3, "unit": "mg/dL"},
        "nt_probnp": {"mean": 125.0, "std": 200.0, "unit": "pg/mL"},
        "bmi": {"mean": 26.5, "std": 5.0, "unit": "kg/m2"},
        "crp": {"mean": 3.0, "std": 5.0, "unit": "mg/L"},
    }

    def compute_weighted_attribution(
        self,
        agent_name: str,
        patient_id: str,
        domain_scores: Dict[str, float],
        domain_weights: Dict[str, float],
        final_score: float,
        risk_level: str,
        feature_details: Dict[str, Dict] = None,
    ) -> AttributionResult:
        """
        Compute attribution for weighted ensemble decisions (e.g., ML Ensemble Agent).

        Args:
            domain_scores: Raw score per domain {domain_name: 0.0-1.0}
            domain_weights: Weight per domain {domain_name: weight}
            final_score: Final weighted score
            risk_level: LOW/MEDIUM/HIGH/CRITICAL
            feature_details: Optional per-domain feature breakdown
        """
        contributions = []
        for domain, raw_score in domain_scores.items():
            weight = domain_weights.get(domain, 0.0)
            weighted = raw_score * weight
            pct_of_total = (weighted / max(final_score, 0.001)) * 100

            contributions.append(FeatureContribution(
                feature=domain,
                value=round(raw_score, 4),
                contribution=round(weighted, 4),
                direction="negative" if raw_score > 0.5 else "positive",
                category="domain_score",
                percentile=round(pct_of_total, 1),
            ))

        # Sort by contribution magnitude (descending)
        contributions.sort(key=lambda c: abs(c.contribution), reverse=True)
        top_drivers = [c.feature for c in contributions[:3]]

        # Compute confidence interval based on domain coverage
        contributed = sum(1 for s in domain_scores.values() if s > 0)
        total_domains = len(domain_scores)
        ci_half = 0.15 - (contributed * 0.02)
        ci = (max(0.0, final_score - ci_half), min(1.0, final_score + ci_half))

        # Generate counterfactuals
        counterfactuals = self._generate_counterfactuals(
            domain_scores, domain_weights, final_score, risk_level
        )

        # Generate natural language explanation
        explanation = self._generate_explanation(
            agent_name, risk_level, final_score, contributions[:3], counterfactuals
        )

        return AttributionResult(
            agent_name=agent_name,
            patient_id=patient_id,
            decision=f"{risk_level} risk (score: {final_score:.3f})",
            final_score=final_score,
            risk_level=risk_level,
            contributions=contributions,
            confidence_interval=ci,
            top_drivers=top_drivers,
            counterfactual_analysis=counterfactuals,
            natural_language_explanation=explanation,
        )

    def compute_clinical_attribution(
        self,
        agent_name: str,
        patient_id: str,
        decision: str,
        features: Dict[str, float],
        thresholds: Dict[str, Dict],
        risk_level: str,
    ) -> AttributionResult:
        """
        Compute attribution for clinical rule-based decisions.

        Args:
            features: Patient feature values {feature_name: value}
            thresholds: Clinical thresholds {feature_name: {"threshold": X, "op": "gt|lt"}}
        """
        contributions = []

        for feature_name, value in features.items():
            threshold_info = thresholds.get(feature_name, {})
            threshold = threshold_info.get("threshold")
            op = threshold_info.get("op", "gt")
            baseline_info = self.CLINICAL_BASELINES.get(feature_name, {})
            baseline_mean = baseline_info.get("mean", 0)
            baseline_std = baseline_info.get("std", 1)

            # Compute deviation from baseline
            if baseline_std > 0:
                z_score = (value - baseline_mean) / baseline_std
                percentile = self._z_to_percentile(z_score)
            else:
                percentile = 50.0

            # Compute contribution based on threshold distance
            if threshold is not None:
                if op == "gt":
                    contrib = max(0, (value - threshold) / max(threshold, 1)) * 0.5
                    direction = "negative" if value > threshold else "positive"
                else:
                    contrib = max(0, (threshold - value) / max(threshold, 1)) * 0.5
                    direction = "negative" if value < threshold else "positive"
            else:
                contrib = abs(z_score) * 0.1 if baseline_std > 0 else 0
                direction = "negative" if z_score > 1.5 else "positive"

            contributions.append(FeatureContribution(
                feature=feature_name,
                value=round(value, 2),
                contribution=round(min(contrib, 1.0), 4),
                direction=direction,
                baseline=baseline_mean,
                percentile=percentile,
                category="clinical",
            ))

        contributions.sort(key=lambda c: abs(c.contribution), reverse=True)

        return AttributionResult(
            agent_name=agent_name,
            patient_id=patient_id,
            decision=decision,
            final_score=sum(c.contribution for c in contributions),
            risk_level=risk_level,
            contributions=contributions,
            top_drivers=[c.feature for c in contributions[:3]],
            natural_language_explanation=self._generate_clinical_explanation(
                contributions[:5], thresholds
            ),
        )

    def compute_recommendation_attribution(
        self,
        agent_name: str,
        patient_id: str,
        recommendation_title: str,
        feature_importance: List[Dict],
        evidence_level: str = None,
        source_guideline: str = None,
        confidence: float = None,
    ) -> AttributionResult:
        """
        Compute attribution for clinical recommendation decisions.

        Args:
            feature_importance: [{"feature": "X", "value": 0.9, "direction": "negative"}, ...]
        """
        contributions = [
            FeatureContribution(
                feature=fi["feature"],
                value=fi["value"],
                contribution=fi["value"],
                direction=fi.get("direction", "negative"),
                category="recommendation",
            )
            for fi in feature_importance
        ]

        evidence_text = ""
        if evidence_level:
            evidence_text = f" Based on {evidence_level}-level evidence"
            if source_guideline:
                evidence_text += f" from {source_guideline}"
            evidence_text += "."

        explanation = (
            f"Recommendation '{recommendation_title}' was triggered by: "
            + ", ".join(
                f"{c.feature} (importance: {c.value:.2f})"
                for c in contributions[:3]
            )
            + f".{evidence_text}"
        )

        return AttributionResult(
            agent_name=agent_name,
            patient_id=patient_id,
            decision=recommendation_title,
            final_score=confidence or max((c.value for c in contributions), default=0),
            risk_level="info",
            contributions=contributions,
            top_drivers=[c.feature for c in contributions[:3]],
            natural_language_explanation=explanation,
        )

    # ── Counterfactual analysis ──────────────────────────────────────

    def _generate_counterfactuals(
        self,
        domain_scores: Dict[str, float],
        domain_weights: Dict[str, float],
        current_score: float,
        current_level: str,
    ) -> List[Dict]:
        """Generate 'what-if' counterfactuals: what would change the risk level?"""
        counterfactuals = []

        # Risk level thresholds
        thresholds = {
            "CRITICAL": 0.70,
            "HIGH": 0.45,
            "MEDIUM": 0.20,
            "LOW": 0.0,
        }

        # For each domain, calculate how much it would need to change
        # to move the patient to the next lower risk level
        target_levels = {
            "CRITICAL": ("HIGH", 0.69),
            "HIGH": ("MEDIUM", 0.44),
            "MEDIUM": ("LOW", 0.19),
        }

        if current_level not in target_levels:
            return counterfactuals

        target_label, target_score = target_levels[current_level]
        needed_reduction = current_score - target_score

        for domain, raw_score in sorted(
            domain_scores.items(),
            key=lambda x: x[1] * domain_weights.get(x[0], 0),
            reverse=True,
        ):
            weight = domain_weights.get(domain, 0)
            if weight == 0 or raw_score == 0:
                continue

            # How much would this domain need to decrease?
            domain_contribution = raw_score * weight
            if domain_contribution >= needed_reduction:
                new_domain_score = max(0, raw_score - (needed_reduction / weight))
                pct_change = ((raw_score - new_domain_score) / max(raw_score, 0.001)) * 100

                counterfactuals.append({
                    "domain": domain,
                    "current_score": round(raw_score, 3),
                    "needed_score": round(new_domain_score, 3),
                    "change_pct": round(pct_change, 1),
                    "result": f"Would move patient from {current_level} to {target_label}",
                    "actionable": pct_change < 50,  # Realistic if <50% reduction
                })

        return counterfactuals[:3]

    # ── Natural language explanations ────────────────────────────────

    def _generate_explanation(
        self,
        agent_name: str,
        risk_level: str,
        score: float,
        top_contributions: List[FeatureContribution],
        counterfactuals: List[Dict],
    ) -> str:
        parts = [
            f"The {agent_name} assessed this patient at {risk_level} risk "
            f"(score: {score:.2f}/1.00)."
        ]

        if top_contributions:
            drivers = []
            for c in top_contributions:
                pct = c.percentile or 0
                drivers.append(f"{c.feature} ({c.contribution:.2f}, {pct:.0f}% of total)")
            parts.append(f"Primary drivers: {', '.join(drivers)}.")

        if counterfactuals:
            cf = counterfactuals[0]
            parts.append(
                f"To reduce risk to the next level, {cf['domain']} would need to "
                f"improve from {cf['current_score']:.2f} to {cf['needed_score']:.2f} "
                f"({cf['change_pct']:.0f}% improvement)."
            )

        return " ".join(parts)

    def _generate_clinical_explanation(
        self,
        top_contributions: List[FeatureContribution],
        thresholds: Dict[str, Dict],
    ) -> str:
        parts = []
        for c in top_contributions:
            threshold_info = thresholds.get(c.feature, {})
            threshold = threshold_info.get("threshold")
            unit = self.CLINICAL_BASELINES.get(c.feature, {}).get("unit", "")

            if threshold:
                op = threshold_info.get("op", "gt")
                comparison = "above" if op == "gt" else "below"
                parts.append(
                    f"{c.feature}: {c.value} {unit} "
                    f"({comparison} threshold of {threshold} {unit}, "
                    f"population {c.percentile:.0f}th percentile)"
                )
            elif c.baseline:
                deviation = "above" if c.value > c.baseline else "below"
                parts.append(
                    f"{c.feature}: {c.value} {unit} "
                    f"({deviation} baseline of {c.baseline} {unit})"
                )

        return "Key clinical factors: " + "; ".join(parts) + "." if parts else ""

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _z_to_percentile(z: float) -> float:
        """Approximate z-score to percentile using error function approximation."""
        return round(50 * (1 + math.erf(z / math.sqrt(2))), 1)
