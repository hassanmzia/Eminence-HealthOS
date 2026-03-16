import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

// Create axios instance for auth
const authApi = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth header to requests
authApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
authApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE}/api/v1/users/token/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem("access_token", access);

          originalRequest.headers.Authorization = `Bearer ${access}`;
          return authApi(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user");
          window.location.href = "/login";
        }
      }
    }

    return Promise.reject(error);
  }
);

// Types
export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  display_name: string;
  role: "admin" | "doctor" | "nurse" | "technician" | "receptionist" | "viewer";
  phone?: string;
  department?: string;
  title?: string;
  license_number?: string;
  specialty?: string;
  is_active: boolean;
  is_verified: boolean;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

export interface UserPermissions {
  can_view_patients: boolean;
  can_edit_patients: boolean;
  can_view_clinical_data: boolean;
  can_edit_clinical_data: boolean;
  can_manage_devices: boolean;
  can_manage_users: boolean;
  can_view_analytics: boolean;
  can_manage_alerts: boolean;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginResponse {
  user: User;
  permissions: UserPermissions;
  tokens: AuthTokens;
}

export interface UserListResponse {
  total: number;
  limit: number;
  offset: number;
  results: User[];
}

export interface AuditLog {
  id: number;
  user: number;
  user_email: string;
  user_name: string;
  action: string;
  resource_type: string;
  resource_id: string;
  description: string;
  ip_address?: string;
  user_agent?: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface AuditLogListResponse {
  total: number;
  limit: number;
  offset: number;
  results: AuditLog[];
}

export interface UserStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  by_role: Record<string, number>;
  by_department: Record<string, number>;
  recent_logins_24h: number;
}

// Role display names
export const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  doctor: "Doctor/Physician",
  nurse: "Nurse",
  technician: "Lab Technician",
  receptionist: "Receptionist",
  viewer: "Read-Only Viewer",
};

// Department display names
export const DEPARTMENT_LABELS: Record<string, string> = {
  general: "General Medicine",
  cardiology: "Cardiology",
  neurology: "Neurology",
  pediatrics: "Pediatrics",
  oncology: "Oncology",
  emergency: "Emergency",
  icu: "Intensive Care Unit",
  surgery: "Surgery",
  radiology: "Radiology",
  laboratory: "Laboratory",
  pharmacy: "Pharmacy",
  other: "Other",
};

// Auth functions
export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await authApi.post<LoginResponse>("/api/v1/users/login/", {
    email,
    password,
  });

  // Store tokens and user
  localStorage.setItem("access_token", response.data.tokens.access);
  localStorage.setItem("refresh_token", response.data.tokens.refresh);
  localStorage.setItem("user", JSON.stringify(response.data.user));
  localStorage.setItem("permissions", JSON.stringify(response.data.permissions));

  return response.data;
}

export async function register(data: {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  phone?: string;
}): Promise<{ user: User; tokens: AuthTokens }> {
  const response = await authApi.post("/api/v1/users/register/", data);

  // Store tokens and user
  localStorage.setItem("access_token", response.data.tokens.access);
  localStorage.setItem("refresh_token", response.data.tokens.refresh);
  localStorage.setItem("user", JSON.stringify(response.data.user));

  return response.data;
}

export async function logout(): Promise<void> {
  const refreshToken = localStorage.getItem("refresh_token");

  try {
    if (refreshToken) {
      await authApi.post("/api/v1/users/logout/", { refresh: refreshToken });
    }
  } finally {
    // Clear local storage regardless of API response
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    localStorage.removeItem("permissions");
  }
}

export async function getCurrentUser(): Promise<{ user: User; permissions: UserPermissions }> {
  const response = await authApi.get("/api/v1/users/me/");
  return response.data;
}

export async function updateProfile(data: Partial<User>): Promise<User> {
  const response = await authApi.put("/api/v1/users/me/", data);
  localStorage.setItem("user", JSON.stringify(response.data));
  return response.data;
}

export async function changePassword(data: {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}): Promise<{ message: string }> {
  const response = await authApi.post("/api/v1/users/me/change-password/", data);
  return response.data;
}

// User management (admin)
export async function fetchUsers(params?: {
  search?: string;
  role?: string;
  department?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<UserListResponse> {
  const response = await authApi.get<UserListResponse>("/api/v1/users/", { params });
  return response.data;
}

export async function fetchUser(userId: number): Promise<User> {
  const response = await authApi.get<User>(`/api/v1/users/${userId}/`);
  return response.data;
}

export async function createUser(data: {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  role: string;
  phone?: string;
  department?: string;
  title?: string;
  license_number?: string;
  specialty?: string;
}): Promise<User> {
  const response = await authApi.post<User>("/api/v1/users/", data);
  return response.data;
}

export async function updateUser(userId: number, data: Partial<User>): Promise<User> {
  const response = await authApi.put<User>(`/api/v1/users/${userId}/`, data);
  return response.data;
}

export async function deleteUser(userId: number): Promise<void> {
  await authApi.delete(`/api/v1/users/${userId}/`);
}

export async function resetUserPassword(userId: number, newPassword: string): Promise<{ message: string }> {
  const response = await authApi.post(`/api/v1/users/${userId}/reset-password/`, {
    new_password: newPassword,
  });
  return response.data;
}

export async function toggleUserStatus(userId: number): Promise<{ message: string; is_active: boolean }> {
  const response = await authApi.post(`/api/v1/users/${userId}/toggle-status/`);
  return response.data;
}

// Audit logs (admin)
export async function fetchAuditLogs(params?: {
  user_id?: number;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditLogListResponse> {
  const response = await authApi.get<AuditLogListResponse>("/api/v1/users/audit-logs/", { params });
  return response.data;
}

// User stats (admin)
export async function fetchUserStats(): Promise<UserStats> {
  const response = await authApi.get<UserStats>("/api/v1/users/stats/");
  return response.data;
}

// Helper functions
export function getStoredUser(): User | null {
  const userStr = localStorage.getItem("user");
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }
  return null;
}

export function getStoredPermissions(): UserPermissions | null {
  const permStr = localStorage.getItem("permissions");
  if (permStr) {
    try {
      return JSON.parse(permStr);
    } catch {
      return null;
    }
  }
  return null;
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("access_token");
}

export { authApi };
