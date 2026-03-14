"""
Eminence HealthOS — Agent Type System
Defines the data contracts for all agent inputs, outputs, and states.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class AgentTier(str, Enum):
    SENSING = "sensing"          # Layer 1: Data ingestion & normalization
    INTERPRETATION = "interpretation"  # Layer 2: Analysis & anomaly detection
    DECISIONING = "decisioning"  # Layer 3: Risk scoring & policy checks
    ACTION = "action"            # Layer 4: Alerts, notifications, orders
    MEASUREMENT = "measurement"  # Layer 5: Outcomes & population health
    # Backward-compatible aliases used by module agents
    MONITORING = "sensing"
    DIAGNOSTIC = "interpretation"
    RISK = "decisioning"
    INTERVENTION = "action"


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_HITL = "waiting_hitl"  # Paused for human-in-the-loop review


class Severity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class VitalType(str, Enum):
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"
    GLUCOSE = "glucose"
    SPO2 = "spo2"
    WEIGHT = "weight"
    TEMPERATURE = "temperature"
    RESPIRATORY_RATE = "respiratory_rate"
    ACTIVITY = "activity"
    SLEEP = "sleep"


class AlertType(str, Enum):
    PATIENT_NOTIFICATION = "patient_notification"
    NURSE_REVIEW = "nurse_review"
    PHYSICIAN_REVIEW = "physician_review"
    TELEHEALTH_TRIGGER = "telehealth_trigger"
    EMERGENCY = "emergency"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════


class AgentMessage(BaseModel):
    """Message passed between agents in the pipeline."""

    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_agent: str
    target_agent: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentInput(BaseModel):
    """Standard input for every agent invocation."""

    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    patient_id: uuid.UUID | None = None
    trigger: str = ""  # What triggered this agent (event type, upstream agent, etc.)
    context: dict[str, Any] = Field(default_factory=dict)
    messages: list[AgentMessage] = Field(default_factory=list)

    @property
    def data(self) -> dict[str, Any]:
        """Backward-compatible alias: module agents access input.data."""
        return self.context

    @property
    def tenant_id(self) -> uuid.UUID:
        """Backward-compatible alias for org_id."""
        return self.org_id


class AgentOutput(BaseModel):
    """Standard output from every agent invocation."""

    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    agent_name: str = ""
    status: AgentStatus = AgentStatus.COMPLETED
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    result: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    messages: list[AgentMessage] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    requires_hitl: bool = False
    hitl_reason: str | None = None
    # Backward-compatible fields used by module agents
    agent_tier: str = ""
    decision: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    feature_contributions: list[dict[str, Any]] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# VITAL SIGN DATA
# ═══════════════════════════════════════════════════════════════════════════════


class VitalReading(BaseModel):
    """A single vital sign reading from a device or manual entry."""

    patient_id: uuid.UUID
    org_id: uuid.UUID
    device_id: str | None = None
    vital_type: VitalType
    value: dict[str, Any]  # e.g. {"systolic": 140, "diastolic": 90} or {"value": 72}
    unit: str
    recorded_at: datetime
    source: str = "wearable"  # wearable, home_device, manual, telehealth
    quality_score: float = 1.0


class NormalizedVital(BaseModel):
    """A vital reading after normalization and validation."""

    patient_id: uuid.UUID
    org_id: uuid.UUID
    vital_type: VitalType
    value: dict[str, Any]
    unit: str
    recorded_at: datetime
    source: str
    quality_score: float
    is_valid: bool = True
    validation_notes: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY & ALERT DATA
# ═══════════════════════════════════════════════════════════════════════════════


class AnomalyDetection(BaseModel):
    """An anomaly detected in patient vitals."""

    patient_id: uuid.UUID
    org_id: uuid.UUID
    anomaly_type: str  # threshold_breach, trend_drift, sudden_change, pattern_anomaly
    vital_type: VitalType
    severity: Severity
    description: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    contributing_vitals: list[uuid.UUID] = Field(default_factory=list)
    detected_by: str = ""  # agent name


class RiskAssessment(BaseModel):
    """A risk score computed for a patient."""

    patient_id: uuid.UUID
    org_id: uuid.UUID
    score_type: str  # deterioration, readmission, hospitalization, medication_adherence
    score: float = Field(ge=0.0, le=1.0)
    risk_level: Severity
    contributing_factors: list[dict[str, Any]] = Field(default_factory=list)
    model_version: str = "v1.0"
    recommendations: list[str] = Field(default_factory=list)


class AlertRequest(BaseModel):
    """A request to generate an alert for clinical review."""

    patient_id: uuid.UUID
    org_id: uuid.UUID
    alert_type: AlertType
    priority: Severity
    message: str
    anomaly_id: uuid.UUID | None = None
    escalation_path: list[dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE STATE (LangGraph)
# ═══════════════════════════════════════════════════════════════════════════════


class PipelineState(BaseModel):
    """Shared state passed through the agent pipeline graph."""

    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    patient_id: uuid.UUID
    trigger_event: str = ""

    # Data flowing through the pipeline
    raw_vitals: list[VitalReading] = Field(default_factory=list)
    normalized_vitals: list[NormalizedVital] = Field(default_factory=list)
    anomalies: list[AnomalyDetection] = Field(default_factory=list)
    risk_assessments: list[RiskAssessment] = Field(default_factory=list)
    alert_requests: list[AlertRequest] = Field(default_factory=list)

    # Agent execution tracking
    executed_agents: list[str] = Field(default_factory=list)
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)

    # Policy & governance
    policy_violations: list[str] = Field(default_factory=list)
    requires_hitl: bool = False
    hitl_reason: str | None = None

    # Context assembled for downstream agents
    patient_context: dict[str, Any] = Field(default_factory=dict)
