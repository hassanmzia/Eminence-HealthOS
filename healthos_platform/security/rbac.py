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
    PATIENT = "patient"
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
        Permission.ANALYTICS_READ,
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
    },
    Role.NURSE: {
        Permission.PATIENT_READ,
        Permission.VITALS_READ,
        Permission.VITALS_WRITE,
        Permission.ALERTS_READ,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.ENCOUNTERS_READ,
        Permission.AGENTS_VIEW,
    },
    Role.PATIENT: {
        Permission.VITALS_READ,
        Permission.ALERTS_READ,
        Permission.ENCOUNTERS_READ,
        Permission.CARE_PLANS_READ,
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
