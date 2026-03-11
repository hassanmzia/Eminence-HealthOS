"""
Eminence HealthOS — Security Unit Tests
"""

from __future__ import annotations

import uuid

import pytest

from platform.security.auth import (
    create_access_token,
    create_tokens,
    decode_token,
    hash_password,
    verify_password,
)
from platform.security.phi_filter import PHIFilter
from platform.security.rbac import Permission, Role, get_permissions, has_permission


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH TESTS
# ═══════════════════════════════════════════════════════════════════════════════


def test_password_hashing():
    password = "secure_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_jwt_creation_and_decode():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    token = create_access_token(user_id, org_id, "clinician")

    payload = decode_token(token)
    assert payload.sub == str(user_id)
    assert payload.org_id == str(org_id)
    assert payload.role == "clinician"


def test_token_pair_creation():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    tokens = create_tokens(user_id, org_id, "admin")

    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"
    assert tokens.expires_in > 0


def test_invalid_token_decode():
    with pytest.raises(ValueError, match="Invalid token"):
        decode_token("invalid.token.here")


# ═══════════════════════════════════════════════════════════════════════════════
# RBAC TESTS
# ═══════════════════════════════════════════════════════════════════════════════


def test_admin_has_all_permissions():
    for perm in Permission:
        assert has_permission("admin", perm)


def test_clinician_permissions():
    assert has_permission("clinician", Permission.PATIENT_READ)
    assert has_permission("clinician", Permission.PATIENT_WRITE)
    assert has_permission("clinician", Permission.ENCOUNTERS_WRITE)
    assert not has_permission("clinician", Permission.ORG_MANAGE)
    assert not has_permission("clinician", Permission.USERS_MANAGE)


def test_patient_permissions():
    assert has_permission("patient", Permission.VITALS_READ)
    assert has_permission("patient", Permission.CARE_PLANS_READ)
    assert not has_permission("patient", Permission.PATIENT_WRITE)
    assert not has_permission("patient", Permission.AGENTS_MANAGE)


def test_nurse_permissions():
    assert has_permission("nurse", Permission.VITALS_READ)
    assert has_permission("nurse", Permission.VITALS_WRITE)
    assert has_permission("nurse", Permission.ALERTS_ACKNOWLEDGE)
    assert not has_permission("nurse", Permission.ENCOUNTERS_WRITE)


def test_invalid_role():
    assert not has_permission("invalid_role", Permission.PATIENT_READ)
    assert get_permissions("invalid_role") == set()


def test_get_permissions():
    perms = get_permissions("patient")
    assert Permission.VITALS_READ in perms
    assert Permission.ORG_MANAGE not in perms


# ═══════════════════════════════════════════════════════════════════════════════
# PHI FILTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


def test_phi_detection_ssn():
    f = PHIFilter()
    text = "Patient SSN is 123-45-6789"
    assert f.has_phi(text)
    detections = f.scan_text(text)
    assert any(d["type"] == "ssn" for d in detections)


def test_phi_detection_phone():
    f = PHIFilter()
    text = "Call the patient at (555) 123-4567"
    assert f.has_phi(text)


def test_phi_detection_email():
    f = PHIFilter()
    text = "Email: patient@hospital.com"
    assert f.has_phi(text)


def test_phi_redaction():
    f = PHIFilter()
    text = "Patient SSN: 123-45-6789, phone: (555) 123-4567"
    redacted = f.redact_text(text)
    assert "123-45-6789" not in redacted
    assert "[REDACTED-SSN]" in redacted


def test_phi_dict_redaction():
    f = PHIFilter()
    data = {
        "name": "John Doe",
        "ssn": "123-45-6789",
        "notes": "Patient called from (555) 123-4567",
        "nested": {
            "email": "Contact: john@example.com for follow-up"
        },
    }
    redacted = f.redact_dict(data)
    assert redacted["ssn"] == "[REDACTED]"
    assert "(555) 123-4567" not in redacted["notes"]


def test_no_phi():
    f = PHIFilter()
    text = "Blood pressure is 120/80 mmHg. Heart rate stable at 72 bpm."
    assert not f.has_phi(text)
