"""Agent execution tracking models."""
import uuid
from django.db import models


class AgentExecution(models.Model):
    """Records every individual agent invocation within a workflow run."""

    AGENT_NAME_CHOICES = [
        ('retrieval', 'Retrieval'),
        ('phenotyping', 'Phenotyping'),
        ('notes_imaging', 'Notes & Imaging'),
        ('safety_governance', 'Safety & Governance'),
        ('coordinator', 'Coordinator'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        'patients.WorkflowRun',
        on_delete=models.CASCADE,
        related_name='agent_executions',
    )
    agent_name = models.CharField(max_length=50, choices=AGENT_NAME_CHOICES, db_index=True)
    patient_id_ref = models.CharField(
        max_length=20,
        blank=True,
        help_text='Patient identifier in P00000 format',
    )
    payload = models.JSONField(default=dict)
    duration_ms = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Agent Execution'
        verbose_name_plural = 'Agent Executions'

    def __str__(self):
        return f"{self.agent_name} | {self.patient_id_ref} | {self.duration_ms:.1f}ms"
