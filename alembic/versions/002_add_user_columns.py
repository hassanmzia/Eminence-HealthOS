"""Add missing columns to users table.

Revision ID: 002_add_user_columns
Revises: 001_initial
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa

revision = "002_add_user_columns"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(500)))
    op.add_column("users", sa.Column("phone", sa.String(50)))
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean, server_default="false"))
    op.add_column("users", sa.Column("mfa_secret", sa.String(255)))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_column("users", "updated_at")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "phone")
    op.drop_column("users", "avatar_url")
