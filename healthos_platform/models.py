"""
Eminence HealthOS — SQLAlchemy ORM Models
Complete schema for multi-tenant healthcare platform.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthos_platform.database import Base


# ═══════════════════════════════════════════════════════════════════════════════
# CORE PLATFORM
# ═══════════════════════════════════════════════════════════════════════════════


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="starter")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    hipaa_baa_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list[User]] = relationship(back_populates="organization")
    patients: Mapped[list[Patient]] = relationship(back_populates="organization", foreign_keys="Patient.org_id")
    hospitals: Mapped[list[Hospital]] = relationship(foreign_keys="Hospital.org_id")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("uq_users_org_email", "org_id", "email", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(50))
    profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255))
    mfa_backup_codes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Security fields (imported from InhealthUSA)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    account_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_password_change: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verification_token: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[str | None] = mapped_column(String(50))
    external_id: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="users")
    provider_profile: Mapped[ProviderProfile | None] = relationship(back_populates="user", uselist=False)
    nurse_profile: Mapped[NurseProfile | None] = relationship(back_populates="user", uselist=False)
    office_admin_profile: Mapped[OfficeAdminProfile | None] = relationship(back_populates="user", uselist=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT DATA
# ═══════════════════════════════════════════════════════════════════════════════


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        Index("idx_patients_org", "org_id"),
        Index("idx_patients_risk", "org_id", "risk_level"),
        Index("idx_patients_mrn", "org_id", "mrn", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hospitals.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    primary_provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    fhir_id: Mapped[str | None] = mapped_column(String(100))
    mrn: Mapped[str | None] = mapped_column(String(100))
    demographics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    conditions: Mapped[list] = mapped_column(JSONB, default=list)
    medications: Mapped[list] = mapped_column(JSONB, default=list)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    care_team: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="patients")
    hospital: Mapped[Hospital | None] = relationship(foreign_keys=[hospital_id])
    department: Mapped[Department | None] = relationship(foreign_keys=[department_id])
    primary_provider: Mapped[User | None] = relationship(foreign_keys=[primary_provider_id])
    vitals: Mapped[list[Vital]] = relationship(back_populates="patient")
    anomalies: Mapped[list[Anomaly]] = relationship(back_populates="patient")
    alerts: Mapped[list[Alert]] = relationship(back_populates="patient")
    risk_scores: Mapped[list[RiskScore]] = relationship(back_populates="patient")
    encounters: Mapped[list[Encounter]] = relationship(back_populates="patient")


# ═══════════════════════════════════════════════════════════════════════════════
# RPM VITALS
# ═══════════════════════════════════════════════════════════════════════════════


class Vital(Base):
    __tablename__ = "vitals"
    __table_args__ = (
        Index("idx_vitals_patient_time", "patient_id", "recorded_at"),
        Index("idx_vitals_type", "org_id", "vital_type", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(100))
    vital_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str | None] = mapped_column(String(50))
    quality_score: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped[Patient] = relationship(back_populates="vitals")


# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALIES & ALERTS
# ═══════════════════════════════════════════════════════════════════════════════


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    vital_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    agent_id: Mapped[str | None] = mapped_column(String(100))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    vital_ids: Mapped[list | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped[Patient] = relationship(back_populates="anomalies")
    alerts: Mapped[list[Alert]] = relationship(back_populates="anomaly")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    anomaly_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("anomalies.id"))
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    escalation_path: Mapped[list] = mapped_column(JSONB, default=list)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped[Patient] = relationship(back_populates="alerts")
    anomaly: Mapped[Anomaly | None] = relationship(back_populates="alerts")


# ═══════════════════════════════════════════════════════════════════════════════
# RISK SCORES
# ═══════════════════════════════════════════════════════════════════════════════


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    score_type: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    factors: Mapped[list] = mapped_column(JSONB, default=list)
    model_version: Mapped[str | None] = mapped_column(String(50))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped[Patient] = relationship(back_populates="risk_scores")


# ═══════════════════════════════════════════════════════════════════════════════
# ENCOUNTERS & CARE PLANS
# ═══════════════════════════════════════════════════════════════════════════════


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    encounter_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    pre_visit_summary: Mapped[dict | None] = mapped_column(JSONB)
    clinical_notes: Mapped[str | None] = mapped_column(Text)
    follow_up_plan: Mapped[dict | None] = mapped_column(JSONB)
    billing_codes: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped[Patient] = relationship(back_populates="encounters")
    department: Mapped[Department | None] = relationship(foreign_keys=[department_id])
    care_plans: Mapped[list[CarePlan]] = relationship(back_populates="encounter")


class CarePlan(Base):
    __tablename__ = "care_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    goals: Mapped[list] = mapped_column(JSONB, default=list)
    interventions: Mapped[list] = mapped_column(JSONB, default=list)
    monitoring_cadence: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    encounter: Mapped[Encounter | None] = relationship(back_populates="care_plans")


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW / OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"))
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_agent: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════════
# PRIOR AUTHORIZATION
# ═══════════════════════════════════════════════════════════════════════════════


class PriorAuthorization(Base):
    __tablename__ = "prior_authorizations"
    __table_args__ = (
        Index("idx_prior_auth_patient", "patient_id", "created_at"),
        Index("idx_prior_auth_status", "org_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    auth_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    payer: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, submitted, approved, denied, appealed
    cpt_codes: Mapped[list] = mapped_column(JSONB, default=list)
    diagnosis_codes: Mapped[list] = mapped_column(JSONB, default=list)
    clinical_summary: Mapped[str | None] = mapped_column(Text)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    payer_response: Mapped[dict | None] = mapped_column(JSONB)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_agent: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INSURANCE VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════


class InsuranceVerification(Base):
    __tablename__ = "insurance_verifications"
    __table_args__ = (
        Index("idx_ins_verif_patient", "patient_id", "verified_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    payer: Mapped[str] = mapped_column(String(100), nullable=False)
    member_id: Mapped[str] = mapped_column(String(100), nullable=False)
    group_number: Mapped[str | None] = mapped_column(String(100))
    plan_name: Mapped[str | None] = mapped_column(String(255))
    plan_type: Mapped[str | None] = mapped_column(String(50))
    eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    coverage_status: Mapped[str] = mapped_column(String(30), default="unknown")
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    termination_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    benefits: Mapped[dict] = mapped_column(JSONB, default=dict)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_agent: Mapped[str | None] = mapped_column(String(100))


# ═══════════════════════════════════════════════════════════════════════════════
# REFERRALS
# ═══════════════════════════════════════════════════════════════════════════════


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        Index("idx_referral_patient", "patient_id", "created_at"),
        Index("idx_referral_status", "org_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    referral_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    urgency: Mapped[str] = mapped_column(String(30), default="routine")
    reason: Mapped[str | None] = mapped_column(Text)
    diagnosis_codes: Mapped[list] = mapped_column(JSONB, default=list)
    referring_provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    specialist_provider_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="created")  # created, sent, scheduled, completed, closed
    clinical_notes: Mapped[str | None] = mapped_column(Text)
    specialist_notes: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(50))
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_agent: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING / CLAIMS
# ═══════════════════════════════════════════════════════════════════════════════


class BillingClaim(Base):
    __tablename__ = "billing_claims"
    __table_args__ = (
        Index("idx_claim_patient", "patient_id", "created_at"),
        Index("idx_claim_status", "org_id", "status"),
        Index("idx_claim_payer", "org_id", "payer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))
    claim_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(20), default="837P")
    payer: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="prepared")  # prepared, submitted, accepted, rejected, paid, denied
    cpt_codes: Mapped[list] = mapped_column(JSONB, default=list)
    diagnosis_codes: Mapped[list] = mapped_column(JSONB, default=list)
    service_lines: Mapped[list] = mapped_column(JSONB, default=list)
    total_charges: Mapped[float] = mapped_column(Float, default=0)
    allowed_amount: Mapped[float | None] = mapped_column(Float)
    paid_amount: Mapped[float | None] = mapped_column(Float)
    patient_responsibility: Mapped[float | None] = mapped_column(Float)
    provider_npi: Mapped[str | None] = mapped_column(String(20))
    date_of_service: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prior_auth_reference: Mapped[str | None] = mapped_column(String(100))
    payer_response: Mapped[dict | None] = mapped_column(JSONB)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adjudicated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_agent: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OperationalWorkflow(Base):
    __tablename__ = "operational_workflows"
    __table_args__ = (
        Index("idx_workflow_org_status", "org_id", "status"),
        Index("idx_workflow_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"))
    workflow_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active")  # created, active, paused, completed, failed, cancelled
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    steps: Mapped[list] = mapped_column(JSONB, default=list)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    created_by_agent: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT AUDIT
# ═══════════════════════════════════════════════════════════════════════════════


class AgentAuditLog(Base):
    __tablename__ = "agent_audit_log"
    __table_args__ = (
        Index("idx_audit_trace", "trace_id"),
        Index("idx_audit_patient", "patient_id", "created_at"),
        Index("idx_audit_agent", "agent_name", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[dict | None] = mapped_column(JSONB)
    output_summary: Mapped[dict | None] = mapped_column(JSONB)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    decision_rationale: Mapped[str | None] = mapped_column(Text)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    policy_checks: Mapped[list] = mapped_column(JSONB, default=list)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════════
# POPULATION ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    patient_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_distribution: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by_agent: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PopulationMetric(Base):
    __tablename__ = "population_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cohorts.id"))
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: RBAC — ROLE-SPECIFIC PROFILES
# (Imported from InhealthUSA Provider/Nurse/OfficeAdministrator models)
# ═══════════════════════════════════════════════════════════════════════════════


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(50))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    departments: Mapped[list[Department]] = relationship(back_populates="hospital")
    providers: Mapped[list[ProviderProfile]] = relationship(back_populates="hospital", foreign_keys="ProviderProfile.hospital_id")
    nurses: Mapped[list[NurseProfile]] = relationship(back_populates="hospital", foreign_keys="NurseProfile.hospital_id")
    office_admins: Mapped[list[OfficeAdminProfile]] = relationship(back_populates="hospital", foreign_keys="OfficeAdminProfile.hospital_id")
    patients: Mapped[list[Patient]] = relationship(back_populates="hospital", foreign_keys="Patient.hospital_id")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    head_of_department: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    hospital: Mapped[Hospital] = relationship(back_populates="departments")
    providers: Mapped[list[ProviderProfile]] = relationship(back_populates="department", foreign_keys="ProviderProfile.department_id")
    nurses: Mapped[list[NurseProfile]] = relationship(back_populates="department", foreign_keys="NurseProfile.department_id")
    office_admins: Mapped[list[OfficeAdminProfile]] = relationship(back_populates="department", foreign_keys="OfficeAdminProfile.department_id")
    patients: Mapped[list[Patient]] = relationship(back_populates="department", foreign_keys="Patient.department_id")
    encounters: Mapped[list[Encounter]] = relationship(back_populates="department", foreign_keys="Encounter.department_id")


class ProviderProfile(Base):
    __tablename__ = "provider_profiles"
    __table_args__ = (
        Index("idx_provider_npi", "npi", unique=True),
        Index("idx_provider_org", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    npi: Mapped[str] = mapped_column(String(20), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(100))
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hospitals.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="provider_profile")
    hospital: Mapped[Hospital | None] = relationship(back_populates="providers", foreign_keys=[hospital_id])
    department: Mapped[Department | None] = relationship(back_populates="providers", foreign_keys=[department_id])


class NurseProfile(Base):
    __tablename__ = "nurse_profiles"
    __table_args__ = (
        Index("idx_nurse_license", "license_number", unique=True),
        Index("idx_nurse_org", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), default="General")
    license_number: Mapped[str] = mapped_column(String(100), nullable=False)
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hospitals.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="nurse_profile")
    hospital: Mapped[Hospital | None] = relationship(back_populates="nurses", foreign_keys=[hospital_id])
    department: Mapped[Department | None] = relationship(back_populates="nurses", foreign_keys=[department_id])


class OfficeAdminProfile(Base):
    __tablename__ = "office_admin_profiles"
    __table_args__ = (
        Index("idx_officeadmin_employee", "employee_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    position: Mapped[str] = mapped_column(String(100), default="Office Administrator")
    employee_id: Mapped[str] = mapped_column(String(50), nullable=False)
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hospitals.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="office_admin_profile")
    hospital: Mapped[Hospital | None] = relationship(back_populates="office_admins", foreign_keys=[hospital_id])
    department: Mapped[Department | None] = relationship(back_populates="office_admins", foreign_keys=[department_id])


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: EHR CLINICAL MODELS
# (Imported from InhealthUSA — replaces JSONB blobs with normalized schema)
# ═══════════════════════════════════════════════════════════════════════════════


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        Index("idx_diagnosis_patient", "patient_id", "diagnosed_at"),
        Index("idx_diagnosis_icd10", "icd10_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))
    diagnosis_description: Mapped[str] = mapped_column(Text, nullable=False)
    icd10_code: Mapped[str | None] = mapped_column(String(20))
    icd11_code: Mapped[str | None] = mapped_column(String(20))
    diagnosis_type: Mapped[str] = mapped_column(String(20), nullable=False)  # Primary, Secondary, Admitting, Discharge
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # Active, Resolved, Chronic
    diagnosed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    diagnosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = (
        Index("idx_prescription_patient", "patient_id", "start_date"),
        Index("idx_prescription_status", "org_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str | None] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    refills: Mapped[int] = mapped_column(Integer, default=0)
    quantity: Mapped[int | None] = mapped_column(Integer)
    instructions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active, Discontinued, Completed
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Allergy(Base):
    __tablename__ = "allergies"
    __table_args__ = (
        Index("idx_allergy_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    allergen: Mapped[str] = mapped_column(String(255), nullable=False)
    allergy_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Medication, Food, Environmental, Other
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # Mild, Moderate, Severe, Life-threatening
    reaction: Mapped[str | None] = mapped_column(Text)
    onset_date: Mapped[datetime | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MedicalHistory(Base):
    __tablename__ = "medical_histories"
    __table_args__ = (
        Index("idx_medhist_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    diagnosis_date: Mapped[datetime | None] = mapped_column(Date)
    resolution_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # Active, Resolved, Chronic
    treatment_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SocialHistory(Base):
    __tablename__ = "social_histories"
    __table_args__ = (
        Index("idx_socialhist_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    smoking_status: Mapped[str] = mapped_column(String(20), default="Never")  # Never, Former, Current
    alcohol_use: Mapped[str] = mapped_column(String(20), default="Never")  # Never, Occasional, Regular, Heavy
    drug_use: Mapped[str | None] = mapped_column(Text)
    occupation: Mapped[str | None] = mapped_column(String(255))
    marital_status: Mapped[str | None] = mapped_column(String(20))  # Single, Married, Divorced, Widowed, Separated
    living_situation: Mapped[str | None] = mapped_column(Text)
    exercise: Mapped[str | None] = mapped_column(Text)
    diet: Mapped[str | None] = mapped_column(Text)
    recorded_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FamilyHistory(Base):
    __tablename__ = "family_histories"
    __table_args__ = (
        Index("idx_familyhist_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)  # Father, Mother, Brother, etc.
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    age_at_diagnosis: Mapped[int | None] = mapped_column(Integer)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    age_at_death: Mapped[int | None] = mapped_column(Integer)
    cause_of_death: Mapped[str | None] = mapped_column(String(255))
    recorded_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LabTest(Base):
    __tablename__ = "lab_tests"
    __table_args__ = (
        Index("idx_labtest_patient", "patient_id", "ordered_date"),
        Index("idx_labtest_status", "org_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_code: Mapped[str | None] = mapped_column(String(50))
    ordered_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sample_collected_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="Ordered")  # Ordered, In Progress, Completed, Cancelled
    result_value: Mapped[str | None] = mapped_column(Text)
    result_unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))
    abnormal_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    interpretation: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: IOT DEVICE API & DATA INGESTION
# (Imported from InhealthUSA Device/DeviceAPIKey/DeviceDataReading models)
# ═══════════════════════════════════════════════════════════════════════════════


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("idx_device_unique_id", "device_unique_id", unique=True),
        Index("idx_device_patient", "patient_id"),
        Index("idx_device_org", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    device_unique_id: Mapped[str] = mapped_column(String(255), nullable=False)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Watch, Ring, EarClip, Adapter, PulseGlucometer
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(100))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    firmware_version: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active, Inactive, Maintenance, Retired
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    battery_level: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DeviceAPIKey(Base):
    __tablename__ = "device_api_keys"
    __table_args__ = (
        Index("idx_apikey_prefix", "key_prefix", unique=True),
        Index("idx_apikey_device_active", "device_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"), nullable=False)
    key_name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    can_write_vitals: Mapped[bool] = mapped_column(Boolean, default=True)
    can_read_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    request_count_today: Mapped[int] = mapped_column(Integer, default=0)
    last_reset_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeviceDataReading(Base):
    __tablename__ = "device_data_readings"
    __table_args__ = (
        Index("idx_reading_device_time", "device_id", "timestamp"),
        Index("idx_reading_patient_time", "patient_id", "timestamp"),
        Index("idx_reading_type_processed", "reading_type", "processed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    reading_type: Mapped[str] = mapped_column(String(20), nullable=False)  # vital_signs, glucose, ecg, activity, sleep
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signal_quality: Mapped[int | None] = mapped_column(Integer)
    battery_level: Mapped[int | None] = mapped_column(Integer)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vital_sign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    device_firmware: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)


class DeviceActivityLog(Base):
    __tablename__ = "device_activity_logs"
    __table_args__ = (
        Index("idx_devlog_device_time", "device_id", "timestamp"),
        Index("idx_devlog_action_time", "action_type", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id"))
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("device_api_keys.id"))
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)  # auth, data_post, data_get, registration, error
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    endpoint: Mapped[str | None] = mapped_column(String(255))
    http_method: Mapped[str | None] = mapped_column(String(10))
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)


class DeviceAlertRule(Base):
    __tablename__ = "device_alert_rules"
    __table_args__ = (
        Index("idx_alertrule_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id"))
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"))
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., heart_rate, blood_pressure_systolic
    condition: Mapped[str] = mapped_column(String(10), nullable=False)  # gt, lt, eq, gte, lte
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    alert_level: Mapped[str] = mapped_column(String(10), nullable=False)  # info, warning, critical
    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    notify_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_provider: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_email: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: MESSAGING & NOTIFICATIONS
# (Imported from InhealthUSA Message/Notification/NotificationPreferences)
# ═══════════════════════════════════════════════════════════════════════════════


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_message_sender", "sender_id", "created_at"),
        Index("idx_message_recipient", "recipient_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notification_user", "user_id", "created_at"),
        Index("idx_notification_type", "notification_type", "is_read"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(20), nullable=False)  # appointment, lab_result, prescription, message, alert, system
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    link: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    # Email
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_emergency: Mapped[bool] = mapped_column(Boolean, default=True)
    email_critical: Mapped[bool] = mapped_column(Boolean, default=True)
    email_warning: Mapped[bool] = mapped_column(Boolean, default=True)
    # SMS
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sms_emergency: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_critical: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    # WhatsApp
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    whatsapp_emergency: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_critical: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    # Quiet hours
    enable_quiet_hours: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_start_time: Mapped[datetime | None] = mapped_column(Time)
    quiet_end_time: Mapped[datetime | None] = mapped_column(Time)
    # Digest
    digest_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_frequency_hours: Mapped[int] = mapped_column(Integer, default=24)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VitalSignAlertResponse(Base):
    __tablename__ = "vital_sign_alert_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vital_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vitals.id"))
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)  # emergency, critical, warning
    patient_response_status: Mapped[str] = mapped_column(String(20), default="none")  # none, ok, help_needed
    patient_wants_doctor: Mapped[bool] = mapped_column(Boolean, default=False)
    patient_wants_nurse: Mapped[bool] = mapped_column(Boolean, default=False)
    patient_wants_ems: Mapped[bool] = mapped_column(Boolean, default=False)
    patient_response_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_response_method: Mapped[str | None] = mapped_column(String(20))  # email, sms, whatsapp
    timeout_minutes: Mapped[int] = mapped_column(Integer, default=15)
    auto_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_escalation_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    doctor_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    nurse_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    ems_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_token: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: BILLING & INSURANCE ENHANCEMENT
# (Imported from InhealthUSA Billing/BillingItem/Payment/InsuranceInformation)
# ═══════════════════════════════════════════════════════════════════════════════


class Billing(Base):
    __tablename__ = "billings"
    __table_args__ = (
        Index("idx_billing_patient", "patient_id", "billing_date"),
        Index("idx_billing_status", "org_id", "status"),
        Index("idx_billing_invoice", "invoice_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    amount_due: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Paid, Partially Paid, Overdue, Cancelled
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list[BillingItem]] = relationship(back_populates="billing")
    payments: Mapped[list[Payment]] = relationship(back_populates="billing")


class BillingItem(Base):
    __tablename__ = "billing_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    billing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billings.id"), nullable=False)
    service_code: Mapped[str] = mapped_column(String(50), nullable=False)
    service_description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    billing: Mapped[Billing] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("idx_payment_patient", "patient_id", "payment_date"),
        Index("idx_payment_billing", "billing_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    billing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billings.id"), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)  # Cash, Credit Card, Debit Card, Check, Insurance, Other
    transaction_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="Completed")  # Completed, Pending, Failed, Refunded
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    billing: Mapped[Billing] = relationship(back_populates="payments")


class InsuranceInformation(Base):
    __tablename__ = "insurance_information"
    __table_args__ = (
        Index("idx_insurance_patient", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_number: Mapped[str] = mapped_column(String(100), nullable=False)
    group_number: Mapped[str | None] = mapped_column(String(100))
    policyholder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policyholder_relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    copay_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    deductible_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: ENTERPRISE AUTH CONFIGURATION
# (Imported from InhealthUSA AuthenticationConfig)
# ═══════════════════════════════════════════════════════════════════════════════


class AuthenticationConfig(Base):
    __tablename__ = "authentication_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    auth_method: Mapped[str] = mapped_column(String(50), nullable=False)  # local, ldap, oauth2, openid, azure_ad, cac, saml, sso
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)  # provider-specific config (URLs, client IDs, etc.)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PasswordHistory(Base):
    __tablename__ = "password_histories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("idx_session_user", "user_id"),
        Index("idx_session_token", "session_token", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Treatment Plans (imported from InhealthUSA) ─────────────────────────────


class AIProposedTreatmentPlan(Base):
    """AI-generated treatment proposals requiring doctor review."""

    __tablename__ = "ai_proposed_treatment_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    # AI-generated content
    proposed_treatment: Mapped[str] = mapped_column(Text, nullable=False)
    medications_suggested: Mapped[str | None] = mapped_column(Text)
    lifestyle_recommendations: Mapped[str | None] = mapped_column(Text)
    follow_up_recommendations: Mapped[str | None] = mapped_column(Text)
    warnings_and_precautions: Mapped[str | None] = mapped_column(Text)

    # Source data snapshots
    vital_signs_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    diagnosis_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    lab_test_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    medical_history_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # AI model metadata
    ai_model_name: Mapped[str | None] = mapped_column(String(100))
    ai_model_version: Mapped[str | None] = mapped_column(String(50))
    generation_time_seconds: Mapped[float | None] = mapped_column(Numeric(8, 3))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)

    # Doctor review
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, reviewed, approved, rejected, implemented
    doctor_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_ai_plan_patient_status", "patient_id", "status"),
        Index("ix_ai_plan_provider_status", "provider_id", "status"),
    )


class DoctorTreatmentPlan(Base):
    """Doctor-created treatment plans with optional AI proposal linkage."""

    __tablename__ = "doctor_treatment_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    plan_title: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))
    ai_proposal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_proposed_treatment_plans.id"))

    # Treatment plan details
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    assessment: Mapped[str | None] = mapped_column(Text)
    treatment_goals: Mapped[str] = mapped_column(Text, nullable=False)

    # Treatment components
    medications: Mapped[str | None] = mapped_column(Text)
    procedures: Mapped[str | None] = mapped_column(Text)
    lifestyle_modifications: Mapped[str | None] = mapped_column(Text)
    dietary_recommendations: Mapped[str | None] = mapped_column(Text)
    exercise_recommendations: Mapped[str | None] = mapped_column(Text)

    # Follow-up
    follow_up_instructions: Mapped[str | None] = mapped_column(Text)
    warning_signs: Mapped[str | None] = mapped_column(Text)
    emergency_instructions: Mapped[str | None] = mapped_column(Text)

    # Status & timeline
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, active, completed, cancelled
    plan_start_date: Mapped[date | None] = mapped_column(Date)
    plan_end_date: Mapped[date | None] = mapped_column(Date)
    next_review_date: Mapped[date | None] = mapped_column(Date)

    # Patient visibility
    is_visible_to_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    patient_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_feedback: Mapped[str | None] = mapped_column(Text)

    additional_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_doctor_plan_patient_status", "patient_id", "status"),
        Index("ix_doctor_plan_provider", "provider_id", "status"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT QUESTIONNAIRES (imported from InhealthUSA clinical documentation)
# ═══════════════════════════════════════════════════════════════════════════════


class PatientQuestionnaire(Base):
    """
    Patient-submitted pre-visit questionnaires.
    Mirrors InhealthUSA clinical documentation tables:
    - Review of Systems (ROS)
    - History of Presenting Illness (HPI)
    - Nursing intake evaluation
    """
    __tablename__ = "patient_questionnaires"
    __table_args__ = (
        Index("idx_questionnaire_patient", "patient_id"),
        Index("idx_questionnaire_type", "org_id", "questionnaire_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encounters.id"))

    questionnaire_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # review_of_systems, history_presenting_illness, nursing_intake, pre_visit

    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, submitted, reviewed
    responses: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
