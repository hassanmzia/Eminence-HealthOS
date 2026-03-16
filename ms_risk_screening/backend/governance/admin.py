from django.contrib import admin
from .models import GovernanceRule, ComplianceReport

@admin.register(GovernanceRule)
class GovernanceRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'severity', 'is_active']
    list_filter = ['rule_type', 'severity', 'is_active']

@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'workflow_run', 'generated_by', 'created_at']
    list_filter = ['report_type']
