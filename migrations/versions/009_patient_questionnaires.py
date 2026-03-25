"""Add patient_questionnaires table for pre-visit intake forms.
Imports questionnaire structures from InhealthUSA clinical documentation
(review_of_systems, history_presenting_illness, nursing_evaluations).

Revision ID: 009_questionnaires
Revises: 008_inhealth_usa
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "009_questionnaires"
down_revision = "008_inhealth_usa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_questionnaires",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=True),
        sa.Column("questionnaire_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("responses", JSONB, nullable=False, server_default="{}"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_questionnaire_patient", "patient_questionnaires", ["patient_id"])
    op.create_index("idx_questionnaire_type", "patient_questionnaires", ["org_id", "questionnaire_type", "status"])


def downgrade() -> None:
    op.drop_index("idx_questionnaire_type", "patient_questionnaires")
    op.drop_index("idx_questionnaire_patient", "patient_questionnaires")
    op.drop_table("patient_questionnaires")
