"""Celery tasks for asynchronous agent workflow execution."""
from celery import shared_task
from .workflow import run_screening_workflow


@shared_task(bind=True, queue='agents', max_retries=2)
def run_screening_workflow_task(self, policy_config_id=None, patient_limit=None):
    """
    Run the full MS screening workflow as an async Celery task.

    Parameters
    ----------
    policy_config_id : str or None
        UUID of a PolicyConfig to use. Falls back to system defaults.
    patient_limit : int or None
        Cap the number of patients loaded (useful for testing).
    """
    try:
        return run_screening_workflow(policy_config_id, patient_limit)
    except Exception as exc:
        self.retry(exc=exc, countdown=30)
