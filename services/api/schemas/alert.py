"""Clinical alert schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from services.api.schemas.common import HealthOSBase


class AlertAcknowledge(BaseModel):
    acknowledged_by: UUID


class AlertResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=1)


class AlertResponse(HealthOSBase):
    id: UUID
    tenant_id: str
    patient_id: UUID
    severity: str
    category: str
    alert_type: str
    title: str
    message: str
    details: dict
    source_agent: str
    source_observation_id: Optional[UUID] = None
    status: str
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    escalation_level: int
    notifications_sent: list
    created_at: datetime


class AlertSummary(HealthOSBase):
    id: UUID
    patient_id: UUID
    severity: str
    category: str
    title: str
    status: str
    source_agent: str
    created_at: datetime
