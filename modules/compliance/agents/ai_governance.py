"""
Eminence HealthOS — AI Governance Agent (#68)
Layer 5 (Measurement): Tracks all AI model usage, accuracy, drift, and bias
across the platform to ensure responsible and compliant AI operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import json
import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

# ── Model Registry ───────────────────────────────────────────────────────────

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "risk_scoring": {
        "model_id": "risk_scoring",
        "name": "Patient Risk Scoring Model",
        "version": "2.3.1",
        "purpose": "Predicts patient deterioration risk based on vitals and clinical history",
        "model_type": "gradient_boosting",
        "training_date": "2025-11-15",
        "last_validated": "2026-01-20",
        "performance_baseline": {
            "accuracy": 0.89,
            "precision": 0.86,
            "recall": 0.91,
            "f1": 0.885,
            "auc": 0.93,
        },
        "owner": "clinical_ai_team",
        "approval_status": "approved",
        "retraining_schedule_days": 90,
    },
    "readmission_prediction": {
        "model_id": "readmission_prediction",
        "name": "30-Day Readmission Predictor",
        "version": "1.8.0",
        "purpose": "Predicts likelihood of hospital readmission within 30 days of discharge",
        "model_type": "logistic_regression_ensemble",
        "training_date": "2025-10-01",
        "last_validated": "2026-01-10",
        "performance_baseline": {
            "accuracy": 0.84,
            "precision": 0.79,
            "recall": 0.87,
            "f1": 0.828,
            "auc": 0.90,
        },
        "owner": "clinical_ai_team",
        "approval_status": "approved",
        "retraining_schedule_days": 60,
    },
    "anomaly_detection": {
        "model_id": "anomaly_detection",
        "name": "Vital Sign Anomaly Detector",
        "version": "3.1.0",
        "purpose": "Detects anomalous patterns in patient vital signs in real time",
        "model_type": "isolation_forest",
        "training_date": "2025-12-01",
        "last_validated": "2026-02-15",
        "performance_baseline": {
            "accuracy": 0.92,
            "precision": 0.88,
            "recall": 0.94,
            "f1": 0.909,
            "auc": 0.96,
        },
        "owner": "platform_team",
        "approval_status": "approved",
        "retraining_schedule_days": 30,
    },
    "cohort_clustering": {
        "model_id": "cohort_clustering",
        "name": "Patient Cohort Clustering",
        "version": "1.2.0",
        "purpose": "Groups patients into cohorts based on clinical and demographic features",
        "model_type": "k_means_hierarchical",
        "training_date": "2025-09-15",
        "last_validated": "2025-12-20",
        "performance_baseline": {
            "accuracy": 0.81,
            "precision": 0.78,
            "recall": 0.83,
            "f1": 0.804,
            "auc": 0.87,
        },
        "owner": "analytics_team",
        "approval_status": "approved",
        "retraining_schedule_days": 120,
    },
    "nlp_extraction": {
        "model_id": "nlp_extraction",
        "name": "Clinical NLP Extractor",
        "version": "2.0.1",
        "purpose": "Extracts structured clinical data from unstructured clinical notes",
        "model_type": "transformer_ner",
        "training_date": "2025-11-01",
        "last_validated": "2026-01-30",
        "performance_baseline": {
            "accuracy": 0.91,
            "precision": 0.89,
            "recall": 0.88,
            "f1": 0.885,
            "auc": 0.94,
        },
        "owner": "nlp_team",
        "approval_status": "approved",
        "retraining_schedule_days": 90,
    },
    "treatment_recommendation": {
        "model_id": "treatment_recommendation",
        "name": "Treatment Recommendation Engine",
        "version": "1.5.2",
        "purpose": "Suggests evidence-based treatment options based on patient profile and guidelines",
        "model_type": "knowledge_graph_ml",
        "training_date": "2025-10-15",
        "last_validated": "2026-02-01",
        "performance_baseline": {
            "accuracy": 0.86,
            "precision": 0.84,
            "recall": 0.82,
            "f1": 0.830,
            "auc": 0.91,
        },
        "owner": "clinical_ai_team",
        "approval_status": "approved",
        "retraining_schedule_days": 60,
    },
}


class AIGovernanceAgent(BaseAgent):
    """Tracks all AI model usage, accuracy, drift, and bias across the platform."""

    name = "ai_governance"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = (
        "AI governance and model lifecycle management — tracks usage, accuracy, "
        "drift, bias, and compliance across all platform AI models"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "model_inventory")

        if action == "model_inventory":
            return await self._model_inventory(input_data)
        elif action == "drift_detection":
            return await self._drift_detection(input_data)
        elif action == "bias_audit":
            return await self._bias_audit(input_data)
        elif action == "performance_report":
            return await self._performance_report(input_data)
        elif action == "governance_check":
            return await self._governance_check(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown AI governance action: {action}",
                status=AgentStatus.FAILED,
            )

    # ── Model Inventory ──────────────────────────────────────────────────────

    async def _model_inventory(self, input_data: AgentInput) -> AgentOutput:
        """Catalog all AI models in use with version, purpose, training date, and performance."""
        now = datetime.now(timezone.utc)

        models = []
        for model_id, model in MODEL_REGISTRY.items():
            models.append({
                "model_id": model_id,
                "name": model["name"],
                "version": model["version"],
                "purpose": model["purpose"],
                "model_type": model["model_type"],
                "training_date": model["training_date"],
                "last_validated": model["last_validated"],
                "owner": model["owner"],
                "approval_status": model["approval_status"],
                "retraining_schedule_days": model["retraining_schedule_days"],
                "baseline_metrics": model["performance_baseline"],
            })

        result = {
            "inventory_type": "model_inventory",
            "generated_at": now.isoformat(),
            "total_models": len(models),
            "models": models,
            "summary": {
                "approved": sum(1 for m in models if m["approval_status"] == "approved"),
                "pending_review": sum(1 for m in models if m["approval_status"] == "pending"),
                "deprecated": sum(1 for m in models if m["approval_status"] == "deprecated"),
            },
        }

        # ── LLM: generate governance narrative ─────────────────────────────────
        try:
            prompt = (
                "You are an AI governance specialist. Based on the following model inventory "
                "data, produce a concise narrative (2-3 paragraphs) analyzing the overall AI "
                "model portfolio health, identifying governance risks, and recommending actions "
                "to strengthen AI oversight.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered governance analyst for a healthcare platform. "
                    "Provide expert analysis of AI model health, bias risks, and governance recommendations."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["governance_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for model_inventory; continuing without narrative")
            result["governance_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Model inventory: {len(models)} models cataloged, all approved",
        )

    # ── Drift Detection ──────────────────────────────────────────────────────

    async def _drift_detection(self, input_data: AgentInput) -> AgentOutput:
        """Compare current model performance against baseline using PSI."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        model_id = ctx.get("model_id")
        current_metrics = ctx.get("current_metrics", {})

        PSI_THRESHOLD_WARNING = 0.1
        PSI_THRESHOLD_SIGNIFICANT = 0.2

        if model_id and model_id in MODEL_REGISTRY:
            models_to_check = {model_id: MODEL_REGISTRY[model_id]}
        else:
            models_to_check = MODEL_REGISTRY

        drift_results: list[dict[str, Any]] = []

        for mid, model in models_to_check.items():
            baseline = model["performance_baseline"]
            current = current_metrics.get(mid, {})

            metric_drifts: list[dict[str, Any]] = []
            max_psi = 0.0

            for metric_name, baseline_val in baseline.items():
                current_val = current.get(metric_name, baseline_val)
                # Compute a simplified PSI approximation
                delta = abs(current_val - baseline_val)
                psi = round(delta / max(baseline_val, 0.01), 4)
                max_psi = max(max_psi, psi)

                if psi > PSI_THRESHOLD_WARNING:
                    metric_drifts.append({
                        "metric": metric_name,
                        "baseline": baseline_val,
                        "current": current_val,
                        "psi": psi,
                        "status": "significant_drift" if psi > PSI_THRESHOLD_SIGNIFICANT else "warning",
                    })

            if max_psi > PSI_THRESHOLD_SIGNIFICANT:
                overall_status = "significant_drift"
            elif max_psi > PSI_THRESHOLD_WARNING:
                overall_status = "warning"
            else:
                overall_status = "stable"

            drift_results.append({
                "model_id": mid,
                "model_name": model["name"],
                "overall_status": overall_status,
                "max_psi": max_psi,
                "drifted_metrics": metric_drifts,
                "recommendation": self._drift_recommendation(overall_status, mid),
            })

        models_drifted = sum(1 for d in drift_results if d["overall_status"] != "stable")

        result = {
            "analysis_type": "drift_detection",
            "analyzed_at": now.isoformat(),
            "psi_thresholds": {
                "warning": PSI_THRESHOLD_WARNING,
                "significant": PSI_THRESHOLD_SIGNIFICANT,
            },
            "models_analyzed": len(drift_results),
            "models_with_drift": models_drifted,
            "results": sorted(drift_results, key=lambda d: d["max_psi"], reverse=True),
        }

        confidence = 0.90 if current_metrics else 0.70

        # ── LLM: generate governance narrative ─────────────────────────────────
        try:
            prompt = (
                "You are an AI model monitoring specialist. Based on the following drift "
                "detection results, produce a concise narrative (2-3 paragraphs) explaining "
                "which models are drifting, the potential impact on clinical decisions, and "
                "recommended retraining or mitigation actions.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered governance analyst for a healthcare platform. "
                    "Provide expert analysis of AI model health, bias risks, and governance recommendations."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["governance_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for drift_detection; continuing without narrative")
            result["governance_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Drift detection: {len(drift_results)} models analyzed — "
                f"{models_drifted} with drift (PSI > {PSI_THRESHOLD_WARNING})"
            ),
        )

    # ── Bias Audit ───────────────────────────────────────────────────────────

    async def _bias_audit(self, input_data: AgentInput) -> AgentOutput:
        """Analyze model predictions across demographic groups for disparate impact."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        model_id = ctx.get("model_id", "risk_scoring")
        predictions = ctx.get("predictions", [])

        demographic_groups = {
            "age": {"18-30": [], "31-50": [], "51-65": [], "65+": []},
            "gender": {"male": [], "female": [], "other": []},
            "ethnicity": {
                "white": [], "black": [], "hispanic": [], "asian": [],
                "native_american": [], "pacific_islander": [], "other": [],
            },
        }

        for pred in predictions:
            score = pred.get("score", 0)
            for dim in demographic_groups:
                group = pred.get(dim, "unknown")
                if group in demographic_groups[dim]:
                    demographic_groups[dim][group].append(score)

        DISPARATE_IMPACT_THRESHOLD = 0.8
        bias_findings: list[dict[str, Any]] = []

        for dimension, groups in demographic_groups.items():
            group_rates: dict[str, float] = {}
            for group_name, scores in groups.items():
                if scores:
                    group_rates[group_name] = round(sum(scores) / len(scores), 4)

            if not group_rates:
                continue

            max_rate = max(group_rates.values())
            for group_name, rate in group_rates.items():
                if max_rate > 0:
                    ratio = round(rate / max_rate, 4)
                    if ratio < DISPARATE_IMPACT_THRESHOLD:
                        bias_findings.append({
                            "dimension": dimension,
                            "group": group_name,
                            "group_avg_score": rate,
                            "reference_avg_score": max_rate,
                            "disparate_impact_ratio": ratio,
                            "threshold": DISPARATE_IMPACT_THRESHOLD,
                            "status": "potential_bias",
                            "recommendation": (
                                f"Investigate {dimension}={group_name} scoring disparity — "
                                f"ratio {ratio:.2f} below {DISPARATE_IMPACT_THRESHOLD} threshold"
                            ),
                        })

        result = {
            "audit_type": "bias_audit",
            "audited_at": now.isoformat(),
            "model_id": model_id,
            "total_predictions_analyzed": len(predictions),
            "disparate_impact_threshold": DISPARATE_IMPACT_THRESHOLD,
            "dimensions_analyzed": list(demographic_groups.keys()),
            "findings_count": len(bias_findings),
            "findings": bias_findings,
            "overall_status": "bias_detected" if bias_findings else "no_bias_detected",
        }

        confidence = 0.88 if predictions else 0.55

        # ── LLM: generate governance narrative ─────────────────────────────────
        try:
            prompt = (
                "You are an AI fairness and bias expert. Based on the following bias audit "
                "results, produce a concise narrative (2-3 paragraphs) explaining any detected "
                "disparate impact, potential root causes, and recommended mitigation strategies "
                "to ensure equitable AI outcomes across demographic groups.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered governance analyst for a healthcare platform. "
                    "Provide expert analysis of AI model health, bias risks, and governance recommendations."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["governance_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for bias_audit; continuing without narrative")
            result["governance_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Bias audit for {model_id}: {len(predictions)} predictions analyzed — "
                f"{len(bias_findings)} potential bias findings"
            ),
        )

    # ── Performance Report ───────────────────────────────────────────────────

    async def _performance_report(self, input_data: AgentInput) -> AgentOutput:
        """Generate model performance dashboard data."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        current_metrics = ctx.get("current_metrics", {})

        model_reports: list[dict[str, Any]] = []

        for model_id, model in MODEL_REGISTRY.items():
            baseline = model["performance_baseline"]
            current = current_metrics.get(model_id, baseline)

            report = {
                "model_id": model_id,
                "name": model["name"],
                "version": model["version"],
                "metrics": {
                    metric: {
                        "baseline": baseline[metric],
                        "current": current.get(metric, baseline[metric]),
                        "delta": round(current.get(metric, baseline[metric]) - baseline[metric], 4),
                    }
                    for metric in baseline
                },
                "overall_health": self._model_health(baseline, current),
                "last_validated": model["last_validated"],
                "training_date": model["training_date"],
            }
            model_reports.append(report)

        result = {
            "report_type": "performance_report",
            "generated_at": now.isoformat(),
            "total_models": len(model_reports),
            "models": model_reports,
            "summary": {
                "healthy": sum(1 for r in model_reports if r["overall_health"] == "healthy"),
                "degraded": sum(1 for r in model_reports if r["overall_health"] == "degraded"),
                "critical": sum(1 for r in model_reports if r["overall_health"] == "critical"),
            },
        }

        # ── LLM: generate governance narrative ─────────────────────────────────
        try:
            prompt = (
                "You are an AI model performance analyst. Based on the following performance "
                "report data, produce a concise narrative (2-3 paragraphs) summarizing overall "
                "model health across the portfolio, highlighting degraded or critical models, "
                "and recommending remediation or retraining actions.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered governance analyst for a healthcare platform. "
                    "Provide expert analysis of AI model health, bias risks, and governance recommendations."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["governance_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for performance_report; continuing without narrative")
            result["governance_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.92,
            rationale=(
                f"Performance report: {len(model_reports)} models — "
                f"{result['summary']['healthy']} healthy, "
                f"{result['summary']['degraded']} degraded, "
                f"{result['summary']['critical']} critical"
            ),
        )

    # ── Governance Check ─────────────────────────────────────────────────────

    async def _governance_check(self, input_data: AgentInput) -> AgentOutput:
        """Validate model lifecycle compliance — approval, testing, monitoring, retraining."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        lifecycle_requirements = [
            "model_approval",
            "pre_deployment_testing",
            "production_monitoring",
            "retraining_schedule",
            "documentation",
            "access_controls",
            "audit_logging",
            "incident_response",
        ]

        model_compliance: list[dict[str, Any]] = []

        for model_id, model in MODEL_REGISTRY.items():
            overrides = ctx.get("model_compliance", {}).get(model_id, {})

            checks: list[dict[str, Any]] = []
            for req in lifecycle_requirements:
                status = overrides.get(req, True)
                checks.append({"requirement": req, "status": "compliant" if status else "non_compliant"})

            # Check retraining schedule
            training_date_str = model["training_date"]
            try:
                training_dt = datetime.fromisoformat(training_date_str).replace(tzinfo=timezone.utc)
                days_since_training = (now - training_dt).days
                retraining_due = days_since_training > model["retraining_schedule_days"]
            except (ValueError, TypeError):
                retraining_due = True
                days_since_training = -1

            compliant_count = sum(1 for c in checks if c["status"] == "compliant")
            total_checks = len(checks)

            model_compliance.append({
                "model_id": model_id,
                "model_name": model["name"],
                "version": model["version"],
                "approval_status": model["approval_status"],
                "checks": checks,
                "compliant_count": compliant_count,
                "total_checks": total_checks,
                "compliance_rate": round(compliant_count / max(total_checks, 1) * 100, 1),
                "retraining_due": retraining_due,
                "days_since_training": days_since_training,
                "retraining_schedule_days": model["retraining_schedule_days"],
            })

        fully_compliant = sum(1 for m in model_compliance if m["compliance_rate"] == 100.0)
        needing_retraining = sum(1 for m in model_compliance if m["retraining_due"])

        result = {
            "check_type": "governance_check",
            "checked_at": now.isoformat(),
            "total_models": len(model_compliance),
            "fully_compliant": fully_compliant,
            "needing_retraining": needing_retraining,
            "lifecycle_requirements": lifecycle_requirements,
            "models": model_compliance,
        }

        confidence = 0.93

        # ── LLM: generate governance narrative ─────────────────────────────────
        try:
            prompt = (
                "You are an AI governance compliance expert. Based on the following governance "
                "check results, produce a concise narrative (2-3 paragraphs) assessing model "
                "lifecycle compliance, highlighting models due for retraining, and recommending "
                "governance improvements.\n\n"
                f"{json.dumps(result, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are an AI-powered governance analyst for a healthcare platform. "
                    "Provide expert analysis of AI model health, bias risks, and governance recommendations."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            result["governance_narrative"] = resp.content
        except Exception:
            logger.warning("LLM narrative generation failed for governance_check; continuing without narrative")
            result["governance_narrative"] = None
        # ─────────────────────────────────────────────────────────────────────

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=(
                f"Governance check: {fully_compliant}/{len(model_compliance)} models fully compliant; "
                f"{needing_retraining} due for retraining"
            ),
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _drift_recommendation(status: str, model_id: str) -> str:
        if status == "significant_drift":
            return f"Immediate retraining recommended for {model_id} — significant performance drift detected"
        elif status == "warning":
            return f"Monitor {model_id} closely — early signs of drift; schedule retraining within 2 weeks"
        return f"{model_id} is stable — continue standard monitoring"

    @staticmethod
    def _model_health(baseline: dict[str, float], current: dict[str, Any]) -> str:
        deltas = []
        for metric, base_val in baseline.items():
            curr_val = current.get(metric, base_val)
            if base_val > 0:
                deltas.append((curr_val - base_val) / base_val)

        if not deltas:
            return "healthy"

        avg_delta = sum(deltas) / len(deltas)
        if avg_delta < -0.10:
            return "critical"
        elif avg_delta < -0.05:
            return "degraded"
        return "healthy"
