"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { fetchMyProfile, type UserProfile } from "@/lib/api";

// Mirror backend role/permission definitions
export type Role = "admin" | "clinician" | "care_manager" | "nurse" | "office_admin" | "patient" | "lab_tech" | "pharmacist" | "billing" | "read_only";

export type Permission =
  | "patient:read" | "patient:write" | "patient:delete"
  | "vitals:read" | "vitals:write"
  | "alerts:read" | "alerts:manage" | "alerts:acknowledge"
  | "encounters:read" | "encounters:write"
  | "care_plans:read" | "care_plans:write"
  | "agents:view" | "agents:manage"
  | "analytics:read" | "analytics:export"
  | "org:manage" | "users:manage" | "audit:read"
  | "diagnosis:read" | "diagnosis:write"
  | "prescription:read" | "prescription:write"
  | "allergy:read" | "allergy:write"
  | "lab:read" | "lab:write"
  | "messages:read" | "messages:write" | "notifications:read"
  | "billing:read" | "billing:write" | "billing:manage"
  | "devices:read" | "devices:write" | "devices:manage"
  | "provider:read" | "provider:write"
  | "hospital:read" | "hospital:manage";

// All possible permissions for the "all" set
const ALL_PERMISSIONS: Permission[] = [
  "patient:read", "patient:write", "patient:delete",
  "vitals:read", "vitals:write",
  "alerts:read", "alerts:manage", "alerts:acknowledge",
  "encounters:read", "encounters:write",
  "care_plans:read", "care_plans:write",
  "agents:view", "agents:manage",
  "analytics:read", "analytics:export",
  "org:manage", "users:manage", "audit:read",
  "diagnosis:read", "diagnosis:write",
  "prescription:read", "prescription:write",
  "allergy:read", "allergy:write",
  "lab:read", "lab:write",
  "messages:read", "messages:write", "notifications:read",
  "billing:read", "billing:write", "billing:manage",
  "devices:read", "devices:write", "devices:manage",
  "provider:read", "provider:write",
  "hospital:read", "hospital:manage",
];

// Role → Permission mapping (mirrors backend rbac.py exactly)
const ROLE_PERMISSIONS: Record<Role, Set<Permission>> = {
  admin: new Set(ALL_PERMISSIONS),
  clinician: new Set([
    "patient:read", "patient:write", "vitals:read", "vitals:write",
    "alerts:read", "alerts:manage", "alerts:acknowledge",
    "encounters:read", "encounters:write",
    "care_plans:read", "care_plans:write",
    "agents:view", "agents:manage", "analytics:read",
    "diagnosis:read", "diagnosis:write",
    "prescription:read", "prescription:write",
    "allergy:read", "allergy:write", "lab:read", "lab:write",
    "messages:read", "messages:write", "notifications:read",
    "billing:read", "devices:read", "devices:write",
    "provider:read", "hospital:read",
  ]),
  care_manager: new Set([
    "patient:read", "patient:write", "vitals:read",
    "alerts:read", "alerts:acknowledge",
    "encounters:read",
    "care_plans:read", "care_plans:write",
    "agents:view", "analytics:read",
    "diagnosis:read", "prescription:read",
    "allergy:read", "lab:read",
    "messages:read", "messages:write", "notifications:read",
    "billing:read", "devices:read",
    "provider:read", "hospital:read",
  ]),
  nurse: new Set([
    "patient:read", "vitals:read", "vitals:write",
    "alerts:read", "alerts:acknowledge",
    "encounters:read", "agents:view",
    "diagnosis:read", "prescription:read",
    "allergy:read", "allergy:write", "lab:read",
    "messages:read", "messages:write", "notifications:read",
    "devices:read", "devices:write",
    "provider:read", "hospital:read",
  ]),
  office_admin: new Set([
    "patient:read", "patient:write", "vitals:read",
    "alerts:read", "encounters:read", "encounters:write",
    "agents:view",
    "diagnosis:read", "prescription:read",
    "allergy:read", "lab:read",
    "messages:read", "messages:write", "notifications:read",
    "billing:read", "billing:write", "billing:manage",
    "devices:read", "devices:manage",
    "provider:read", "provider:write",
    "hospital:read", "hospital:manage",
    "users:manage", "audit:read",
  ]),
  patient: new Set([
    "vitals:read", "alerts:read",
    "encounters:read", "care_plans:read",
    "diagnosis:read", "prescription:read",
    "allergy:read", "lab:read",
    "messages:read", "messages:write", "notifications:read",
    "billing:read", "devices:read", "provider:read",
  ]),
  lab_tech: new Set([
    "patient:read", "vitals:read",
    "alerts:read",
    "lab:read", "lab:write",
    "diagnosis:read",
    "messages:read", "messages:write", "notifications:read",
    "devices:read",
    "provider:read", "hospital:read",
  ]),
  pharmacist: new Set([
    "patient:read", "vitals:read",
    "alerts:read",
    "prescription:read", "prescription:write",
    "allergy:read", "lab:read",
    "diagnosis:read",
    "messages:read", "messages:write", "notifications:read",
    "devices:read",
    "provider:read", "hospital:read",
  ]),
  billing: new Set([
    "patient:read",
    "encounters:read",
    "billing:read", "billing:write", "billing:manage",
    "messages:read", "messages:write", "notifications:read",
    "analytics:read",
    "provider:read", "hospital:read",
  ]),
  read_only: new Set([
    "patient:read", "vitals:read",
    "alerts:read",
    "encounters:read", "care_plans:read",
    "diagnosis:read", "prescription:read",
    "allergy:read", "lab:read",
    "billing:read",
    "notifications:read",
    "analytics:read",
    "devices:read",
    "provider:read", "hospital:read",
  ]),
};

// Route → allowed roles mapping for frontend route guards
export const ROUTE_ACCESS: Record<string, Role[]> = {
  "/dashboard": ["admin", "clinician", "care_manager", "nurse", "office_admin", "lab_tech", "pharmacist", "billing", "read_only"],
  "/clinical-workspace": ["admin", "clinician", "care_manager", "nurse"],
  "/patients": ["admin", "clinician", "care_manager", "nurse", "office_admin", "lab_tech", "pharmacist", "billing", "read_only"],
  "/alerts": ["admin", "clinician", "care_manager", "nurse", "office_admin", "lab_tech", "pharmacist", "billing", "read_only"],
  "/messaging": ["admin", "clinician", "care_manager", "nurse", "office_admin", "patient", "lab_tech", "pharmacist", "billing"],
  "/rpm": ["admin", "clinician", "care_manager", "nurse"],
  "/telehealth": ["admin", "clinician", "care_manager", "nurse"],
  "/ambient-ai": ["admin", "clinician"],
  "/pharmacy": ["admin", "clinician", "care_manager", "nurse", "pharmacist", "read_only"],
  "/labs": ["admin", "clinician", "care_manager", "nurse", "lab_tech", "pharmacist", "read_only"],
  "/imaging": ["admin", "clinician", "lab_tech"],
  "/mental-health": ["admin", "clinician", "care_manager", "nurse"],
  "/sdoh": ["admin", "clinician", "care_manager", "nurse"],
  "/patient-timeline": ["admin", "clinician", "care_manager", "nurse"],
  "/clinical-assessment": ["admin", "clinician"],
  "/clinical-intelligence": ["admin", "clinician", "care_manager"],
  "/knowledge-graph": ["admin", "clinician", "care_manager"],
  "/ml-models": ["admin", "clinician"],
  "/agents": ["admin", "clinician", "care_manager"],
  "/digital-twin": ["admin", "clinician"],
  "/ms-risk-screening": ["admin", "clinician", "care_manager"],
  "/fairness": ["admin"],
  "/ai-explainability": ["admin", "clinician", "care_manager"],
  "/operations": ["admin", "office_admin", "clinician"],
  "/rcm": ["admin", "office_admin", "billing"],
  "/analytics": ["admin", "office_admin", "clinician", "billing", "read_only"],
  "/compliance": ["admin", "office_admin", "billing", "read_only"],
  "/ehr-connect": ["admin"],
  "/audit-log": ["admin", "office_admin", "read_only"],
  "/admin": ["admin"],
  "/research-genomics": ["admin", "clinician"],
  "/patient-engagement": ["admin", "clinician"],
  "/marketplace": ["admin", "clinician"],
  "/simulator": ["admin", "clinician"],
  "/profile": ["admin", "clinician", "care_manager", "nurse", "office_admin", "patient", "lab_tech", "pharmacist", "billing", "read_only"],
  "/patient-portal": ["patient"],
};

/**
 * Check if a role is allowed to access a given pathname.
 * Only allows access if the route is explicitly listed and the role is included.
 * Unlisted routes default to deny for safety.
 */
export function canAccessRoute(pathname: string, role: Role | null): boolean {
  if (!role) return false;
  // Find the most specific matching route prefix
  const matchingRoute = Object.keys(ROUTE_ACCESS)
    .filter((r) => pathname.startsWith(r))
    .sort((a, b) => b.length - a.length)[0];
  if (!matchingRoute) return false; // no rule = deny by default
  return ROUTE_ACCESS[matchingRoute].includes(role);
}

interface AuthContextValue {
  user: UserProfile | null;
  role: Role | null;
  loading: boolean;
  permissions: Set<Permission>;
  hasPermission: (perm: Permission) => boolean;
  hasAnyPermission: (...perms: Permission[]) => boolean;
  hasRole: (...roles: Role[]) => boolean;
  isAdmin: boolean;
  isClinician: boolean;
  isNurse: boolean;
  isPatient: boolean;
  isOfficeAdmin: boolean;
  isCareManager: boolean;
  isLabTech: boolean;
  isPharmacist: boolean;
  isBilling: boolean;
  isReadOnly: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const role = (user?.role as Role) ?? null;
  const permissions = role ? (ROLE_PERMISSIONS[role] ?? new Set<Permission>()) : new Set<Permission>();

  const refreshUser = useCallback(async () => {
    try {
      const profile = await fetchMyProfile();
      setUser(profile);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (token) {
      refreshUser();
    } else {
      setLoading(false);
    }
  }, [refreshUser]);

  const hasPermission = useCallback((perm: Permission) => permissions.has(perm), [permissions]);
  const hasAnyPermission = useCallback((...perms: Permission[]) => perms.some((p) => permissions.has(p)), [permissions]);
  const hasRole = useCallback((...roles: Role[]) => role !== null && roles.includes(role), [role]);

  const value: AuthContextValue = {
    user,
    role,
    loading,
    permissions,
    hasPermission,
    hasAnyPermission,
    hasRole,
    isAdmin: role === "admin",
    isClinician: role === "clinician",
    isNurse: role === "nurse",
    isPatient: role === "patient",
    isOfficeAdmin: role === "office_admin",
    isCareManager: role === "care_manager",
    isLabTech: role === "lab_tech",
    isPharmacist: role === "pharmacist",
    isBilling: role === "billing",
    isReadOnly: role === "read_only",
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
