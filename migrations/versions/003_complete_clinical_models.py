"""Add all remaining clinical models — providers, observations, conditions,
medications, medication_orders, agent_decisions, agent_interactions,
clinical_alerts, audit_logs, consent_records.

Revision ID: 003_clinical_models
Revises: 002_add_user_columns
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "003_clinical_models"
down_revision = "002_add_user_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Providers ──────────────────────────────────────────────────────────
    op.create_table(
        "providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("npi", sa.String(20), nullable=True, unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("specialty", sa.String(100), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("keycloak_id", sa.String(100), nullable=True, unique=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("notification_preferences", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_providers_tenant", "providers", ["tenant_id"])
    op.create_index("idx_providers_role", "providers", ["tenant_id", "role"])

    # ── Observations (FHIR R4) ────────────────────────────────────────────
    op.create_table(
        "observations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=True),
        sa.Column("fhir_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="final"),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("loinc_code", sa.String(20), nullable=False),
        sa.Column("display", sa.String(255), nullable=False),
        sa.Column("value_quantity", sa.Float, nullable=True),
        sa.Column("value_unit", sa.String(30), nullable=True),
        sa.Column("value_string", sa.Text, nullable=True),
        sa.Column("value_code", sa.String(50), nullable=True),
        sa.Column("reference_low", sa.Float, nullable=True),
        sa.Column("reference_high", sa.Float, nullable=True),
        sa.Column("interpretation", sa.String(30), nullable=True),
        sa.Column("data_source", sa.String(50), server_default="manual"),
        sa.Column("device_id", sa.String(100), nullable=True),
        sa.Column("effective_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("components", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_observations_patient", "observations", ["patient_id"])
    op.create_index("ix_observations_patient_category", "observations", ["patient_id", "category"])
    op.create_index("ix_observations_patient_loinc", "observations", ["patient_id", "loinc_code"])
    op.create_index("ix_observations_effective", "observations", ["effective_datetime"])
    op.create_index("ix_observations_category", "observations", ["category"])

    # ── Conditions (FHIR R4) ──────────────────────────────────────────────
    op.create_table(
        "conditions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("fhir_id", sa.String(100), nullable=True),
        sa.Column("clinical_status", sa.String(20), server_default="active"),
        sa.Column("verification_status", sa.String(20), server_default="confirmed"),
        sa.Column("category", sa.String(30), server_default="encounter-diagnosis"),
        sa.Column("icd10_code", sa.String(20), nullable=False),
        sa.Column("display", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("onset_date", sa.Date, nullable=True),
        sa.Column("abatement_date", sa.Date, nullable=True),
        sa.Column("recorded_date", sa.Date, nullable=True),
        sa.Column("body_site", sa.String(100), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_conditions_patient", "conditions", ["patient_id"])
    op.create_index("idx_conditions_icd10", "conditions", ["icd10_code"])

    # ── Medications ────────────────────────────────────────────────────────
    op.create_table(
        "medications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("rxnorm_code", sa.String(20), nullable=True),
        sa.Column("ndc_code", sa.String(20), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("generic_name", sa.String(255), nullable=True),
        sa.Column("dosage", sa.String(100), nullable=True),
        sa.Column("dosage_value", sa.Float, nullable=True),
        sa.Column("dosage_unit", sa.String(20), nullable=True),
        sa.Column("frequency", sa.String(50), nullable=True),
        sa.Column("route", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("is_prn", sa.Boolean, server_default="false"),
        sa.Column("prescriber_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_medications_patient", "medications", ["patient_id"])
    op.create_index("idx_medications_status", "medications", ["patient_id", "status"])

    # ── Medication Orders ──────────────────────────────────────────────────
    op.create_table(
        "medication_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("medication_id", UUID(as_uuid=True), sa.ForeignKey("medications.id"), nullable=True),
        sa.Column("prescriber_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("order_type", sa.String(30), server_default="new"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("medication_name", sa.String(255), nullable=False),
        sa.Column("dosage", sa.String(100), nullable=True),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("quantity", sa.Integer, nullable=True),
        sa.Column("refills", sa.Integer, server_default="0"),
        sa.Column("agent_name", sa.String(100), nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("requires_hitl", sa.Boolean, server_default="true"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_med_orders_patient", "medication_orders", ["patient_id"])
    op.create_index("idx_med_orders_status", "medication_orders", ["status"])

    # ── Agent Decisions ────────────────────────────────────────────────────
    op.create_table(
        "agent_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("trace_id", sa.String(100), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("agent_tier", sa.String(30), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("decision_type", sa.String(30), server_default="recommendation"),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("rationale", sa.Text, server_default=""),
        sa.Column("confidence", sa.Float, server_default="0.0"),
        sa.Column("feature_contributions", JSONB, server_default="[]"),
        sa.Column("alternatives", JSONB, server_default="[]"),
        sa.Column("evidence_references", JSONB, server_default="[]"),
        sa.Column("requires_hitl", sa.Boolean, server_default="false"),
        sa.Column("safety_flags", JSONB, server_default="[]"),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("input_summary", JSONB, server_default="{}"),
        sa.Column("output_summary", JSONB, server_default="{}"),
        sa.Column("duration_ms", sa.Integer, server_default="0"),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer, server_default="0"),
        sa.Column("output_tokens", sa.Integer, server_default="0"),
        sa.Column("cost_usd", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_decisions_trace", "agent_decisions", ["trace_id"])
    op.create_index("ix_agent_decisions_patient", "agent_decisions", ["patient_id"])
    op.create_index("ix_agent_decisions_agent_tier", "agent_decisions", ["agent_name", "agent_tier"])

    # ── Agent Interactions ─────────────────────────────────────────────────
    op.create_table(
        "agent_interactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("trace_id", sa.String(100), nullable=False),
        sa.Column("sender_agent", sa.String(100), nullable=False),
        sa.Column("receiver_agent", sa.String(100), nullable=False),
        sa.Column("message_type", sa.String(30), nullable=False),
        sa.Column("capability", sa.String(100), nullable=True),
        sa.Column("payload", JSONB, server_default="{}"),
        sa.Column("response", JSONB, server_default="{}"),
        sa.Column("success", sa.Boolean, server_default="true"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_interactions_trace", "agent_interactions", ["trace_id"])
    op.create_index("ix_agent_interactions_sender", "agent_interactions", ["sender_agent"])

    # ── Clinical Alerts ────────────────────────────────────────────────────
    op.create_table(
        "clinical_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column("source_agent", sa.String(100), nullable=False),
        sa.Column("source_observation_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("acknowledged_by", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("escalation_level", sa.Integer, server_default="0"),
        sa.Column("notifications_sent", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_clinical_alerts_patient", "clinical_alerts", ["patient_id"])
    op.create_index("idx_clinical_alerts_severity", "clinical_alerts", ["severity"])
    op.create_index("idx_clinical_alerts_status", "clinical_alerts", ["status"])

    # ── Audit Logs (HIPAA — hash-chained) ──────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("actor_type", sa.String(30), server_default="agent"),
        sa.Column("patient_id", sa.String(100), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("action", sa.String(50), nullable=True),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("previous_hash", sa.String(64), server_default="genesis"),
        sa.Column("record_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("idx_audit_logs_actor", "audit_logs", ["actor_id"])
    op.create_index("idx_audit_logs_patient", "audit_logs", ["patient_id"])
    op.create_index("idx_audit_logs_hash", "audit_logs", ["record_hash"])

    # ── Consent Records ────────────────────────────────────────────────────
    op.create_table(
        "consent_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("scope", JSONB, server_default="{}"),
        sa.Column("data_categories", JSONB, server_default="[]"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(50), server_default="patient_portal"),
        sa.Column("verification_method", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_consent_patient", "consent_records", ["patient_id"])
    op.create_index("idx_consent_type", "consent_records", ["consent_type", "status"])


def downgrade() -> None:
    op.drop_table("consent_records")
    op.drop_table("audit_logs")
    op.drop_table("clinical_alerts")
    op.drop_table("agent_interactions")
    op.drop_table("agent_decisions")
    op.drop_table("medication_orders")
    op.drop_table("medications")
    op.drop_table("conditions")
    op.drop_table("observations")
    op.drop_table("providers")
