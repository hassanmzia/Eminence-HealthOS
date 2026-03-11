"""Observation request/response schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from services.api.schemas.common import HealthOSBase


class ObservationCreate(BaseModel):
    patient_id: UUID
    encounter_id: Optional[UUID] = None
    status: str = "final"
    category: str = Field(..., max_length=30)
    loinc_code: str = Field(..., max_length=20)
    display: str = Field(..., max_length=255)
    value_quantity: Optional[float] = None
    value_unit: Optional[str] = None
    value_string: Optional[str] = None
    value_code: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    interpretation: Optional[str] = None
    data_source: str = "manual"
    device_id: Optional[str] = None
    effective_datetime: datetime
    components: Optional[dict] = None


class ObservationResponse(HealthOSBase):
    id: UUID
    tenant_id: str
    patient_id: UUID
    encounter_id: Optional[UUID] = None
    fhir_id: Optional[str] = None
    status: str
    category: str
    loinc_code: str
    display: str
    value_quantity: Optional[float] = None
    value_unit: Optional[str] = None
    value_string: Optional[str] = None
    value_code: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    interpretation: Optional[str] = None
    data_source: str
    device_id: Optional[str] = None
    effective_datetime: datetime
    components: Optional[dict] = None
    created_at: datetime


class ObservationSummary(HealthOSBase):
    id: UUID
    patient_id: UUID
    category: str
    loinc_code: str
    display: str
    value_quantity: Optional[float] = None
    value_unit: Optional[str] = None
    interpretation: Optional[str] = None
    effective_datetime: datetime
