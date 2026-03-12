"""
Eminence HealthOS — Image Analysis Agent (#52)
Layer 2 (Interpretation): AI-powered medical image analysis including
chest X-ray screening, fracture detection, and retinal scan analysis.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

# AI models per modality
AI_MODELS: dict[str, dict[str, Any]] = {
    "chest_xray": {
        "model": "CheXNet-v2",
        "architecture": "DenseNet-121",
        "findings": ["pneumonia", "cardiomegaly", "pleural_effusion", "pneumothorax", "nodule", "fracture", "atelectasis", "consolidation"],
        "performance": {"auc": 0.94, "sensitivity": 0.91, "specificity": 0.92},
    },
    "ct_head": {
        "model": "DeepBleed-v1",
        "architecture": "ResNet-50",
        "findings": ["hemorrhage", "midline_shift", "mass_effect", "hydrocephalus", "infarct"],
        "performance": {"auc": 0.96, "sensitivity": 0.93, "specificity": 0.95},
    },
    "ct_chest": {
        "model": "LungNet-v2",
        "architecture": "EfficientNet-B7",
        "findings": ["pulmonary_embolism", "lung_nodule", "ground_glass_opacity", "consolidation", "lymphadenopathy"],
        "performance": {"auc": 0.95, "sensitivity": 0.92, "specificity": 0.93},
    },
    "mammography": {
        "model": "BreastScreen-v1",
        "architecture": "EfficientNet + Attention",
        "findings": ["mass", "calcification", "architectural_distortion", "asymmetry"],
        "performance": {"auc": 0.93, "sensitivity": 0.90, "specificity": 0.91},
    },
    "retinal": {
        "model": "RetinaNet-DR",
        "architecture": "InceptionV3",
        "findings": ["diabetic_retinopathy", "macular_degeneration", "glaucoma", "microaneurysm"],
        "performance": {"auc": 0.97, "sensitivity": 0.95, "specificity": 0.96},
    },
    "ecg": {
        "model": "CardioAI-ECG",
        "architecture": "1D-CNN + LSTM",
        "findings": ["stemi", "afib", "avblock", "qt_prolongation", "lvh", "rvh"],
        "performance": {"auc": 0.96, "sensitivity": 0.94, "specificity": 0.95},
    },
}

SEVERITY_MAP = {"critical": 0, "high": 1, "moderate": 2, "low": 3}


class ImageAnalysisAgent(BaseAgent):
    """AI-powered medical image analysis across multiple modalities."""

    name = "image_analysis"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = (
        "AI image analysis — chest X-ray screening, CT hemorrhage detection, "
        "mammography, retinal scanning, ECG interpretation, and fracture detection"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "analyze_image")

        if action == "analyze_image":
            return self._analyze_image(input_data)
        elif action == "detect_findings":
            return self._detect_findings(input_data)
        elif action == "compare_priors":
            return self._compare_priors(input_data)
        elif action == "model_info":
            return self._model_info(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown image analysis action: {action}",
                status=AgentStatus.FAILED,
            )

    def _analyze_image(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        study_type = ctx.get("study_type", "chest_xray")
        study_id = ctx.get("study_id", str(uuid.uuid4()))

        model_info = AI_MODELS.get(study_type, AI_MODELS["chest_xray"])

        # Simulated AI findings based on study type
        findings_by_type: dict[str, list[dict[str, Any]]] = {
            "chest_xray": [
                {"finding": "cardiomegaly", "confidence": 0.87, "severity": "moderate", "location": "cardiac_silhouette", "description": "Mild cardiomegaly with cardiothoracic ratio 0.55"},
                {"finding": "clear_lungs", "confidence": 0.94, "severity": "low", "location": "bilateral_lung_fields", "description": "No focal consolidation or pleural effusion"},
            ],
            "ct_head": [
                {"finding": "no_hemorrhage", "confidence": 0.97, "severity": "low", "location": "intracranial", "description": "No acute intracranial hemorrhage"},
                {"finding": "no_midline_shift", "confidence": 0.98, "severity": "low", "location": "midline", "description": "No midline shift or mass effect"},
            ],
            "mammography": [
                {"finding": "birads_2", "confidence": 0.91, "severity": "low", "location": "bilateral_breast", "description": "BI-RADS 2 — Benign finding, scattered fibroglandular densities"},
            ],
            "retinal": [
                {"finding": "mild_npdr", "confidence": 0.89, "severity": "moderate", "location": "bilateral_retina", "description": "Mild non-proliferative diabetic retinopathy with microaneurysms"},
            ],
        }

        findings = findings_by_type.get(study_type, findings_by_type["chest_xray"])
        has_critical = any(f["severity"] == "critical" for f in findings)

        result = {
            "analysis_id": str(uuid.uuid4()),
            "study_id": study_id,
            "analyzed_at": now.isoformat(),
            "study_type": study_type,
            "model_used": model_info["model"],
            "model_architecture": model_info["architecture"],
            "model_performance": model_info["performance"],
            "findings": findings,
            "total_findings": len(findings),
            "highest_severity": min((f["severity"] for f in findings), key=lambda s: SEVERITY_MAP.get(s, 99)) if findings else None,
            "has_critical_finding": has_critical,
            "requires_urgent_read": has_critical,
            "ai_confidence": round(sum(f["confidence"] for f in findings) / max(len(findings), 1), 3),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.88,
            rationale=f"AI analysis ({model_info['model']}): {len(findings)} findings, highest severity: {result['highest_severity']}",
        )

    def _detect_findings(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        study_type = ctx.get("study_type", "chest_xray")
        model_info = AI_MODELS.get(study_type, AI_MODELS["chest_xray"])

        detections = [
            {"finding": f, "detected": False, "confidence": 0.0}
            for f in model_info["findings"]
        ]
        # Simulate one positive finding
        if detections:
            detections[0]["detected"] = True
            detections[0]["confidence"] = 0.87

        result = {
            "study_type": study_type,
            "detected_at": now.isoformat(),
            "model": model_info["model"],
            "detections": detections,
            "positive_findings": sum(1 for d in detections if d["detected"]),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.87,
            rationale=f"Detection scan: {result['positive_findings']} positive findings",
        )

    def _compare_priors(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "compared_at": now.isoformat(),
            "current_study_id": ctx.get("current_study_id", "STD-001"),
            "prior_study_id": ctx.get("prior_study_id", "STD-000"),
            "interval_days": ctx.get("interval_days", 90),
            "changes": [
                {"finding": "cardiomegaly", "current": "mild", "prior": "borderline", "change": "slightly_worse", "clinical_significance": "monitor"},
                {"finding": "pleural_effusion", "current": "none", "prior": "none", "change": "stable", "clinical_significance": "none"},
            ],
            "overall_impression": "Mild interval progression of cardiomegaly, otherwise stable",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82,
            rationale="Prior comparison: mild interval changes noted",
        )

    def _model_info(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        study_type = ctx.get("study_type")

        if study_type and study_type in AI_MODELS:
            models = {study_type: AI_MODELS[study_type]}
        else:
            models = AI_MODELS

        result = {
            "models": models,
            "total_models": len(models),
            "supported_study_types": list(AI_MODELS.keys()),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.99,
            rationale=f"Model info: {len(models)} model(s) returned",
        )
