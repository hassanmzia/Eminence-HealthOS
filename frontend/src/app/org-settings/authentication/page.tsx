"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  fetchAuthConfigs,
  createAuthConfig,
  updateAuthConfig,
  deleteAuthConfig,
  fetchSessions,
  revokeSession,
  revokeAllSessions,
  type AuthConfigResponse,
  type SessionResponse,
} from "@/lib/platform-api";

/* ── icons ─────────────────────────────────────────────────────────────────── */
const IconBack = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
);
const IconPlus = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
);
const IconShield = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
);

const AUTH_METHOD_LABELS: Record<string, string> = {
  saml_sso: "SAML SSO",
  oidc_sso: "OpenID Connect SSO",
  totp_mfa: "TOTP MFA (Authenticator App)",
  sms_mfa: "SMS MFA",
  email_mfa: "Email MFA",
  password: "Password",
  api_key: "API Key",
};

const AUTH_METHOD_OPTIONS = Object.entries(AUTH_METHOD_LABELS);

/* ── Create Auth Config Modal ──────────────────────────────────────────────── */
function CreateAuthConfigModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [method, setMethod] = useState("totp_mfa");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await createAuthConfig({ auth_method: method, is_enabled: true });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create auth config");
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-md mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">Add Auth Method</h3>
        {error && <div className="mb-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-2 text-sm text-red-700 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Authentication Method</label>
            <select value={method} onChange={(e) => setMethod(e.target.value)} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
              {AUTH_METHOD_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500 disabled:opacity-50">{saving ? "Adding..." : "Add Method"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Auth Config Card ──────────────────────────────────────────────────────── */
function AuthConfigCard({ config, onRefresh }: { config: AuthConfigResponse; onRefresh: () => void }) {
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleToggle = async () => {
    setToggling(true);
    try {
      await updateAuthConfig(config.id, { auth_method: config.auth_method, is_enabled: !config.is_enabled });
      onRefresh();
    } catch { /* ignore */ }
    setToggling(false);
  };

  const handleDelete = async () => {
    if (!confirm("Remove this authentication method?")) return;
    setDeleting(true);
    try {
      await deleteAuthConfig(config.id);
      onRefresh();
    } catch { /* ignore */ }
    setDeleting(false);
  };

  return (
    <div className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center gap-3">
        <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
          <IconShield />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{AUTH_METHOD_LABELS[config.auth_method] || config.auth_method}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {config.is_primary && <span className="text-healthos-600 dark:text-healthos-400 font-medium mr-2">Primary</span>}
            Added {new Date(config.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {/* Toggle */}
        <button onClick={handleToggle} disabled={toggling} className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${config.is_enabled ? "bg-healthos-600" : "bg-gray-300 dark:bg-gray-600"}`}>
          <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${config.is_enabled ? "translate-x-6" : "translate-x-1"}`} />
        </button>
        {/* Delete */}
        <button onClick={handleDelete} disabled={deleting} className="rounded-lg p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
        </button>
      </div>
    </div>
  );
}

/* ── Main Page ─────────────────────────────────────────────────────────────── */
export default function AuthenticationPage() {
  const { isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState<"methods" | "sessions">("methods");
  const [configs, setConfigs] = useState<AuthConfigResponse[]>([]);
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [revokingAll, setRevokingAll] = useState(false);

  const loadConfigs = useCallback(async () => {
    try { setConfigs(await fetchAuthConfigs()); } catch { /* ignore */ }
  }, []);

  const loadSessions = useCallback(async () => {
    try { setSessions(await fetchSessions()); } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadConfigs(), loadSessions()]).finally(() => setLoading(false));
  }, [loadConfigs, loadSessions]);

  const handleRevokeSession = async (id: string) => {
    try { await revokeSession(id); loadSessions(); } catch { /* ignore */ }
  };

  const handleRevokeAll = async () => {
    if (!confirm("Revoke all active sessions? All users will be logged out.")) return;
    setRevokingAll(true);
    try { await revokeAllSessions(); loadSessions(); } catch { /* ignore */ }
    setRevokingAll(false);
  };

  if (!isAdmin) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">Admin access required</p>
      </div>
    );
  }

  const tabs = [
    { key: "methods" as const, label: "Auth Methods" },
    { key: "sessions" as const, label: "Active Sessions" },
  ];

  return (
    <div className="space-y-6 bg-mesh min-h-full max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <a href="/org-settings" className="rounded-lg border border-gray-200 dark:border-gray-700 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition">
          <IconBack />
        </a>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Authentication</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">SSO, MFA, and session management</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)} className={`px-4 py-2 text-sm font-medium border-b-2 transition ${activeTab === t.key ? "border-healthos-600 text-healthos-600 dark:text-healthos-400" : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
        </div>
      ) : activeTab === "methods" ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500 transition">
              <IconPlus /> Add Auth Method
            </button>
          </div>
          {configs.length === 0 ? (
            <div className="card !p-8 text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400 mb-3">
                <IconShield />
              </div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">No auth methods configured</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-4">Add SSO or MFA methods to secure your organization.</p>
              <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500">
                <IconPlus /> Add Auth Method
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {configs.map((c) => (
                <AuthConfigCard key={c.id} config={c} onRefresh={loadConfigs} />
              ))}
            </div>
          )}
          <CreateAuthConfigModal open={showCreate} onClose={() => setShowCreate(false)} onCreated={loadConfigs} />
        </div>
      ) : (
        /* Sessions tab */
        <div className="space-y-4">
          {sessions.length > 0 && (
            <div className="flex justify-end">
              <button onClick={handleRevokeAll} disabled={revokingAll} className="rounded-lg border border-red-300 dark:border-red-700 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition disabled:opacity-50">
                {revokingAll ? "Revoking..." : "Revoke All Sessions"}
              </button>
            </div>
          )}
          {sessions.length === 0 ? (
            <div className="card !p-8 text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">No active sessions found.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.map((s) => (
                <div key={s.id} className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
                  <div>
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{s.ip_address || "Unknown IP"}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-sm">
                      {s.user_agent || "Unknown device"} · Last active {new Date(s.last_activity).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${s.is_active ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"}`}>
                      {s.is_active ? "Active" : "Expired"}
                    </span>
                    {s.is_active && (
                      <button onClick={() => handleRevokeSession(s.id)} className="rounded-lg px-3 py-1 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition">
                        Revoke
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
