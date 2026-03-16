"""
Management command: seed_data
Generates synthetic patient records and a default PolicyConfiguration,
reproducing the notebook's make_patients() logic and augmented-marker generation.

Usage:
    python manage.py seed_data              # default 2500 patients
    python manage.py seed_data --patients 500
"""

import math
import random

import numpy as np
from django.core.management.base import BaseCommand

from patients.models import Patient, PolicyConfiguration


# ---------------------------------------------------------------------------
# Constants (mirrors notebook exactly)
# ---------------------------------------------------------------------------

SYMPTOMS = [
    "optic_neuritis",
    "paresthesia",
    "weakness",
    "gait_instability",
    "vertigo",
    "fatigue",
    "bladder_issues",
    "cognitive_fog",
]

LOOKALIKE_DIAG = [
    "migraine",
    "b12_deficiency",
    "anxiety",
    "fibromyalgia",
    "stroke_TIA",
    "none",
]
LOOKALIKE_PROBS = [0.18, 0.10, 0.12, 0.08, 0.05, 0.47]

NOTE_PHRASES_MS = [
    "demyelinating",
    "periventricular lesions",
    "oligoclonal bands",
    "optic neuritis",
    "relapsing symptoms",
    "neurology referral",
    "MRI brain w/wo contrast",
]
NOTE_PHRASES_NONMS = [
    "tension headache",
    "vitamin deficiency",
    "stress-related",
    "poor sleep",
    "peripheral neuropathy",
    "viral illness",
    "benign positional vertigo",
]

LOOKALIKE_PENALTY = {
    "migraine": 0.6,
    "b12_deficiency": 0.7,
    "anxiety": 0.4,
    "fibromyalgia": 0.5,
    "stroke_TIA": 0.8,
    "none": 0.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sigmoid(x):
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        exp_x = math.exp(x)
        return exp_x / (1.0 + exp_x)


# ---------------------------------------------------------------------------
# Patient generation (mirrors notebook cell 10 exactly)
# ---------------------------------------------------------------------------


def make_patient_row(index):
    """Generate a single synthetic patient dict (same logic as notebook)."""
    age = int(np.clip(np.random.normal(42, 14), 18, 85))
    sex = np.random.choice(["F", "M"], p=[0.62, 0.38])
    visits_last_year = int(np.clip(np.random.poisson(3), 0, 15))
    lookalike = np.random.choice(LOOKALIKE_DIAG, p=LOOKALIKE_PROBS)

    # Symptom probabilities (roughly plausible, not clinical)
    symptom_base = 0.08 + 0.03 * (sex == "F") + 0.01 * (age < 55)
    symptoms = {s: int(np.random.rand() < symptom_base) for s in SYMPTOMS}

    # Correlated symptom patterns
    if np.random.rand() < 0.05:
        symptoms["optic_neuritis"] = 1
        symptoms["paresthesia"] = int(np.random.rand() < 0.65)
    if np.random.rand() < 0.06:
        symptoms["gait_instability"] = 1
        symptoms["weakness"] = int(np.random.rand() < 0.5)

    # Structured "evidence" signal
    struct_signal = (
        1.6 * symptoms["optic_neuritis"]
        + 1.1 * symptoms["paresthesia"]
        + 1.0 * symptoms["weakness"]
        + 0.8 * symptoms["gait_instability"]
        + 0.7 * symptoms["vertigo"]
        + 0.6 * symptoms["fatigue"]
        + 0.4 * symptoms["bladder_issues"]
        + 0.3 * symptoms["cognitive_fog"]
    )

    lookalike_pen = LOOKALIKE_PENALTY[lookalike]

    # Note generation
    note_ms_prob = sigmoid(struct_signal - lookalike_pen - 1.2)
    note_has_ms_terms = int(np.random.rand() < note_ms_prob)

    note_terms = []
    if note_has_ms_terms:
        note_terms += random.sample(NOTE_PHRASES_MS, k=random.randint(1, 3))
    else:
        note_terms += random.sample(NOTE_PHRASES_NONMS, k=random.randint(1, 3))
    note = " ; ".join(note_terms)

    # MRI report availability
    has_mri = int(
        np.random.rand()
        < (0.20 + 0.10 * symptoms["optic_neuritis"] + 0.05 * visits_last_year / 10)
    )
    mri_lesions = int(has_mri and (np.random.rand() < sigmoid(struct_signal - 1.0)))

    # Ground truth
    risk_latent = sigmoid(
        struct_signal
        + 0.9 * note_has_ms_terms
        + 0.8 * mri_lesions
        - lookalike_pen
        - 1.6
    )
    at_risk = int(np.random.rand() < risk_latent)

    return {
        "patient_id": f"P{index:05d}",
        "age": age,
        "sex": sex,
        "visits_last_year": visits_last_year,
        "lookalike_dx": lookalike,
        "note": note,
        "has_mri": bool(has_mri),
        "mri_lesions": bool(mri_lesions),
        "note_has_ms_terms": bool(note_has_ms_terms),
        "true_at_risk": bool(at_risk),
        **{s: bool(v) for s, v in symptoms.items()},
    }


# ---------------------------------------------------------------------------
# Augmented marker generation (mirrors notebook cell 48)
# ---------------------------------------------------------------------------


def augment_patient(row):
    """
    Add vitamin D, mono history, smartform score, PATHS-like score.
    Mutates and returns the same dict.
    """
    at_risk_int = int(row["true_at_risk"])
    age = row["age"]

    # Vitamin D (ng/mL): lower on average for higher-risk in this synthetic world
    base_vitd = float(np.clip(np.random.normal(28, 10), 5, 80))
    risk_influence = 6.0 * at_risk_int
    row["vitamin_d_ngml"] = round(
        float(
            np.clip(
                base_vitd - risk_influence + np.random.normal(0, 3), 5, 80
            )
        ),
        2,
    )
    row["vitamin_d_deficient"] = row["vitamin_d_ngml"] < 20.0

    # EBV / mono history (binary), correlated with risk
    row["infectious_mono_history"] = bool(
        np.random.rand() < (0.10 + 0.18 * at_risk_int)
    )

    # Smartform-like structured symptom score: compress symptom evidence
    symptom_sum = sum(1 for s in SYMPTOMS if row.get(s))
    row["smartform_neuro_symptom_score"] = round(
        float(np.clip(symptom_sum + np.random.normal(0, 0.75), 0, 8)), 4
    )

    # PATHS-like performance score (lower => worse function)
    row["paths_like_function_score"] = round(
        float(
            np.clip(
                100 - 6 * at_risk_int - 0.15 * age + np.random.normal(0, 6),
                0,
                100,
            )
        ),
        4,
    )

    return row


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed the database with synthetic patient data and a default policy."

    def add_arguments(self, parser):
        parser.add_argument(
            "--patients",
            type=int,
            default=2500,
            help="Number of synthetic patients to generate (default: 2500)",
        )

    def handle(self, *args, **options):
        n_patients = options["patients"]

        # -----------------------------------------------------------------
        # Guard: skip if patients already exist
        # -----------------------------------------------------------------
        existing_count = Patient.objects.count()
        if existing_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping patient generation: {existing_count} patients already exist."
                )
            )
        else:
            self.stdout.write(f"Generating {n_patients} synthetic patients ...")

            patients_to_create = []
            for i in range(n_patients):
                row = make_patient_row(i)
                row = augment_patient(row)
                patients_to_create.append(Patient(**row))

            Patient.objects.bulk_create(patients_to_create, batch_size=500)

            self.stdout.write(
                self.style.SUCCESS(f"Created {n_patients} patients.")
            )

        # -----------------------------------------------------------------
        # Default PolicyConfiguration
        # -----------------------------------------------------------------
        if PolicyConfiguration.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Skipping policy creation: policies already exist."
                )
            )
        else:
            PolicyConfiguration.objects.create(
                name="Default MS Screening Policy",
                risk_review_threshold=0.65,
                draft_order_threshold=0.80,
                auto_order_threshold=0.90,
                max_auto_actions_per_day=20,
                is_active=True,
                created_by="seed_data",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Created default PolicyConfiguration (active)."
                )
            )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
