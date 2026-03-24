"""
Eminence HealthOS — Role-Based Access Control
Defines roles, permissions, and access policies for the platform.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class Role(str, Enum):
    ADMIN = "admin"
    CLINICIAN = "clinician"
    CARE_MANAGER = "care_manager"
    NURSE = "nurse"
    OFFICE_ADMIN = "office_admin"
    SYSTEM = "system"  # For agent-to-agent and internal operations


class Permission(str, Enum):
    # Patient data
    PATIENT_READ = "patient:read"
    PATIENT_WRITE = "patient:write"
    PATIENT_DELETE = "patient:delete"

    # Vitals / RPM
    VITALS_READ = "vitals:read"
    VITALS_WRITE = "vitals:write"

    # Alerts
    ALERTS_READ = "alerts:read"
    ALERTS_MANAGE = "alerts:manage"
    ALERTS_ACKNOWLEDGE = "alerts:acknowledge"

    # Encounters
    ENCOUNTERS_READ = "encounters:read"
    ENCOUNTERS_WRITE = "encounters:write"

    # Care plans
    CARE_PLANS_READ = "care_plans:read"
    CARE_PLANS_WRITE = "care_plans:write"

    # Agents
    AGENTS_VIEW = "agents:view"
    AGENTS_MANAGE = "agents:manage"

    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Admin
    ORG_MANAGE = "org:manage"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"

    # Clinical data (Phase 2)
    DIAGNOSIS_READ = "diagnosis:read"
    DIAGNOSIS_WRITE = "diagnosis:write"
    PRESCRIPTION_READ = "prescription:read"
    PRESCRIPTION_WRITE = "prescription:write"
    ALLERGY_READ = "allergy:read"
    ALLERGY_WRITE = "allergy:write"
    LAB_READ = "lab:read"
    LAB_WRITE = "lab:write"

    # Messaging (Phase 4)
    MESSAGES_READ = "messages:read"
    MESSAGES_WRITE = "messages:write"
    NOTIFICATIONS_READ = "notifications:read"

    # Billing (Phase 5)
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_MANAGE = "billing:manage"

    # IoT / Devices (Phase 3)
    DEVICES_READ = "devices:read"
    DEVICES_WRITE = "devices:write"
    DEVICES_MANAGE = "devices:manage"

    # Provider management
    PROVIDER_READ = "provider:read"
    PROVIDER_WRITE = "provider:write"

    # Hospital / Department
    HOSPITAL_READ = "hospital:read"
    HOSPITAL_MANAGE = "hospital:manage"


# Role → Permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),  # All permissions
    Role.CLINICIAN: {
        Permission.PATIENT_READ,
        Permission.PATIENT_WRITE,
        Permission.VITALS_READ,
        Permission.VITALS_WRITE,
        Permission.ALERTS_READ,
        Permission.ALERTS_MANAGE,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.ENCOUNTERS_READ,
        Permission.ENCOUNTERS_WRITE,
        Permission.CARE_PLANS_READ,
        Permission.CARE_PLANS_WRITE,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_MANAGE,
        Permission.ANALYTICS_READ,
        Permission.DIAGNOSIS_READ,
        Permission.DIAGNOSIS_WRITE,
        Permission.PRESCRIPTION_READ,
        Permission.PRESCRIPTION_WRITE,
        Permission.ALLERGY_READ,
        Permission.ALLERGY_WRITE,
        Permission.LAB_READ,
        Permission.LAB_WRITE,
        Permission.MESSAGES_READ,
        Permission.MESSAGES_WRITE,
        Permission.NOTIFICATIONS_READ,
        Permission.BILLING_READ,
        Permission.DEVICES_READ,
        Permission.DEVICES_WRITE,
        Permission.PROVIDER_READ,
        Permission.HOSPITAL_READ,
    },
    Role.CARE_MANAGER: {
        Permission.PATIENT_READ,
        Permission.PATIENT_WRITE,
        Permission.VITALS_READ,
        Permission.ALERTS_READ,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.ENCOUNTERS_READ,
        Permission.CARE_PLANS_READ,
        Permission.CARE_PLANS_WRITE,
        Permission.AGENTS_VIEW,
        Permission.ANALYTICS_READ,
        Permission.DIAGNOSIS_READ,
        Permission.PRESCRIPTION_READ,
        Permission.ALLERGY_READ,
        Permission.LAB_READ,
        Permission.MESSAGES_READ,
        Permission.MESSAGES_WRITE,
        Permission.NOTIFICATIONS_READ,
        Permission.BILLING_READ,
        Permission.DEVICES_READ,
        Permission.PROVIDER_READ,
        Permission.HOSPITAL_READ,
    },
    Role.NURSE: {
        Permission.PATIENT_READ,
        Permission.VITALS_READ,
        Permission.VITALS_WRITE,
        Permission.ALERTS_READ,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.ENCOUNTERS_READ,
        Permission.AGENTS_VIEW,
        Permission.DIAGNOSIS_READ,
        Permission.PRESCRIPTION_READ,
        Permission.ALLERGY_READ,
        Permission.ALLERGY_WRITE,
        Permission.LAB_READ,
        Permission.MESSAGES_READ,
        Permission.MESSAGES_WRITE,
        Permission.NOTIFICATIONS_READ,
        Permission.DEVICES_READ,
        Permission.DEVICES_WRITE,
        Permission.PROVIDER_READ,
        Permission.HOSPITAL_READ,
    },
    Role.OFFICE_ADMIN: {
        Permission.PATIENT_READ,
        Permission.PATIENT_WRITE,
        Permission.VITALS_READ,
        Permission.ALERTS_READ,
        Permission.ENCOUNTERS_READ,
        Permission.ENCOUNTERS_WRITE,
        Permission.AGENTS_VIEW,
        Permission.DIAGNOSIS_READ,
        Permission.PRESCRIPTION_READ,
        Permission.ALLERGY_READ,
        Permission.LAB_READ,
        Permission.MESSAGES_READ,
        Permission.MESSAGES_WRITE,
        Permission.NOTIFICATIONS_READ,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.BILLING_MANAGE,
        Permission.DEVICES_READ,
        Permission.DEVICES_MANAGE,
        Permission.PROVIDER_READ,
        Permission.PROVIDER_WRITE,
        Permission.HOSPITAL_READ,
        Permission.HOSPITAL_MANAGE,
        Permission.USERS_MANAGE,
        Permission.AUDIT_READ,
    },
    Role.SYSTEM: set(Permission),  # Internal system has full access
}


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    try:
        r = Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(r, set())


def get_permissions(role: str) -> set[Permission]:
    """Get all permissions for a role."""
    try:
        r = Role(role)
    except ValueError:
        return set()
    return ROLE_PERMISSIONS.get(r, set())
