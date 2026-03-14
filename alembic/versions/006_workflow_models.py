"""Add workflows and workflow_steps tables.

Revision ID: 006_workflow_models
Revises: 005_operations_models
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "005_workflow_models"
down_revision = "004_telehealth_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Workflows ─────────────────────────────────────────────────────────
    op.create_table(
        "workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("workflow_id", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("workflow_type", sa.String(100), nullable=False),
        sa.Column("org_id", sa.String(100), nullable=False),
        sa.Column("patient_id", sa.String(100), nullable=True),
        sa.Column("priority", sa.String(20), server_default="normal"),
        sa.Column("status", sa.String(20), server_default="created"),
        sa.Column("context", JSONB, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_workflows_workflow_id", "workflows", ["workflow_id"], unique=True)
    op.create_index("ix_workflows_org_id", "workflows", ["org_id"])
    op.create_index("ix_workflows_workflow_type", "workflows", ["workflow_type"])
    op.create_index("ix_workflows_status", "workflows", ["status"])
    op.create_index("ix_workflows_patient_id", "workflows", ["patient_id"])
    op.create_index("ix_workflows_tenant_id", "workflows", ["tenant_id"])

    # ── Workflow Steps ────────────────────────────────────────────────────
    op.create_table(
        "workflow_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("depends_on", JSONB, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("max_retries", sa.Integer, server_default="2"),
        sa.Column("timeout_minutes", sa.Integer, server_default="60"),
        sa.Column("sla_hours", sa.Float, server_default="24.0"),
        sa.Column("output", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_steps_workflow_id", "workflow_steps", ["workflow_id"])
    op.create_index("ix_workflow_steps_step_id", "workflow_steps", ["step_id"], unique=True)
    op.create_index("ix_workflow_steps_status", "workflow_steps", ["status"])


def downgrade() -> None:
    op.drop_table("workflow_steps")
    op.drop_table("workflows")
