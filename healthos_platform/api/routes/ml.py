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
