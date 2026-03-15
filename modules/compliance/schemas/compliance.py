"""Compliance & Governance module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class HIPAAScanRequest(BaseModel):
    scope: str = Field("full", description="full, access_controls, encryption, audit_logging")
    tenant_id: Optional[str] = None


class HIPAAScanResult(BaseModel):
    scan_id: str
    compliance_rate: float
    findings: list[dict]
    passed: int
    failed: int
    timestamp: str


class AIModelAudit(BaseModel):
    model_id: str
    model_name: str
    audit_type: str = Field("bias", description="bias, performance, drift, explainability")


class AIModelAuditResult(BaseModel):
    model_id: str
    audit_type: str
    score: float
    findings: list[dict]
    recommendation: str


class ConsentCapture(BaseModel):
    patient_id: UUID
    consent_type: str = Field(..., description="treatment, data_sharing, research, telehealth")
    granted: bool
    scope: Optional[str] = None
    expiry_days: Optional[int] = None


class ConsentStatus(BaseModel):
    patient_id: str
    consent_type: str
    granted: bool
    captured_at: str
    expires_at: Optional[str] = None


class ComplianceReport(BaseModel):
    framework: str = Field(..., description="hipaa, soc2, hitrust, gdpr")
    period: str = "quarterly"
    include_remediation: bool = True
