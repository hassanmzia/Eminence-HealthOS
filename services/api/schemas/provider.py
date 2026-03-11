"""Provider request/response schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from services.api.schemas.common import HealthOSBase


class ProviderCreate(BaseModel):
    npi: Optional[str] = Field(None, max_length=20)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    role: str = Field(..., max_length=50)
    specialty: Optional[str] = None
    department: Optional[str] = None
    keycloak_id: Optional[str] = None


class ProviderUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    specialty: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    notification_preferences: Optional[dict] = None


class ProviderResponse(HealthOSBase):
    id: UUID
    tenant_id: str
    npi: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    role: str
    specialty: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProviderSummary(HealthOSBase):
    id: UUID
    first_name: str
    last_name: str
    role: str
    specialty: Optional[str] = None
