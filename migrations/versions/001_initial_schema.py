"""Initial schema — all HealthOS platform tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Organizations ─────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("tier", sa.String(50), server_default="starter"),
        sa.Column("settings", JSONB, server_default="{}"),
        sa.Column("hipaa_baa_signed", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("full_name", sa.String(255), server_default=""),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("phone", sa.String(50)),
        sa.Column("profile", JSONB, server_default="{}"),
        sa.Column("mfa_enabled", sa.Boolean, server_default="false"),
        sa.Column("mfa_secret", sa.String(255)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("uq_users_org_email", "users", ["org_id", "email"], unique=True)

    # ── Patients ──────────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("fhir_id", sa.String(100)),
        sa.Column("mrn", sa.String(100)),
        sa.Column("demographics", JSONB, nullable=False),
        sa.Column("conditions", JSONB, server_default="[]"),
        sa.Column("medications", JSONB, server_default="[]"),
        sa.Column("risk_level", sa.String(20), server_default="low"),
        sa.Column("care_team", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_patients_org", "patients", ["org_id"])
    op.create_index("idx_patients_risk", "patients", ["org_id", "risk_level"])
    op.create_index("idx_patients_mrn", "patients", ["org_id", "mrn"], unique=True)

    # ── Vitals ────────────────────────────────────────────────────────────
    op.create_table(
        "vitals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("device_id", sa.String(100)),
        sa.Column("vital_type", sa.String(50), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("unit", sa.String(20)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(50)),
        sa.Column("quality_score", sa.Float),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_vitals_patient_time", "vitals", ["patient_id", "recorded_at"])
    op.create_index("idx_vitals_type", "vitals", ["org_id", "vital_type", "recorded_at"])

    # ── Anomalies ─────────────────────────────────────────────────────────
    op.create_table(
        "anomalies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("anomaly_type", sa.String(50), nullable=False),
        sa.Column("vital_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("agent_id", sa.String(100)),
        sa.Column("confidence_score", sa.Float),
        sa.Column("vital_ids", ARRAY(UUID(as_uuid=True))),
        sa.Column("resolved", sa.Boolean, server_default="false"),
        sa.Column("resolved_by", UUID(as_uuid=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Alerts ────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("anomaly_id", UUID(as_uuid=True), sa.ForeignKey("anomalies.id")),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("escalation_path", JSONB, server_default="[]"),
        sa.Column("message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    # ── Risk Scores ───────────────────────────────────────────────────────
    op.create_table(
        "risk_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("score_type", sa.String(50), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("factors", JSONB, server_default="[]"),
        sa.Column("model_version", sa.String(50)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Encounters ────────────────────────────────────────────────────────
    op.create_table(
        "encounters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("encounter_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.Text),
        sa.Column("triggered_by", UUID(as_uuid=True)),
        sa.Column("pre_visit_summary", JSONB),
        sa.Column("clinical_notes", sa.Text),
        sa.Column("follow_up_plan", JSONB),
        sa.Column("billing_codes", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Care Plans ────────────────────────────────────────────────────────
    op.create_table(
        "care_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id")),
        sa.Column("plan_type", sa.String(50), nullable=False),
        sa.Column("goals", JSONB, server_default="[]"),
        sa.Column("interventions", JSONB, server_default="[]"),
        sa.Column("monitoring_cadence", JSONB),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Workflow Tasks ────────────────────────────────────────────────────
    op.create_table(
        "workflow_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id")),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("priority", sa.String(20), server_default="normal"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("payload", JSONB, server_default="{}"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_agent", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Agent Audit Log ───────────────────────────────────────────────────
    op.create_table(
        "agent_audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("trace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("input_summary", JSONB),
        sa.Column("output_summary", JSONB),
        sa.Column("confidence_score", sa.Float),
        sa.Column("decision_rationale", sa.Text),
        sa.Column("patient_id", UUID(as_uuid=True)),
        sa.Column("policy_checks", JSONB, server_default="[]"),
        sa.Column("human_review_required", sa.Boolean, server_default="false"),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_trace", "agent_audit_log", ["trace_id"])
    op.create_index("idx_audit_patient", "agent_audit_log", ["patient_id", "created_at"])
    op.create_index("idx_audit_agent", "agent_audit_log", ["agent_name", "created_at"])

    # ── Cohorts ───────────────────────────────────────────────────────────
    op.create_table(
        "cohorts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("criteria", JSONB, nullable=False),
        sa.Column("patient_count", sa.Integer, server_default="0"),
        sa.Column("risk_distribution", JSONB, server_default="{}"),
        sa.Column("created_by_agent", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Population Metrics ────────────────────────────────────────────────
    op.create_table(
        "population_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("cohort_id", UUID(as_uuid=True), sa.ForeignKey("cohorts.id")),
        sa.Column("metric_type", sa.String(50), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("breakdown", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("population_metrics")
    op.drop_table("cohorts")
    op.drop_table("agent_audit_log")
    op.drop_table("workflow_tasks")
    op.drop_table("care_plans")
    op.drop_table("encounters")
    op.drop_table("risk_scores")
    op.drop_table("alerts")
    op.drop_table("anomalies")
    op.drop_table("vitals")
    op.drop_table("patients")
    op.drop_table("users")
    op.drop_table("organizations")
