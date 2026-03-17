"""
Eminence HealthOS — ML Model Registry API Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/ml", tags=["ML Models"])


@router.get("/models")
async def list_models(ctx: TenantContext = Depends(get_current_user)):
    """List registered ML models."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    return {
        "models": [
            {
                "id": "bilstm-glucose",
                "name": "BiLSTM Glucose Predictor",
                "type": "BiLSTM",
                "version": "3.2.1",
                "status": "active",
                "accuracy": 0.943,
                "last_trained": "2026-03-10T08:00:00Z",
                "predictions_count": 12847,
                "description": "Bidirectional LSTM for continuous glucose level prediction",
            },
            {
                "id": "xgb-readmission",
                "name": "XGBoost Readmission Risk",
                "type": "XGBoost",
                "version": "2.1.0",
                "status": "active",
                "accuracy": 0.891,
                "last_trained": "2026-03-08T14:30:00Z",
                "predictions_count": 8432,
                "description": "30-day hospital readmission risk prediction",
            },
            {
                "id": "rf-sepsis",
                "name": "Random Forest Sepsis Detector",
                "type": "Random Forest",
                "version": "1.4.2",
                "status": "active",
                "accuracy": 0.927,
                "last_trained": "2026-03-12T11:00:00Z",
                "predictions_count": 5621,
                "description": "Early sepsis detection from vitals and lab results",
            },
            {
                "id": "cnn-xray",
                "name": "CNN Chest X-Ray Classifier",
                "type": "CNN",
                "version": "4.0.0",
                "status": "active",
                "accuracy": 0.961,
                "last_trained": "2026-03-05T09:15:00Z",
                "predictions_count": 3210,
                "description": "Multi-label chest X-ray pathology classification",
            },
        ]
    }


_MODEL_METRICS: dict[str, dict] = {
    "bilstm-glucose": {
        "accuracy": 0.943, "precision": 0.931, "recall": 0.956, "f1": 0.943, "auc_roc": 0.978,
        "fairness": {"demographic_parity": 0.92, "equalized_odds": 0.89, "calibration": 0.94},
        "performance_by_group": {
            "age_18_40": {"accuracy": 0.951, "count": 3200},
            "age_41_65": {"accuracy": 0.942, "count": 5800},
            "age_65_plus": {"accuracy": 0.931, "count": 3847},
        },
    },
    "xgb-readmission": {
        "accuracy": 0.891, "precision": 0.874, "recall": 0.912, "f1": 0.893, "auc_roc": 0.945,
        "fairness": {"demographic_parity": 0.88, "equalized_odds": 0.85, "calibration": 0.91},
        "performance_by_group": {
            "age_18_40": {"accuracy": 0.903, "count": 2100},
            "age_41_65": {"accuracy": 0.889, "count": 3800},
            "age_65_plus": {"accuracy": 0.878, "count": 2532},
        },
    },
    "rf-sepsis": {
        "accuracy": 0.927, "precision": 0.918, "recall": 0.937, "f1": 0.927, "auc_roc": 0.968,
        "fairness": {"demographic_parity": 0.90, "equalized_odds": 0.87, "calibration": 0.93},
        "performance_by_group": {
            "age_18_40": {"accuracy": 0.935, "count": 1400},
            "age_41_65": {"accuracy": 0.928, "count": 2500},
            "age_65_plus": {"accuracy": 0.916, "count": 1721},
        },
    },
    "cnn-xray": {
        "accuracy": 0.961, "precision": 0.955, "recall": 0.967, "f1": 0.961, "auc_roc": 0.989,
        "fairness": {"demographic_parity": 0.95, "equalized_odds": 0.93, "calibration": 0.96},
        "performance_by_group": {
            "age_18_40": {"accuracy": 0.968, "count": 800},
            "age_41_65": {"accuracy": 0.960, "count": 1400},
            "age_65_plus": {"accuracy": 0.952, "count": 1010},
        },
    },
}


@router.get("/models/{model_id}/metrics")
async def get_model_metrics(model_id: str, ctx: TenantContext = Depends(get_current_user)):
    """Get detailed metrics for a specific ML model."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    from fastapi import HTTPException
    metrics = _MODEL_METRICS.get(model_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return {"model_id": model_id, **metrics}


@router.get("/federated/status")
async def federated_status(ctx: TenantContext = Depends(get_current_user)):
    """Get federated learning status."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    return {
        "status": "in_progress",
        "current_round": 7,
        "total_rounds": 12,
        "participating_tenants": 5,
        "global_accuracy": 0.908,
        "privacy_budget_remaining": 0.64,
        "last_aggregation": "2026-03-14T22:30:00Z",
    }
