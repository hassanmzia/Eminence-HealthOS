"""
Vitals Generator - Generates realistic synthetic vital signs data.
Supports various patient conditions and realistic variations.
"""

import random
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class PatientProfile:
    """Patient profile that influences vital sign generation."""
    age: int = 50
    condition: str = "normal"  # normal, hypertensive, hypotensive, fever, tachycardic, bradycardic, hypoxic, diabetic, diabetic_hyper, afib, mi_risk

    @classmethod
    def random(cls) -> "PatientProfile":
        conditions = ["normal", "normal", "normal", "hypertensive", "hypotensive",
                      "fever", "tachycardic", "bradycardic", "hypoxic", "diabetic", "afib"]
        return cls(
            age=random.randint(25, 85),
            condition=random.choice(conditions)
        )


# ECG Interpretations for different conditions
ECG_PATTERNS = {
    "normal": [
        {"rhythm": "Normal sinus rhythm", "rate": "60-100", "interpretation": "Normal ECG", "findings": []},
        {"rhythm": "Sinus rhythm", "rate": "60-100", "interpretation": "Within normal limits", "findings": []},
    ],
    "tachycardic": [
        {"rhythm": "Sinus tachycardia", "rate": ">100", "interpretation": "Elevated heart rate", "findings": ["Tachycardia"]},
    ],
    "bradycardic": [
        {"rhythm": "Sinus bradycardia", "rate": "<60", "interpretation": "Slow heart rate", "findings": ["Bradycardia"]},
    ],
    "afib": [
        {"rhythm": "Atrial fibrillation", "rate": "irregular", "interpretation": "Irregular rhythm, absent P waves", "findings": ["Atrial fibrillation", "Irregularly irregular rhythm"]},
        {"rhythm": "Atrial fibrillation with RVR", "rate": ">110", "interpretation": "Rapid ventricular response", "findings": ["Atrial fibrillation", "Rapid ventricular response"]},
    ],
    "mi_risk": [
        {"rhythm": "Sinus rhythm", "rate": "60-100", "interpretation": "ST elevation in leads V1-V4", "findings": ["ST elevation", "Possible anterior MI"]},
        {"rhythm": "Sinus rhythm", "rate": "60-100", "interpretation": "ST depression, T wave inversion", "findings": ["ST depression", "T wave inversion", "Ischemic changes"]},
    ],
    "hypertensive": [
        {"rhythm": "Sinus rhythm", "rate": "60-100", "interpretation": "Left ventricular hypertrophy pattern", "findings": ["LVH by voltage criteria"]},
    ],
}


class VitalsGenerator:
    """Generates realistic vital signs based on patient profile and device capabilities."""

    # Normal ranges for vital signs
    NORMAL_RANGES = {
        "heart_rate": (60, 100),           # bpm
        "blood_pressure_systolic": (110, 130),    # mmHg
        "blood_pressure_diastolic": (70, 85),     # mmHg
        "spo2": (95, 100),                 # %
        "temperature": (36.1, 37.2),       # Celsius
        "respiratory_rate": (12, 20),      # breaths/min
        "glucose": (70, 100),              # mg/dL (fasting)
    }

    # Abnormal ranges by condition
    CONDITION_MODIFIERS = {
        "hypertensive": {
            "blood_pressure_systolic": (140, 180),
            "blood_pressure_diastolic": (90, 110),
            "heart_rate": (70, 110),
        },
        "hypotensive": {
            "blood_pressure_systolic": (80, 100),
            "blood_pressure_diastolic": (50, 65),
            "heart_rate": (90, 120),  # compensatory tachycardia
        },
        "fever": {
            "temperature": (38.0, 40.0),
            "heart_rate": (90, 130),  # elevated due to fever
            "respiratory_rate": (18, 28),
        },
        "tachycardic": {
            "heart_rate": (100, 150),
        },
        "bradycardic": {
            "heart_rate": (40, 55),
        },
        "hypoxic": {
            "spo2": (85, 93),
            "respiratory_rate": (22, 35),
            "heart_rate": (90, 130),
        },
        "diabetic": {
            "glucose": (100, 140),  # Slightly elevated fasting glucose
        },
        "diabetic_hyper": {
            "glucose": (180, 350),  # Hyperglycemia
            "heart_rate": (90, 110),
        },
        "afib": {
            "heart_rate": (80, 160),  # Irregular, often fast
        },
        "mi_risk": {
            "heart_rate": (60, 110),
            "blood_pressure_systolic": (90, 140),
        },
    }

    # LOINC codes for vital signs
    LOINC_CODES = {
        "heart_rate": {"code": "8867-4", "display": "Heart rate", "unit": "/min"},
        "blood_pressure_systolic": {"code": "8480-6", "display": "Systolic blood pressure", "unit": "mm[Hg]"},
        "blood_pressure_diastolic": {"code": "8462-4", "display": "Diastolic blood pressure", "unit": "mm[Hg]"},
        "spo2": {"code": "59408-5", "display": "Oxygen saturation in Arterial blood by Pulse oximetry", "unit": "%"},
        "temperature": {"code": "8310-5", "display": "Body temperature", "unit": "Cel"},
        "respiratory_rate": {"code": "9279-1", "display": "Respiratory rate", "unit": "/min"},
        "glucose": {"code": "2339-0", "display": "Glucose [Mass/volume] in Blood", "unit": "mg/dL"},
        "ecg": {"code": "8601-7", "display": "ECG interpretation", "unit": "interpretation"},
    }

    # Map device capabilities to vitals
    CAPABILITY_VITALS = {
        "heart_rate": ["heart_rate"],
        "blood_pressure": ["blood_pressure_systolic", "blood_pressure_diastolic"],
        "bp": ["blood_pressure_systolic", "blood_pressure_diastolic"],
        "spo2": ["spo2"],
        "oxygen": ["spo2"],
        "temperature": ["temperature"],
        "temp": ["temperature"],
        "respiratory_rate": ["respiratory_rate"],
        "respiration": ["respiratory_rate"],
        "glucose": ["glucose"],
        "blood_sugar": ["glucose"],
        "ecg": ["ecg"],
        "ekg": ["ecg"],
        "electrocardiogram": ["ecg"],
    }

    def __init__(self, profile: Optional[PatientProfile] = None):
        self.profile = profile or PatientProfile()
        self._last_values = {}  # For realistic variations
        self._last_ecg = None  # For ECG consistency

    def _generate_ecg(self) -> dict:
        """Generate ECG interpretation based on patient condition."""
        condition = self.profile.condition

        # Map condition to ECG pattern category
        if condition in ECG_PATTERNS:
            patterns = ECG_PATTERNS[condition]
        elif condition in ["diabetic", "diabetic_hyper"]:
            # Diabetics might have normal or tachycardic patterns
            patterns = ECG_PATTERNS["normal"] if random.random() > 0.3 else ECG_PATTERNS["tachycardic"]
        elif condition in ["hypotensive", "fever", "hypoxic"]:
            patterns = ECG_PATTERNS["tachycardic"]
        else:
            patterns = ECG_PATTERNS["normal"]

        ecg = random.choice(patterns)

        # Add some variation in findings
        if random.random() < 0.1:  # 10% chance of PVCs
            ecg = ecg.copy()
            ecg["findings"] = ecg["findings"] + ["Occasional PVCs"]

        return ecg

    def _get_range(self, vital: str) -> tuple:
        """Get the range for a vital sign based on patient condition."""
        if self.profile.condition in self.CONDITION_MODIFIERS:
            modifiers = self.CONDITION_MODIFIERS[self.profile.condition]
            if vital in modifiers:
                return modifiers[vital]
        return self.NORMAL_RANGES.get(vital, (0, 100))

    def _generate_value(self, vital: str) -> float:
        """Generate a realistic value with small variations from last reading."""
        min_val, max_val = self._get_range(vital)

        # If we have a previous value, vary slightly from it
        if vital in self._last_values:
            last = self._last_values[vital]
            # Allow 5-10% variation from last value
            variation = (max_val - min_val) * 0.1
            new_val = last + random.uniform(-variation, variation)
            # Clamp to range with some tolerance
            new_val = max(min_val - (max_val - min_val) * 0.05,
                         min(max_val + (max_val - min_val) * 0.05, new_val))
        else:
            # First reading - generate within range
            new_val = random.uniform(min_val, max_val)

        self._last_values[vital] = new_val

        # Round appropriately
        if vital in ["spo2", "heart_rate", "respiratory_rate"]:
            return round(new_val)
        elif vital == "temperature":
            return round(new_val, 1)
        else:
            return round(new_val)

    def generate_vitals(self, capabilities: list[str]) -> dict:
        """Generate vitals based on device capabilities."""
        vitals = {}

        # Determine which vitals to generate
        vitals_to_generate = set()
        for cap in capabilities:
            cap_lower = cap.lower().replace("-", "_").replace(" ", "_")
            if cap_lower in self.CAPABILITY_VITALS:
                vitals_to_generate.update(self.CAPABILITY_VITALS[cap_lower])

        # If no capabilities specified, generate common vitals (including glucose and ECG)
        if not vitals_to_generate:
            vitals_to_generate = {"heart_rate", "spo2", "blood_pressure_systolic",
                                  "blood_pressure_diastolic", "temperature", "respiratory_rate",
                                  "glucose", "ecg"}

        # Generate each vital
        for vital in vitals_to_generate:
            if vital == "ecg":
                # ECG is special - it's an interpretation, not a numeric value
                ecg_data = self._generate_ecg()
                vitals[vital] = {
                    "value": ecg_data,
                    "loinc": self.LOINC_CODES[vital]
                }
            elif vital in self.LOINC_CODES:
                vitals[vital] = {
                    "value": self._generate_value(vital),
                    "loinc": self.LOINC_CODES[vital]
                }

        return vitals

    def create_fhir_observations(self, vitals: dict, patient_id: str, device_id: str) -> list[dict]:
        """Convert generated vitals to FHIR Observation resources."""
        observations = []
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Handle blood pressure as combined observation with components
        if "blood_pressure_systolic" in vitals and "blood_pressure_diastolic" in vitals:
            sys_data = vitals["blood_pressure_systolic"]
            dia_data = vitals["blood_pressure_diastolic"]
            bp_obs = {
                "resourceType": "Observation",
                "status": "final",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }]
                }],
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel with all children optional"
                    }],
                    "text": "Blood pressure"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "device": {
                    "reference": f"Device/{device_id}"
                },
                "effectiveDateTime": timestamp,
                "component": [
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": sys_data["value"],
                            "unit": "mm[Hg]",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    },
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure"
                            }]
                        },
                        "valueQuantity": {
                            "value": dia_data["value"],
                            "unit": "mm[Hg]",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm[Hg]"
                        }
                    }
                ]
            }
            observations.append(bp_obs)

        # Handle ECG as special observation with interpretation
        if "ecg" in vitals:
            ecg_data = vitals["ecg"]["value"]
            loinc = vitals["ecg"]["loinc"]
            ecg_obs = {
                "resourceType": "Observation",
                "status": "final",
                "category": [
                    {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }]
                    },
                    {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "procedure",
                            "display": "Procedure"
                        }]
                    }
                ],
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": loinc["code"],
                        "display": loinc["display"]
                    }],
                    "text": "ECG Interpretation"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "device": {
                    "reference": f"Device/{device_id}"
                },
                "effectiveDateTime": timestamp,
                "valueCodeableConcept": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "271921002",
                        "display": ecg_data["rhythm"]
                    }],
                    "text": ecg_data["interpretation"]
                },
                "component": [
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8884-9",
                                "display": "Heart rhythm"
                            }]
                        },
                        "valueString": ecg_data["rhythm"]
                    },
                    {
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "8889-8",
                                "display": "Heart rate"
                            }]
                        },
                        "valueString": ecg_data["rate"]
                    }
                ]
            }
            # Add findings as additional components
            for finding in ecg_data.get("findings", []):
                ecg_obs["component"].append({
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "18844-1",
                            "display": "ECG finding"
                        }]
                    },
                    "valueString": finding
                })
            observations.append(ecg_obs)

        # Handle other vitals as regular observations
        for vital_name, vital_data in vitals.items():
            # Skip BP components and ECG as they're handled above
            if vital_name in ("blood_pressure_systolic", "blood_pressure_diastolic", "ecg"):
                continue

            loinc = vital_data["loinc"]
            obs = {
                "resourceType": "Observation",
                "status": "final",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }]
                }],
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": loinc["code"],
                        "display": loinc["display"]
                    }],
                    "text": loinc["display"]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "device": {
                    "reference": f"Device/{device_id}"
                },
                "effectiveDateTime": timestamp,
                "valueQuantity": {
                    "value": vital_data["value"],
                    "unit": loinc["unit"],
                    "system": "http://unitsofmeasure.org",
                    "code": loinc["unit"]
                }
            }
            observations.append(obs)

        return observations


# Patient profile cache to maintain consistency across readings
_patient_profiles: dict[str, PatientProfile] = {}


def get_patient_profile(patient_id: str) -> PatientProfile:
    """Get or create a patient profile for consistent vital generation."""
    if patient_id not in _patient_profiles:
        _patient_profiles[patient_id] = PatientProfile.random()
    return _patient_profiles[patient_id]


def reset_patient_profile(patient_id: str, condition: Optional[str] = None):
    """Reset or update a patient's profile."""
    if condition:
        age = _patient_profiles.get(patient_id, PatientProfile()).age
        _patient_profiles[patient_id] = PatientProfile(age=age, condition=condition)
    elif patient_id in _patient_profiles:
        del _patient_profiles[patient_id]
