import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUsers,
  fetchUserStats,
  fetchAuditLogs,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
  toggleUserStatus,
  ROLE_LABELS,
  DEPARTMENT_LABELS,
  type User,
  type AuditLog,
} from "../lib/authApi";
import { useAuth } from "../context/AuthContext";

type Tab = "users" | "audit" | "stats";

// User Form Modal
function UserFormModal({
  user,
  onClose,
  onSuccess,
}: {
  user: User | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!user;

  const [formData, setFormData] = useState({
    email: user?.email || "",
    password: "",
    password_confirm: "",
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    role: user?.role || "viewer",
    phone: user?.phone || "",
    department: user?.department || "",
    title: user?.title || "",
    license_number: user?.license_number || "",
    specialty: user?.specialty || "",
    is_active: user?.is_active ?? true,
    is_verified: user?.is_verified ?? false,
  });

  const [error, setError] = useState("");

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onSuccess();
    },
    onError: (err: unknown) => {
      if (err && typeof err === "object" && "response" in err) {
        const axiosError = err as { response?: { data?: Record<string, string[]> } };
        const data = axiosError.response?.data;
        if (data) {
          const firstError = Object.values(data)[0];
          setError(Array.isArray(firstError) ? firstError[0] : String(firstError));
        }
      } else {
        setError("Failed to create user");
      }
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<User>) => updateUser(user!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onSuccess();
    },
    onError: () => setError("Failed to update user"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!isEdit && formData.password !== formData.password_confirm) {
      setError("Passwords do not match");
      return;
    }

    if (isEdit) {
      const { email, password, password_confirm, ...updateData } = formData;
      updateMutation.mutate(updateData);
    } else {
      createMutation.mutate(formData);
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: "rgba(0,0,0,0.5)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000,
    }}>
      <div style={{
        background: "white",
        borderRadius: 12,
        padding: 24,
        width: "100%",
        maxWidth: 500,
        maxHeight: "90vh",
        overflow: "auto",
      }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 18, fontWeight: 600 }}>
          {isEdit ? "Edit User" : "Create User"}
        </h2>

        {error && (
          <div style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 8,
            padding: 12,
            marginBottom: 16,
            color: "#dc2626",
            fontSize: 13,
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>First Name *</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                required
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Last Name *</label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                required
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              />
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Email *</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              disabled={isEdit}
              style={{
                width: "100%",
                padding: 8,
                border: "1px solid #ddd",
                borderRadius: 6,
                fontSize: 13,
                boxSizing: "border-box",
                background: isEdit ? "#f3f4f6" : "white",
              }}
            />
          </div>

          {!isEdit && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Password *</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Confirm Password *</label>
                <input
                  type="password"
                  value={formData.password_confirm}
                  onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })}
                  required
                  style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
                />
              </div>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Role *</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value as User["role"] })}
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              >
                {Object.entries(ROLE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Department</label>
              <select
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              >
                <option value="">Select department...</option>
                {Object.entries(DEPARTMENT_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Title</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g., MD, RN"
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Phone</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>License Number</label>
              <input
                type="text"
                value={formData.license_number}
                onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Specialty</label>
              <input
                type="text"
                value={formData.specialty}
                onChange={(e) => setFormData({ ...formData, specialty: e.target.value })}
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              />
            </div>
          </div>

          {isEdit && (
            <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
                Active
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={formData.is_verified}
                  onChange={(e) => setFormData({ ...formData, is_verified: e.target.checked })}
                />
                Verified
              </label>
            </div>
          )}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 20 }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: "8px 16px", border: "1px solid #ddd", borderRadius: 6, background: "white", cursor: "pointer" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              style={{
                padding: "8px 16px",
                border: "none",
                borderRadius: 6,
                background: isLoading ? "#9ca3af" : "#3b82f6",
                color: "white",
                cursor: isLoading ? "not-allowed" : "pointer",
              }}
            >
              {isLoading ? "Saving..." : isEdit ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Reset Password Modal
function ResetPasswordModal({
  user,
  onClose,
  onSuccess,
}: {
  user: User;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => resetUserPassword(user.id, password),
    onSuccess: () => onSuccess(),
    onError: () => setError("Failed to reset password"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    mutation.mutate();
  };

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: "rgba(0,0,0,0.5)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000,
    }}>
      <div style={{ background: "white", borderRadius: 12, padding: 24, width: "100%", maxWidth: 400 }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 18 }}>Reset Password</h2>
        <p style={{ fontSize: 13, color: "#666", marginBottom: 16 }}>
          Reset password for <strong>{user.full_name}</strong>
        </p>

        {error && (
          <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: 12, marginBottom: 16, color: "#dc2626", fontSize: 13 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>New Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
            />
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
            <button type="button" onClick={onClose} style={{ padding: "8px 16px", border: "1px solid #ddd", borderRadius: 6, background: "white", cursor: "pointer" }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              style={{ padding: "8px 16px", border: "none", borderRadius: 6, background: mutation.isPending ? "#9ca3af" : "#ef4444", color: "white", cursor: mutation.isPending ? "not-allowed" : "pointer" }}
            >
              {mutation.isPending ? "Resetting..." : "Reset Password"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Users Tab
function UsersTab() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userToResetPassword, setUserToResetPassword] = useState<User | null>(null);

  const usersQ = useQuery({
    queryKey: ["users", search, roleFilter],
    queryFn: () => fetchUsers({ search: search || undefined, role: roleFilter || undefined, limit: 100 }),
  });

  const toggleMutation = useMutation({
    mutationFn: toggleUserStatus,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  const handleEdit = (user: User) => {
    setSelectedUser(user);
    setShowForm(true);
  };

  const handleDelete = (user: User) => {
    if (confirm(`Are you sure you want to delete ${user.full_name}?`)) {
      deleteMutation.mutate(user.id);
    }
  };

  const roleColors: Record<string, string> = {
    admin: "#dc2626",
    doctor: "#2563eb",
    nurse: "#059669",
    technician: "#7c3aed",
    receptionist: "#d97706",
    viewer: "#6b7280",
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, width: 200 }}
          />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13 }}
          >
            <option value="">All roles</option>
            {Object.entries(ROLE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => { setSelectedUser(null); setShowForm(true); }}
          style={{ padding: "8px 16px", background: "#3b82f6", color: "white", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
        >
          + Add User
        </button>
      </div>

      {usersQ.isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading users...</div>
      ) : usersQ.error ? (
        <div style={{ padding: 20, background: "#fef2f2", borderRadius: 8, color: "#ef4444" }}>
          Error loading users
        </div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Name</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Email</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Role</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Department</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Status</th>
              <th style={{ padding: 12, textAlign: "right", fontWeight: 600 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {usersQ.data?.results.map((user) => (
              <tr key={user.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: 12 }}>
                  <div style={{ fontWeight: 500 }}>{user.display_name}</div>
                  {user.specialty && <div style={{ fontSize: 11, color: "#666" }}>{user.specialty}</div>}
                </td>
                <td style={{ padding: 12, color: "#666" }}>{user.email}</td>
                <td style={{ padding: 12 }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 500,
                    background: `${roleColors[user.role]}15`,
                    color: roleColors[user.role],
                  }}>
                    {ROLE_LABELS[user.role]}
                  </span>
                </td>
                <td style={{ padding: 12, color: "#666" }}>{user.department ? DEPARTMENT_LABELS[user.department] : "-"}</td>
                <td style={{ padding: 12 }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 500,
                    background: user.is_active ? "#dcfce7" : "#fee2e2",
                    color: user.is_active ? "#166534" : "#991b1b",
                  }}>
                    {user.is_active ? "Active" : "Disabled"}
                  </span>
                </td>
                <td style={{ padding: 12, textAlign: "right" }}>
                  <div style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}>
                    <button
                      onClick={() => handleEdit(user)}
                      style={{ padding: "4px 8px", border: "1px solid #ddd", borderRadius: 4, background: "white", cursor: "pointer", fontSize: 11 }}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setUserToResetPassword(user)}
                      style={{ padding: "4px 8px", border: "1px solid #ddd", borderRadius: 4, background: "white", cursor: "pointer", fontSize: 11 }}
                    >
                      Reset PW
                    </button>
                    {user.id !== currentUser?.id && (
                      <>
                        <button
                          onClick={() => toggleMutation.mutate(user.id)}
                          style={{ padding: "4px 8px", border: "1px solid #ddd", borderRadius: 4, background: "white", cursor: "pointer", fontSize: 11 }}
                        >
                          {user.is_active ? "Disable" : "Enable"}
                        </button>
                        <button
                          onClick={() => handleDelete(user)}
                          style={{ padding: "4px 8px", border: "1px solid #fecaca", borderRadius: 4, background: "#fef2f2", color: "#dc2626", cursor: "pointer", fontSize: 11 }}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showForm && (
        <UserFormModal
          user={selectedUser}
          onClose={() => { setShowForm(false); setSelectedUser(null); }}
          onSuccess={() => { setShowForm(false); setSelectedUser(null); }}
        />
      )}

      {userToResetPassword && (
        <ResetPasswordModal
          user={userToResetPassword}
          onClose={() => setUserToResetPassword(null)}
          onSuccess={() => setUserToResetPassword(null)}
        />
      )}
    </div>
  );
}

// Audit Log Tab
function AuditTab() {
  const [actionFilter, setActionFilter] = useState("");

  const logsQ = useQuery({
    queryKey: ["audit-logs", actionFilter],
    queryFn: () => fetchAuditLogs({ action: actionFilter || undefined, limit: 100 }),
  });

  const actionColors: Record<string, string> = {
    login: "#059669",
    logout: "#6b7280",
    create: "#2563eb",
    read: "#8b5cf6",
    update: "#d97706",
    delete: "#dc2626",
    export: "#0891b2",
    acknowledge: "#059669",
    other: "#6b7280",
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13 }}
        >
          <option value="">All actions</option>
          <option value="login">Login</option>
          <option value="logout">Logout</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
        </select>
      </div>

      {logsQ.isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading audit logs...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Timestamp</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>User</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Action</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Resource</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Description</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>IP Address</th>
            </tr>
          </thead>
          <tbody>
            {logsQ.data?.results.map((log: AuditLog) => (
              <tr key={log.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: 12, color: "#666" }}>{new Date(log.timestamp).toLocaleString()}</td>
                <td style={{ padding: 12 }}>{log.user_name || log.user_email || "-"}</td>
                <td style={{ padding: 12 }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 500,
                    background: `${actionColors[log.action]}15`,
                    color: actionColors[log.action],
                  }}>
                    {log.action}
                  </span>
                </td>
                <td style={{ padding: 12 }}>
                  {log.resource_type}
                  {log.resource_id && <span style={{ color: "#666" }}> #{log.resource_id}</span>}
                </td>
                <td style={{ padding: 12, color: "#666", maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {log.description || "-"}
                </td>
                <td style={{ padding: 12, color: "#666", fontSize: 11, fontFamily: "monospace" }}>{log.ip_address || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// Stats Tab
function StatsTab() {
  const statsQ = useQuery({
    queryKey: ["user-stats"],
    queryFn: fetchUserStats,
  });

  if (statsQ.isLoading) {
    return <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading stats...</div>;
  }

  if (!statsQ.data) return null;

  const stats = statsQ.data;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#3b82f6" }}>{stats.total_users}</div>
          <div style={{ fontSize: 12, color: "#666" }}>Total Users</div>
        </div>
        <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#10b981" }}>{stats.active_users}</div>
          <div style={{ fontSize: 12, color: "#666" }}>Active Users</div>
        </div>
        <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#ef4444" }}>{stats.inactive_users}</div>
          <div style={{ fontSize: 12, color: "#666" }}>Inactive Users</div>
        </div>
        <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#8b5cf6" }}>{stats.recent_logins_24h}</div>
          <div style={{ fontSize: 12, color: "#666" }}>Logins (24h)</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Users by Role</div>
          {Object.entries(stats.by_role).map(([role, count]) => (
            <div key={role} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f3f4f6" }}>
              <span>{ROLE_LABELS[role] || role}</span>
              <span style={{ fontWeight: 600 }}>{count}</span>
            </div>
          ))}
        </div>
        <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 12, padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Users by Department</div>
          {Object.entries(stats.by_department).length > 0 ? (
            Object.entries(stats.by_department).map(([dept, count]) => (
              <div key={dept} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f3f4f6" }}>
                <span>{DEPARTMENT_LABELS[dept] || dept}</span>
                <span style={{ fontWeight: 600 }}>{count}</span>
              </div>
            ))
          ) : (
            <div style={{ color: "#999", fontSize: 13 }}>No department data</div>
          )}
        </div>
      </div>
    </div>
  );
}

export function UserManagement() {
  const [activeTab, setActiveTab] = useState<Tab>("users");

  const tabButtonStyle = (active: boolean) => ({
    padding: "8px 16px",
    borderRadius: 8,
    border: "none",
    background: active ? "#3b82f6" : "transparent",
    color: active ? "white" : "#666",
    cursor: "pointer",
    fontWeight: active ? 600 : 400,
    fontSize: 14,
  });

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>User Management</h2>
        <p style={{ margin: "4px 0 0", fontSize: 12, color: "#666" }}>
          Manage users, roles, and view audit logs
        </p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button style={tabButtonStyle(activeTab === "users")} onClick={() => setActiveTab("users")}>Users</button>
        <button style={tabButtonStyle(activeTab === "audit")} onClick={() => setActiveTab("audit")}>Audit Log</button>
        <button style={tabButtonStyle(activeTab === "stats")} onClick={() => setActiveTab("stats")}>Statistics</button>
      </div>

      {activeTab === "users" && <UsersTab />}
      {activeTab === "audit" && <AuditTab />}
      {activeTab === "stats" && <StatsTab />}
    </div>
  );
}
