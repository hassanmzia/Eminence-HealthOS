"""
FHIR R4 resource mapping utilities.

Converts between HealthOS internal models and FHIR R4 JSON representations.
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID


# ---------------------------------------------------------------------------
# Coding system URIs
# ---------------------------------------------------------------------------
SYSTEM_ICD10 = "http://hl7.org/fhir/sid/icd-10-cm"
SYSTEM_RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
SYSTEM_NDC = "http://hl7.org/fhir/sid/ndc"
SYSTEM_LOINC = "http://loinc.org"
SYSTEM_UCUM = "http://unitsofmeasure.org"
SYSTEM_OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
SYSTEM_OBS_INTERP = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"
SYSTEM_CONDITION_CLINICAL = "http://terminology.hl7.org/CodeSystem/condition-clinical"
SYSTEM_CONDITION_VERIFICATION = "http://terminology.hl7.org/CodeSystem/condition-ver-status"
SYSTEM_CONDITION_CATEGORY = "http://terminology.hl7.org/CodeSystem/condition-category"
SYSTEM_CONDITION_SEVERITY = "http://snomed.info/sct"
SYSTEM_MEDICATION_STATUS = "http://hl7.org/fhir/CodeSystem/medication-statement-status"
SYSTEM_ENCOUNTER_CLASS = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
SYSTEM_CARE_PLAN_CATEGORY = "http://hl7.org/fhir/us/core/CodeSystem/careplan-category"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _isoformat(value) -> Optional[str]:
    """Safely convert a date/datetime to ISO-8601 string."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _severity_snomed(severity: str) -> dict:
    """Map plain severity text to SNOMED CT coding."""
    mapping = {
        "mild": {"code": "255604002", "display": "Mild"},
        "moderate": {"code": "6736007", "display": "Moderate"},
        "severe": {"code": "24484000", "display": "Severe"},
    }
    entry = mapping.get(severity.lower(), {"code": severity, "display": severity})
    return {
        "coding": [
            {
                "system": SYSTEM_CONDITION_SEVERITY,
                "code": entry["code"],
                "display": entry["display"],
            }
        ]
    }


# ---------------------------------------------------------------------------
# Patient
# ---------------------------------------------------------------------------

def to_fhir_patient(patient) -> dict:
    """Convert a Patient model to FHIR R4 Patient resource."""
    resource = {
        "resourceType": "Patient",
        "id": str(patient.id) if hasattr(patient, "id") else None,
        "identifier": [
            {
                "system": "urn:healthos:mrn",
                "value": patient.mrn,
            }
        ],
        "active": not getattr(patient, "is_deleted", False),
        "name": [
            {
                "use": "official",
                "family": patient.last_name,
                "given": [patient.first_name],
            }
        ],
        "gender": patient.sex,
        "birthDate": patient.date_of_birth.isoformat()
        if isinstance(patient.date_of_birth, date)
        else patient.date_of_birth,
    }

    # Contact
    telecoms = []
    if getattr(patient, "phone", None):
        telecoms.append({"system": "phone", "value": patient.phone})
    if getattr(patient, "email", None):
        telecoms.append({"system": "email", "value": patient.email})
    if telecoms:
        resource["telecom"] = telecoms

    # Address
    if getattr(patient, "address_line1", None):
        resource["address"] = [
            {
                "use": "home",
                "line": [patient.address_line1],
                "city": getattr(patient, "city", None),
                "state": getattr(patient, "state", None),
                "postalCode": getattr(patient, "postal_code", None),
                "country": getattr(patient, "country", "US"),
            }
        ]

    # Communication
    if getattr(patient, "preferred_language", None):
        resource["communication"] = [
            {
                "language": {
                    "coding": [
                        {
                            "system": "urn:ietf:bcp:47",
                            "code": patient.preferred_language,
                        }
                    ]
                },
                "preferred": True,
            }
        ]

    return resource


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

def to_fhir_observation(obs) -> dict:
    """Convert an Observation model to FHIR R4 Observation resource."""
    resource = {
        "resourceType": "Observation",
        "id": str(obs.id) if hasattr(obs, "id") else None,
        "status": obs.status,
        "category": [
            {
                "coding": [
                    {
                        "system": SYSTEM_OBS_CATEGORY,
                        "code": obs.category,
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": SYSTEM_LOINC,
                    "code": obs.loinc_code,
                    "display": obs.display,
                }
            ]
        },
        "subject": {"reference": f"Patient/{obs.patient_id}"},
        "effectiveDateTime": obs.effective_datetime.isoformat()
        if isinstance(obs.effective_datetime, datetime)
        else obs.effective_datetime,
    }

    # Value
    if obs.value_quantity is not None:
        resource["valueQuantity"] = {
            "value": obs.value_quantity,
            "unit": obs.value_unit or "",
            "system": SYSTEM_UCUM,
        }
    elif getattr(obs, "value_string", None):
        resource["valueString"] = obs.value_string

    # Reference range
    if getattr(obs, "reference_low", None) or getattr(obs, "reference_high", None):
        ref_range = {}
        if obs.reference_low is not None:
            ref_range["low"] = {"value": obs.reference_low, "unit": obs.value_unit or ""}
        if obs.reference_high is not None:
            ref_range["high"] = {"value": obs.reference_high, "unit": obs.value_unit or ""}
        resource["referenceRange"] = [ref_range]

    # Interpretation
    if getattr(obs, "interpretation", None):
        interp_map = {
            "N": "Normal", "H": "High", "L": "Low",
            "HH": "Critical high", "LL": "Critical low",
        }
        resource["interpretation"] = [
            {
                "coding": [
                    {
                        "system": SYSTEM_OBS_INTERP,
                        "code": obs.interpretation,
                        "display": interp_map.get(obs.interpretation, obs.interpretation),
                    }
                ]
            }
        ]

    # Components
    if getattr(obs, "components", None):
        resource["component"] = obs.components

    return resource


# ---------------------------------------------------------------------------
# Condition
# ---------------------------------------------------------------------------

def to_fhir_condition(condition) -> dict:
    """Convert a Condition model to FHIR R4 Condition resource."""
    resource: dict[str, Any] = {
        "resourceType": "Condition",
        "id": str(condition.id) if hasattr(condition, "id") else None,
        "clinicalStatus": {
            "coding": [
                {
                    "system": SYSTEM_CONDITION_CLINICAL,
                    "code": condition.clinical_status,
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": SYSTEM_CONDITION_VERIFICATION,
                    "code": condition.verification_status,
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": SYSTEM_CONDITION_CATEGORY,
                        "code": getattr(condition, "category", "encounter-diagnosis"),
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": SYSTEM_ICD10,
                    "code": condition.icd10_code,
                    "display": condition.display,
                }
            ]
        },
        "subject": {"reference": f"Patient/{condition.patient_id}"},
    }

    # Severity
    if getattr(condition, "severity", None):
        resource["severity"] = _severity_snomed(condition.severity)

    # Dates
    onset = _isoformat(getattr(condition, "onset_date", None))
    if onset:
        resource["onsetDateTime"] = onset

    abatement = _isoformat(getattr(condition, "abatement_date", None))
    if abatement:
        resource["abatementDateTime"] = abatement

    recorded = _isoformat(getattr(condition, "recorded_date", None))
    if recorded:
        resource["recordedDate"] = recorded

    # Body site
    if getattr(condition, "body_site", None):
        resource["bodySite"] = [
            {
                "text": condition.body_site,
            }
        ]

    # Note
    if getattr(condition, "note", None):
        resource["note"] = [{"text": condition.note}]

    return resource


# ---------------------------------------------------------------------------
# Medication  (-> FHIR R4 MedicationStatement)
# ---------------------------------------------------------------------------

def to_fhir_medication(medication) -> dict:
    """Convert a Medication model to FHIR R4 MedicationStatement resource."""
    # Build medication codeable concept with available code systems
    codings = []
    if getattr(medication, "rxnorm_code", None):
        codings.append({
            "system": SYSTEM_RXNORM,
            "code": medication.rxnorm_code,
            "display": medication.name,
        })
    if getattr(medication, "ndc_code", None):
        codings.append({
            "system": SYSTEM_NDC,
            "code": medication.ndc_code,
            "display": medication.name,
        })
    # Always include at least a text entry
    medication_codeable: dict[str, Any] = {"text": medication.name}
    if codings:
        medication_codeable["coding"] = codings

    resource: dict[str, Any] = {
        "resourceType": "MedicationStatement",
        "id": str(medication.id) if hasattr(medication, "id") else None,
        "status": medication.status,
        "medicationCodeableConcept": medication_codeable,
        "subject": {"reference": f"Patient/{medication.patient_id}"},
    }

    # Effective period
    start = _isoformat(getattr(medication, "start_date", None))
    end = _isoformat(getattr(medication, "end_date", None))
    if start or end:
        period: dict[str, str] = {}
        if start:
            period["start"] = start
        if end:
            period["end"] = end
        resource["effectivePeriod"] = period

    # Dosage
    dosage_entry: dict[str, Any] = {}

    if getattr(medication, "dosage", None):
        dosage_entry["text"] = medication.dosage

    if getattr(medication, "frequency", None):
        dosage_entry["timing"] = {
            "code": {"text": medication.frequency},
        }

    if getattr(medication, "route", None):
        dosage_entry["route"] = {"text": medication.route}

    if getattr(medication, "dosage_value", None) is not None:
        dose_quantity: dict[str, Any] = {"value": medication.dosage_value}
        if getattr(medication, "dosage_unit", None):
            dose_quantity["unit"] = medication.dosage_unit
            dose_quantity["system"] = SYSTEM_UCUM
        dosage_entry["doseAndRate"] = [{"doseQuantity": dose_quantity}]

    if dosage_entry:
        resource["dosage"] = [dosage_entry]

    return resource


# ---------------------------------------------------------------------------
# Encounter
# ---------------------------------------------------------------------------

def to_fhir_encounter(encounter) -> dict:
    """Convert an Encounter model to FHIR R4 Encounter resource."""
    resource: dict[str, Any] = {
        "resourceType": "Encounter",
        "id": str(encounter.id) if hasattr(encounter, "id") else None,
        "status": encounter.status,
        "class": {
            "system": SYSTEM_ENCOUNTER_CLASS,
            "code": getattr(encounter, "encounter_class", "AMB"),
        },
        "type": [
            {
                "text": getattr(encounter, "encounter_type", "office_visit"),
            }
        ],
        "subject": {"reference": f"Patient/{encounter.patient_id}"},
    }

    # Participant (provider)
    provider_id = getattr(encounter, "provider_id", None)
    if provider_id:
        resource["participant"] = [
            {
                "individual": {"reference": f"Practitioner/{provider_id}"},
            }
        ]

    # Period
    start = _isoformat(getattr(encounter, "start_time", None) or getattr(encounter, "started_at", None))
    end = _isoformat(getattr(encounter, "end_time", None) or getattr(encounter, "ended_at", None))
    if start or end:
        period: dict[str, str] = {}
        if start:
            period["start"] = start
        if end:
            period["end"] = end
        resource["period"] = period

    # Reason
    reason_code = getattr(encounter, "reason_code", None)
    reason_display = getattr(encounter, "reason_display", None) or getattr(encounter, "reason", None)
    if reason_code or reason_display:
        reason_entry: dict[str, Any] = {}
        if reason_code:
            reason_entry["coding"] = [
                {
                    "system": SYSTEM_ICD10,
                    "code": reason_code,
                    "display": reason_display or "",
                }
            ]
        elif reason_display:
            reason_entry["text"] = reason_display
        resource["reasonCode"] = [reason_entry]

    # Priority
    if getattr(encounter, "priority", None):
        resource["priority"] = {"text": encounter.priority}

    # Discharge disposition
    if getattr(encounter, "discharge_disposition", None):
        resource["hospitalization"] = {
            "dischargeDisposition": {"text": encounter.discharge_disposition},
        }

    return resource


# ---------------------------------------------------------------------------
# CarePlan
# ---------------------------------------------------------------------------

def to_fhir_care_plan(care_plan) -> dict:
    """Convert a CarePlan model to FHIR R4 CarePlan resource."""
    resource: dict[str, Any] = {
        "resourceType": "CarePlan",
        "id": str(care_plan.id) if hasattr(care_plan, "id") else None,
        "status": care_plan.status,
        "intent": getattr(care_plan, "intent", "plan"),
        "title": getattr(care_plan, "title", None),
        "subject": {"reference": f"Patient/{care_plan.patient_id}"},
    }

    # Category
    category = getattr(care_plan, "category", None) or getattr(care_plan, "plan_type", None)
    if category:
        resource["category"] = [
            {
                "coding": [
                    {
                        "system": SYSTEM_CARE_PLAN_CATEGORY,
                        "code": category,
                    }
                ]
            }
        ]

    # Description
    if getattr(care_plan, "description", None):
        resource["description"] = care_plan.description

    # Period
    start = _isoformat(getattr(care_plan, "start_date", None))
    end = _isoformat(getattr(care_plan, "end_date", None))
    if start or end:
        period: dict[str, str] = {}
        if start:
            period["start"] = start
        if end:
            period["end"] = end
        resource["period"] = period

    # Goals — map list entries to FHIR Goal references or descriptions
    goals = getattr(care_plan, "goals", None)
    if goals:
        goal_entries = []
        if isinstance(goals, list):
            for i, g in enumerate(goals):
                if isinstance(g, dict):
                    goal_entries.append({
                        "reference": g.get("reference", f"#goal-{i}"),
                        "display": g.get("description", g.get("display", "")),
                    })
                else:
                    goal_entries.append({"display": str(g)})
        resource["goal"] = goal_entries

    # Activities — map interventions / activities list
    activities = getattr(care_plan, "activities", None) or getattr(care_plan, "interventions", None)
    if activities:
        activity_entries = []
        if isinstance(activities, list):
            for act in activities:
                if isinstance(act, dict):
                    detail: dict[str, Any] = {
                        "status": act.get("status", "not-started"),
                        "description": act.get("description", act.get("detail", "")),
                    }
                    activity_entries.append({"detail": detail})
                else:
                    activity_entries.append({
                        "detail": {
                            "status": "not-started",
                            "description": str(act),
                        }
                    })
        resource["activity"] = activity_entries

    # Addresses (condition references)
    addresses = getattr(care_plan, "addresses", None)
    if addresses and isinstance(addresses, list):
        resource["addresses"] = [
            {"reference": f"Condition/{ref}" if isinstance(ref, str) else ref.get("reference", str(ref))}
            for ref in addresses
        ]

    # Author (provider)
    provider_id = getattr(care_plan, "provider_id", None)
    if provider_id:
        resource["author"] = {"reference": f"Practitioner/{provider_id}"}

    # Monitoring cadence stored as extension
    monitoring = getattr(care_plan, "monitoring_cadence", None)
    if monitoring:
        resource.setdefault("extension", []).append({
            "url": "urn:healthos:care-plan:monitoring-cadence",
            "valueString": str(monitoring),
        })

    return resource


# ---------------------------------------------------------------------------
# from_fhir_* reverse converters
# ---------------------------------------------------------------------------

def from_fhir_patient(fhir: dict) -> dict:
    """Extract HealthOS patient fields from a FHIR R4 Patient resource."""
    result = {}

    names = fhir.get("name", [])
    if names:
        result["last_name"] = names[0].get("family", "")
        given = names[0].get("given", [])
        result["first_name"] = given[0] if given else ""

    result["sex"] = fhir.get("gender", "unknown")
    result["date_of_birth"] = fhir.get("birthDate")

    identifiers = fhir.get("identifier", [])
    for ident in identifiers:
        if ident.get("system") == "urn:healthos:mrn":
            result["mrn"] = ident.get("value")

    telecoms = fhir.get("telecom", [])
    for t in telecoms:
        if t.get("system") == "phone":
            result["phone"] = t.get("value")
        elif t.get("system") == "email":
            result["email"] = t.get("value")

    addresses = fhir.get("address", [])
    if addresses:
        addr = addresses[0]
        lines = addr.get("line", [])
        result["address_line1"] = lines[0] if lines else None
        result["city"] = addr.get("city")
        result["state"] = addr.get("state")
        result["postal_code"] = addr.get("postalCode")
        result["country"] = addr.get("country", "US")

    return result


def from_fhir_observation(fhir: dict) -> dict:
    """Extract HealthOS observation fields from a FHIR R4 Observation resource."""
    result: dict[str, Any] = {}

    result["status"] = fhir.get("status", "final")

    # Category
    categories = fhir.get("category", [])
    if categories:
        cat_codings = categories[0].get("coding", [])
        if cat_codings:
            result["category"] = cat_codings[0].get("code")

    # Code (LOINC)
    code_block = fhir.get("code", {})
    codings = code_block.get("coding", [])
    for coding in codings:
        if coding.get("system") == SYSTEM_LOINC:
            result["loinc_code"] = coding.get("code")
            result["display"] = coding.get("display")
            break
    else:
        # Fall back to first coding if no LOINC found
        if codings:
            result["loinc_code"] = codings[0].get("code")
            result["display"] = codings[0].get("display")

    # Subject
    subject = fhir.get("subject", {})
    ref = subject.get("reference", "")
    if ref.startswith("Patient/"):
        result["patient_id"] = ref.split("/", 1)[1]

    # Effective datetime
    result["effective_datetime"] = fhir.get("effectiveDateTime")

    # Value
    if "valueQuantity" in fhir:
        vq = fhir["valueQuantity"]
        result["value_quantity"] = vq.get("value")
        result["value_unit"] = vq.get("unit")
    elif "valueString" in fhir:
        result["value_string"] = fhir["valueString"]
    elif "valueCodeableConcept" in fhir:
        cc = fhir["valueCodeableConcept"]
        result["value_string"] = cc.get("text") or (
            cc["coding"][0].get("display") if cc.get("coding") else None
        )

    # Reference range
    ref_ranges = fhir.get("referenceRange", [])
    if ref_ranges:
        rr = ref_ranges[0]
        if "low" in rr:
            result["reference_low"] = rr["low"].get("value")
        if "high" in rr:
            result["reference_high"] = rr["high"].get("value")

    # Interpretation
    interps = fhir.get("interpretation", [])
    if interps:
        interp_codings = interps[0].get("coding", [])
        if interp_codings:
            result["interpretation"] = interp_codings[0].get("code")

    # Components
    if "component" in fhir:
        result["components"] = fhir["component"]

    return result


def from_fhir_condition(fhir: dict) -> dict:
    """Extract HealthOS condition fields from a FHIR R4 Condition resource."""
    result: dict[str, Any] = {}

    # Clinical status
    clinical_status = fhir.get("clinicalStatus", {})
    cs_codings = clinical_status.get("coding", [])
    if cs_codings:
        result["clinical_status"] = cs_codings[0].get("code", "active")
    else:
        result["clinical_status"] = "active"

    # Verification status
    ver_status = fhir.get("verificationStatus", {})
    vs_codings = ver_status.get("coding", [])
    if vs_codings:
        result["verification_status"] = vs_codings[0].get("code", "confirmed")
    else:
        result["verification_status"] = "confirmed"

    # Category
    categories = fhir.get("category", [])
    if categories:
        cat_codings = categories[0].get("coding", [])
        if cat_codings:
            result["category"] = cat_codings[0].get("code")

    # Code (ICD-10)
    code_block = fhir.get("code", {})
    codings = code_block.get("coding", [])
    for coding in codings:
        if coding.get("system") == SYSTEM_ICD10:
            result["icd10_code"] = coding.get("code")
            result["display"] = coding.get("display")
            break
    else:
        if codings:
            result["icd10_code"] = codings[0].get("code")
            result["display"] = codings[0].get("display")

    # Subject
    subject = fhir.get("subject", {})
    ref = subject.get("reference", "")
    if ref.startswith("Patient/"):
        result["patient_id"] = ref.split("/", 1)[1]

    # Severity
    severity = fhir.get("severity", {})
    sev_codings = severity.get("coding", [])
    if sev_codings:
        sev_display = sev_codings[0].get("display", "").lower()
        if sev_display in ("mild", "moderate", "severe"):
            result["severity"] = sev_display
        else:
            result["severity"] = sev_codings[0].get("code")

    # Dates
    if "onsetDateTime" in fhir:
        result["onset_date"] = fhir["onsetDateTime"]
    if "abatementDateTime" in fhir:
        result["abatement_date"] = fhir["abatementDateTime"]
    if "recordedDate" in fhir:
        result["recorded_date"] = fhir["recordedDate"]

    # Body site
    body_sites = fhir.get("bodySite", [])
    if body_sites:
        result["body_site"] = body_sites[0].get("text") or (
            body_sites[0]["coding"][0].get("display")
            if body_sites[0].get("coding")
            else None
        )

    # Note
    notes = fhir.get("note", [])
    if notes:
        result["note"] = notes[0].get("text")

    return result


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------

def to_fhir_bundle(resources: list[dict], bundle_type: str = "searchset") -> dict:
    """Wrap a list of FHIR resources into a FHIR R4 Bundle."""
    entries = []
    for res in resources:
        resource_type = res.get("resourceType", "Unknown")
        resource_id = res.get("id", "")
        entry: dict[str, Any] = {
            "fullUrl": f"{resource_type}/{resource_id}" if resource_id else None,
            "resource": res,
        }
        entries.append(entry)

    return {
        "resourceType": "Bundle",
        "type": bundle_type,
        "total": len(resources),
        "entry": entries,
    }
