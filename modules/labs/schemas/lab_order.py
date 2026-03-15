"""Labs module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LabOrderCreate(BaseModel):
    patient_id: UUID
    tests: list[str]
    priority: str = Field("routine", description="routine, stat, urgent")
    ordering_provider_id: Optional[UUID] = None
    clinical_notes: Optional[str] = None


class LabOrderResponse(BaseModel):
    order_id: str
    patient_id: str
    tests: list[str]
    priority: str
    status: str
    created_at: str


class LabResultIngest(BaseModel):
    order_id: str
    results: list[dict]
    performing_lab: Optional[str] = None


class LabResultResponse(BaseModel):
    result_id: str
    order_id: str
    test_name: str
    value: str
    unit: str
    reference_range: str
    flag: Optional[str] = None


class CriticalValueAlert(BaseModel):
    result_id: str
    patient_id: str
    test_name: str
    value: str
    severity: str
    acknowledged: bool = False
