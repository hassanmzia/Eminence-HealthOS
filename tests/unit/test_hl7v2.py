"""
Unit tests for HL7 v2.x message parser and builder.
"""

from __future__ import annotations

import pytest

from shared.utils.hl7v2 import (
    build_ack,
    build_adt_a01,
    build_oru_r01,
    parse_hl7_message,
)


# ── Parser Tests ─────────────────────────────────────────────────────────────


class TestParseHL7Message:
    def test_parse_msh_segment(self):
        msg = (
            "MSH|^~\\&|HealthOS|CLINIC|LAB|HOSPITAL|20260314120000||ADT^A01|MSG001|P|2.5.1\r"
            "PID|1||MRN-001^^^HealthOS||Doe^Jane||19850615|F|||123 Main St^^Springfield^IL^62701\r"
        )
        result = parse_hl7_message(msg)
        assert "MSH" in result
        assert result["MSH"]["sending_application"] == "HealthOS"
        assert result["MSH"]["message_type"] == "ADT^A01"
        assert result["MSH"]["message_control_id"] == "MSG001"

    def test_parse_pid_segment(self):
        msg = (
            "MSH|^~\\&|HealthOS|CLINIC|LAB|HOSPITAL|20260314120000||ADT^A01|MSG001|P|2.5.1\r"
            "PID|1||MRN-001^^^HealthOS||Doe^Jane^Q||19850615|F|||123 Main St^^Springfield^IL^62701\r"
        )
        result = parse_hl7_message(msg)
        assert "PID" in result
        pid = result["PID"]
        assert pid["patient_id"] == "MRN-001"
        assert pid["family_name"] == "Doe"
        assert pid["given_name"] == "Jane"

    def test_parse_obx_segment(self):
        msg = (
            "MSH|^~\\&|LAB|HOSPITAL|HealthOS|CLINIC|20260314120000||ORU^R01|MSG002|P|2.5.1\r"
            "OBX|1|NM|8480-6^Systolic BP^LN||130|mmHg|90-140|N|||F\r"
        )
        result = parse_hl7_message(msg)
        assert "OBX" in result
        obx = result["OBX"]
        if isinstance(obx, list):
            obx = obx[0]
        assert obx["value"] == "130"

    def test_parse_empty_message(self):
        result = parse_hl7_message("")
        assert result == {} or "MSH" not in result


# ── ADT^A01 Builder Tests ────────────────────────────────────────────────────


class TestBuildAdtA01:
    def test_builds_valid_adt_message(self):
        patient = {
            "mrn": "MRN-001",
            "family_name": "Doe",
            "given_name": "Jane",
            "date_of_birth": "19850615",
            "sex": "F",
            "address": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
        }
        msg = build_adt_a01(patient)
        assert "MSH|" in msg
        assert "ADT^A01" in msg
        assert "PID|" in msg
        assert "MRN-001" in msg
        assert "Doe^Jane" in msg

    def test_minimal_patient_data(self):
        patient = {"mrn": "MRN-002", "family_name": "Smith", "given_name": "John"}
        msg = build_adt_a01(patient)
        assert "MSH|" in msg
        assert "Smith^John" in msg


# ── ORU^R01 Builder Tests ────────────────────────────────────────────────────


class TestBuildOruR01:
    def test_builds_valid_oru_message(self):
        observation = {
            "loinc_code": "8480-6",
            "display": "Systolic BP",
            "value": "130",
            "unit": "mmHg",
            "reference_range": "90-140",
            "interpretation": "N",
            "patient_mrn": "MRN-001",
            "patient_name": "Doe^Jane",
        }
        msg = build_oru_r01(observation)
        assert "MSH|" in msg
        assert "ORU^R01" in msg
        assert "OBX|" in msg
        assert "8480-6" in msg
        assert "130" in msg


# ── ACK Builder Tests ────────────────────────────────────────────────────────


class TestBuildAck:
    def test_builds_ack_aa(self):
        msg = build_ack("MSG001", "AA")
        assert "MSH|" in msg
        assert "ACK" in msg
        assert "AA" in msg
        assert "MSG001" in msg

    def test_builds_ack_ae(self):
        msg = build_ack("MSG002", "AE")
        assert "AE" in msg
