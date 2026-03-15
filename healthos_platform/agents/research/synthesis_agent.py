"""
Eminence HealthOS — Synthesis Agent
Synthesizes evidence from multiple research sources (guidelines, literature,
trial data) into actionable clinical summaries.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentTier

logger = structlog.get_logger()


class SynthesisAgent(BaseAgent):
    """
    Aggregates and synthesizes evidence from guidelines, literature,
    and clinical trials into cohesive clinical recommendations.
    """

    name = "synthesis_agent"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Evidence synthesis across multiple clinical sources"
    min_confidence = 0.70

    async def process(self, input_data: AgentInput) -> AgentOutput:
        context = input_data.context or {}
        guidelines = context.get("guidelines", [])
        literature = context.get("literature", [])
        trials = context.get("trials", [])
        patient_conditions = context.get("conditions", [])

        # Synthesize across sources
        synthesis = self._synthesize(guidelines, literature, trials, patient_conditions)

        # Generate recommendations
        recommendations = self._generate_recommendations(synthesis)

        # Calculate evidence strength
        evidence_strength = self._calculate_evidence_strength(synthesis)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "synthesis": synthesis,
                "recommendations": recommendations,
                "evidence_strength": evidence_strength,
                "sources_analyzed": {
                    "guidelines": len(guidelines),
                    "literature": len(literature),
                    "trials": len(trials),
                },
            },
            confidence=evidence_strength.get("overall_score", 0.5),
            rationale=(
                f"Synthesized {len(guidelines)} guidelines, {len(literature)} articles, "
                f"{len(trials)} trials — evidence strength: "
                f"{evidence_strength.get('overall_level', 'unknown')}"
            ),
        )

    def _synthesize(
        self,
        guidelines: list[dict],
        literature: list[dict],
        trials: list[dict],
        conditions: list[dict],
    ) -> list[dict[str, Any]]:
        """Cross-reference evidence from multiple sources."""
        findings: list[dict[str, Any]] = []

        # Extract key themes from guidelines
        for g in guidelines:
            for rec in g.get("recommendations", []):
                findings.append({
                    "finding": rec.get("rec", rec.get("recommendation", "")),
                    "source_type": "guideline",
                    "source": g.get("source", ""),
                    "evidence_level": g.get("evidence_level", "D"),
                    "supporting_sources": 1,
                })

        # Cross-reference with literature
        for article in literature:
            for finding in findings:
                # Simple keyword matching for cross-referencing
                if article.get("relevance_score", 0) > 0.7:
                    finding["supporting_sources"] += 1

        return findings

    def _generate_recommendations(
        self, synthesis: list[dict]
    ) -> list[dict[str, Any]]:
        """Generate prioritized recommendations from synthesis."""
        recs = []
        for finding in synthesis:
            priority = "high" if finding.get("supporting_sources", 0) >= 2 else "moderate"
            recs.append({
                "recommendation": finding["finding"],
                "priority": priority,
                "evidence_level": finding.get("evidence_level", "D"),
                "source": finding.get("source", ""),
                "supporting_sources": finding.get("supporting_sources", 1),
            })

        # Sort by evidence level then supporting sources
        level_order = {"A": 0, "B": 1, "C": 2, "D": 3}
        recs.sort(key=lambda r: (level_order.get(r["evidence_level"], 4), -r["supporting_sources"]))
        return recs

    def _calculate_evidence_strength(
        self, synthesis: list[dict]
    ) -> dict[str, Any]:
        """Calculate overall evidence strength from synthesized findings."""
        if not synthesis:
            return {"overall_score": 0.3, "overall_level": "insufficient"}

        level_scores = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}
        scores = [
            level_scores.get(f.get("evidence_level", "D"), 0.25) for f in synthesis
        ]
        avg_score = sum(scores) / len(scores) if scores else 0.3

        if avg_score >= 0.85:
            level = "strong"
        elif avg_score >= 0.65:
            level = "moderate"
        elif avg_score >= 0.45:
            level = "limited"
        else:
            level = "insufficient"

        return {
            "overall_score": round(avg_score, 2),
            "overall_level": level,
            "findings_count": len(synthesis),
        }
