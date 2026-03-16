"""Django admin registration for the agents app."""
from django.contrib import admin
from .models import AgentExecution


@admin.register(AgentExecution)
class AgentExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'agent_name',
        'patient_id_ref',
        'duration_ms',
        'run',
        'created_at',
    ]
    list_filter = ['agent_name', 'created_at']
    search_fields = ['patient_id_ref', 'agent_name']
    readonly_fields = ['id', 'created_at', 'payload']
    ordering = ['-created_at']
