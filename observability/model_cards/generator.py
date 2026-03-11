"""
Model Card Generator for HealthOS Agents.

Generates standardized model cards for each AI agent, documenting
capabilities, limitations, intended use, performance metrics,
fairness analysis, and clinical safety considerations.

Based on Google's Model Cards for Model Reporting (Mitchell et al., 2019)
adapted for healthcare AI agent transparency.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("healthos.observability.model_cards")


@dataclass
class PerformanceMetrics:
    """Performance metrics for a model or agent."""
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0
    auc_roc: float = 0.0
    calibration_error: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_rate: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in self.__dict__.items()
            if k != "custom_metrics"
        }
        d["custom_metrics"] = self.custom_metrics
        return d


@dataclass
class FairnessAnalysis:
    """Fairness analysis results for a model or agent."""
    group_by: str  # e.g., "sex", "age_band", "race"
    subgroups: List[Dict[str, Any]]  # Per-subgroup metrics
    disparity_ratio: float = 0.0  # Max/min flagged_rate ratio
    equalized_odds_gap: float = 0.0
    demographic_parity_gap: float = 0.0
    assessment: str = ""  # "pass" / "flag" / "fail"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_by": self.group_by,
            "subgroups": self.subgroups,
            "disparity_ratio": round(self.disparity_ratio, 4),
            "equalized_odds_gap": round(self.equalized_odds_gap, 4),
            "demographic_parity_gap": round(self.demographic_parity_gap, 4),
            "assessment": self.assessment,
        }


@dataclass
class ModelCard:
    """Standardized model card for a HealthOS agent."""

    # Identity
    agent_name: str
    agent_id: int
    version: str
    agent_tier: str
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Overview
    description: str = ""
    intended_use: str = ""
    out_of_scope_uses: List[str] = field(default_factory=list)
    primary_users: List[str] = field(default_factory=list)

    # Technical
    model_type: str = ""  # "LLM", "ensemble", "rules-engine", "ML-model"
    underlying_models: List[str] = field(default_factory=list)
    input_schema: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    # Performance
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    evaluation_dataset: str = ""
    evaluation_methodology: str = ""

    # Fairness
    fairness_analyses: List[FairnessAnalysis] = field(default_factory=list)

    # Safety
    safety_considerations: List[str] = field(default_factory=list)
    known_limitations: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    hitl_requirements: str = ""
    regulatory_status: str = ""

    # Clinical
    clinical_evidence_level: str = ""  # A/B/C/D/E
    source_guidelines: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)

    # Monitoring
    monitoring_metrics: List[str] = field(default_factory=list)
    alerting_thresholds: Dict[str, float] = field(default_factory=dict)
    retraining_criteria: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": {
                "agent_name": self.agent_name,
                "agent_id": self.agent_id,
                "version": self.version,
                "agent_tier": self.agent_tier,
                "last_updated": self.last_updated,
            },
            "overview": {
                "description": self.description,
                "intended_use": self.intended_use,
                "out_of_scope_uses": self.out_of_scope_uses,
                "primary_users": self.primary_users,
            },
            "technical": {
                "model_type": self.model_type,
                "underlying_models": self.underlying_models,
                "input_schema": self.input_schema,
                "output_schema": self.output_schema,
                "dependencies": self.dependencies,
            },
            "performance": self.performance.to_dict(),
            "evaluation": {
                "dataset": self.evaluation_dataset,
                "methodology": self.evaluation_methodology,
            },
            "fairness": [fa.to_dict() for fa in self.fairness_analyses],
            "safety": {
                "considerations": self.safety_considerations,
                "known_limitations": self.known_limitations,
                "failure_modes": self.failure_modes,
                "hitl_requirements": self.hitl_requirements,
                "regulatory_status": self.regulatory_status,
            },
            "clinical": {
                "evidence_level": self.clinical_evidence_level,
                "source_guidelines": self.source_guidelines,
                "contraindications": self.contraindications,
            },
            "monitoring": {
                "metrics": self.monitoring_metrics,
                "alerting_thresholds": self.alerting_thresholds,
                "retraining_criteria": self.retraining_criteria,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class ModelCardGenerator:
    """
    Generates model cards for HealthOS agents.

    Pre-loaded with cards for all standard tier agents.
    Supports dynamic generation from runtime metrics.
    """

    def __init__(self):
        self._cards: Dict[str, ModelCard] = {}
        self._register_standard_cards()

    def _register_standard_cards(self):
        """Register model cards for all standard HealthOS agents."""

        # ── Tier 1: Monitoring Agents ────────────────────────────────

        self.register(ModelCard(
            agent_name="glucose_monitoring_agent",
            agent_id=1,
            version="1.0.0",
            agent_tier="tier1_monitoring",
            description="Monitors blood glucose levels from continuous glucose monitors (CGM) and point-of-care testing. Detects hypo/hyperglycemia, glucose variability, and trend analysis.",
            intended_use="Real-time glucose monitoring for patients with diabetes (Type 1, Type 2, gestational). Triggers alerts for out-of-range values.",
            out_of_scope_uses=["Insulin dosing decisions (requires physician)", "Non-diabetic patients without glucose monitoring orders"],
            primary_users=["Endocrinologists", "Primary care physicians", "Diabetes educators"],
            model_type="rules-engine + LLM narrative",
            underlying_models=["Rules engine v1", "Claude Sonnet (narrative)"],
            input_schema={"glucose_value": "float (mg/dL)", "timestamp": "ISO8601", "source": "CGM|POC"},
            output_schema={"status": "normal|low|high|critical", "trend": "rising|stable|falling", "alert": "dict|null"},
            safety_considerations=[
                "False negatives for hypoglycemia can be life-threatening",
                "CGM lag of 5-15 minutes vs blood glucose",
                "Compression lows from CGM (false low readings during sleep)",
            ],
            known_limitations=[
                "Does not account for insulin-on-board",
                "Cannot predict hypoglycemia, only detect current state",
                "Accuracy degrades for glucose > 400 mg/dL",
            ],
            clinical_evidence_level="A",
            source_guidelines=["ADA Standards of Care 2024, Section 7", "AACE CGM Consensus 2023"],
            monitoring_metrics=["alert_accuracy", "false_negative_rate", "detection_latency_ms"],
            alerting_thresholds={"hypoglycemia": 70.0, "hyperglycemia": 250.0, "critical_low": 54.0, "critical_high": 400.0},
        ))

        self.register(ModelCard(
            agent_name="cardiac_monitoring_agent",
            agent_id=2,
            version="1.0.0",
            agent_tier="tier1_monitoring",
            description="Monitors heart rate, blood pressure, and cardiac rhythm data. Detects bradycardia, tachycardia, hypertension, hypotension, and irregular rhythms.",
            intended_use="Continuous cardiac monitoring for patients with cardiovascular disease, heart failure, or arrhythmia history.",
            out_of_scope_uses=["12-lead ECG interpretation (see ECG agent)", "Cardiac catheterization decisions"],
            primary_users=["Cardiologists", "Hospitalists", "Emergency physicians"],
            model_type="rules-engine + LLM narrative",
            underlying_models=["Rules engine v1", "Claude Sonnet (narrative)"],
            safety_considerations=[
                "Missed arrhythmia detection could delay treatment",
                "Motion artifact can cause false positive tachycardia alerts",
                "Blood pressure readings affected by cuff size and positioning",
            ],
            clinical_evidence_level="A",
            source_guidelines=["ACC/AHA 2023 Heart Failure Guidelines", "ESC 2023 Arrhythmia Guidelines"],
            monitoring_metrics=["alert_accuracy", "false_alarm_rate", "detection_latency_ms"],
        ))

        # ── Tier 3: Risk Assessment ──────────────────────────────────

        self.register(ModelCard(
            agent_name="ml_ensemble_agent",
            agent_id=14,
            version="1.0.0",
            agent_tier="tier3_risk",
            description="Multi-modal ML ensemble combining 5 risk domains (hospitalization, comorbidity, SDOH, family history, monitoring alerts) using attention-weighted fusion to generate unified patient risk scores.",
            intended_use="Unified risk stratification for chronic care patients. Generates tiered risk levels (LOW/MEDIUM/HIGH/CRITICAL) with explainable domain contributions.",
            out_of_scope_uses=["Acute emergency triage (use dedicated triage agent)", "Pediatric risk assessment (model trained on adult population)"],
            primary_users=["Care coordinators", "Population health managers", "Primary care physicians"],
            model_type="ensemble",
            underlying_models=["Weighted ensemble (5 domains)", "Claude Sonnet (risk narrative)"],
            input_schema={
                "hospitalization_7d": "float (0-1) from prediction agent",
                "comorbidity_risk": "float (CCI normalized to 0-1)",
                "sdoh_risk": "float (0-1) from SDOH agent",
                "family_history_risk": "float (0-1) from family history agent",
                "monitoring_alerts": "float (0-1) from active alert severity",
            },
            output_schema={
                "unified_score": "float (0-1)",
                "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
                "confidence_interval": "[float, float]",
                "domain_contributions": "dict (per-domain breakdown)",
                "top_risk_drivers": "list[str]",
                "risk_narrative": "str (LLM-generated)",
            },
            performance=PerformanceMetrics(
                auc_roc=0.82,
                calibration_error=0.05,
                avg_latency_ms=89,
                p95_latency_ms=150,
            ),
            safety_considerations=[
                "Emergency override: any EMERGENCY alert forces minimum score to 0.70",
                "Confidence intervals widen when fewer domains contribute data",
                "CRITICAL risk always triggers physician notification within 15 minutes",
            ],
            known_limitations=[
                "Domain weights are static (not learned from data in current version)",
                "Missing domain data is treated as 0 risk, which could underestimate",
                "No temporal modeling (scores are point-in-time, not trajectory)",
            ],
            failure_modes=[
                "Missing domain data → underestimated risk → false LOW classification",
                "Multiple borderline domains → score just below CRITICAL threshold",
                "SDOH data unavailable in rural settings → domain contributes 0",
            ],
            hitl_requirements="CRITICAL risk decisions require physician approval before Tier 5 actions execute.",
            clinical_evidence_level="B",
            source_guidelines=["LACE+ Index", "HOSPITAL Score", "Charlson Comorbidity Index"],
            monitoring_metrics=["auc_roc", "calibration_error", "risk_level_accuracy", "domain_coverage_rate"],
            alerting_thresholds={"auc_roc_min": 0.75, "calibration_error_max": 0.10, "error_rate_max": 0.05},
            retraining_criteria="Retrain when AUC-ROC drops below 0.75 on rolling 30-day evaluation window.",
        ))

        # ── Tier 4: Intervention ─────────────────────────────────────

        self.register(ModelCard(
            agent_name="contraindication_agent",
            agent_id=17,
            version="1.0.0",
            agent_tier="tier4_intervention",
            description="Checks proposed interventions against patient medication list, allergies, and conditions for drug-drug interactions, drug-disease contraindications, and allergy conflicts.",
            intended_use="Safety check layer before any prescription or medication recommendation is executed. Integrated into Tier 4 intervention pipeline.",
            out_of_scope_uses=["Dosage calculation", "Pharmacokinetic modeling", "OTC supplement interactions"],
            primary_users=["Prescribing physicians", "Clinical pharmacists", "Nurse practitioners"],
            model_type="rules-engine + knowledge graph",
            underlying_models=["Drug interaction database (FDA/NLM)", "Claude Sonnet (severity assessment)"],
            safety_considerations=[
                "Must NEVER suppress a contraindicated interaction",
                "Severity mapping: contraindicated → EMERGENCY, major → HIGH, moderate → MEDIUM",
                "All EMERGENCY-level interactions immediately interrupt for physician review",
            ],
            known_limitations=[
                "Limited to interactions in the loaded drug database",
                "Does not account for patient-specific pharmacogenomics",
                "May not detect novel drug combinations without prior documentation",
            ],
            hitl_requirements="All contraindicated interactions require physician override before proceeding.",
            clinical_evidence_level="A",
            source_guidelines=["FDA Drug Interaction Database", "Lexicomp", "KDIGO 2024"],
            monitoring_metrics=["interaction_detection_rate", "false_positive_rate", "override_rate"],
        ))

        # ── Fairness Analysis Agent ──────────────────────────────────

        self.register(ModelCard(
            agent_name="fairness_analyzer",
            agent_id=99,
            version="1.0.0",
            agent_tier="analytics",
            description="Analyzes agent decisions for demographic fairness across sex, age band, race/ethnicity, and diagnosis groups. Computes disparity ratios, equalized odds gaps, and calibration per subgroup.",
            intended_use="Post-run fairness auditing for any workflow. Generates compliance reports for regulatory review.",
            out_of_scope_uses=["Real-time fairness enforcement (use guardrails)", "Individual patient bias detection"],
            primary_users=["Compliance officers", "ML engineers", "Clinical leadership"],
            model_type="statistical analysis",
            underlying_models=["NumPy/Pandas statistical engine"],
            performance=PerformanceMetrics(
                avg_latency_ms=200,
                custom_metrics={
                    "max_acceptable_disparity_ratio": 1.25,
                    "max_demographic_parity_gap": 0.10,
                },
            ),
            safety_considerations=[
                "Small subgroup sizes (n<30) can produce unreliable fairness metrics",
                "Intersectional fairness (e.g., elderly Black women) requires separate analysis",
            ],
            source_guidelines=["HHS AI Trustworthiness Framework", "NIST AI 100-1"],
        ))

    def register(self, card: ModelCard):
        """Register a model card."""
        self._cards[card.agent_name] = card

    def get_card(self, agent_name: str) -> Optional[ModelCard]:
        return self._cards.get(agent_name)

    def get_all_cards(self) -> Dict[str, Dict]:
        return {name: card.to_dict() for name, card in self._cards.items()}

    def list_agents(self) -> List[Dict[str, str]]:
        return [
            {
                "agent_name": card.agent_name,
                "agent_id": card.agent_id,
                "tier": card.agent_tier,
                "version": card.version,
                "model_type": card.model_type,
            }
            for card in sorted(self._cards.values(), key=lambda c: c.agent_id)
        ]

    def update_performance(
        self,
        agent_name: str,
        metrics: Dict[str, float],
    ) -> Optional[ModelCard]:
        """Update performance metrics for an agent's model card."""
        card = self._cards.get(agent_name)
        if not card:
            return None

        for key, value in metrics.items():
            if hasattr(card.performance, key):
                setattr(card.performance, key, value)
            else:
                card.performance.custom_metrics[key] = value

        card.last_updated = datetime.now(timezone.utc).isoformat()
        return card

    def add_fairness_analysis(
        self,
        agent_name: str,
        analysis: FairnessAnalysis,
    ) -> Optional[ModelCard]:
        """Add fairness analysis results to an agent's model card."""
        card = self._cards.get(agent_name)
        if not card:
            return None
        card.fairness_analyses.append(analysis)
        card.last_updated = datetime.now(timezone.utc).isoformat()
        return card

    def generate_report(self, agent_name: str) -> str:
        """Generate a human-readable model card report."""
        card = self._cards.get(agent_name)
        if not card:
            return f"No model card found for agent: {agent_name}"

        lines = [
            f"# Model Card: {card.agent_name}",
            f"**Version:** {card.version} | **Tier:** {card.agent_tier} | **Type:** {card.model_type}",
            f"**Last Updated:** {card.last_updated}",
            "",
            "## Description",
            card.description,
            "",
            "## Intended Use",
            card.intended_use,
            "",
        ]

        if card.out_of_scope_uses:
            lines.append("## Out of Scope Uses")
            for use in card.out_of_scope_uses:
                lines.append(f"- {use}")
            lines.append("")

        if card.safety_considerations:
            lines.append("## Safety Considerations")
            for sc in card.safety_considerations:
                lines.append(f"- {sc}")
            lines.append("")

        if card.known_limitations:
            lines.append("## Known Limitations")
            for lim in card.known_limitations:
                lines.append(f"- {lim}")
            lines.append("")

        if card.failure_modes:
            lines.append("## Failure Modes")
            for fm in card.failure_modes:
                lines.append(f"- {fm}")
            lines.append("")

        perf = card.performance.to_dict()
        non_zero = {k: v for k, v in perf.items() if v and k != "custom_metrics"}
        if non_zero:
            lines.append("## Performance Metrics")
            for k, v in non_zero.items():
                lines.append(f"- **{k}:** {v}")
            for k, v in perf.get("custom_metrics", {}).items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")

        if card.fairness_analyses:
            lines.append("## Fairness Analysis")
            for fa in card.fairness_analyses:
                lines.append(f"### By {fa.group_by}")
                lines.append(f"- Disparity ratio: {fa.disparity_ratio:.3f}")
                lines.append(f"- Assessment: {fa.assessment}")
                for sg in fa.subgroups:
                    lines.append(f"  - {sg.get('group', '?')}: n={sg.get('n', 0)}, flagged_rate={sg.get('flagged_rate', 0):.3f}")
            lines.append("")

        if card.source_guidelines:
            lines.append("## Clinical Evidence")
            lines.append(f"- Evidence level: {card.clinical_evidence_level}")
            for sg in card.source_guidelines:
                lines.append(f"- {sg}")
            lines.append("")

        if card.hitl_requirements:
            lines.append("## Human-in-the-Loop Requirements")
            lines.append(card.hitl_requirements)
            lines.append("")

        return "\n".join(lines)
