"""
FHIR R4 resource mapping utilities.

Converts between HealthOS internal models and FHIR R4 JSON representations.
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID


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
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": obs.category,
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
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
            "system": "http://unitsofmeasure.org",
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
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
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
