"""
HealthOS Agent Observability & Explainability Module

Provides unified tracing, decision logging, feature attribution,
model cards, and audit trails for all healthcare AI agents.
"""

from observability.core.tracer import (
    ObservabilityManager,
    TraceContext,
    SpanContext,
    trace_agent_action,
    trace_decision,
)
from observability.core.audit import AuditLogger, AuditEventType
from observability.explainability.feature_attribution import FeatureAttributionEngine
from observability.explainability.decision_explainer import DecisionExplainer
from observability.model_cards.generator import ModelCardGenerator
from observability.metrics.collector import MetricsCollector

__all__ = [
    "ObservabilityManager",
    "TraceContext",
    "SpanContext",
    "trace_agent_action",
    "trace_decision",
    "AuditLogger",
    "AuditEventType",
    "FeatureAttributionEngine",
    "DecisionExplainer",
    "ModelCardGenerator",
    "MetricsCollector",
]
