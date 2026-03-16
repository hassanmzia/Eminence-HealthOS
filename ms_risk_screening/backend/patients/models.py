import uuid

from django.db import models


class Patient(models.Model):
    """
    Synthetic patient record for MS risk screening.
    Fields mirror the notebook's make_patients() output plus augmented marker columns.
    """

    SEX_CHOICES = [
        ("F", "Female"),
        ("M", "Male"),
    ]

    # Primary key & identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_id = models.CharField(max_length=10, unique=True, help_text="Format P00000")

    # Demographics & utilisation
    age = models.IntegerField()
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    visits_last_year = models.IntegerField()

    # Differential / look-alike diagnosis
    lookalike_dx = models.CharField(
        max_length=30,
        help_text="Simulated differential diagnosis (e.g. migraine, b12_deficiency, none)",
    )

    # Clinical note (synthetic)
    note = models.TextField(help_text="Synthetic clinical note excerpt")

    # Imaging
    has_mri = models.BooleanField(default=False)
    mri_lesions = models.BooleanField(default=False)

    # Note analysis flag
    note_has_ms_terms = models.BooleanField(default=False)

    # Ground truth label (simulated)
    true_at_risk = models.BooleanField(
        default=False,
        help_text="Simulated ground-truth: patient is at risk and needs review",
    )

    # --- 8 symptom boolean fields ---
    optic_neuritis = models.BooleanField(default=False)
    paresthesia = models.BooleanField(default=False)
    weakness = models.BooleanField(default=False)
    gait_instability = models.BooleanField(default=False)
    vertigo = models.BooleanField(default=False)
    fatigue = models.BooleanField(default=False)
    bladder_issues = models.BooleanField(default=False)
    cognitive_fog = models.BooleanField(default=False)

    # --- Augmented precursor-marker fields (nullable – populated by seed) ---
    vitamin_d_ngml = models.FloatField(null=True, blank=True, help_text="Serum 25(OH)D ng/mL")
    vitamin_d_deficient = models.BooleanField(null=True, blank=True)
    infectious_mono_history = models.BooleanField(null=True, blank=True)
    smartform_neuro_symptom_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Structured symptom score (smart-form style)",
    )
    paths_like_function_score = models.FloatField(
        null=True,
        blank=True,
        help_text="PATHS-like neuroperformance function score (0-100, lower is worse)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Computed helpers ---
    SYMPTOM_FIELDS = [
        "optic_neuritis",
        "paresthesia",
        "weakness",
        "gait_instability",
        "vertigo",
        "fatigue",
        "bladder_issues",
        "cognitive_fog",
    ]

    @property
    def symptom_count(self) -> int:
        """Return the number of active symptom flags for this patient."""
        return sum(
            1 for field in self.SYMPTOM_FIELDS if getattr(self, field)
        )

    class Meta:
        ordering = ["patient_id"]

    def __str__(self) -> str:
        return f"{self.patient_id} (age={self.age}, sex={self.sex})"


class RiskAssessment(models.Model):
    """
    One risk-assessment record per workflow run per patient.
    Stores the phenotyping score, action decision, safety flags, and review state.
    """

    ACTION_CHOICES = [
        ("NO_ACTION", "No Action"),
        ("RECOMMEND_NEURO_REVIEW", "Recommend Neuro Review"),
        ("DRAFT_MRI_ORDER", "Draft MRI Order"),
        ("AUTO_ORDER_MRI_AND_NOTIFY_NEURO", "Auto-Order MRI & Notify Neuro"),
    ]

    AUTONOMY_CHOICES = [
        ("RECOMMEND_ONLY", "Recommend Only"),
        ("DRAFT_ORDER", "Draft Order"),
        ("AUTO_ORDER_WITH_GUARDRAILS", "Auto-Order with Guardrails"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="risk_assessments",
    )
    run_id = models.UUIDField(help_text="Batch / workflow run identifier")

    # Phenotyping output
    risk_score = models.FloatField()
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    autonomy_level = models.CharField(max_length=40, choices=AUTONOMY_CHOICES)

    # Interpretability
    feature_contributions = models.JSONField(
        default=dict,
        help_text="Per-feature contribution dict from phenotyping agent",
    )
    flags = models.JSONField(
        default=list,
        help_text="List of safety / governance flags",
    )
    flag_count = models.IntegerField(default=0)
    rationale = models.JSONField(
        default=dict,
        help_text="Coordinator rationale payload",
    )
    notes_analysis = models.JSONField(
        default=dict,
        help_text="Notes/Imaging agent output",
    )

    # LLM summary (optional)
    llm_summary = models.TextField(blank=True, default="")

    # Patient card snapshot
    patient_card = models.JSONField(
        default=dict,
        help_text="Snapshot of patient data at assessment time",
    )

    # Clinician review
    reviewed_by = models.CharField(max_length=150, blank=True, default="")
    review_notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Assessment {str(self.id)[:8]} – {self.patient.patient_id} risk={self.risk_score:.2f}"


class PolicyConfiguration(models.Model):
    """
    Stores threshold and autonomy-limit settings for a workflow policy.
    Only one configuration should be active at a time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)

    # Risk-score thresholds
    risk_review_threshold = models.FloatField(
        default=0.65,
        help_text="Risk score >= this triggers RECOMMEND_NEURO_REVIEW",
    )
    draft_order_threshold = models.FloatField(
        default=0.80,
        help_text="Risk score >= this triggers DRAFT_MRI_ORDER",
    )
    auto_order_threshold = models.FloatField(
        default=0.90,
        help_text="Risk score >= this triggers AUTO_ORDER_MRI_AND_NOTIFY_NEURO",
    )

    # Guardrails
    max_auto_actions_per_day = models.IntegerField(default=20)
    is_active = models.BooleanField(default=False)

    # Audit
    created_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        active_label = " [ACTIVE]" if self.is_active else ""
        return f"{self.name}{active_label}"


class WorkflowRun(models.Model):
    """
    Tracks a single execution of the multi-agent screening pipeline.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("RUNNING", "Running"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        PolicyConfiguration,
        on_delete=models.PROTECT,
        related_name="workflow_runs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    # Counts
    total_patients = models.IntegerField(default=0)
    candidates_found = models.IntegerField(default=0)
    flagged_count = models.IntegerField(default=0)

    # Performance metrics (populated after run completes)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)

    # Action breakdown
    auto_actions = models.IntegerField(default=0)
    draft_actions = models.IntegerField(default=0)
    recommend_actions = models.IntegerField(default=0)

    # Safety
    safety_flag_rate = models.FloatField(null=True, blank=True)

    # Execution metadata
    duration_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Run {str(self.id)[:8]} [{self.status}] – {self.candidates_found} candidates"
