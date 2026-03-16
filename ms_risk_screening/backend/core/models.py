"""Core models shared across the application."""
import uuid
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class AuditLog(TimeStampedModel):
    """Comprehensive audit trail for all system actions."""
    ACTION_TYPES = [
        ('AGENT_RUN', 'Agent Run'),
        ('DECISION', 'Decision Made'),
        ('POLICY_CHANGE', 'Policy Change'),
        ('MANUAL_REVIEW', 'Manual Review'),
        ('EXPORT', 'Data Export'),
        ('OVERRIDE', 'Decision Override'),
        ('ALERT', 'Alert Generated'),
    ]

    action_type = models.CharField(max_length=50, choices=ACTION_TYPES, db_index=True)
    actor = models.CharField(max_length=200, default='system')
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=200, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.action_type} by {self.actor} at {self.created_at}"


class SystemConfiguration(TimeStampedModel):
    """Runtime system configuration stored in DB."""
    key = models.CharField(max_length=200, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.key} = {self.value}"


class Notification(TimeStampedModel):
    """System notifications for clinicians and administrators."""
    SEVERITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('success', 'Success'),
    ]

    title = models.CharField(max_length=300)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    category = models.CharField(max_length=100, db_index=True)
    is_read = models.BooleanField(default=False)
    related_patient_id = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return f"[{self.severity}] {self.title}"
