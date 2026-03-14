"""
Eminence HealthOS — SQLAlchemy ORM Models
Complete schema for multi-tenant healthcare platform.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
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
    patients: Mapped[list[Patient]] = relationship(back_populates="organization")


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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="users")


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
