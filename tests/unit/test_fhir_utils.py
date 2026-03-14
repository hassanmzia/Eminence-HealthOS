"""
Unit tests for FHIR R4 resource mapping utilities.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from shared.utils.fhir import (
    from_fhir_patient,
    to_fhir_observation,
    to_fhir_patient,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_patient(**overrides):
    defaults = {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "mrn": "MRN-001",
        "first_name": "Jane",
        "last_name": "Doe",
        "sex": "female",
        "date_of_birth": date(1985, 6, 15),
        "phone": "555-0100",
        "email": "jane.doe@example.com",
        "is_deleted": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _mock_observation(**overrides):
    defaults = {
        "id": "obs-001",
        "status": "final",
        "category": "vital-signs",
        "loinc_code": "8480-6",
        "display": "Systolic blood pressure",
        "patient_id": "patient-001",
        "value_quantity": 130.0,
        "value_unit": "mmHg",
        "value_string": None,
        "effective_datetime": datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc),
        "reference_low": 90.0,
        "reference_high": 140.0,
        "interpretation": "N",
        "components": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── to_fhir_patient ──────────────────────────────────────────────────────────


class TestToFhirPatient:
    def test_basic_fields(self):
        p = _mock_patient()
        fhir = to_fhir_patient(p)
        assert fhir["resourceType"] == "Patient"
        assert fhir["gender"] == "female"
        assert fhir["birthDate"] == "1985-06-15"
        assert fhir["active"] is True

    def test_name_structure(self):
        p = _mock_patient()
        fhir = to_fhir_patient(p)
        assert fhir["name"][0]["family"] == "Doe"
        assert fhir["name"][0]["given"] == ["Jane"]

    def test_identifiers_include_mrn(self):
        p = _mock_patient(mrn="MRN-XYZ")
        fhir = to_fhir_patient(p)
        ids = fhir["identifier"]
        assert any(i["value"] == "MRN-XYZ" for i in ids)

    def test_telecom_phone_and_email(self):
        p = _mock_patient(phone="555-1234", email="test@example.com")
        fhir = to_fhir_patient(p)
        telecoms = fhir["telecom"]
        phones = [t for t in telecoms if t["system"] == "phone"]
        emails = [t for t in telecoms if t["system"] == "email"]
        assert len(phones) == 1
        assert phones[0]["value"] == "555-1234"
        assert len(emails) == 1

    def test_deleted_patient_inactive(self):
        p = _mock_patient(is_deleted=True)
        fhir = to_fhir_patient(p)
        assert fhir["active"] is False


# ── to_fhir_observation ──────────────────────────────────────────────────────


class TestToFhirObservation:
    def test_basic_fields(self):
        obs = _mock_observation()
        fhir = to_fhir_observation(obs)
        assert fhir["resourceType"] == "Observation"
        assert fhir["status"] == "final"
        assert fhir["subject"]["reference"] == "Patient/patient-001"

    def test_loinc_coding(self):
        obs = _mock_observation(loinc_code="8480-6", display="Systolic BP")
        fhir = to_fhir_observation(obs)
        coding = fhir["code"]["coding"][0]
        assert coding["system"] == "http://loinc.org"
        assert coding["code"] == "8480-6"

    def test_value_quantity(self):
        obs = _mock_observation(value_quantity=130.0, value_unit="mmHg")
        fhir = to_fhir_observation(obs)
        assert fhir["valueQuantity"]["value"] == 130.0
        assert fhir["valueQuantity"]["unit"] == "mmHg"

    def test_value_string_fallback(self):
        obs = _mock_observation(value_quantity=None, value_string="Positive")
        fhir = to_fhir_observation(obs)
        assert "valueQuantity" not in fhir
        assert fhir["valueString"] == "Positive"

    def test_reference_range(self):
        obs = _mock_observation(reference_low=90.0, reference_high=140.0)
        fhir = to_fhir_observation(obs)
        ref = fhir["referenceRange"][0]
        assert ref["low"]["value"] == 90.0
        assert ref["high"]["value"] == 140.0

    def test_interpretation_code(self):
        obs = _mock_observation(interpretation="HH")
        fhir = to_fhir_observation(obs)
        interp = fhir["interpretation"][0]["coding"][0]
        assert interp["code"] == "HH"
        assert interp["display"] == "Critical high"

    def test_category_coding(self):
        obs = _mock_observation(category="vital-signs")
        fhir = to_fhir_observation(obs)
        cat = fhir["category"][0]["coding"][0]
        assert cat["code"] == "vital-signs"


# ── from_fhir_patient ────────────────────────────────────────────────────────


class TestFromFhirPatient:
    def test_extracts_name(self):
        fhir = {
            "name": [{"family": "Smith", "given": ["John", "Q"]}],
            "gender": "male",
            "birthDate": "1990-01-01",
        }
        result = from_fhir_patient(fhir)
        assert result["last_name"] == "Smith"
        assert result["first_name"] == "John"

    def test_extracts_mrn(self):
        fhir = {
            "identifier": [
                {"system": "urn:healthos:mrn", "value": "MRN-99"},
                {"system": "other", "value": "X"},
            ],
            "name": [],
        }
        result = from_fhir_patient(fhir)
        assert result["mrn"] == "MRN-99"

    def test_extracts_telecom(self):
        fhir = {
            "telecom": [
                {"system": "phone", "value": "555-9999"},
                {"system": "email", "value": "a@b.com"},
            ],
            "name": [],
        }
        result = from_fhir_patient(fhir)
        assert result["phone"] == "555-9999"
        assert result["email"] == "a@b.com"

    def test_extracts_address(self):
        fhir = {
            "address": [
                {
                    "line": ["123 Main St"],
                    "city": "Springfield",
                    "state": "IL",
                    "postalCode": "62701",
                }
            ],
            "name": [],
        }
        result = from_fhir_patient(fhir)
        assert result["address_line1"] == "123 Main St"
        assert result["city"] == "Springfield"
        assert result["state"] == "IL"

    def test_empty_fhir_resource(self):
        result = from_fhir_patient({"name": []})
        assert result.get("sex") == "unknown"
