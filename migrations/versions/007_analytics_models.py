"""Add indexes for analytics tables (cohorts, population_metrics, risk_scores).

Revision ID: 007_analytics_models
Revises: 005_workflow_models
Create Date: 2026-03-14
"""

from alembic import op

revision = "007_analytics_models"
down_revision = "005_workflow_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Cohorts indexes ──────────────────────────────────────────────────
    op.create_index("ix_cohorts_org_name", "cohorts", ["org_id", "name"])

    # ── Population Metrics indexes ───────────────────────────────────────
    op.create_index(
        "ix_pop_metrics_cohort_type", "population_metrics", ["cohort_id", "metric_type"]
    )
    op.create_index(
        "ix_pop_metrics_period", "population_metrics", ["period_start", "period_end"]
    )

    # ── Risk Scores indexes ──────────────────────────────────────────────
    op.create_index(
        "ix_risk_scores_patient_type", "risk_scores", ["patient_id", "score_type"]
    )
    op.create_index("ix_risk_scores_risk_level", "risk_scores", ["risk_level"])


def downgrade() -> None:
    op.drop_index("ix_risk_scores_risk_level", table_name="risk_scores")
    op.drop_index("ix_risk_scores_patient_type", table_name="risk_scores")
    op.drop_index("ix_pop_metrics_period", table_name="population_metrics")
    op.drop_index("ix_pop_metrics_cohort_type", table_name="population_metrics")
    op.drop_index("ix_cohorts_org_name", table_name="cohorts")
