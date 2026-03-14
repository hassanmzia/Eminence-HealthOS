"""Add telehealth_sessions, clinical_notes, and follow_up_plans tables.

Revision ID: 004_telehealth_models
Revises: 003_clinical_models
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "004_telehealth_models"
down_revision = "003_clinical_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Telehealth Sessions ───────────────────────────────────────────────
    op.create_table(
        "telehealth_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=False, unique=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("visit_type", sa.String(30), server_default="on_demand"),
        sa.Column("urgency", sa.String(20), server_default="routine"),
        sa.Column("status", sa.String(20), server_default="waiting"),
        sa.Column("chief_complaint", sa.Text, nullable=True),
        sa.Column("symptoms", JSONB, nullable=True),
        sa.Column("estimated_wait_minutes", sa.Integer, nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_telehealth_sessions_session_id", "telehealth_sessions", ["session_id"], unique=True)
    op.create_index("ix_telehealth_sessions_tenant_status", "telehealth_sessions", ["tenant_id", "status"])
    op.create_index("ix_telehealth_sessions_patient", "telehealth_sessions", ["patient_id"])

    # ── Clinical Notes ────────────────────────────────────────────────────
    op.create_table(
        "clinical_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("telehealth_sessions.id"), nullable=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("note_type", sa.String(30), server_default="soap"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("subjective", sa.Text, nullable=True),
        sa.Column("objective", sa.Text, nullable=True),
        sa.Column("assessment", sa.Text, nullable=True),
        sa.Column("plan", sa.Text, nullable=True),
        sa.Column("icd10_codes", JSONB, nullable=True),
        sa.Column("cpt_codes", JSONB, nullable=True),
        sa.Column("ai_generated", sa.Boolean, server_default="false"),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("amendments", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_clinical_notes_encounter", "clinical_notes", ["encounter_id"])
    op.create_index("ix_clinical_notes_session", "clinical_notes", ["session_id"])
    op.create_index("ix_clinical_notes_status", "clinical_notes", ["status"])

    # ── Follow-Up Plans ───────────────────────────────────────────────────
    op.create_table(
        "follow_up_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("telehealth_sessions.id"), nullable=True),
        sa.Column("follow_up_days", sa.Integer, nullable=True),
        sa.Column("monitoring_plan", sa.Text, nullable=True),
        sa.Column("action_items", JSONB, nullable=True),
        sa.Column("patient_education", JSONB, nullable=True),
        sa.Column("medications", JSONB, nullable=True),
        sa.Column("referrals", JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("ai_generated", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_follow_up_plans_encounter", "follow_up_plans", ["encounter_id"])
    op.create_index("ix_follow_up_plans_session", "follow_up_plans", ["session_id"])
    op.create_index("ix_follow_up_plans_status", "follow_up_plans", ["status"])


def downgrade() -> None:
    op.drop_table("follow_up_plans")
    op.drop_table("clinical_notes")
    op.drop_table("telehealth_sessions")
