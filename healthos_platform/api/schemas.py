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


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    org_id: uuid.UUID
    avatar_url: str | None = None
    phone: str | None = None
    profile: dict[str, Any] = {}
    mfa_enabled: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    profile: dict[str, Any] | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


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
    hospital_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    primary_provider_id: uuid.UUID | None = None
    demographics: dict[str, Any]  # name, dob, gender, contact
    conditions: list[dict[str, Any]] = []
    medications: list[dict[str, Any]] = []


class PatientResponse(BaseModel):
    id: uuid.UUID
    mrn: str | None
    hospital_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    primary_provider_id: uuid.UUID | None = None
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


class AgentExecutionEntry(BaseModel):
    id: str
    agent_name: str
    action: str
    status: str
    confidence_score: float | None = None
    duration_ms: int | None = None
    patient_id: str | None = None
    trace_id: str
    created_at: str | None = None


class PipelineRunEntry(BaseModel):
    trace_id: str
    agents_executed: list[str]
    total_duration_ms: int
    trigger_event: str
    started_at: str | None = None


class AgentActivityResponse(BaseModel):
    executions: list[AgentExecutionEntry]
    pipeline_runs: list[PipelineRunEntry]
    agent_statuses: dict[str, str]


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
