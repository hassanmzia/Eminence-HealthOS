"""
Decision Explainer for HealthOS Agent Pipeline.

Provides end-to-end explanation of how a multi-agent pipeline arrived
at a clinical decision, including tier-by-tier reasoning chain,
evidence references, and patient-facing summaries.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("healthos.observability.explainability")


@dataclass
class TierExplanation:
    """Explanation for a single tier's contribution to the decision."""
    tier: str
    tier_name: str
    agents_involved: List[str]
    summary: str
    findings: Dict[str, Any]
    confidence: float
    duration_ms: int = 0
    alerts_generated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "tier_name": self.tier_name,
            "agents_involved": self.agents_involved,
            "summary": self.summary,
            "findings": self.findings,
            "confidence": round(self.confidence, 3),
            "duration_ms": self.duration_ms,
            "alerts_generated": self.alerts_generated,
        }


@dataclass
class PipelineExplanation:
    """Complete explanation of a multi-agent pipeline decision."""
    patient_id: str
    pipeline_name: str
    final_decision: str
    final_risk_level: str
    final_score: float
    tier_explanations: List[TierExplanation]
    evidence_chain: List[Dict]
    hitl_decisions: List[Dict]
    safety_checks: List[Dict]
    total_duration_ms: int = 0
    patient_summary: str = ""
    clinician_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "pipeline_name": self.pipeline_name,
            "final_decision": self.final_decision,
            "final_risk_level": self.final_risk_level,
            "final_score": round(self.final_score, 4),
            "tier_explanations": [t.to_dict() for t in self.tier_explanations],
            "evidence_chain": self.evidence_chain,
            "hitl_decisions": self.hitl_decisions,
            "safety_checks": self.safety_checks,
            "total_duration_ms": self.total_duration_ms,
            "patient_summary": self.patient_summary,
            "clinician_summary": self.clinician_summary,
        }


class DecisionExplainer:
    """
    Generates multi-level explanations of agent pipeline decisions.

    Provides:
    1. Clinician-facing: Tier-by-tier reasoning chain with evidence
    2. Patient-facing: Plain-language summary (health literacy level 5)
    3. Audit-facing: Complete decision provenance for regulatory review
    """

    TIER_NAMES = {
        "tier1": "Vital Signs Monitoring",
        "tier2": "Diagnostic Analysis",
        "tier3": "Risk Assessment",
        "tier4": "Clinical Intervention",
        "tier5": "Action Execution",
    }

    RISK_DESCRIPTIONS = {
        "CRITICAL": {
            "clinician": "Immediate clinical intervention required. Hospital observation or same-day urgent evaluation.",
            "patient": "Your health readings need urgent attention. Your care team has been notified and will contact you shortly.",
        },
        "HIGH": {
            "clinician": "Urgent outpatient visit within 24-48 hours. Intensified monitoring recommended.",
            "patient": "Some of your health numbers need attention soon. Please schedule a visit with your doctor this week.",
        },
        "MEDIUM": {
            "clinician": "Scheduled follow-up within 1-2 weeks. Optimize current medications.",
            "patient": "Your health is mostly on track, but a few things could be better. Let's check in at your next visit.",
        },
        "LOW": {
            "clinician": "Continue current care plan. Routine monitoring schedule.",
            "patient": "Your health readings look good. Keep up what you're doing!",
        },
    }

    def explain_pipeline(
        self,
        patient_id: str,
        pipeline_state: Dict[str, Any],
        decisions: List[Dict],
        conversations: List[Dict],
    ) -> PipelineExplanation:
        """
        Generate a complete explanation from pipeline state and decision logs.

        Args:
            pipeline_state: The LangGraph PatientMonitoringState
            decisions: List of DecisionRecord dicts from ObservabilityManager
            conversations: List of ConversationRecord dicts
        """
        tier_explanations = []
        evidence_chain = []
        safety_checks = []
        total_duration = 0

        # Build tier explanations from state
        tier_data = {
            "tier1": {
                "key": "monitoring_results",
                "agents": self._find_tier_agents(decisions, "tier1"),
            },
            "tier2": {
                "key": "diagnostic_results",
                "agents": self._find_tier_agents(decisions, "tier2"),
            },
            "tier3": {
                "key": "risk_scores",
                "agents": self._find_tier_agents(decisions, "tier3"),
            },
            "tier4": {
                "key": "interventions",
                "agents": self._find_tier_agents(decisions, "tier4"),
            },
            "tier5": {
                "key": "actions_taken",
                "agents": self._find_tier_agents(decisions, "tier5"),
            },
        }

        for tier, info in tier_data.items():
            state_data = pipeline_state.get(info["key"], {})
            if not state_data and not info["agents"]:
                continue

            tier_decisions = [
                d for d in decisions
                if d.get("agent_tier") == tier
            ]

            duration = sum(d.get("duration_ms", 0) for d in tier_decisions)
            total_duration += duration

            alerts = sum(
                1 for d in tier_decisions
                if d.get("safety_flags")
            )

            confidence = (
                sum(d.get("confidence", 0.8) for d in tier_decisions) / len(tier_decisions)
                if tier_decisions else 0.8
            )

            summary = self._summarize_tier(tier, state_data, tier_decisions)

            tier_explanations.append(TierExplanation(
                tier=tier,
                tier_name=self.TIER_NAMES.get(tier, tier),
                agents_involved=info["agents"],
                summary=summary,
                findings=state_data if isinstance(state_data, dict) else {"data": state_data},
                confidence=confidence,
                duration_ms=duration,
                alerts_generated=alerts,
            ))

            # Build evidence chain
            for d in tier_decisions:
                if d.get("evidence_references"):
                    evidence_chain.extend(d["evidence_references"])
                if d.get("safety_flags"):
                    safety_checks.append({
                        "tier": tier,
                        "agent": d.get("agent_name"),
                        "flags": d["safety_flags"],
                    })

        # Extract HITL decisions
        hitl_decisions = [
            d for d in decisions
            if d.get("requires_hitl") or "hitl" in d.get("decision", "").lower()
        ]

        # Determine final risk level
        risk_scores = pipeline_state.get("risk_scores", {})
        ensemble = risk_scores.get("ml_ensemble_agent", {})
        findings = ensemble.get("findings", {}) if isinstance(ensemble, dict) else {}
        final_score = findings.get("unified_score", 0.0)
        final_level = findings.get("risk_level", "LOW")

        # Generate summaries
        clinician_summary = self._generate_clinician_summary(
            final_level, final_score, tier_explanations, evidence_chain
        )
        patient_summary = self._generate_patient_summary(
            final_level, tier_explanations
        )

        return PipelineExplanation(
            patient_id=patient_id,
            pipeline_name="patient_monitoring_pipeline",
            final_decision=f"{final_level} risk — score {final_score:.3f}",
            final_risk_level=final_level,
            final_score=final_score,
            tier_explanations=tier_explanations,
            evidence_chain=evidence_chain,
            hitl_decisions=[d for d in hitl_decisions],
            safety_checks=safety_checks,
            total_duration_ms=total_duration,
            clinician_summary=clinician_summary,
            patient_summary=patient_summary,
        )

    def explain_single_decision(
        self, decision: Dict, context: Dict = None,
    ) -> Dict[str, Any]:
        """Generate explanation for a single agent decision."""
        agent = decision.get("agent_name", "unknown")
        rationale = decision.get("rationale", "")
        confidence = decision.get("confidence", 0.0)
        features = decision.get("feature_contributions", [])

        explanation = {
            "agent": agent,
            "decision": decision.get("decision", ""),
            "rationale": rationale,
            "confidence": confidence,
            "confidence_label": self._confidence_label(confidence),
        }

        if features:
            explanation["key_factors"] = [
                f"{f['feature']}: {f['value']:.2f} ({f['direction']})"
                for f in features[:5]
            ]

        if decision.get("alternatives"):
            explanation["alternatives_considered"] = [
                {
                    "option": alt.get("decision", ""),
                    "score": alt.get("score", 0),
                    "reason_not_chosen": (
                        "Lower confidence score"
                        if alt.get("score", 0) < confidence
                        else "Did not meet threshold"
                    ),
                }
                for alt in decision["alternatives"][:3]
            ]

        if decision.get("evidence_references"):
            explanation["evidence"] = decision["evidence_references"]

        return explanation

    # ── Internal helpers ─────────────────────────────────────────────

    def _find_tier_agents(self, decisions: List[Dict], tier: str) -> List[str]:
        return list({
            d.get("agent_name", "")
            for d in decisions
            if d.get("agent_tier") == tier
        })

    def _summarize_tier(
        self, tier: str, state_data: Any, decisions: List[Dict],
    ) -> str:
        if not decisions:
            return f"No agent decisions recorded for {self.TIER_NAMES.get(tier, tier)}."

        rationales = [d.get("rationale", "") for d in decisions if d.get("rationale")]
        if rationales:
            return " | ".join(rationales[:3])

        return f"{len(decisions)} agent(s) processed in {self.TIER_NAMES.get(tier, tier)}."

    def _generate_clinician_summary(
        self,
        risk_level: str,
        score: float,
        tiers: List[TierExplanation],
        evidence: List[Dict],
    ) -> str:
        parts = [
            self.RISK_DESCRIPTIONS.get(risk_level, {}).get(
                "clinician", f"Risk level: {risk_level}"
            ),
            f"Unified risk score: {score:.2f}/1.00.",
        ]

        for tier in tiers:
            if tier.alerts_generated > 0:
                parts.append(
                    f"{tier.tier_name}: {tier.alerts_generated} alert(s) — {tier.summary[:100]}"
                )

        if evidence:
            guidelines = {e.get("source", "") for e in evidence if e.get("source")}
            if guidelines:
                parts.append(f"Evidence base: {', '.join(list(guidelines)[:3])}.")

        return " ".join(parts)

    def _generate_patient_summary(
        self, risk_level: str, tiers: List[TierExplanation],
    ) -> str:
        base = self.RISK_DESCRIPTIONS.get(risk_level, {}).get(
            "patient",
            "Please check in with your care team about your recent results.",
        )

        # Add context from monitoring tier
        monitoring = next((t for t in tiers if t.tier == "tier1"), None)
        if monitoring and monitoring.alerts_generated > 0:
            base += " We noticed some changes in your vital signs that we want to keep an eye on."

        return base

    @staticmethod
    def _confidence_label(confidence: float) -> str:
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.75:
            return "high"
        elif confidence >= 0.5:
            return "moderate"
        elif confidence >= 0.25:
            return "low"
        return "very_low"
