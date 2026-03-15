"""
HealthOS ML Models
==================

Adapted from InHealth Capstone Project for the HealthOS platform.
All models use plain-dict / Pydantic patient data interfaces (no Django ORM).

Models:
    - PatientDigitalTwin: Physiological ODE simulation (glucose, BP, CKD)
    - LSTMGlucoseModel: BiLSTM glucose prediction (30/60/120 min horizons)
    - RandomForestDiseaseClassifier: Multi-label chronic disease classification
    - XGBoostRiskModel: 7-day hospitalization risk scoring
    - HMMLifestyleModel: Lifestyle pattern detection via Hidden Markov Model
    - MultiModalAttentionFusion: Cross-modal attention risk assessment

Federated Learning:
    - FederatedCoordinator: Privacy-preserving federated training across tenants
    - FederatedClient: Per-tenant local training with differential privacy
"""

from .digital_twin import (
    PatientDigitalTwin,
    PatientPhysiologyParams,
    SimulationResult,
    SimulationScenario,
)
from .hmm_lifestyle import HMMLifestyleModel
from .lstm_glucose import LSTMGlucoseModel
from .multimodal_risk import MultiModalAttentionFusion
from .random_forest import RandomForestDiseaseClassifier
from .xgboost_risk import XGBoostRiskModel

__all__ = [
    # Digital Twin
    "PatientDigitalTwin",
    "PatientPhysiologyParams",
    "SimulationScenario",
    "SimulationResult",
    # ML Models
    "LSTMGlucoseModel",
    "RandomForestDiseaseClassifier",
    "XGBoostRiskModel",
    "HMMLifestyleModel",
    "MultiModalAttentionFusion",
]
