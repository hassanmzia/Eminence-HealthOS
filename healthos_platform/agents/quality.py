"""
Eminence HealthOS — Quality / Confidence Agent
Layer 5 (Measurement): Scores the overall quality and confidence of pipeline
outputs.  Evaluates data completeness, agent agreement, output consistency,
and clinical safety signals to produce a unified quality scorecard that
determines whether results can be auto-actioned or require manual review.
"""

from __future__ import annotations

import statistics
from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    PipelineState,
)

logger = structlog.get_logger()


# ── Quality Scoring Weights ───────────────────────────────────────────────────

DEFAULT_QUALITY_CONFIG: dict[str, Any] = {
    # Weights for the composite quality score (must sum to 1.0)
    "weights": {
        "agent_confidence": 0.30,
        "data_completeness": 0.25,
        "output_consistency": 0.25,
        "clinical_safety": 0.20,
    },
    # Thresholds for quality classification
    "thresholds": {
        "auto_action": 0.85,     # Above this: safe for automated action
        "acceptable": 0.70,      # Above this: acceptable with monitoring
        "review_required": 0.50, # Below this: mandatory manual review
    },
    # Minimum number of agents expected for a complete pipeline
    "min_agents_for_completeness": 3,
    # Expected data elements for completeness check
    "expected_data_elements": [
        "normalized_vitals",
        "anomalies",
        "risk_assessments",
    ],
}


class QualityConfidenceAgent(BaseAgent):
    """
    Produces a unified quality scorecard for the pipeline execution.

    Scores four dimensions:
    1. **Agent Confidence** — aggregate confidence across all agent outputs
    2. **Data Completeness** — are expected data elements present and populated?
    3. **Output Consistency** — do agent outputs agree (no contradictions)?
    4. **Clinical Safety** — are safety-critical items properly flagged?

    The composite score determines the ``quality_grade``:
    - A (≥0.85): Safe for auto-action
    - B (≥0.70): Acceptable with monitoring
    - C (≥0.50): Review recommended
    - D (<0.50): Mandatory manual review
    """

    name = "quality_confidence"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Scores output quality, completeness, and confidence for the pipeline"
    min_confidence = 0.90

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.config = config or DEFAULT_QUALITY_CONFIG

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Score quality from standalone input context."""
        context = input_data.context or {}
        scorecard = self._score_from_dict(context)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"quality_scorecard": scorecard},
            confidence=scorecard["composite_score"],
            rationale=self._build_rationale(scorecard),
        )

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """Score the full pipeline execution quality."""
        dimensions: dict[str, float] = {}

        # 1. Agent confidence score
        dimensions["agent_confidence"] = self._score_agent_confidence(state)

        # 2. Data completeness score
        dimensions["data_completeness"] = self._score_data_completeness(state)

        # 3. Output consistency score
        dimensions["output_consistency"] = self._score_output_consistency(state)

        # 4. Clinical safety score
        dimensions["clinical_safety"] = self._score_clinical_safety(state)

        # Compute weighted composite
        weights = self.config.get("weights", DEFAULT_QUALITY_CONFIG["weights"])
        composite = sum(
            dimensions.get(dim, 0.0) * weight
            for dim, weight in weights.items()
        )
        composite = round(min(1.0, max(0.0, composite)), 4)

        grade = self._classify_grade(composite)
        requires_review = grade in ("C", "D")

        scorecard = {
            "composite_score": composite,
            "grade": grade,
            "dimensions": dimensions,
            "weights": weights,
            "requires_review": requires_review,
            "auto_actionable": grade == "A",
            "agent_count": len(state.executed_agents),
            "details": self._build_details(state, dimensions),
        }

        # Store on pipeline state
        state.patient_context["quality_scorecard"] = scorecard

        if requires_review and not state.requires_hitl:
            state.requires_hitl = True
            state.hitl_reason = (
                f"Quality grade {grade} (score {composite:.2f}) requires manual review"
            )

        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = self.build_output(
            trace_id=state.trace_id,
            result={"quality_scorecard": scorecard},
            confidence=composite,
            rationale=self._build_rationale(scorecard),
        )

        return state

    # ── Dimension Scorers ─────────────────────────────────────────────────────

    def _score_agent_confidence(self, state: PipelineState) -> float:
        """Aggregate confidence across all agent outputs."""
        if not state.agent_outputs:
            return 0.5

        confidences = [
            output.confidence
            for output in state.agent_outputs.values()
            if output.status != AgentStatus.FAILED
        ]

        if not confidences:
            return 0.3

        # Use harmonic mean to penalize low-confidence outliers
        try:
            return round(statistics.harmonic_mean(confidences), 4)
        except statistics.StatisticsError:
            return round(sum(confidences) / len(confidences), 4)

    def _score_data_completeness(self, state: PipelineState) -> float:
        """Check that expected data elements are present and populated."""
        expected = self.config.get(
            "expected_data_elements",
            DEFAULT_QUALITY_CONFIG["expected_data_elements"],
        )
        min_agents = self.config.get(
            "min_agents_for_completeness",
            DEFAULT_QUALITY_CONFIG["min_agents_for_completeness"],
        )

        scores: list[float] = []

        # Check data element presence
        data_map = {
            "normalized_vitals": state.normalized_vitals,
            "anomalies": state.anomalies,
            "risk_assessments": state.risk_assessments,
        }
        for element in expected:
            data = data_map.get(element, [])
            scores.append(1.0 if len(data) > 0 else 0.3)

        # Check agent execution completeness
        agent_ratio = min(1.0, len(state.executed_agents) / max(min_agents, 1))
        scores.append(agent_ratio)

        # Check patient context completeness
        context_keys = set(state.patient_context.keys()) if state.patient_context else set()
        context_score = min(1.0, len(context_keys) / 3) if context_keys else 0.3
        scores.append(context_score)

        return round(sum(scores) / len(scores), 4) if scores else 0.5

    def _score_output_consistency(self, state: PipelineState) -> float:
        """Check that agent outputs are internally consistent."""
        if len(state.agent_outputs) < 2:
            return 0.8  # Not enough agents to judge consistency

        scores: list[float] = []

        # Check for contradictory statuses (e.g. one says COMPLETED, another FAILED)
        statuses = [o.status for o in state.agent_outputs.values()]
        failed_count = sum(1 for s in statuses if s == AgentStatus.FAILED)
        completed_count = sum(1 for s in statuses if s == AgentStatus.COMPLETED)

        if failed_count > 0 and completed_count > 0:
            # Mixed results reduce consistency
            scores.append(max(0.4, 1.0 - (failed_count / len(statuses))))
        else:
            scores.append(1.0)

        # Check confidence variance (high variance = low consistency)
        confidences = [o.confidence for o in state.agent_outputs.values()]
        if len(confidences) >= 2:
            try:
                stdev = statistics.stdev(confidences)
                scores.append(max(0.3, 1.0 - stdev))
            except statistics.StatisticsError:
                scores.append(0.8)
        else:
            scores.append(0.8)

        # Check for conflicting HITL signals
        hitl_flags = [o.requires_hitl for o in state.agent_outputs.values()]
        if any(hitl_flags) and not all(hitl_flags):
            # Some agents flagged HITL, some didn't — slightly reduces consistency
            scores.append(0.7)
        else:
            scores.append(1.0)

        return round(sum(scores) / len(scores), 4) if scores else 0.8

    def _score_clinical_safety(self, state: PipelineState) -> float:
        """
        Evaluate clinical safety signals — higher score means safety
        mechanisms are working correctly.
        """
        scores: list[float] = []

        # Check that critical anomalies triggered appropriate responses
        from healthos_platform.agents.types import Severity

        critical_anomalies = [
            a for a in state.anomalies if a.severity == Severity.CRITICAL
        ]
        if critical_anomalies:
            # Good: critical anomalies exist AND alerts or HITL were triggered
            if state.alert_requests or state.requires_hitl:
                scores.append(1.0)
            else:
                scores.append(0.3)  # Bad: critical anomalies but no escalation
        else:
            scores.append(1.0)  # No critical anomalies to handle

        # Check that policy violations were flagged
        if state.policy_violations:
            # Violations detected = safety mechanisms working
            scores.append(0.9)
        else:
            scores.append(1.0)

        # Check that high-risk scores triggered HITL
        high_risk = [r for r in state.risk_assessments if r.score >= 0.75]
        if high_risk:
            if state.requires_hitl:
                scores.append(1.0)
            else:
                scores.append(0.4)
        else:
            scores.append(1.0)

        return round(sum(scores) / len(scores), 4) if scores else 0.8

    # ── Utility Methods ───────────────────────────────────────────────────────

    def _classify_grade(self, composite: float) -> str:
        """Map composite score to a letter grade."""
        thresholds = self.config.get("thresholds", DEFAULT_QUALITY_CONFIG["thresholds"])
        if composite >= thresholds.get("auto_action", 0.85):
            return "A"
        if composite >= thresholds.get("acceptable", 0.70):
            return "B"
        if composite >= thresholds.get("review_required", 0.50):
            return "C"
        return "D"

    @staticmethod
    def _build_details(
        state: PipelineState, dimensions: dict[str, float]
    ) -> dict[str, Any]:
        """Build detailed breakdown for the scorecard."""
        return {
            "agents_executed": list(state.executed_agents),
            "total_anomalies": len(state.anomalies),
            "total_risk_assessments": len(state.risk_assessments),
            "total_alerts": len(state.alert_requests),
            "total_policy_violations": len(state.policy_violations),
            "hitl_required": state.requires_hitl,
            "dimension_scores": {k: round(v, 4) for k, v in dimensions.items()},
        }

    def _score_from_dict(self, context: dict[str, Any]) -> dict[str, Any]:
        """Score quality from raw dict context (standalone mode)."""
        agent_outputs = context.get("agent_outputs", {})
        confidences = [
            o.get("confidence", 0.0)
            for o in agent_outputs.values()
            if isinstance(o, dict)
        ]

        agent_confidence = (
            round(statistics.harmonic_mean(confidences), 4)
            if confidences
            else 0.5
        )

        # Simplified completeness check
        data_elements = ["normalized_vitals", "anomalies", "risk_assessments"]
        present = sum(1 for e in data_elements if context.get(e))
        data_completeness = round(present / len(data_elements), 4) if data_elements else 0.5

        weights = self.config.get("weights", DEFAULT_QUALITY_CONFIG["weights"])
        composite = (
            agent_confidence * weights.get("agent_confidence", 0.30)
            + data_completeness * weights.get("data_completeness", 0.25)
            + 0.8 * weights.get("output_consistency", 0.25)
            + 0.8 * weights.get("clinical_safety", 0.20)
        )
        composite = round(min(1.0, max(0.0, composite)), 4)

        grade = self._classify_grade(composite)

        return {
            "composite_score": composite,
            "grade": grade,
            "dimensions": {
                "agent_confidence": agent_confidence,
                "data_completeness": data_completeness,
                "output_consistency": 0.8,
                "clinical_safety": 0.8,
            },
            "requires_review": grade in ("C", "D"),
            "auto_actionable": grade == "A",
        }

    @staticmethod
    def _build_rationale(scorecard: dict[str, Any]) -> str:
        grade = scorecard.get("grade", "?")
        composite = scorecard.get("composite_score", 0.0)
        dims = scorecard.get("dimensions", {})
        dim_parts = [f"{k}={v:.2f}" for k, v in dims.items()]
        return (
            f"Quality grade {grade} (score {composite:.2f}): "
            f"{', '.join(dim_parts)}"
        )
