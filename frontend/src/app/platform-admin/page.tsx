"use client";

import { useState, useEffect, FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface OrgData {
  id: string;
  name: string;
  slug: string;
  tier: string;
  hipaa_baa_signed: boolean;
  user_count: number;
  patient_count: number;
  created_at: string;
}

const TIER_COLORS: Record<string, string> = {
  starter: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  standard: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  enterprise: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
};

function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

export default function PlatformAdminPage() {
  const { user, isSuperAdmin } = useAuth();
  const [orgs, setOrgs] = useState<OrgData[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filterTier, setFilterTier] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [newTier, setNewTier] = useState("enterprise");
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminPassword, setNewAdminPassword] = useState("");
  const [newAdminName, setNewAdminName] = useState("");
  const [newHipaa, setNewHipaa] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createLoading, setCreateLoading] = useState(false);

  async function fetchOrgs() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (search) params.set("search", search);
      if (filterTier) params.set("tier", filterTier);

      const res = await fetch(`/api/v1/organizations/?${params}`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setOrgs(data.organizations || []);
        setTotal(data.total || 0);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }

  useEffect(() => { fetchOrgs(); }, [page, search, filterTier]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreateError("");
    setCreateLoading(true);

    try {
      const body: Record<string, unknown> = {
        name: newName,
        slug: newSlug,
        tier: newTier,
        hipaa_baa_signed: newHipaa,
      };
      if (newAdminEmail) {
        body.admin_email = newAdminEmail;
        body.admin_password = newAdminPassword;
        body.admin_full_name = newAdminName;
      }

      const res = await fetch("/api/v1/organizations/", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setCreateError(data.detail || "Failed to create organization");
        setCreateLoading(false);
        return;
      }

      setShowCreate(false);
      setNewName(""); setNewSlug(""); setNewTier("enterprise");
      setNewAdminEmail(""); setNewAdminPassword(""); setNewAdminName("");
      setNewHipaa(false);
      fetchOrgs();
    } catch {
      setCreateError("Unable to connect to server");
    }
    setCreateLoading(false);
  }

  async function handleUpdateTier(orgId: string, tier: string) {
    await fetch(`/api/v1/organizations/${orgId}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ tier }),
    });
    fetchOrgs();
  }

  async function handleToggleHipaa(orgId: string, current: boolean) {
    await fetch(`/api/v1/organizations/${orgId}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ hipaa_baa_signed: !current }),
    });
    fetchOrgs();
  }

  if (!isSuperAdmin) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">Super Admin access required</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Platform Administration</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Manage all organizations on the Eminence HealthOS platform
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-teal-500 to-cyan-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-teal-500/20 hover:from-teal-400 hover:to-cyan-500"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Provision Organization
        </button>
      </div>

      {/* Platform Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Organizations</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{total}</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Enterprise</p>
          <p className="text-lg font-bold text-purple-600">{orgs.filter(o => o.tier === "enterprise").length}</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Standard</p>
          <p className="text-lg font-bold text-blue-600">{orgs.filter(o => o.tier === "standard").length}</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Starter</p>
          <p className="text-lg font-bold text-gray-600">{orgs.filter(o => o.tier === "starter").length}</p>
        </div>
      </div>

      {/* Create Organization Form */}
      {showCreate && (
        <div className="card !p-5 animate-fade-in-up border-teal-500/30">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Provision New Organization (Enterprise)</h2>
          {createError && (
            <div className="mb-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-600 dark:text-red-400">
              {createError}
            </div>
          )}
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Organization Name</label>
              <input
                required
                value={newName}
                onChange={(e) => { setNewName(e.target.value); setNewSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")); }}
                placeholder="St. Mary's Health System"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">URL Slug</label>
              <input
                required
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                placeholder="st-marys"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Tier</label>
              <select
                value={newTier}
                onChange={(e) => setNewTier(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:outline-none"
              >
                <option value="starter">Starter</option>
                <option value="standard">Standard</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>
            <div className="flex items-end gap-3">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input type="checkbox" checked={newHipaa} onChange={(e) => setNewHipaa(e.target.checked)} className="rounded" />
                HIPAA BAA Signed
              </label>
            </div>

            <div className="sm:col-span-2">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Initial Admin User (optional)</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Admin Full Name</label>
              <input
                value={newAdminName}
                onChange={(e) => setNewAdminName(e.target.value)}
                placeholder="Dr. Jane Smith"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Admin Email</label>
              <input
                type="email"
                value={newAdminEmail}
                onChange={(e) => setNewAdminEmail(e.target.value)}
                placeholder="admin@stmarys.org"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Admin Password</label>
              <input
                type="password"
                minLength={8}
                value={newAdminPassword}
                onChange={(e) => setNewAdminPassword(e.target.value)}
                placeholder="Min. 8 characters"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:outline-none"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={createLoading}
                className="rounded-lg bg-teal-600 px-6 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:opacity-50"
              >
                {createLoading ? "Creating..." : "Create Organization"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Search & Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search organizations..."
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>
        <select
          value={filterTier}
          onChange={(e) => { setFilterTier(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
        >
          <option value="">All Tiers</option>
          <option value="starter">Starter</option>
          <option value="standard">Standard</option>
          <option value="enterprise">Enterprise</option>
        </select>
      </div>

      {/* Organizations Table */}
      <div className="card overflow-hidden !p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Organization</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Slug</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Tier</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Users</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">HIPAA BAA</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Created</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    <div className="h-6 w-6 mx-auto animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
                  </td>
                </tr>
              ) : orgs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">No organizations found</td>
                </tr>
              ) : orgs.map((org) => (
                <tr key={org.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900 dark:text-gray-100">{org.name}</p>
                    <p className="text-[11px] text-gray-500 font-mono">{org.id.slice(0, 8)}...</p>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600 dark:text-gray-400">{org.slug}</td>
                  <td className="px-4 py-3">
                    <select
                      value={org.tier}
                      onChange={(e) => handleUpdateTier(org.id, e.target.value)}
                      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold border-0 cursor-pointer ${TIER_COLORS[org.tier] || TIER_COLORS.starter}`}
                    >
                      <option value="starter">Starter</option>
                      <option value="standard">Standard</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{org.user_count}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleToggleHipaa(org.id, org.hipaa_baa_signed)} className="text-xs">
                      {org.hipaa_baa_signed
                        ? <span className="text-emerald-600 font-semibold">Signed</span>
                        : <span className="text-red-500 font-semibold">Not Signed</span>
                      }
                    </button>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{org.created_at ? new Date(org.created_at).toLocaleDateString() : "—"}</td>
                  <td className="px-4 py-3">
                    <button className="text-xs text-teal-600 hover:text-teal-500 font-medium">Manage</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > 20 && (
          <div className="flex items-center justify-between border-t border-gray-200 dark:border-gray-700 px-4 py-3">
            <p className="text-xs text-gray-500">
              Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {total}
            </p>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1 text-xs disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={page * 20 >= total}
                onClick={() => setPage(page + 1)}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1 text-xs disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
