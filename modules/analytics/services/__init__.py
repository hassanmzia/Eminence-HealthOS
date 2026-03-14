"""Analytics service layer — cohort management, metrics, and risk scoring."""

from modules.analytics.services.cohort_service import (
    create_cohort,
    delete_cohort,
    get_cohort,
    list_cohorts,
    update_cohort_stats,
)
from modules.analytics.services.metrics_service import (
    compute_population_summary,
    get_cohort_metrics,
    get_metrics,
    record_metric,
)
from modules.analytics.services.risk_service import (
    get_high_risk_patients,
    get_patient_risk,
    get_risk_distribution,
    record_risk_score,
)

__all__ = [
    # cohort_service
    "create_cohort",
    "get_cohort",
    "list_cohorts",
    "update_cohort_stats",
    "delete_cohort",
    # metrics_service
    "record_metric",
    "get_metrics",
    "get_cohort_metrics",
    "compute_population_summary",
    # risk_service
    "record_risk_score",
    "get_patient_risk",
    "get_high_risk_patients",
    "get_risk_distribution",
]
