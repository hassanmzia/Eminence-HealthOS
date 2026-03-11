"""Patient request/response schemas."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from services.api.schemas.common import HealthOSBase


class PatientCreate(BaseModel):
    mrn: str = Field(..., max_length=50)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    date_of_birth: date
    sex: str = Field(..., max_length=20)
    gender_identity: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    preferred_language: str = "en"
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    insurance_group_number: Optional[str] = None
    primary_provider_id: Optional[UUID] = None
    blood_type: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sex: Optional[str] = None
    gender_identity: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    preferred_language: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    insurance_group_number: Optional[str] = None
    primary_provider_id: Optional[UUID] = None
    blood_type: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None


class PatientResponse(HealthOSBase):
    id: UUID
    tenant_id: str
    mrn: str
    fhir_id: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    gender_identity: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    preferred_language: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    primary_provider_id: Optional[UUID] = None
    blood_type: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PatientSummary(HealthOSBase):
    id: UUID
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    risk_level: Optional[str] = None
