"""
Eminence HealthOS — EHR Data Mappers

Bidirectional mapping between internal HealthOS models and external wire
formats (FHIR R4 JSON, HL7v2 pipe-delimited messages).

These mappers are intentionally kept as pure functions with no I/O so they
can be reused by both the FHIR and HL7v2 connectors as well as unit tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from shared.utils.hl7v2 import (
    COMPONENT_SEP,
    SEGMENT_TERMINATOR,
    _build_msh,
    _build_evn,
    _build_pid,
    _build_pv1,
    _build_segment,
    _hl7_timestamp,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR R4 — Internal -> FHIR
# ═══════════════════════════════════════════════════════════════════════════════


# Map internal encounter_type to FHIR class codes
_ENCOUNTER_CLASS_MAP: dict[str, dict[str, str]] = {
    "office_visit": {"code": "AMB", "display": "ambulatory"},
    "telehealth": {"code": "VR", "display": "virtual"},
    "rpm_review": {"code": "VR", "display": "virtual"},
    "emergency": {"code": "EMER", "display": "emergency"},
    "inpatient": {"code": "IMP", "display": "inpatient encounter"},
    "home_health": {"code": "HH", "display": "home health"},
}

# Map internal vital_type to LOINC codes
_LOINC_MAP: dict[str, tuple[str, str, str]] = {
    "heart_rate": ("8867-4", "Heart rate", "bpm"),
    "blood_pressure": ("85354-9", "Blood pressure panel", "mmHg"),
    "glucose": ("2339-0", "Glucose [Mass/volume] in Blood", "mg/dL"),
    "spo2": ("2708-6", "Oxygen saturation in Arterial blood", "%"),
    "weight": ("29463-7", "Body weight", "kg"),
    "temperature": ("8310-5", "Body temperature", "Cel"),
    "respiratory_rate": ("9279-1", "Respiratory rate", "/min"),
}


def encounter_to_fhir(encounter: Any) -> dict[str, Any]:
    """
    Convert an internal Encounter ORM object to a FHIR R4 Encounter resource.

    Supports both the ``healthos_platform.models.Encounter`` (main models.py)
    and ``shared.models.encounter.Encounter`` schemas.
    """
    enc_id = str(getattr(encounter, "id", ""))
    patient_id = str(getattr(encounter, "patient_id", ""))
    provider_id = getattr(encounter, "provider_id", None)

    # Determine encounter class
    enc_type = getattr(encounter, "encounter_type", "office_visit")
    class_info = _ENCOUNTER_CLASS_MAP.get(enc_type, {"code": "AMB", "display": "ambulatory"})

    # Status mapping — internal statuses map 1:1 to FHIR
    status = getattr(encounter, "status", "in-progress")

    # Period — handle both column-naming conventions
    start = getattr(encounter, "started_at", None) or getattr(encounter, "start_time", None)
    end = getattr(encounter, "ended_at", None) or getattr(encounter, "end_time", None)

    period: dict[str, str] = {}
    if start:
        period["start"] = _ensure_iso(start)
    if end:
        period["end"] = _ensure_iso(end)

    # Reason
    reason_code = getattr(encounter, "reason_code", None) or ""
    reason_display = (
        getattr(encounter, "reason_display", None)
        or getattr(encounter, "reason", None)
        or ""
    )

    resource: dict[str, Any] = {
        "resourceType": "Encounter",
        "id": enc_id,
        "status": status,
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            **class_info,
        },
        "type": [
            {
                "coding": [
                    {
                        "system": "http://eminence.health/encounter-type",
                        "code": enc_type,
                        "display": enc_type.replace("_", " ").title(),
                    }
                ]
            }
        ],
        "subject": {"reference": f"Patient/{patient_id}"},
    }

    if period:
        resource["period"] = period

    if provider_id:
        resource["participant"] = [
            {
                "type": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                                "code": "ATND",
                                "display": "attender",
                            }
                        ]
                    }
                ],
                "individual": {"reference": f"Practitioner/{provider_id}"},
            }
        ]

    if reason_code or reason_display:
        reason_coding: dict[str, Any] = {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": reason_code,
                    "display": reason_display,
                }
            ],
            "text": reason_display,
        }
        resource["reasonCode"] = [reason_coding]

    # Clinical notes as text
    notes = getattr(encounter, "clinical_notes", None)
    if notes:
        resource["text"] = {
            "status": "generated",
            "div": f'<div xmlns="http://www.w3.org/1999/xhtml"><p>{notes}</p></div>',
        }

    return resource


def clinical_note_to_fhir(note: Any) -> dict[str, Any]:
    """
    Convert an internal ClinicalNote ORM object to a FHIR R4
    DocumentReference resource.
    """
    note_id = str(getattr(note, "id", ""))
    encounter_id = str(getattr(note, "encounter_id", ""))
    author_id = getattr(note, "author_id", None)

    # Build the document content from SOAP sections
    sections: list[str] = []
    for section in ("subjective", "objective", "assessment", "plan"):
        text = getattr(note, section, None)
        if text:
            sections.append(f"{section.upper()}: {text}")
    content_text = "\n\n".join(sections) if sections else ""

    # Map note status to FHIR DocumentReference status
    status_map = {
        "draft": "preliminary",
        "pending_review": "preliminary",
        "signed": "current",
        "amended": "amended",
    }
    note_status = getattr(note, "status", "draft")
    fhir_status = status_map.get(note_status, "preliminary")

    # Map note_type to LOINC doc type
    type_map = {
        "soap": ("11506-3", "Progress note"),
        "progress": ("11506-3", "Progress note"),
        "procedure": ("28570-0", "Procedure note"),
    }
    note_type = getattr(note, "note_type", "soap")
    loinc_code, loinc_display = type_map.get(note_type, ("11506-3", "Progress note"))

    resource: dict[str, Any] = {
        "resourceType": "DocumentReference",
        "id": note_id,
        "status": fhir_status,
        "type": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": loinc_display,
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                        "code": "clinical-note",
                        "display": "Clinical Note",
                    }
                ]
            }
        ],
        "context": {
            "encounter": [{"reference": f"Encounter/{encounter_id}"}],
        },
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain",
                    "data": content_text,
                }
            }
        ],
    }

    if author_id:
        resource["author"] = [{"reference": f"Practitioner/{author_id}"}]

    signed_at = getattr(note, "signed_at", None)
    if signed_at:
        resource["date"] = _ensure_iso(signed_at)

    created_at = getattr(note, "created_at", None)
    if created_at:
        resource["date"] = resource.get("date", _ensure_iso(created_at))

    return resource


def vital_to_fhir_observation(vital: Any) -> dict[str, Any]:
    """
    Convert an internal Vital/Observation ORM object to a FHIR R4
    Observation resource.

    Handles both ``healthos_platform.models.Vital`` (JSONB value) and
    ``shared.models.observation.Observation`` (scalar value_quantity) schemas.
    """
    obs_id = str(getattr(vital, "id", ""))
    patient_id = str(getattr(vital, "patient_id", ""))

    # Detect which model we're dealing with
    vital_type = getattr(vital, "vital_type", None)
    loinc_code_attr = getattr(vital, "loinc_code", None)

    if loinc_code_attr:
        # shared.models.observation.Observation
        loinc_code = loinc_code_attr
        display = getattr(vital, "display", vital_type or "")
        unit = getattr(vital, "value_unit", "")
    elif vital_type and vital_type in _LOINC_MAP:
        loinc_code, display, unit = _LOINC_MAP[vital_type]
    else:
        loinc_code = "unknown"
        display = vital_type or "Unknown"
        unit = getattr(vital, "unit", "") or ""

    effective = (
        getattr(vital, "effective_datetime", None)
        or getattr(vital, "recorded_at", None)
    )

    observation: dict[str, Any] = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": getattr(vital, "status", "final"),
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": getattr(vital, "category", "vital-signs"),
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display,
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
    }

    if effective:
        observation["effectiveDateTime"] = _ensure_iso(effective)

    # Value handling — JSONB (Vital) vs scalar (Observation)
    value_data = getattr(vital, "value", None)
    value_quantity = getattr(vital, "value_quantity", None)

    if isinstance(value_data, dict):
        # Blood pressure has components
        if "systolic" in value_data and "diastolic" in value_data:
            observation["component"] = [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": value_data["systolic"],
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": {
                        "value": value_data["diastolic"],
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]",
                    },
                },
            ]
        else:
            val = value_data.get("value", 0)
            observation["valueQuantity"] = {
                "value": val,
                "unit": getattr(vital, "unit", "") or unit,
                "system": "http://unitsofmeasure.org",
            }
    elif value_quantity is not None:
        observation["valueQuantity"] = {
            "value": value_quantity,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
        }

    # Components from Observation model
    components = getattr(vital, "components", None)
    if isinstance(components, dict) and "component" not in observation:
        fhir_components = []
        for comp_code, comp_data in components.items():
            fhir_components.append({
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": comp_data.get("loinc_code", comp_code),
                            "display": comp_data.get("display", comp_code),
                        }
                    ]
                },
                "valueQuantity": {
                    "value": comp_data.get("value", 0),
                    "unit": comp_data.get("unit", ""),
                    "system": "http://unitsofmeasure.org",
                },
            })
        if fhir_components:
            observation["component"] = fhir_components

    return observation


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR R4 — FHIR -> Internal
# ═══════════════════════════════════════════════════════════════════════════════


def fhir_encounter_to_internal(fhir_json: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a FHIR R4 Encounter resource dict into a flat dict suitable for
    creating/updating an internal Encounter record.
    """
    # Extract patient ID from subject reference
    subject_ref = fhir_json.get("subject", {}).get("reference", "")
    patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""

    # Extract provider from participants
    provider_id = ""
    for participant in fhir_json.get("participant", []):
        individual = participant.get("individual", {}).get("reference", "")
        if individual.startswith("Practitioner/"):
            provider_id = individual.replace("Practitioner/", "")
            break

    # Encounter class -> encounter_type
    enc_class = fhir_json.get("class", {})
    class_code = enc_class.get("code", "AMB")
    class_to_type = {v["code"]: k for k, v in _ENCOUNTER_CLASS_MAP.items()}
    encounter_type = class_to_type.get(class_code, "office_visit")

    # Period
    period = fhir_json.get("period", {})
    start_time = period.get("start")
    end_time = period.get("end")

    # Reason
    reason_codes = fhir_json.get("reasonCode", [])
    reason_code = ""
    reason_display = ""
    if reason_codes:
        codings = reason_codes[0].get("coding", [])
        if codings:
            reason_code = codings[0].get("code", "")
            reason_display = codings[0].get("display", "")
        if not reason_display:
            reason_display = reason_codes[0].get("text", "")

    return {
        "fhir_id": fhir_json.get("id", ""),
        "patient_id": patient_id,
        "provider_id": provider_id or None,
        "status": fhir_json.get("status", "in-progress"),
        "encounter_type": encounter_type,
        "started_at": start_time,
        "ended_at": end_time,
        "reason": reason_display,
        "reason_code": reason_code,
        "reason_display": reason_display,
    }


def fhir_observation_to_internal(fhir_json: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a FHIR R4 Observation resource dict into a flat dict suitable
    for creating/updating an internal Observation/Vital record.
    """
    subject_ref = fhir_json.get("subject", {}).get("reference", "")
    patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""

    code_info = fhir_json.get("code", {})
    codings = code_info.get("coding", [])
    loinc_code = codings[0].get("code", "") if codings else ""
    display = codings[0].get("display", "") if codings else ""

    # Value
    vq = fhir_json.get("valueQuantity", {})
    value_quantity = vq.get("value")
    value_unit = vq.get("unit", "")

    # Category
    categories = fhir_json.get("category", [])
    category = "vital-signs"
    if categories:
        cat_codings = categories[0].get("coding", [])
        if cat_codings:
            category = cat_codings[0].get("code", "vital-signs")

    return {
        "fhir_id": fhir_json.get("id", ""),
        "patient_id": patient_id,
        "status": fhir_json.get("status", "final"),
        "category": category,
        "loinc_code": loinc_code,
        "display": display,
        "value_quantity": value_quantity,
        "value_unit": value_unit,
        "effective_datetime": fhir_json.get("effectiveDateTime"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HL7v2 — Internal -> HL7v2 messages
# ═══════════════════════════════════════════════════════════════════════════════


def encounter_to_hl7_adt(encounter: Any, patient: Any = None) -> str:
    """
    Build an HL7v2 ADT^A01 (admit) or ADT^A03 (discharge) message from an
    internal Encounter + Patient.

    If no patient object is provided, the PID segment will contain only the
    patient_id as the MRN.
    """
    enc_status = getattr(encounter, "status", "in-progress")

    # Choose event type based on status
    if enc_status in ("finished", "cancelled"):
        event_code = "A03"
    elif enc_status in ("arrived", "triaged", "in-progress"):
        event_code = "A01"
    else:
        event_code = "A04"  # pre-registration / scheduled

    # Build patient data dict for the PID builder
    patient_data = _build_patient_data_dict(encounter, patient)

    # Map encounter class to HL7 patient class
    enc_type = getattr(encounter, "encounter_type", "office_visit")
    patient_class_map = {
        "office_visit": "O",
        "telehealth": "O",
        "rpm_review": "O",
        "emergency": "E",
        "inpatient": "I",
        "home_health": "O",
    }
    patient_class = patient_class_map.get(enc_type, "O")

    start = getattr(encounter, "started_at", None) or getattr(encounter, "start_time", None)
    provider_id = getattr(encounter, "provider_id", "") or ""
    visit_number = str(getattr(encounter, "id", ""))

    now = datetime.now(timezone.utc)
    control_id = f"HEALTHOS-{_hl7_timestamp(now)}"

    segments = [
        _build_msh(
            message_type=f"ADT{COMPONENT_SEP}A{event_code[1:]}",
            message_control_id=control_id,
            timestamp=now,
        ),
        _build_evn(event_code, now),
        _build_pid(patient_data),
        _build_pv1(
            patient_class=patient_class,
            attending_doctor=str(provider_id),
            admit_datetime=start if isinstance(start, datetime) else None,
            visit_number=visit_number,
        ),
    ]

    # Add reason as DG1 if present
    reason_code = getattr(encounter, "reason_code", None)
    reason_display = (
        getattr(encounter, "reason_display", None)
        or getattr(encounter, "reason", None)
        or ""
    )
    if reason_code:
        dg1_fields = [""] * 7
        dg1_fields[0] = "1"
        dg1_fields[1] = "I10"
        dg1_fields[2] = COMPONENT_SEP.join([reason_code, reason_display, "I10"])
        dg1_fields[3] = reason_display
        dg1_fields[4] = _hl7_timestamp(now)
        dg1_fields[5] = "A"  # Admitting diagnosis
        segments.append(_build_segment("DG1", dg1_fields))

    return SEGMENT_TERMINATOR.join(segments) + SEGMENT_TERMINATOR


def vital_to_hl7_oru(vital: Any, patient: Any = None) -> str:
    """
    Build an HL7v2 ORU^R01 (observation result) message from an internal
    Vital/Observation record.
    """
    patient_data = _build_patient_data_dict_from_vital(vital, patient)

    # Determine observation details
    vital_type = getattr(vital, "vital_type", None)
    loinc_code = getattr(vital, "loinc_code", None)
    display = getattr(vital, "display", None)

    if loinc_code:
        code = loinc_code
        obs_display = display or ""
    elif vital_type and vital_type in _LOINC_MAP:
        code, obs_display, _ = _LOINC_MAP[vital_type]
    else:
        code = "unknown"
        obs_display = vital_type or "Unknown"

    # Extract value
    value_data = getattr(vital, "value", None)
    value_quantity = getattr(vital, "value_quantity", None)

    observations: list[dict[str, Any]] = []

    if isinstance(value_data, dict):
        if "systolic" in value_data and "diastolic" in value_data:
            observations.append({
                "code": "8480-6",
                "display": "Systolic blood pressure",
                "value": value_data["systolic"],
                "units": "mmHg",
            })
            observations.append({
                "code": "8462-4",
                "display": "Diastolic blood pressure",
                "value": value_data["diastolic"],
                "units": "mmHg",
            })
        else:
            val = value_data.get("value", 0)
            unit = getattr(vital, "unit", "") or ""
            observations.append({
                "code": code,
                "display": obs_display,
                "value": val,
                "units": unit,
            })
    elif value_quantity is not None:
        unit = getattr(vital, "value_unit", "") or getattr(vital, "unit", "") or ""
        observations.append({
            "code": code,
            "display": obs_display,
            "value": value_quantity,
            "units": unit,
        })

    patient_data["observations"] = observations
    patient_data["order_code"] = code
    patient_data["order_display"] = obs_display

    # Build using existing hl7v2 utility
    from shared.utils.hl7v2 import build_oru_r01
    return build_oru_r01(patient_data)


def clinical_note_to_hl7_mdm(note: Any, patient: Any = None) -> str:
    """
    Build an HL7v2 MDM^T02 (document notification with content) message
    from an internal ClinicalNote.
    """
    patient_data = _build_patient_data_for_note(note, patient)
    now = datetime.now(timezone.utc)
    control_id = f"HEALTHOS-{_hl7_timestamp(now)}"

    segments = [
        _build_msh(
            message_type=f"MDM{COMPONENT_SEP}T02",
            message_control_id=control_id,
            timestamp=now,
        ),
        _build_evn("T02", now),
        _build_pid(patient_data),
    ]

    # TXA — Transcription Document Header
    note_type = getattr(note, "note_type", "soap")
    doc_type_map = {
        "soap": "SOAP",
        "progress": "PN",
        "procedure": "PROC",
    }
    doc_type = doc_type_map.get(note_type, "CN")

    note_status = getattr(note, "status", "draft")
    completion_map = {
        "draft": "IP",   # In progress
        "pending_review": "IP",
        "signed": "AU",  # Authenticated
        "amended": "LA",  # Legally authenticated
    }
    completion_status = completion_map.get(note_status, "IP")

    author_id = str(getattr(note, "author_id", "")) or ""
    note_id = str(getattr(note, "id", ""))

    txa_fields = [""] * 23
    txa_fields[0] = "1"                     # TXA-1: Set ID
    txa_fields[1] = doc_type                # TXA-2: Document Type
    txa_fields[2] = "TX"                    # TXA-3: Content Type (text)
    txa_fields[3] = _hl7_timestamp(now)     # TXA-4: Activity Date
    txa_fields[4] = author_id               # TXA-5: Primary Activity Provider
    txa_fields[11] = note_id                # TXA-12: Unique Document Number
    txa_fields[16] = completion_status       # TXA-17: Document Completion Status
    segments.append(_build_segment("TXA", txa_fields))

    # OBX — Embed the note content
    sections: list[str] = []
    for section in ("subjective", "objective", "assessment", "plan"):
        text = getattr(note, section, None)
        if text:
            sections.append(f"{section.upper()}: {text}")
    content = "\\n".join(sections) if sections else ""

    obx_fields = [""] * 15
    obx_fields[0] = "1"
    obx_fields[1] = "TX"                    # Value type: text
    obx_fields[2] = COMPONENT_SEP.join([doc_type, f"Clinical Note - {note_type.title()}", "L"])
    obx_fields[4] = content                  # OBX-5: Observation Value
    obx_fields[10] = "F"                     # OBX-11: Result Status (Final)
    segments.append(_build_segment("OBX", obx_fields))

    return SEGMENT_TERMINATOR.join(segments) + SEGMENT_TERMINATOR


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _ensure_iso(dt: Any) -> str:
    """Ensure a datetime is returned as an ISO 8601 string."""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)


def _build_patient_data_dict(encounter: Any, patient: Any = None) -> dict[str, Any]:
    """Extract patient data fields needed by the HL7v2 PID builder."""
    if patient is not None:
        return {
            "patient_id": str(getattr(patient, "id", "")),
            "mrn": getattr(patient, "mrn", "") or "",
            "first_name": getattr(patient, "first_name", ""),
            "last_name": getattr(patient, "last_name", ""),
            "date_of_birth": getattr(patient, "date_of_birth", None),
            "sex": getattr(patient, "sex", "unknown"),
            "phone": getattr(patient, "phone", "") or "",
            "address_line1": getattr(patient, "address_line1", "") or "",
            "city": getattr(patient, "city", "") or "",
            "state": getattr(patient, "state", "") or "",
            "postal_code": getattr(patient, "postal_code", "") or "",
            "country": getattr(patient, "country", "US"),
        }
    # Fallback: use encounter's patient_id as MRN
    return {
        "patient_id": str(getattr(encounter, "patient_id", "")),
        "mrn": str(getattr(encounter, "patient_id", "")),
        "first_name": "",
        "last_name": "",
        "sex": "U",
    }


def _build_patient_data_dict_from_vital(vital: Any, patient: Any = None) -> dict[str, Any]:
    """Extract patient data fields from a vital record for PID building."""
    if patient is not None:
        return _build_patient_data_dict(vital, patient)
    return {
        "patient_id": str(getattr(vital, "patient_id", "")),
        "mrn": str(getattr(vital, "patient_id", "")),
        "first_name": "",
        "last_name": "",
        "sex": "U",
    }


def _build_patient_data_for_note(note: Any, patient: Any = None) -> dict[str, Any]:
    """Extract patient data fields from a clinical note for PID building."""
    if patient is not None:
        return _build_patient_data_dict(note, patient)
    # ClinicalNote doesn't have patient_id directly; use encounter_id as fallback
    return {
        "patient_id": str(getattr(note, "encounter_id", "")),
        "mrn": str(getattr(note, "encounter_id", "")),
        "first_name": "",
        "last_name": "",
        "sex": "U",
    }
