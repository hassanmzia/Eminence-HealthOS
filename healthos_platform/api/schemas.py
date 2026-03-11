"""
Eminence HealthOS — API Request/Response Schemas
Pydantic models for API serialization.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "clinician"
    org_slug: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    org_id: uuid.UUID
    is_active: bool

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# ORGANIZATION
# ═══════════════════════════════════════════════════════════════════════════════


class OrgCreateRequest(BaseModel):
    name: str
    slug: str
    tier: str = "starter"


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    tier: str
    hipaa_baa_signed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT
# ═══════════════════════════════════════════════════════════════════════════════


class PatientCreateRequest(BaseModel):
    mrn: str | None = None
    demographics: dict[str, Any]  # name, dob, gender, contact
    conditions: list[dict[str, Any]] = []
    medications: list[dict[str, Any]] = []


class PatientResponse(BaseModel):
    id: uuid.UUID
    mrn: str | None
    demographics: dict[str, Any]
    conditions: list
    medications: list
    risk_level: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int
    page: int
    page_size: int


# ═══════════════════════════════════════════════════════════════════════════════
# VITALS
# ═══════════════════════════════════════════════════════════════════════════════


class VitalCreateRequest(BaseModel):
    patient_id: uuid.UUID
    device_id: str | None = None
    vital_type: str
    value: dict[str, Any]
    unit: str
    recorded_at: datetime
    source: str = "wearable"


class VitalResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    vital_type: str
    value: dict[str, Any]
    unit: str
    recorded_at: datetime
    source: str | None
    quality_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VitalBatchRequest(BaseModel):
    """Batch upload of vitals from a device."""
    vitals: list[VitalCreateRequest]


# ═══════════════════════════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════════════════════════


class AlertResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    alert_type: str
    priority: str
    status: str
    message: str | None
    created_at: datetime
    acknowledged_at: datetime | None

    model_config = {"from_attributes": True}


class AlertAcknowledgeRequest(BaseModel):
    notes: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# AGENTS
# ═══════════════════════════════════════════════════════════════════════════════


class AgentInfoResponse(BaseModel):
    name: str
    tier: str
    version: str
    description: str
    requires_hitl: bool


class AgentTriggerRequest(BaseModel):
    event_type: str
    patient_id: uuid.UUID
    payload: dict[str, Any] = {}


class PipelineResultResponse(BaseModel):
    trace_id: uuid.UUID
    trigger_event: str
    executed_agents: list[str]
    requires_hitl: bool
    hitl_reason: str | None
    anomalies_detected: int
    alerts_generated: int


# ═══════════════════════════════════════════════════════════════════════════════
# COMMON
# ═══════════════════════════════════════════════════════════════════════════════


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: dict[str, str] = {}


class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = None
