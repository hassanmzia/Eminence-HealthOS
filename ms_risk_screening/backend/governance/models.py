"""Governance and compliance models."""
import uuid
from django.db import models


class GovernanceRule(models.Model):
    """Configurable governance rules for the safety agent."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    rule_type = models.CharField(max_length=50, choices=[
        ('PHI_CHECK', 'PHI Detection'),
        ('EVIDENCE_CHECK', 'Evidence Quality'),
        ('DEMOGRAPHIC_CHECK', 'Demographic Guard'),
        ('CONTRADICTION_CHECK', 'Contradiction Detection'),
        ('RATE_LIMIT', 'Rate Limiting'),
        ('CUSTOM', 'Custom Rule'),
    ])
    condition = models.JSONField(help_text="Rule condition configuration")
    severity = models.CharField(max_length=20, choices=[
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('blocking', 'Blocking'),
    ], default='warning')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class ComplianceReport(models.Model):
    """Generated compliance/audit reports."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=50, choices=[
        ('FAIRNESS', 'Fairness Analysis'),
        ('SAFETY', 'Safety Audit'),
        ('PERFORMANCE', 'Performance Review'),
        ('FULL', 'Full Compliance Report'),
    ])
    workflow_run = models.ForeignKey(
        'patients.WorkflowRun', on_delete=models.CASCADE,
        related_name='compliance_reports', null=True, blank=True
    )
    data = models.JSONField(default=dict)
    summary = models.TextField(blank=True)
    generated_by = models.CharField(max_length=200, default='system')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report_type} report - {self.created_at}"
