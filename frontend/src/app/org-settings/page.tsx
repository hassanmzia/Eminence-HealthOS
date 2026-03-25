"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface OrgSettings {
  id: string;
  name: string;
  slug: string;
  tier: string;
  hipaa_baa_signed: boolean;
  settings: Record<string, unknown>;
  user_count: number;
  created_at: string;
}

function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

const TIER_INFO: Record<string, { label: string; color: string; limits: string }> = {
  starter: { label: "Starter", color: "text-gray-600 bg-gray-100 dark:bg-gray-800", limits: "5 users, 100 patients" },
  standard: { label: "Standard", color: "text-blue-600 bg-blue-100 dark:bg-blue-900/30", limits: "50 users, unlimited patients" },
  enterprise: { label: "Enterprise", color: "text-purple-600 bg-purple-100 dark:bg-purple-900/30", limits: "Unlimited users & patients" },
};

export default function OrgSettingsPage() {
  const { user, isAdmin } = useAuth();
  const [org, setOrg] = useState<OrgSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editName, setEditName] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  async function fetchOrg() {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/organizations/me/settings", { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setOrg(data);
        setEditName(data.name);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }

  useEffect(() => { fetchOrg(); }, []);

  async function handleSave() {
    if (!editName || editName === org?.name) return;
    setSaving(true);
    setSuccessMsg("");
    try {
      const res = await fetch("/api/v1/organizations/me/settings", {
        method: "PATCH",
        headers: getAuthHeaders(),
        body: JSON.stringify({ name: editName }),
      });
      if (res.ok) {
        setSuccessMsg("Organization settings updated");
        fetchOrg();
      }
    } catch { /* ignore */ }
    setSaving(false);
  }

  if (!isAdmin) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">Admin access required to manage organization settings</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
      </div>
    );
  }

  const tierInfo = TIER_INFO[org?.tier || "starter"] || TIER_INFO.starter;

  return (
    <div className="space-y-6 bg-mesh min-h-full max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Organization Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Manage your organization&apos;s configuration and subscription
        </p>
      </div>

      {successMsg && (
        <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 p-3 text-sm text-emerald-700 dark:text-emerald-400">
          {successMsg}
        </div>
      )}

      {/* Organization Info */}
      <div className="card !p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">General</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Organization Name</label>
            <input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">URL Slug</label>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 px-3 py-2 text-sm text-gray-500">
              {org?.slug}
            </div>
            <p className="text-[11px] text-gray-400 mt-1">Contact support to change your slug</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Organization ID</label>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 px-3 py-2 text-sm text-gray-500 font-mono">
              {org?.id}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Created</label>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 px-3 py-2 text-sm text-gray-500">
              {org?.created_at ? new Date(org.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "—"}
            </div>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving || editName === org?.name}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      {/* Subscription & Plan */}
      <div className="card !p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Subscription</h2>
        <div className="flex items-start gap-4">
          <div className={`rounded-lg px-4 py-3 ${tierInfo.color}`}>
            <p className="text-lg font-bold">{tierInfo.label}</p>
            <p className="text-xs opacity-75">{tierInfo.limits}</p>
          </div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
              <span className="text-xs text-gray-600 dark:text-gray-400">Active Users</span>
              <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{org?.user_count ?? 0}</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
              <span className="text-xs text-gray-600 dark:text-gray-400">HIPAA BAA</span>
              <span className={`text-sm font-bold ${org?.hipaa_baa_signed ? "text-emerald-600" : "text-red-500"}`}>
                {org?.hipaa_baa_signed ? "Signed" : "Not Signed"}
              </span>
            </div>
          </div>
        </div>
        {org?.tier !== "enterprise" && (
          <div className="mt-4 rounded-lg border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/10 p-4">
            <p className="text-sm font-medium text-purple-700 dark:text-purple-300">Upgrade to Enterprise</p>
            <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
              Get unlimited users, dedicated infrastructure, HIPAA BAA, custom integrations, and 24/7 support.
              Contact <span className="font-medium">sales@eminence.health</span> to upgrade.
            </p>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="card !p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-4">Administration</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {[
            {
              label: "User Management",
              description: "Add, edit, and manage staff accounts",
              href: "/admin",
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
              ),
              color: "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400",
            },
            {
              label: "Hospital & Departments",
              description: "Configure facilities and departments",
              href: "/org-settings/hospitals",
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0H5m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
              ),
              color: "bg-healthos-100 dark:bg-healthos-900/30 text-healthos-600 dark:text-healthos-400",
            },
            {
              label: "Compliance & Audit",
              description: "HIPAA compliance tracking and audit logs",
              href: "/compliance",
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
              ),
              color: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400",
            },
            {
              label: "Authentication",
              description: "SSO, MFA, and session management",
              href: "/org-settings/authentication",
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
              ),
              color: "bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400",
            },
          ].map((item) => (
            <a key={item.label} href={item.href} className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-700 p-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition">
              <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${item.color}`}>
                {item.icon}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.label}</p>
                <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.description}</p>
              </div>
              <svg className="ml-auto w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
