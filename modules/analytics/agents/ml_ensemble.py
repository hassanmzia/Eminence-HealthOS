"""
ML Ensemble Risk Agent — Tier 3 (Decisioning / Risk).

Combines outputs from multiple risk domains using weighted attention fusion
to generate a unified, calibrated patient risk score with explainability.
Produces tiered risk levels: LOW / MEDIUM / HIGH / CRITICAL.

Adapted from InHealth ml_ensemble_agent (Tier 3 Risk).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.ml_ensemble")

# Weights for each risk domain in the ensemble
DOMAIN_WEIGHTS = {
    "hospitalization_7d": 0.35,
    "comorbidity_risk": 0.20,
    "sdoh_risk": 0.15,
    "family_history_risk": 0.10,
    "monitoring_alerts": 0.20,
}


class MLEnsembleAgent(HealthOSAgent):
    """Multi-modal ML ensemble for unified patient risk scoring."""

    def __init__(self) -> None:
        super().__init__(
            name="ml_ensemble",
            tier=AgentTier.RISK,
            description=(
                "Combines risk domain outputs via weighted attention fusion into a "
                "unified, calibrated risk score with explainability"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.RISK_SCORING, AgentCapability.CLINICAL_SUMMARY]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        # Collect risk inputs from upstream agents
        risk_scores: dict[str, Any] = data.get("risk_scores", {})
        alerts: list[dict[str, Any]] = data.get("alerts", [])

        # Extract individual risk scores
        hosp_risk = risk_scores.get("hospitalization_7d", {})
        comorbidity_data = risk_scores.get("comorbidity_agent", {})
        sdoh_data = risk_scores.get("sdoh_agent", {})
        family_data = risk_scores.get("family_history_agent", {})

        # 1. Hospitalization prediction score (0-1)
        hosp_score = float(hosp_risk.get("score", 0.0)) if hosp_risk else 0.0

        # 2. Comorbidity risk (normalize CCI to 0-1; max practical CCI ~10)
        cci_raw = (comorbidity_data.get("findings", {}) or {}).get("charlson_index", {}).get("score", 0)
        comorbidity_score = min(float(cci_raw) / 10.0, 1.0)

        # 3. SDOH risk score
        sdoh_pct = (sdoh_data.get("findings", {}) or {}).get("sdoh_score", {}).get("percentage", 0)
        sdoh_score = float(sdoh_pct) / 100.0

        # 4. Family history risk
        family_findings = (family_data.get("findings", {}) or {}).get("polygenic_risk_approximation", {})
        fam_high = sum(
            1 for v in family_findings.values()
            if isinstance(v, dict) and v.get("risk_level") == "HIGH"
        )
        family_score = min(float(fam_high) / 3.0, 1.0)

        # 5. Active monitoring alerts severity
        critical_alert_count = sum(1 for a in alerts if a.get("severity") in ("EMERGENCY", "CRITICAL"))
        high_alert_count = sum(1 for a in alerts if a.get("severity") == "HIGH")
        alert_score = min((critical_alert_count * 0.4 + high_alert_count * 0.2), 1.0)

        # -- Attention fusion (weighted sum) --
        domain_scores = {
            "hospitalization_7d": hosp_score,
            "comorbidity_risk": comorbidity_score,
            "sdoh_risk": sdoh_score,
            "family_history_risk": family_score,
            "monitoring_alerts": alert_score,
        }

        weighted_score = sum(
            domain_scores[d] * DOMAIN_WEIGHTS[d] for d in DOMAIN_WEIGHTS
        )

        # Emergency override
        if critical_alert_count > 0:
            weighted_score = max(weighted_score, 0.70)

        # Risk level
        if weighted_score >= 0.70:
            risk_level = "CRITICAL"
        elif weighted_score >= 0.45:
            risk_level = "HIGH"
        elif weighted_score >= 0.20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Confidence interval
        contributed_domains = sum(1 for s in domain_scores.values() if s > 0)
        ci_half = 0.15 - (contributed_domains * 0.02)
        ci_low = max(0.0, weighted_score - ci_half)
        ci_high = min(1.0, weighted_score + ci_half)

        # Explainability
        domain_contributions = {
            d: {
                "raw_score": round(domain_scores[d], 3),
                "weight": DOMAIN_WEIGHTS[d],
                "weighted_contribution": round(domain_scores[d] * DOMAIN_WEIGHTS[d], 3),
                "pct_of_total": round(
                    (domain_scores[d] * DOMAIN_WEIGHTS[d]) / max(weighted_score, 0.001) * 100, 1,
                ),
            }
            for d in DOMAIN_WEIGHTS
        }
        top_domains = sorted(
            domain_contributions.items(),
            key=lambda x: x[1]["weighted_contribution"],
            reverse=True,
        )[:3]

        out_alerts: list[dict[str, Any]] = []
        if risk_level == "CRITICAL":
            out_alerts.append({
                "severity": "EMERGENCY",
                "message": (
                    f"CRITICAL UNIFIED RISK: Ensemble score {weighted_score:.2f} ({risk_level}). "
                    "Immediate clinical intervention required."
                ),
            })
        elif risk_level == "HIGH":
            out_alerts.append({
                "severity": "HIGH",
                "message": (
                    f"HIGH RISK: Ensemble score {weighted_score:.2f}. "
                    "Urgent care coordination needed within 24-48 hours."
                ),
            })

        recommendations = self._generate_recommendations(risk_level, top_domains, weighted_score)

        # LLM narrative
        risk_narrative = None
        try:
            contrib_lines = "\n".join([
                f"  {d}: raw={info['raw_score']:.3f}, weighted={info['weighted_contribution']:.3f} ({info['pct_of_total']:.1f}%)"
                for d, info in domain_contributions.items()
            ])
            prompt = (
                f"ML Ensemble Risk Assessment:\n"
                f"  Unified risk score: {weighted_score:.3f} ({risk_level})\n"
                f"  95% CI: [{ci_low:.3f}, {ci_high:.3f}]\n\n"
                f"Domain contributions:\n{contrib_lines}\n\n"
                f"Top risk drivers: {[d[0] for d in top_domains]}\n"
                f"Active emergency alerts: {critical_alert_count}\n\n"
                "Provide:\n"
                "1. Integrated risk narrative\n"
                "2. Priority interventions with expected risk reduction\n"
                "3. Risk trajectory prediction (30 days)\n"
                "4. Tailored care escalation pathway\n"
                "5. Patient-facing risk communication (health literacy level 5)"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical risk stratification narrator. "
                    "Reference LACE+, HOSPITAL score, CCI, and condition-specific risk models."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            risk_narrative = resp.content
        except Exception:
            logger.warning("LLM ensemble narrative failed; using fallback")
            risk_narrative = f"Unified risk level: {risk_level} (score: {weighted_score:.2f})"

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=f"risk_level_{risk_level.lower()}",
            rationale=f"Ensemble score {weighted_score:.3f} ({risk_level}); top drivers: {', '.join(d[0] for d in top_domains)}",
            confidence=0.85 + (contributed_domains * 0.02),
            data={
                "unified_score": round(weighted_score, 3),
                "risk_level": risk_level,
                "confidence_interval": [round(ci_low, 3), round(ci_high, 3)],
                "domain_contributions": domain_contributions,
                "top_risk_drivers": [d[0] for d in top_domains],
                "risk_narrative": risk_narrative,
                "contributed_domains": contributed_domains,
                "alerts": out_alerts,
                "recommendations": recommendations,
            },
            requires_hitl=risk_level == "CRITICAL",
            hitl_reason="CRITICAL unified risk score requires immediate clinical review" if risk_level == "CRITICAL" else None,
        )

    def _generate_recommendations(
        self, risk_level: str, top_domains: list, score: float,
    ) -> list[str]:
        recs: list[str] = []
        if risk_level == "CRITICAL":
            recs.append(
                "CRITICAL RISK: Hospital observation or same-day urgent evaluation. "
                "Activate care management protocol. Physician notification within 15 minutes."
            )
        elif risk_level == "HIGH":
            recs.append(
                "HIGH RISK: Urgent outpatient visit within 24-48 hours. "
                "Intensified monitoring. Care coordinator assignment."
            )
        elif risk_level == "MEDIUM":
            recs.append(
                "MEDIUM RISK: Scheduled follow-up within 1-2 weeks. "
                "Optimize medications. Patient education on warning signs."
            )

        top_names = [d[0] for d in top_domains]
        if "monitoring_alerts" in top_names:
            recs.append("Active monitoring alerts are driving risk - review and address outstanding alerts.")
        if "sdoh_risk" in top_names:
            recs.append("Social determinants contributing to risk - social work engagement essential.")
        return recs
