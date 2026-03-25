"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import {
  fetchHospitals,
  fetchDepartments,
  fetchProviders,
  fetchNurses,
  fetchOfficeAdmins,
  fetchAuthConfigs,
  fetchSessions,
  fetchAdminUsers,
  createAdminUser,
  createProvider,
  createNurse,
  createOfficeAdmin,
  updateAdminUser,
  deactivateAdminUser,
  promoteSelfToAdmin,
  unlockAccount,
  getUserRole,
  type HospitalResponse,
  type DepartmentResponse,
  type ProviderProfileResponse,
  type AuthConfigResponse,
  type SessionResponse,
  type AdminUserResponse,
} from "@/lib/platform-api";
import { fetchMyProfile, type UserProfile } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface User {
  id: number;
  backendId?: string; // UUID from the backend for API calls
  name: string;
  email: string;
  role: string;
  department: string;
  hospitalId?: string;
  hospitalName?: string;
  departmentId?: string;
  status: "active" | "inactive" | "locked";
  lastLogin: string;
  avatar?: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
  color: string;
  userCount: number;
  permissions: string[];
}

interface Permission {
  category: string;
  actions: string[];
}

interface AuditEntry {
  id: number;
  timestamp: string;
  user: string;
  action: string;
  target: string;
  ip: string;
}

/* ------------------------------------------------------------------ */
/*  Demo data                                                          */
/* ------------------------------------------------------------------ */
const INITIAL_USERS: User[] = [
  { id: 1, name: "Dr. Sarah Chen", email: "s.chen@eminence.health", role: "Physician", department: "Cardiology", status: "active", lastLogin: "2026-03-15 08:12" },
  { id: 2, name: "James Rodriguez", email: "j.rodriguez@eminence.health", role: "Super Admin", department: "IT", status: "active", lastLogin: "2026-03-15 09:45" },
  { id: 3, name: "Maria Gonzalez", email: "m.gonzalez@eminence.health", role: "Nurse", department: "Emergency", status: "active", lastLogin: "2026-03-14 22:30" },
  { id: 4, name: "Dr. Alan Patel", email: "a.patel@eminence.health", role: "Physician", department: "Neurology", status: "active", lastLogin: "2026-03-15 07:55" },
  { id: 5, name: "Linda Park", email: "l.park@eminence.health", role: "Lab Tech", department: "Pathology", status: "active", lastLogin: "2026-03-14 16:20" },
  { id: 6, name: "Robert Kim", email: "r.kim@eminence.health", role: "Pharmacist", department: "Pharmacy", status: "active", lastLogin: "2026-03-15 10:05" },
  { id: 7, name: "Emily Watson", email: "e.watson@eminence.health", role: "Billing", department: "Finance", status: "inactive", lastLogin: "2026-02-28 14:00" },
  { id: 8, name: "Dr. Fatima Al-Rashid", email: "f.alrashid@eminence.health", role: "Physician", department: "Oncology", status: "active", lastLogin: "2026-03-15 06:30" },
  { id: 9, name: "Tom Bradley", email: "t.bradley@eminence.health", role: "Admin", department: "IT", status: "active", lastLogin: "2026-03-14 18:45" },
  { id: 10, name: "Nurse Jackie Peyton", email: "j.peyton@eminence.health", role: "Nurse", department: "ICU", status: "locked", lastLogin: "2026-03-10 11:15" },
  { id: 11, name: "David Okafor", email: "d.okafor@eminence.health", role: "Read Only", department: "Compliance", status: "active", lastLogin: "2026-03-15 09:00" },
  { id: 12, name: "Anna Kowalski", email: "a.kowalski@eminence.health", role: "Lab Tech", department: "Radiology", status: "active", lastLogin: "2026-03-14 15:40" },
  { id: 13, name: "Dr. Michael Osei", email: "m.osei@eminence.health", role: "Physician", department: "Pediatrics", status: "active", lastLogin: "2026-03-15 08:50" },
  { id: 14, name: "Sophie Turner", email: "s.turner@eminence.health", role: "Billing", department: "Finance", status: "active", lastLogin: "2026-03-13 17:25" },
  { id: 15, name: "Carlos Mendez", email: "c.mendez@eminence.health", role: "Pharmacist", department: "Pharmacy", status: "inactive", lastLogin: "2026-01-20 09:10" },
  { id: 16, name: "Rachel Nguyen", email: "r.nguyen@eminence.health", role: "Admin", department: "Operations", status: "active", lastLogin: "2026-03-15 10:30" },
  { id: 17, name: "Dr. Hiroshi Tanaka", email: "h.tanaka@eminence.health", role: "Physician", department: "Surgery", status: "active", lastLogin: "2026-03-15 05:45" },
  { id: 18, name: "Grace Abigail Liu", email: "g.liu@eminence.health", role: "Nurse", department: "Pediatrics", status: "active", lastLogin: "2026-03-15 07:20" },
  { id: 19, name: "Dr. Benjamin Clark", email: "b.clark@eminence.health", role: "Physician", department: "Dermatology", status: "inactive", lastLogin: "2026-02-15 13:00" },
];

const ROLES: Role[] = [
  { id: 1, name: "Super Admin", description: "Full system access with all administrative privileges", color: "red", userCount: 1, permissions: ["patients:read", "patients:write", "patients:delete", "labs:read", "labs:write", "labs:delete", "pharmacy:read", "pharmacy:write", "pharmacy:delete", "billing:read", "billing:write", "billing:delete", "admin:read", "admin:write", "admin:delete", "ai_models:read", "ai_models:write", "ai_models:delete", "compliance:read", "compliance:write", "compliance:delete", "analytics:read", "analytics:write", "analytics:delete"] },
  { id: 2, name: "Admin", description: "Administrative access excluding compliance deletion", color: "orange", userCount: 2, permissions: ["patients:read", "patients:write", "labs:read", "labs:write", "pharmacy:read", "pharmacy:write", "billing:read", "billing:write", "admin:read", "admin:write", "ai_models:read", "ai_models:write", "compliance:read", "compliance:write", "analytics:read", "analytics:write"] },
  { id: 3, name: "Physician", description: "Clinical access for patient care and ordering", color: "blue", userCount: 5, permissions: ["patients:read", "patients:write", "labs:read", "labs:write", "pharmacy:read", "pharmacy:write", "billing:read", "ai_models:read", "ai_models:write", "analytics:read"] },
  { id: 4, name: "Nurse", description: "Patient care access with charting capabilities", color: "green", userCount: 2, permissions: ["patients:read", "patients:write", "labs:read", "pharmacy:read", "analytics:read"] },
  { id: 5, name: "Lab Tech", description: "Laboratory results and sample management", color: "purple", userCount: 2, permissions: ["patients:read", "labs:read", "labs:write", "analytics:read"] },
  { id: 6, name: "Pharmacist", description: "Medication dispensing and interaction checks", color: "teal", userCount: 2, permissions: ["patients:read", "pharmacy:read", "pharmacy:write", "labs:read", "ai_models:read", "analytics:read"] },
  { id: 7, name: "Billing", description: "Financial operations and claims management", color: "yellow", userCount: 2, permissions: ["patients:read", "billing:read", "billing:write", "analytics:read"] },
  { id: 8, name: "Read Only", description: "View-only access for auditors and compliance", color: "gray", userCount: 1, permissions: ["patients:read", "labs:read", "pharmacy:read", "billing:read", "compliance:read", "analytics:read"] },
  { id: 9, name: "Patient", description: "Patient portal access for personal health records", color: "cyan", userCount: 0, permissions: ["patients:read"] },
  { id: 10, name: "Office Admin", description: "Office administration and scheduling management", color: "indigo", userCount: 0, permissions: ["patients:read", "patients:write", "billing:read", "billing:write", "analytics:read"] },
  { id: 11, name: "Care Manager", description: "Care coordination and patient follow-up management", color: "pink", userCount: 0, permissions: ["patients:read", "patients:write", "labs:read", "pharmacy:read", "analytics:read"] },
];

const PERMISSION_CATEGORIES: Permission[] = [
  { category: "Patients", actions: ["read", "write", "delete"] },
  { category: "Labs", actions: ["read", "write", "delete"] },
  { category: "Pharmacy", actions: ["read", "write", "delete"] },
  { category: "Billing", actions: ["read", "write", "delete"] },
  { category: "Admin", actions: ["read", "write", "delete"] },
  { category: "AI Models", actions: ["read", "write", "delete"] },
  { category: "Compliance", actions: ["read", "write", "delete"] },
  { category: "Analytics", actions: ["read", "write", "delete"] },
];

const AUDIT_LOG: AuditEntry[] = [
  { id: 1, timestamp: "2026-03-15 10:32:05", user: "James Rodriguez", action: "Modified permissions", target: "Role: Nurse", ip: "10.0.12.45" },
  { id: 2, timestamp: "2026-03-15 09:58:12", user: "James Rodriguez", action: "Deactivated user", target: "Carlos Mendez", ip: "10.0.12.45" },
  { id: 3, timestamp: "2026-03-15 09:15:44", user: "Rachel Nguyen", action: "Created role", target: "Role: Intern", ip: "10.0.14.22" },
  { id: 4, timestamp: "2026-03-14 17:42:30", user: "Tom Bradley", action: "Reset password", target: "Nurse Jackie Peyton", ip: "10.0.11.88" },
  { id: 5, timestamp: "2026-03-14 16:10:08", user: "James Rodriguez", action: "Locked account", target: "Nurse Jackie Peyton", ip: "10.0.12.45" },
  { id: 6, timestamp: "2026-03-14 14:28:55", user: "Rachel Nguyen", action: "Added user", target: "David Okafor", ip: "10.0.14.22" },
  { id: 7, timestamp: "2026-03-14 11:05:33", user: "Tom Bradley", action: "Modified permissions", target: "Role: Pharmacist", ip: "10.0.11.88" },
  { id: 8, timestamp: "2026-03-13 09:44:19", user: "James Rodriguez", action: "Deactivated user", target: "Emily Watson", ip: "10.0.12.45" },
  { id: 9, timestamp: "2026-03-13 08:30:00", user: "Rachel Nguyen", action: "Created role", target: "Role: Read Only", ip: "10.0.14.22" },
  { id: 10, timestamp: "2026-03-12 15:22:47", user: "James Rodriguez", action: "Modified permissions", target: "Role: Lab Tech", ip: "10.0.12.45" },
  { id: 11, timestamp: "2026-03-12 10:11:03", user: "Tom Bradley", action: "Added user", target: "Anna Kowalski", ip: "10.0.11.88" },
  { id: 12, timestamp: "2026-03-11 13:55:28", user: "Rachel Nguyen", action: "Reset password", target: "Sophie Turner", ip: "10.0.14.22" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
const ROLE_COLOR_MAP: Record<string, string> = {
  red: "badge-red",
  orange: "badge-orange",
  blue: "badge-blue",
  green: "badge-green",
  purple: "badge-purple",
  teal: "badge-teal",
  yellow: "badge-yellow",
  gray: "badge-gray",
};

function roleBadgeClass(roleName: string): string {
  const role = ROLES.find((r) => r.name === roleName);
  if (!role) return "badge-gray";
  return ROLE_COLOR_MAP[role.color] ?? "badge-gray";
}

function statusBadge(status: User["status"]) {
  const map: Record<string, string> = {
    active: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    inactive: "bg-zinc-100 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300",
    locked: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  };
  return map[status] ?? "";
}

/* ------------------------------------------------------------------ */
/*  Tab definitions                                                    */
/* ------------------------------------------------------------------ */
const TABS = ["Users", "Roles", "Permissions", "Audit Trail"] as const;
type Tab = (typeof TABS)[number];

/* ================================================================== */
/*  Page Component                                                     */
/* ================================================================== */
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Users");
  const [users, setUsers] = useState<User[]>(INITIAL_USERS);
  const [hospitals, setHospitals] = useState<HospitalResponse[]>([]);
  const [authConfigs, setAuthConfigs] = useState<AuthConfigResponse[]>([]);
  const [sessions, setSessions] = useState<SessionResponse[]>([]);

  const activeUsers = users.filter((u) => u.status === "active").length;
  const lockedUsers = users.filter((u) => u.status === "locked").length;
  const totalPermissions = PERMISSION_CATEGORIES.reduce((sum, c) => sum + c.actions.length, 0) * ROLES.length;

  const ROLE_MAP: Record<string, string> = {
    admin: "Super Admin",
    super_admin: "Super Admin",
    clinician: "Physician",
    nurse: "Nurse",
    care_manager: "Care Manager",
    lab_tech: "Lab Tech",
    pharmacist: "Pharmacist",
    billing: "Billing",
    read_only: "Read Only",
    patient: "Patient",
    office_admin: "Office Admin",
  };

  // Convert a profile to a User entry for the table
  function profileToUser(profile: UserProfile, id: number): User {
    return {
      id,
      name: profile.full_name || profile.email.split("@")[0],
      email: profile.email,
      role: ROLE_MAP[profile.role] ?? profile.role,
      department: profile.role === "clinician" ? "Clinical" : profile.role === "admin" ? "IT" : "General",
      status: profile.is_active ? "active" : "inactive",
      lastLogin: profile.updated_at?.split("T")[0] ?? profile.created_at?.split("T")[0] ?? "",
    };
  }

  // Load real data from APIs — always include the logged-in user
  useEffect(() => {
    (async () => {
      try {
        const isAdmin = getUserRole() === "admin";

        // Always fetch the current user's profile
        const myProfile = await fetchMyProfile().catch(() => null);

        const [hospitalList, configList, sessionList] = await Promise.all([
          fetchHospitals().catch(() => []),
          isAdmin ? fetchAuthConfigs().catch(() => []) : Promise.resolve([]),
          fetchSessions().catch(() => []),
        ]);
        setHospitals(hospitalList);
        setAuthConfigs(configList);
        setSessions(sessionList);

        // Try the real admin users API first
        try {
          const adminData = await fetchAdminUsers({ page: 1, page_size: 100 });
          if (adminData.users.length > 0) {
            const realUsers: User[] = adminData.users.map((u: AdminUserResponse, idx: number) => ({
              id: idx + 1,
              backendId: u.id,
              name: u.full_name || u.email.split("@")[0],
              email: u.email,
              role: ROLE_MAP[u.role] ?? u.role,
              department: u.role === "clinician" ? "Clinical" : u.role === "admin" ? "IT" : "General",
              status: u.is_active ? "active" as const : "inactive" as const,
              lastLogin: u.updated_at?.split("T")[0] ?? u.created_at?.split("T")[0] ?? "",
            }));
            // Ensure current user is in the list
            if (myProfile && !realUsers.some((u) => u.email === myProfile.email)) {
              realUsers.unshift(profileToUser(myProfile, 0));
            }
            setUsers(realUsers);
            return;
          }
        } catch {
          // Admin API not available, fall back
        }

        // Fallback: merge provider/nurse/admin data into user list
        const [providerList, nurseList, adminList] = await Promise.all([
          fetchProviders().catch(() => []),
          fetchNurses().catch(() => []),
          fetchOfficeAdmins().catch(() => []),
        ]);
        const apiUsers: User[] = [];
        let idx = 100;

        // Always include the logged-in user first
        if (myProfile) {
          apiUsers.push(profileToUser(myProfile, idx++));
        }

        for (const p of providerList) {
          apiUsers.push({
            id: idx++,
            name: p.user_id.slice(0, 8),
            email: `${p.user_id.slice(0, 8)}@eminence.health`,
            role: "Physician",
            department: p.specialty,
            status: p.is_active ? "active" : "inactive",
            lastLogin: p.created_at?.split("T")[0] ?? "",
          });
        }
        for (const n of nurseList) {
          apiUsers.push({
            id: idx++,
            name: n.user_id.slice(0, 8),
            email: `${n.user_id.slice(0, 8)}@eminence.health`,
            role: "Nurse",
            department: n.specialty,
            status: n.is_active ? "active" : "inactive",
            lastLogin: n.created_at?.split("T")[0] ?? "",
          });
        }
        for (const a of adminList) {
          apiUsers.push({
            id: idx++,
            name: a.user_id.slice(0, 8),
            email: `${a.user_id.slice(0, 8)}@eminence.health`,
            role: "Admin",
            department: a.position,
            status: a.is_active ? "active" : "inactive",
            lastLogin: a.created_at?.split("T")[0] ?? "",
          });
        }

        if (apiUsers.length > 0) {
          setUsers(apiUsers);
        } else if (myProfile) {
          // Even if all API calls return empty, show the current user + demo data
          const demoWithCurrentUser = [...INITIAL_USERS];
          if (!demoWithCurrentUser.some((u) => u.email === myProfile.email)) {
            demoWithCurrentUser.unshift(profileToUser(myProfile, 0));
          }
          setUsers(demoWithCurrentUser);
        }
      } catch {
        // Keep demo data
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 p-6 lg:p-5 sm:p-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-xl sm:text-3xl font-bold text-zinc-900 dark:text-white">Administration</h1>
        <p className="mt-1 text-zinc-500 dark:text-zinc-400">Manage roles, permissions, and user access</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="card p-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Total Users</p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-white">{users.length}</p>
          <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">{activeUsers} active</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Roles</p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-white">{ROLES.length}</p>
          <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">system-defined</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Permission Slots</p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-white">{totalPermissions}</p>
          <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">{PERMISSION_CATEGORIES.length} categories</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Alerts</p>
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">{lockedUsers}</p>
          <p className="text-xs text-red-500 dark:text-red-400 mt-1">locked account{lockedUsers !== 1 ? "s" : ""}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-200 dark:border-zinc-700 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab
                ? "bg-white dark:bg-zinc-800 text-blue-600 dark:text-blue-400 border border-b-0 border-zinc-200 dark:border-zinc-700"
                : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "Users" && <UsersTab />}
      {activeTab === "Roles" && <RolesTab />}
      {activeTab === "Permissions" && <PermissionsTab />}
      {activeTab === "Audit Trail" && <AuditTrailTab />}
    </div>
  );
}

/* ================================================================== */
/*  Users Tab                                                          */
/* ================================================================== */
function UserAvatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .filter((p) => p.length > 0)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const colors = [
    "bg-blue-500", "bg-emerald-500", "bg-purple-500", "bg-amber-500",
    "bg-rose-500", "bg-cyan-500", "bg-indigo-500", "bg-teal-500",
  ];
  const colorIndex = name.length % colors.length;

  return (
    <span
      className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-bold ${colors[colorIndex]}`}
    >
      {initials}
    </span>
  );
}

/* Roles that require Hospital + Department assignment */
const STAFF_ROLES = new Set(["Physician", "Nurse", "Office Admin", "Care Manager", "Lab Tech", "Pharmacist"]);
/* Roles that need provider-specific fields (specialty, NPI, license) */
const PROVIDER_ROLES = new Set(["Physician"]);
/* Roles that need nurse-specific fields (specialty, license) */
const NURSE_ROLES = new Set(["Nurse"]);
/* Roles that need office-admin-specific fields (position, employee_id) */
const OFFICE_ADMIN_ROLES = new Set(["Office Admin"]);

function UsersTab() {
  const [users, setUsers] = useState<User[]>(INITIAL_USERS);
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [isAdmin, setIsAdmin] = useState(() => getUserRole() === "admin" || getUserRole() === "super_admin");
  const [promoting, setPromoting] = useState(false);

  // Edit modal state
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editName, setEditName] = useState("");
  const [editRole, setEditRole] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editHospitalId, setEditHospitalId] = useState("");
  const [editDeptId, setEditDeptId] = useState("");
  const [editSpecialty, setEditSpecialty] = useState("");
  const [editNPI, setEditNPI] = useState("");
  const [editLicense, setEditLicense] = useState("");
  const [editPosition, setEditPosition] = useState("");
  const [editEmployeeId, setEditEmployeeId] = useState("");

  const editRoleRequiresHospital = STAFF_ROLES.has(editRole);
  const editRoleIsProvider = PROVIDER_ROLES.has(editRole);
  const editRoleIsNurse = NURSE_ROLES.has(editRole);
  const editRoleIsOfficeAdmin = OFFICE_ADMIN_ROLES.has(editRole);
  const editDepartments = editHospitalId ? (departmentsByHospital[editHospitalId] || []) : [];

  // Load departments when edit hospital changes
  useEffect(() => {
    if (editHospitalId) loadDepartmentsForHospital(editHospitalId);
  }, [editHospitalId, loadDepartmentsForHospital]);

  const ROLE_MAP_TAB: Record<string, string> = {
    admin: "Super Admin",
    super_admin: "Super Admin",
    clinician: "Physician",
    nurse: "Nurse",
    care_manager: "Care Manager",
    lab_tech: "Lab Tech",
    pharmacist: "Pharmacist",
    billing: "Billing",
    read_only: "Read Only",
    patient: "Patient",
    office_admin: "Office Admin",
  };

  const ROLE_REVERSE_MAP: Record<string, string> = {
    "Super Admin": "admin",
    Physician: "clinician",
    Nurse: "nurse",
    Admin: "admin",
    "Lab Tech": "lab_tech",
    Pharmacist: "pharmacist",
    Billing: "billing",
    "Read Only": "read_only",
    Patient: "patient",
    "Office Admin": "office_admin",
    "Care Manager": "care_manager",
  };

  // Load real user data — always include current logged-in user
  const loadUsers = useCallback(async () => {
    try {
      const myProfile = await fetchMyProfile().catch(() => null);

      // Try admin users API first
      try {
        const adminData = await fetchAdminUsers({ page: 1, page_size: 100 });
        if (adminData.users.length > 0) {
          const realUsers: User[] = adminData.users.map((u: AdminUserResponse, idx: number) => ({
            id: idx + 1,
            backendId: u.id,
            name: u.full_name || u.email.split("@")[0],
            email: u.email,
            role: ROLE_MAP_TAB[u.role] ?? u.role,
            department: u.role === "clinician" ? "Clinical" : u.role === "admin" ? "IT" : "General",
            status: u.is_active ? "active" as const : "inactive" as const,
            lastLogin: u.updated_at?.split("T")[0] ?? u.created_at?.split("T")[0] ?? "",
          }));
          if (myProfile && !realUsers.some((u) => u.email === myProfile.email)) {
            realUsers.unshift({
              id: 0,
              backendId: myProfile.id,
              name: myProfile.full_name || myProfile.email.split("@")[0],
              email: myProfile.email,
              role: ROLE_MAP_TAB[myProfile.role] ?? myProfile.role,
              department: myProfile.role === "clinician" ? "Clinical" : myProfile.role === "admin" ? "IT" : "General",
              status: myProfile.is_active ? "active" : "inactive",
              lastLogin: myProfile.updated_at?.split("T")[0] ?? myProfile.created_at?.split("T")[0] ?? "",
            });
          }
          setUsers(realUsers);
          return;
        }
      } catch {
        // Admin API not available, fall back
      }

      // Fallback: merge provider/nurse/admin data
      const [providerList, nurseList, adminList] = await Promise.all([
        fetchProviders().catch(() => []),
        fetchNurses().catch(() => []),
        fetchOfficeAdmins().catch(() => []),
      ]);
      const apiUsers: User[] = [];
      let idx = 100;

      if (myProfile) {
        apiUsers.push({
          id: idx++,
          backendId: myProfile.id,
          name: myProfile.full_name || myProfile.email.split("@")[0],
          email: myProfile.email,
          role: ROLE_MAP_TAB[myProfile.role] ?? myProfile.role,
          department: myProfile.role === "clinician" ? "Clinical" : myProfile.role === "admin" ? "IT" : "General",
          status: myProfile.is_active ? "active" : "inactive",
          lastLogin: myProfile.updated_at?.split("T")[0] ?? myProfile.created_at?.split("T")[0] ?? "",
        });
      }

      for (const p of providerList) {
        apiUsers.push({ id: idx++, name: p.user_id.slice(0, 8), email: `${p.user_id.slice(0, 8)}@eminence.health`, role: "Physician", department: p.specialty, status: p.is_active ? "active" : "inactive", lastLogin: p.created_at?.split("T")[0] ?? "" });
      }
      for (const n of nurseList) {
        apiUsers.push({ id: idx++, name: n.user_id.slice(0, 8), email: `${n.user_id.slice(0, 8)}@eminence.health`, role: "Nurse", department: n.specialty, status: n.is_active ? "active" : "inactive", lastLogin: n.created_at?.split("T")[0] ?? "" });
      }
      for (const a of adminList) {
        apiUsers.push({ id: idx++, name: a.user_id.slice(0, 8), email: `${a.user_id.slice(0, 8)}@eminence.health`, role: "Admin", department: a.position, status: a.is_active ? "active" : "inactive", lastLogin: a.created_at?.split("T")[0] ?? "" });
      }

      if (apiUsers.length > 0) {
        setUsers(apiUsers);
      } else if (myProfile) {
        const demoWithUser = [...INITIAL_USERS];
        if (!demoWithUser.some((u) => u.email === myProfile.email)) {
          demoWithUser.unshift({
            id: 0,
            backendId: myProfile.id,
            name: myProfile.full_name || myProfile.email.split("@")[0],
            email: myProfile.email,
            role: ROLE_MAP_TAB[myProfile.role] ?? myProfile.role,
            department: myProfile.role === "clinician" ? "Clinical" : myProfile.role === "admin" ? "IT" : "General",
            status: myProfile.is_active ? "active" : "inactive",
            lastLogin: myProfile.updated_at?.split("T")[0] ?? myProfile.created_at?.split("T")[0] ?? "",
          });
        }
        setUsers(demoWithUser);
      }
    } catch { /* keep demo */ }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const [filterRole, setFilterRole] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");
  const [filterDept, setFilterDept] = useState("All");
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<Set<number>>(new Set());
  const [sortField, setSortField] = useState<keyof User>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  /* Hospital / Department data */
  const [hospitals, setHospitals] = useState<HospitalResponse[]>([]);
  const [departmentsByHospital, setDepartmentsByHospital] = useState<Record<string, DepartmentResponse[]>>({});

  useEffect(() => {
    fetchHospitals().then(setHospitals).catch(() => {});
  }, []);

  const loadDepartmentsForHospital = useCallback(async (hospitalId: string) => {
    if (!hospitalId || departmentsByHospital[hospitalId]) return;
    try {
      const depts = await fetchDepartments(hospitalId);
      setDepartmentsByHospital((prev) => ({ ...prev, [hospitalId]: depts }));
    } catch { /* ignore */ }
  }, [departmentsByHospital]);

  /* Form state */
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPassword, setFormPassword] = useState("");
  const [formRole, setFormRole] = useState("");
  const [formHospitalId, setFormHospitalId] = useState("");
  const [formDeptId, setFormDeptId] = useState("");
  // Provider fields
  const [formSpecialty, setFormSpecialty] = useState("");
  const [formNPI, setFormNPI] = useState("");
  const [formLicense, setFormLicense] = useState("");
  // Office Admin fields
  const [formPosition, setFormPosition] = useState("");
  const [formEmployeeId, setFormEmployeeId] = useState("");

  const formDepartments = formHospitalId ? (departmentsByHospital[formHospitalId] || []) : [];
  const formRoleRequiresHospital = STAFF_ROLES.has(formRole);
  const formRoleIsProvider = PROVIDER_ROLES.has(formRole);
  const formRoleIsNurse = NURSE_ROLES.has(formRole);
  const formRoleIsOfficeAdmin = OFFICE_ADMIN_ROLES.has(formRole);

  // Load departments when hospital changes
  useEffect(() => {
    if (formHospitalId) {
      loadDepartmentsForHospital(formHospitalId);
      setFormDeptId(""); // reset department when hospital changes
    }
  }, [formHospitalId, loadDepartmentsForHospital]);

  const userDepartments = useMemo(() => Array.from(new Set(users.map((u) => u.department))).sort(), [users]);
  const roleNames = useMemo(() => Array.from(new Set(ROLES.map((r) => r.name))).sort(), []);

  const filtered = useMemo(() => {
    const result = users.filter((u) => {
      const matchSearch =
        !search ||
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase());
      const matchRole = filterRole === "All" || u.role === filterRole;
      const matchStatus = filterStatus === "All" || u.status === filterStatus;
      const matchDept = filterDept === "All" || u.department === filterDept;
      return matchSearch && matchRole && matchStatus && matchDept;
    });

    result.sort((a, b) => {
      const aVal = String(a[sortField]).toLowerCase();
      const bVal = String(b[sortField]).toLowerCase();
      const cmp = aVal.localeCompare(bVal);
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [users, search, filterRole, filterStatus, filterDept, sortField, sortDir]);

  const handleSort = useCallback((field: keyof User) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        return prev;
      }
      setSortDir("asc");
      return field;
    });
  }, []);

  const toggleSelect = (id: number) => {
    setSelectedUsers((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedUsers.size === filtered.length) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(filtered.map((u) => u.id)));
    }
  };

  const resetAddForm = () => {
    setFormName(""); setFormEmail(""); setFormPassword(""); setFormRole("");
    setFormHospitalId(""); setFormDeptId(""); setFormSpecialty(""); setFormNPI("");
    setFormLicense(""); setFormPosition(""); setFormEmployeeId("");
  };

  const canSubmitAddForm = () => {
    if (!formName || !formEmail || !formPassword || !formRole) return false;
    // Staff roles require hospital + department
    if (formRoleRequiresHospital && (!formHospitalId || !formDeptId)) return false;
    // Provider requires specialty + NPI
    if (formRoleIsProvider && (!formSpecialty || !formNPI)) return false;
    // Nurse requires license number
    if (formRoleIsNurse && !formLicense) return false;
    // Office Admin requires employee ID
    if (formRoleIsOfficeAdmin && !formEmployeeId) return false;
    return true;
  };

  const handleAddUser = async () => {
    if (!canSubmitAddForm()) return;
    setError("");
    setSaving(true);
    try {
      const backendRole = ROLE_REVERSE_MAP[formRole] ?? "read_only";
      // Step 1: Create the user account
      const newUser = await createAdminUser({
        email: formEmail,
        password: formPassword,
        full_name: formName,
        role: backendRole,
        hospital_id: formHospitalId || undefined,
        department_id: formDeptId || undefined,
        specialty: formSpecialty || undefined,
        npi: formNPI || undefined,
        license_number: formLicense || undefined,
        position: formPosition || undefined,
        employee_id: formEmployeeId || undefined,
      });

      // Step 2: Create role-specific profile (provider/nurse/office-admin)
      if (formRoleIsProvider && newUser?.id) {
        await createProvider({
          user_id: newUser.id,
          specialty: formSpecialty,
          npi: formNPI,
          license_number: formLicense || undefined,
          hospital_id: formHospitalId || undefined,
          department_id: formDeptId || undefined,
        }).catch(() => {}); // best-effort
      } else if (formRoleIsNurse && newUser?.id) {
        await createNurse({
          user_id: newUser.id,
          specialty: formSpecialty || undefined,
          license_number: formLicense,
          hospital_id: formHospitalId || undefined,
          department_id: formDeptId || undefined,
        }).catch(() => {});
      } else if (formRoleIsOfficeAdmin && newUser?.id) {
        await createOfficeAdmin({
          user_id: newUser.id,
          position: formPosition || undefined,
          employee_id: formEmployeeId,
          hospital_id: formHospitalId || undefined,
          department_id: formDeptId || undefined,
        }).catch(() => {});
      }

      await loadUsers();
      resetAddForm();
      setShowAddForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setEditName(user.name);
    setEditRole(user.role);
    setEditPhone("");
    setEditHospitalId(user.hospitalId || "");
    setEditDeptId(user.departmentId || "");
    setEditSpecialty("");
    setEditNPI("");
    setEditLicense("");
    setEditPosition("");
    setEditEmployeeId("");
    setError("");
    if (user.hospitalId) loadDepartmentsForHospital(user.hospitalId);
  };

  const handleSaveEdit = async () => {
    if (!editingUser?.backendId) {
      setError("Cannot edit this user — no backend ID available");
      return;
    }
    // Validate hierarchy for staff roles
    if (editRoleRequiresHospital && (!editHospitalId || !editDeptId)) {
      setError(`${editRole} accounts must be assigned to a Hospital and Department.`);
      return;
    }
    setError("");
    setSaving(true);
    try {
      const backendRole = ROLE_REVERSE_MAP[editRole] ?? undefined;
      await updateAdminUser(editingUser.backendId, {
        full_name: editName || undefined,
        role: backendRole,
        phone: editPhone || undefined,
        hospital_id: editHospitalId || undefined,
        department_id: editDeptId || undefined,
        specialty: editSpecialty || undefined,
        npi: editNPI || undefined,
        license_number: editLicense || undefined,
        position: editPosition || undefined,
        employee_id: editEmployeeId || undefined,
      });
      await loadUsers();
      setEditingUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (user: User) => {
    if (!user.backendId) return;
    setSaving(true);
    try {
      await deactivateAdminUser(user.backendId);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to deactivate user");
    } finally {
      setSaving(false);
    }
  };

  const handlePromoteSelf = async () => {
    setPromoting(true);
    setError("");
    try {
      await promoteSelfToAdmin();
      // Update local role state — user needs to re-login for new JWT
      setIsAdmin(true);
      // Force re-login to get updated JWT with admin role
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login?promoted=1";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to promote. An admin may already exist.");
    } finally {
      setPromoting(false);
    }
  };

  const sortIndicator = (field: keyof User) => {
    if (sortField !== field) return null;
    return <span className="ml-1 text-blue-500">{sortDir === "asc" ? "\u2191" : "\u2193"}</span>;
  };

  return (
    <div className="card p-6">
      {/* Admin role required banner */}
      {!isAdmin && (
        <div className="mb-4 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-semibold text-amber-800 dark:text-amber-200">Admin access required</h4>
              <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                Your account has a <strong>{getUserRole() || "non-admin"}</strong> role. User management requires admin privileges.
                If no admin exists in your organization, you can promote yourself.
              </p>
            </div>
            <button
              onClick={handlePromoteSelf}
              disabled={promoting}
              className="btn-primary whitespace-nowrap ml-4"
            >
              {promoting ? "Promoting..." : "Become Admin"}
            </button>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError("")} className="text-red-500 hover:text-red-700 font-bold ml-4">&times;</button>
        </div>
      )}

      {/* Edit Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4">
          <div className="bg-white dark:bg-zinc-900 rounded-t-2xl sm:rounded-xl shadow-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto mx-0 sm:mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-zinc-900 dark:text-white">Edit User</h3>
              <button onClick={() => setEditingUser(null)} className="text-zinc-400 hover:text-zinc-600 text-xl leading-none">&times;</button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Email</label>
                <input value={editingUser.email} disabled className="input w-full opacity-60 cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Full Name</label>
                <input value={editName} onChange={(e) => setEditName(e.target.value)} className="input w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Role</label>
                <select value={editRole} onChange={(e) => { setEditRole(e.target.value); setEditHospitalId(""); setEditDeptId(""); }} className="select w-full">
                  {roleNames.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Phone (optional)</label>
                <input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} placeholder="+1 555-0123" className="input w-full" />
              </div>

              {/* Hospital + Department for staff roles */}
              {editRoleRequiresHospital && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Hospital *</label>
                    <select value={editHospitalId} onChange={(e) => { setEditHospitalId(e.target.value); setEditDeptId(""); }} className="select w-full">
                      <option value="">Select hospital</option>
                      {hospitals.map((h) => (
                        <option key={h.id} value={h.id}>{h.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Department *</label>
                    <select value={editDeptId} onChange={(e) => setEditDeptId(e.target.value)} disabled={!editHospitalId} className="select w-full disabled:opacity-50">
                      <option value="">Select department</option>
                      {editDepartments.map((d) => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {/* Provider fields */}
              {editRoleIsProvider && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Specialty</label>
                    <input value={editSpecialty} onChange={(e) => setEditSpecialty(e.target.value)} placeholder="e.g. Cardiology" className="input w-full" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">NPI Number</label>
                    <input value={editNPI} onChange={(e) => setEditNPI(e.target.value)} placeholder="10-digit NPI" className="input w-full" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">License Number</label>
                    <input value={editLicense} onChange={(e) => setEditLicense(e.target.value)} className="input w-full" />
                  </div>
                </>
              )}

              {/* Nurse fields */}
              {editRoleIsNurse && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">License Number</label>
                    <input value={editLicense} onChange={(e) => setEditLicense(e.target.value)} placeholder="Nursing license #" className="input w-full" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Specialty</label>
                    <input value={editSpecialty} onChange={(e) => setEditSpecialty(e.target.value)} placeholder="e.g. ICU, Pediatrics" className="input w-full" />
                  </div>
                </>
              )}

              {/* Office Admin fields */}
              {editRoleIsOfficeAdmin && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Employee ID</label>
                    <input value={editEmployeeId} onChange={(e) => setEditEmployeeId(e.target.value)} placeholder="EMP-0001" className="input w-full" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Position</label>
                    <input value={editPosition} onChange={(e) => setEditPosition(e.target.value)} placeholder="e.g. Office Manager" className="input w-full" />
                  </div>
                </>
              )}

              {/* Hierarchy validation notice */}
              {editRoleRequiresHospital && (!editHospitalId || !editDeptId) && (
                <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300 text-xs">
                  <strong>{editRole}</strong> accounts must be assigned to a Hospital and Department.
                </div>
              )}
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <button onClick={handleSaveEdit} disabled={saving} className="btn-primary">
                {saving ? "Saving..." : "Save Changes"}
              </button>
              <button onClick={() => setEditingUser(null)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-4 mb-6">
        <input
          type="text"
          placeholder="Search by name or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input w-full lg:w-64"
        />
        <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)} className="select">
          <option value="All">All Roles</option>
          {roleNames.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="select">
          <option value="All">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="locked">Locked</option>
        </select>
        <select value={filterDept} onChange={(e) => setFilterDept(e.target.value)} className="select">
          <option value="All">All Departments</option>
          {userDepartments.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <div className="flex gap-2 ml-auto">
          {selectedUsers.size > 0 && (
            <button className="btn-danger whitespace-nowrap text-sm">
              Bulk Deactivate ({selectedUsers.size})
            </button>
          )}
          <button onClick={() => { setShowAddForm(!showAddForm); setError(""); }} className="btn-primary whitespace-nowrap">
            + Add User
          </button>
        </div>
      </div>

      {/* Inline Add Form */}
      {showAddForm && (
        <div className="card-hover p-5 mb-6 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-3">New User</h3>

          {/* Row 1: Basic info */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Full Name *</label>
              <input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Jane Doe" className="input w-full" />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Email *</label>
              <input value={formEmail} onChange={(e) => setFormEmail(e.target.value)} placeholder="j.doe@eminence.health" type="email" className="input w-full" />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Password *</label>
              <input value={formPassword} onChange={(e) => setFormPassword(e.target.value)} placeholder="Min 8 characters" type="password" className="input w-full" />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Role *</label>
              <select value={formRole} onChange={(e) => { setFormRole(e.target.value); setFormHospitalId(""); setFormDeptId(""); setFormSpecialty(""); setFormNPI(""); setFormLicense(""); setFormPosition(""); setFormEmployeeId(""); }} className="select w-full">
                <option value="" disabled>Select role</option>
                {roleNames.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 2: Hospital + Department (for staff roles) */}
          {formRoleRequiresHospital && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">
                  Hospital *
                  <span className="text-zinc-400 dark:text-zinc-500 font-normal ml-1">(required for {formRole})</span>
                </label>
                <select value={formHospitalId} onChange={(e) => setFormHospitalId(e.target.value)} className="select w-full">
                  <option value="">Select hospital</option>
                  {hospitals.map((h) => (
                    <option key={h.id} value={h.id}>{h.name}</option>
                  ))}
                </select>
                {hospitals.length === 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">No hospitals found. Create a hospital in Org Settings first.</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">
                  Department *
                  <span className="text-zinc-400 dark:text-zinc-500 font-normal ml-1">(select hospital first)</span>
                </label>
                <select value={formDeptId} onChange={(e) => setFormDeptId(e.target.value)} disabled={!formHospitalId} className="select w-full disabled:opacity-50">
                  <option value="">Select department</option>
                  {formDepartments.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
                {formHospitalId && formDepartments.length === 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">No departments in this hospital. Create one first.</p>
                )}
              </div>
            </div>
          )}

          {/* Row 3: Provider-specific fields */}
          {formRoleIsProvider && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Specialty *</label>
                <input value={formSpecialty} onChange={(e) => setFormSpecialty(e.target.value)} placeholder="e.g. Cardiology" className="input w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">NPI Number *</label>
                <input value={formNPI} onChange={(e) => setFormNPI(e.target.value)} placeholder="10-digit NPI" className="input w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">License Number</label>
                <input value={formLicense} onChange={(e) => setFormLicense(e.target.value)} placeholder="Optional" className="input w-full" />
              </div>
            </div>
          )}

          {/* Row 3: Nurse-specific fields */}
          {formRoleIsNurse && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">License Number *</label>
                <input value={formLicense} onChange={(e) => setFormLicense(e.target.value)} placeholder="Nursing license #" className="input w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Specialty</label>
                <input value={formSpecialty} onChange={(e) => setFormSpecialty(e.target.value)} placeholder="e.g. ICU, Pediatrics" className="input w-full" />
              </div>
            </div>
          )}

          {/* Row 3: Office Admin-specific fields */}
          {formRoleIsOfficeAdmin && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Employee ID *</label>
                <input value={formEmployeeId} onChange={(e) => setFormEmployeeId(e.target.value)} placeholder="EMP-0001" className="input w-full" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Position</label>
                <input value={formPosition} onChange={(e) => setFormPosition(e.target.value)} placeholder="e.g. Office Manager" className="input w-full" />
              </div>
            </div>
          )}

          {/* Validation summary */}
          {formRole && formRoleRequiresHospital && (!formHospitalId || !formDeptId) && (
            <div className="mb-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300 text-xs">
              <strong>{formRole}</strong> accounts must be assigned to a Hospital and Department per the organizational hierarchy.
            </div>
          )}

          <div className="flex gap-2 justify-end">
            <button onClick={handleAddUser} disabled={saving || !canSubmitAddForm()} className="btn-primary disabled:opacity-50">
              {saving ? "Creating..." : "Save User"}
            </button>
            <button onClick={() => { setShowAddForm(false); resetAddForm(); }} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-sm">
          <thead>
            <tr className="table-header">
              <th className="p-3 w-10">
                <input
                  type="checkbox"
                  checked={filtered.length > 0 && selectedUsers.size === filtered.length}
                  onChange={toggleSelectAll}
                  className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-600"
                />
              </th>
              <th className="text-left p-3 font-semibold cursor-pointer select-none" onClick={() => handleSort("name")}>
                Name {sortIndicator("name")}
              </th>
              <th className="text-left p-3 font-semibold cursor-pointer select-none" onClick={() => handleSort("email")}>
                Email {sortIndicator("email")}
              </th>
              <th className="text-left p-3 font-semibold cursor-pointer select-none" onClick={() => handleSort("role")}>
                Role {sortIndicator("role")}
              </th>
              <th className="text-left p-3 font-semibold cursor-pointer select-none" onClick={() => handleSort("department")}>
                Department {sortIndicator("department")}
              </th>
              <th className="text-left p-3 font-semibold cursor-pointer select-none" onClick={() => handleSort("status")}>
                Status {sortIndicator("status")}
              </th>
              <th className="text-left p-3 font-semibold cursor-pointer select-none" onClick={() => handleSort("lastLogin")}>
                Last Login {sortIndicator("lastLogin")}
              </th>
              <th className="text-right p-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((user) => (
              <tr key={user.id} className={`table-row border-b border-zinc-100 dark:border-zinc-800 ${
                selectedUsers.has(user.id) ? "bg-blue-50 dark:bg-blue-900/10" : ""
                }`}
              >
                <td className="p-3">
                  <input
                    type="checkbox"
                    checked={selectedUsers.has(user.id)}
                    onChange={() => toggleSelect(user.id)}
                    className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-600"
                  />
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <UserAvatar name={user.name} />
                    <span className="font-medium text-zinc-900 dark:text-white">{user.name}</span>
                  </div>
                </td>
                <td className="p-3 text-zinc-500 dark:text-zinc-400">{user.email}</td>
                <td className="p-3">
                  <span className={`${roleBadgeClass(user.role)} inline-block px-2 py-0.5 rounded-full text-xs font-medium`}>
                    {user.role}
                  </span>
                </td>
                <td className="p-3 text-zinc-600 dark:text-zinc-300">{user.department}</td>
                <td className="p-3">
                  <span className={`${statusBadge(user.status)} inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize`}>
                    {user.status}
                  </span>
                </td>
                <td className="p-3 text-zinc-500 dark:text-zinc-400 whitespace-nowrap">{user.lastLogin}</td>
                <td className="p-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button onClick={() => handleEditUser(user)} className="btn-secondary text-xs px-2 py-1" title="Edit user">Edit</button>
                    <button onClick={() => handleDeactivate(user)} disabled={saving} className="btn-danger text-xs px-2 py-1" title="Deactivate user">Deactivate</button>
                    <button className="btn-secondary text-xs px-2 py-1" title="Reset password">Reset PW</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
        {filtered.length === 0 && (
          <div className="text-center py-6 sm:py-12">
            <p className="text-zinc-400 dark:text-zinc-500 text-lg mb-1">No users found</p>
            <p className="text-zinc-300 dark:text-zinc-600 text-sm">Try adjusting your search or filter criteria.</p>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-zinc-400 dark:text-zinc-500">
          Showing {filtered.length} of {users.length} users
        </p>
        <div className="flex gap-1">
          <button className="btn-secondary text-xs px-3 py-1 opacity-50 cursor-not-allowed">Previous</button>
          <button className="btn-primary text-xs px-3 py-1">1</button>
          <button className="btn-secondary text-xs px-3 py-1 opacity-50 cursor-not-allowed">Next</button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Roles Tab                                                          */
/* ================================================================== */
function RolesTab() {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const colorClasses: Record<string, string> = {
    red: "border-red-400 dark:border-red-600",
    orange: "border-orange-400 dark:border-orange-600",
    blue: "border-blue-400 dark:border-blue-600",
    green: "border-green-400 dark:border-green-600",
    purple: "border-purple-400 dark:border-purple-600",
    teal: "border-teal-400 dark:border-teal-600",
    yellow: "border-yellow-400 dark:border-yellow-600",
    gray: "border-zinc-400 dark:border-zinc-600",
  };

  const dotColors: Record<string, string> = {
    red: "bg-red-500",
    orange: "bg-orange-500",
    blue: "bg-blue-500",
    green: "bg-green-500",
    purple: "bg-purple-500",
    teal: "bg-teal-500",
    yellow: "bg-yellow-500",
    gray: "bg-zinc-500",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">{ROLES.length} roles configured</p>
        <button onClick={() => setShowCreateForm(!showCreateForm)} className="btn-primary">
          + Create Role
        </button>
      </div>

      {/* Create Role Form */}
      {showCreateForm && (
        <div className="card p-6 mb-6 border border-blue-200 dark:border-blue-800">
          <h3 className="text-lg font-semibold text-zinc-900 dark:text-white mb-4">Create New Role</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Role Name</label>
              <input placeholder="e.g., Intern" className="input w-full" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Description</label>
              <input placeholder="Brief description of the role" className="input w-full" />
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-2">Badge Color</label>
            <div className="flex gap-3">
              {Object.keys(dotColors).map((c) => (
                <button key={c} className={`w-7 h-7 rounded-full ${dotColors[c]} ring-2 ring-offset-2 ring-transparent hover:ring-blue-400 dark:ring-offset-zinc-900 transition-all`} title={c} />
              ))}
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-2">Base Permissions (clone from existing role)</label>
            <select className="select" defaultValue="">
              <option value="">Start with no permissions</option>
              {ROLES.map((r) => (
                <option key={r.id} value={r.name}>Clone from: {r.name} ({r.permissions.length} permissions)</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <button className="btn-primary">Create Role</button>
            <button onClick={() => setShowCreateForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {/* Role Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {ROLES.map((role) => {
          const isExpanded = expandedId === role.id;
          return (
            <div
              key={role.id}
              className={`card-hover p-5 border-l-4 cursor-pointer transition-all ${colorClasses[role.color] ?? "border-zinc-400"} ${isExpanded ? "md:col-span-2 xl:col-span-4" : ""}`}
              onClick={() => setExpandedId(isExpanded ? null : role.id)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${dotColors[role.color]}`} />
                  <h3 className="font-semibold text-zinc-900 dark:text-white">{role.name}</h3>
                </div>
                <span className="text-xs text-zinc-400">{isExpanded ? "Collapse" : "Expand"}</span>
              </div>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-3">{role.description}</p>
              <div className="flex gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                <span>{role.userCount} user{role.userCount !== 1 ? "s" : ""}</span>
                <span>{role.permissions.length} permissions</span>
              </div>

              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700" onClick={(e) => e.stopPropagation()}>
                  <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Assigned Permissions</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {role.permissions.map((perm) => (
                      <span
                        key={perm}
                        className="badge-blue inline-block px-2 py-0.5 rounded text-xs font-mono"
                      >
                        {perm}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Permissions Tab                                                    */
/* ================================================================== */
function PermissionsTab() {
  const buildInitial = () => {
    const state: Record<string, Record<string, boolean>> = {};
    ROLES.forEach((role) => {
      state[role.name] = {};
      PERMISSION_CATEGORIES.forEach((cat) => {
        const key = cat.category.toLowerCase().replace(/ /g, "_");
        cat.actions.forEach((action) => {
          state[role.name][`${key}:${action}`] = role.permissions.includes(`${key}:${action}`);
        });
      });
    });
    return state;
  };

  const [matrix, setMatrix] = useState(buildInitial);

  const toggle = (roleName: string, perm: string) => {
    setMatrix((prev) => ({
      ...prev,
      [roleName]: { ...prev[roleName], [perm]: !prev[roleName][perm] },
    }));
  };

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">Permission Matrix</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Toggle permissions per role across all categories</p>
        </div>
        <button className="btn-primary">Save Changes</button>
      </div>

      <div className="overflow-x-auto">
        <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-xs">
          <thead>
            <tr className="table-header">
              <th className="p-2 text-left font-semibold sticky left-0 bg-zinc-100 dark:bg-zinc-800 z-10 min-w-[120px]">
                Category / Action
              </th>
              {ROLES.map((role) => (
                <th key={role.name} className="p-2 text-center font-semibold min-w-[90px]">
                  <span className="block">{role.name}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PERMISSION_CATEGORIES.map((cat) => {
              const key = cat.category.toLowerCase().replace(/ /g, "_"); return cat.actions.map((action, ai) => ( <tr key={`${cat.category}-${action}`} className={`table-row border-b border-zinc-100 dark:border-zinc-800 ${ai === 0 ?"border-t-2 border-t-zinc-200 dark:border-t-zinc-700" : ""}`}
                >
                  <td className="p-2 sticky left-0 bg-white dark:bg-zinc-900 z-10">
                    <div className="flex items-center gap-2">
                      {ai === 0 && (
                        <span className="font-semibold text-zinc-800 dark:text-zinc-200">{cat.category}</span>
                      )}
                      {ai !== 0 && <span className="pl-4" />}
                      <span className="text-zinc-500 dark:text-zinc-400 capitalize">{action}</span>
                    </div>
                  </td>
                  {ROLES.map((role) => {
                    const permKey = `${key}:${action}`;
                    const checked = matrix[role.name]?.[permKey] ?? false;
                    return (
                      <td key={role.name} className="p-2 text-center">
                        <label className="inline-flex items-center justify-center">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggle(role.name, permKey)}
                            className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-600 text-blue-600 focus:ring-blue-500 dark:bg-zinc-700"
                          />
                        </label>
                      </td>
                    );
                  })}
                </tr>
              ));
            })}
          </tbody>
        </table></div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex gap-6 text-xs text-zinc-500 dark:text-zinc-400">
        <span className="flex items-center gap-1">
          <input type="checkbox" checked readOnly className="w-3 h-3 rounded text-blue-600" /> Granted
        </span>
        <span className="flex items-center gap-1">
          <input type="checkbox" readOnly className="w-3 h-3 rounded" /> Denied
        </span>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Audit Trail Tab                                                    */
/* ================================================================== */
function AuditTrailTab() {
  const [filterAction, setFilterAction] = useState("All");
  const [filterUser, setFilterUser] = useState("All");
  const [searchTarget, setSearchTarget] = useState("");

  const actionTypes = useMemo(
    () => Array.from(new Set(AUDIT_LOG.map((e) => e.action))).sort(),
    []
  );

  const auditUsers = useMemo(
    () => Array.from(new Set(AUDIT_LOG.map((e) => e.user))).sort(),
    []
  );

  const filtered = useMemo(() => {
    return AUDIT_LOG.filter((e) => {
      const matchAction = filterAction === "All" || e.action === filterAction;
      const matchUser = filterUser === "All" || e.user === filterUser;
      const matchTarget =
        !searchTarget || e.target.toLowerCase().includes(searchTarget.toLowerCase());
      return matchAction && matchUser && matchTarget;
    });
  }, [filterAction, filterUser, searchTarget]);

  const actionColor = (action: string) => {
    if (action.includes("Created") || action.includes("Added"))
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300";
    if (action.includes("Modified"))
      return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300";
    if (action.includes("Deactivated") || action.includes("Locked"))
      return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
    if (action.includes("Reset"))
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
    return "bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300";
  };

  const actionIcon = (action: string) => {
    if (action.includes("Created") || action.includes("Added")) return "+";
    if (action.includes("Modified")) return "~";
    if (action.includes("Deactivated") || action.includes("Locked")) return "!";
    if (action.includes("Reset")) return "*";
    return "?";
  };

  return (
    <div className="card p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">Audit Trail</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Recent administrative actions log -- {AUDIT_LOG.length} total entries
          </p>
        </div>
        <button className="btn-secondary text-sm">Export CSV</button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          type="text"
          placeholder="Search target..."
          value={searchTarget}
          onChange={(e) => setSearchTarget(e.target.value)}
          className="input w-full sm:w-48"
        />
        <select value={filterAction} onChange={(e) => setFilterAction(e.target.value)} className="select">
          <option value="All">All Actions</option>
          {actionTypes.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select value={filterUser} onChange={(e) => setFilterUser(e.target.value)} className="select">
          <option value="All">All Admins</option>
          {auditUsers.map((u) => (
            <option key={u} value={u}>{u}</option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto">
        <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-sm">
          <thead>
            <tr className="table-header">
              <th className="text-center p-3 font-semibold w-10"></th>
              <th className="text-left p-3 font-semibold">Timestamp</th>
              <th className="text-left p-3 font-semibold">Admin User</th>
              <th className="text-left p-3 font-semibold">Action</th>
              <th className="text-left p-3 font-semibold">Target</th>
              <th className="text-left p-3 font-semibold">IP Address</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((entry) => (
              <tr key={entry.id} className="table-row border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                <td className="p-3 text-center">
                  <span className={`${actionColor(entry.action)} inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold`}>
                    {actionIcon(entry.action)}
                  </span>
                </td>
                <td className="p-3 text-zinc-500 dark:text-zinc-400 whitespace-nowrap font-mono text-xs">
                  {entry.timestamp}
                </td>
                <td className="p-3 font-medium text-zinc-900 dark:text-white">{entry.user}</td>
                <td className="p-3">
                  <span className={`${actionColor(entry.action)} inline-block px-2 py-0.5 rounded-full text-xs font-medium`}>
                    {entry.action}
                  </span>
                </td>
                <td className="p-3 text-zinc-600 dark:text-zinc-300">{entry.target}</td>
                <td className="p-3 text-zinc-400 dark:text-zinc-500 font-mono text-xs">{entry.ip}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        {filtered.length === 0 && (
          <div className="text-center py-6 sm:py-12">
            <p className="text-zinc-400 dark:text-zinc-500 text-lg mb-1">No audit entries found</p>
            <p className="text-zinc-300 dark:text-zinc-600 text-sm">Try adjusting your filters.</p>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-zinc-400 dark:text-zinc-500">
          Showing {filtered.length} of {AUDIT_LOG.length} entries
        </p>
        <p className="text-xs text-zinc-400 dark:text-zinc-500">
          Retention policy: 90 days
        </p>
      </div>
    </div>
  );
}
