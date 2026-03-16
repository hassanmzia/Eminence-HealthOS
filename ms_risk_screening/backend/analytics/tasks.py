"""Async analytics tasks."""
from celery import shared_task
from .services import compute_workflow_metrics, subgroup_analysis


@shared_task(queue='analytics')
def generate_compliance_report(run_id):
    """Generate a full compliance report for a workflow run."""
    from governance.models import ComplianceReport
    
    metrics = compute_workflow_metrics(run_id)
    fairness_sex = subgroup_analysis(run_id, 'sex')
    fairness_age = subgroup_analysis(run_id, 'age_band')
    fairness_dx = subgroup_analysis(run_id, 'lookalike_dx')
    
    report = ComplianceReport.objects.create(
        report_type='FULL',
        workflow_run_id=run_id,
        data={
            'metrics': metrics,
            'fairness': {
                'by_sex': fairness_sex,
                'by_age_band': fairness_age,
                'by_diagnosis': fairness_dx,
            }
        },
        summary=f"Precision: {metrics.get('precision', 'N/A')}, Recall: {metrics.get('recall', 'N/A')}, Flagged: {metrics.get('flagged_count', 0)}"
    )
    return str(report.id)
