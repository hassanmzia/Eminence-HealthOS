from django.contrib import admin

from .models import Patient, PolicyConfiguration, RiskAssessment, WorkflowRun


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "patient_id",
        "age",
        "sex",
        "visits_last_year",
        "lookalike_dx",
        "has_mri",
        "mri_lesions",
        "note_has_ms_terms",
        "true_at_risk",
        "symptom_count",
        "created_at",
    )
    list_filter = (
        "sex",
        "true_at_risk",
        "has_mri",
        "mri_lesions",
        "note_has_ms_terms",
        "lookalike_dx",
        "optic_neuritis",
        "paresthesia",
        "weakness",
        "gait_instability",
        "vertigo",
        "fatigue",
        "bladder_issues",
        "cognitive_fog",
        "vitamin_d_deficient",
        "infectious_mono_history",
    )
    search_fields = ("patient_id", "note", "lookalike_dx")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (
            "Identification",
            {"fields": ("id", "patient_id", "age", "sex", "visits_last_year", "lookalike_dx")},
        ),
        (
            "Symptoms",
            {
                "fields": (
                    "optic_neuritis",
                    "paresthesia",
                    "weakness",
                    "gait_instability",
                    "vertigo",
                    "fatigue",
                    "bladder_issues",
                    "cognitive_fog",
                ),
            },
        ),
        (
            "Notes & Imaging",
            {"fields": ("note", "note_has_ms_terms", "has_mri", "mri_lesions")},
        ),
        (
            "Augmented Markers",
            {
                "fields": (
                    "vitamin_d_ngml",
                    "vitamin_d_deficient",
                    "infectious_mono_history",
                    "smartform_neuro_symptom_score",
                    "paths_like_function_score",
                ),
            },
        ),
        (
            "Ground Truth & Timestamps",
            {"fields": ("true_at_risk", "created_at", "updated_at")},
        ),
    )

    def symptom_count(self, obj):
        return obj.symptom_count

    symptom_count.short_description = "Symptoms"


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient",
        "run_id",
        "risk_score",
        "action",
        "autonomy_level",
        "flag_count",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = (
        "action",
        "autonomy_level",
        "flag_count",
    )
    search_fields = ("patient__patient_id", "reviewed_by", "review_notes")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("patient",)


@admin.register(PolicyConfiguration)
class PolicyConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "risk_review_threshold",
        "draft_order_threshold",
        "auto_order_threshold",
        "max_auto_actions_per_day",
        "is_active",
        "created_by",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "created_by")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "policy",
        "status",
        "total_patients",
        "candidates_found",
        "flagged_count",
        "precision",
        "recall",
        "auto_actions",
        "draft_actions",
        "recommend_actions",
        "duration_seconds",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("error_message",)
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("policy",)
