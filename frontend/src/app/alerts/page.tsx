"use client";

import { useState, useEffect } from "react";
import { fetchAlerts, acknowledgeAlert, resolveAlert, type AlertData } from "@/lib/api";

const PRIORITY_CONFIG: Record<string, { badge: string; bg: string; icon: string }> = {
  critical: { badge: "badge-critical", bg: "bg-red-500", icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" },
  high: { badge: "badge-high", bg: "bg-orange-500", icon: "M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622A11.99 11.99 0 0020.402 6a11.959 11.959 0 01-8.402-3.286z" },
  moderate: { badge: "badge-moderate", bg: "bg-yellow-500", icon: "M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" },
  low: { badge: "badge-low", bg: "bg-emerald-500", icon: "M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" },
};

const STATUS_CONFIG: Record<string, { label: string; color: string; dotColor: string }> = {
  pending: { label: "Pending", color: "text-amber-700 bg-amber-50 ring-amber-600/20", dotColor: "bg-amber-500" },
  acknowledged: { label: "Acknowledged", color: "text-blue-700 bg-blue-50 ring-blue-600/20", dotColor: "bg-blue-500" },
  resolved: { label: "Resolved", color: "text-emerald-700 bg-emerald-50 ring-emerald-600/20", dotColor: "bg-emerald-500" },
  dismissed: { label: "Dismissed", color: "text-gray-600 bg-gray-50 ring-gray-500/20", dotColor: "bg-gray-400" },
};

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function AlertsPage() {
  const [priority, setPriority] = useState("");
  const [status, setStatus] = useState("");
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState<AlertData | null>(null);

  useEffect(() => {
    fetchAlerts({ priority: priority || undefined, status: status || undefined })
      .then(setAlerts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [priority, status]);

  // Distribution counts
  const priorityCounts = alerts.reduce<Record<string, number>>((acc, a) => {
    acc[a.priority] = (acc[a.priority] || 0) + 1;
    return acc;
  }, {});

  const statusCounts = alerts.reduce<Record<string, number>>((acc, a) => {
    acc[a.status] = (acc[a.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="text-sm text-gray-500">Monitor and manage clinical alerts across all patients</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 ring-1 ring-inset ring-emerald-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-emerald-700">Real-time</span>
          </div>
        </div>
      </div>

      {/* Priority stat cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(["critical", "high", "moderate", "low"] as const).map((level) => {
          const cfg = PRIORITY_CONFIG[level];
          const count = priorityCounts[level] || 0;
          return (
            <button
              key={level}
              onClick={() => setPriority(priority === level ? "" : level)}
              className={`metric-card text-left transition-all ${priority === level ? "ring-2 ring-healthos-500" : ""}`}
            >
              <div className={`absolute left-0 top-0 h-1 w-full rounded-t-xl ${cfg.bg}`} />
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">{level}</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-gray-900">{count}</p>
                </div>
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${level === "critical" ? "bg-red-50" : level === "high" ? "bg-orange-50" : level === "moderate" ? "bg-yellow-50" : "bg-emerald-50"}`}>
                  <svg className={`h-4.5 w-4.5 ${level === "critical" ? "text-red-600" : level === "high" ? "text-orange-600" : level === "moderate" ? "text-yellow-600" : "text-emerald-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={cfg.icon} />
                  </svg>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-md">
          <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            type="text"
            placeholder="Search alerts..."
            className="input !pl-10"
          />
        </div>
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="select !w-auto"
        >
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="moderate">Moderate</option>
          <option value="low">Low</option>
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="select !w-auto"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
        {(priority || status) && (
          <button
            onClick={() => { setPriority(""); setStatus(""); }}
            className="btn-ghost !px-3 !py-2 text-xs"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Alert list */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-start gap-4">
                <div className="skeleton-circle h-10 w-10" />
                <div className="flex-1 space-y-2">
                  <div className="skeleton-text w-2/3" />
                  <div className="skeleton-text w-1/3" />
                </div>
                <div className="skeleton h-6 w-20 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50">
            <svg className="h-7 w-7 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="mt-4 text-sm font-medium text-gray-900">All clear</p>
          <p className="mt-1 text-xs text-gray-500">No alerts match your current filters</p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert, i) => {
            const pcfg = PRIORITY_CONFIG[alert.priority] || PRIORITY_CONFIG.low;
            const scfg = STATUS_CONFIG[alert.status] || STATUS_CONFIG.pending;
            const isSelected = selectedAlert?.id === alert.id;
            return (
              <div
                key={alert.id}
                onClick={() => setSelectedAlert(isSelected ? null : alert)}
                className={`card card-hover cursor-pointer animate-fade-in-up ${isSelected ? "ring-2 ring-healthos-500 shadow-glow-blue" : ""}`}
                style={{ animationDelay: `${i * 0.03}s`, animationFillMode: "both" }}
              >
                <div className="flex items-start gap-4">
                  {/* Priority icon */}
                  <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${
                    alert.priority === "critical" ? "bg-red-50" :
                    alert.priority === "high" ? "bg-orange-50" :
                    alert.priority === "moderate" ? "bg-yellow-50" : "bg-emerald-50"
                  }`}>
                    <svg className={`h-5 w-5 ${
                      alert.priority === "critical" ? "text-red-600" :
                      alert.priority === "high" ? "text-orange-600" :
                      alert.priority === "moderate" ? "text-yellow-600" : "text-emerald-600"
                    }`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d={pcfg.icon} />
                    </svg>
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{alert.message || `${alert.alert_type} Alert`}</p>
                        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                          <span className={pcfg.badge}>{alert.priority}</span>
                          <span>&middot;</span>
                          <span className="capitalize">{alert.alert_type.replace(/_/g, " ")}</span>
                          {alert.created_at && (
                            <>
                              <span>&middot;</span>
                              <span>{timeAgo(alert.created_at)}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${scfg.color}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${scfg.dotColor}`} />
                        {scfg.label}
                      </span>
                    </div>

                    {/* Expanded details */}
                    {isSelected && (
                      <div className="mt-4 animate-fade-in rounded-lg bg-gray-50 p-4">
                        <div className="grid grid-cols-2 gap-4 text-xs">
                          <div>
                            <p className="font-semibold text-gray-400 uppercase tracking-wider">Alert ID</p>
                            <p className="mt-1 font-mono text-gray-700">{alert.id.slice(0, 8)}...</p>
                          </div>
                          <div>
                            <p className="font-semibold text-gray-400 uppercase tracking-wider">Type</p>
                            <p className="mt-1 text-gray-700 capitalize">{alert.alert_type.replace(/_/g, " ")}</p>
                          </div>
                          <div>
                            <p className="font-semibold text-gray-400 uppercase tracking-wider">Created</p>
                            <p className="mt-1 text-gray-700">{alert.created_at ? new Date(alert.created_at).toLocaleString() : "—"}</p>
                          </div>
                          <div>
                            <p className="font-semibold text-gray-400 uppercase tracking-wider">Status</p>
                            <p className="mt-1 text-gray-700 capitalize">{alert.status}</p>
                          </div>
                        </div>
                        <div className="mt-4 flex gap-2">
                          {alert.status !== "acknowledged" && alert.status !== "resolved" && (
                            <button
                              onClick={(e) => { e.stopPropagation(); acknowledgeAlert(alert.id).then((updated) => { setAlerts((prev) => prev.map((a) => a.id === alert.id ? { ...a, status: updated.status || "acknowledged" } : a)); setSelectedAlert(null); }).catch(() => {}); }}
                              className="btn-primary !py-1.5 !px-3 !text-xs"
                            >Acknowledge</button>
                          )}
                          {alert.status !== "resolved" && (
                            <button
                              onClick={(e) => { e.stopPropagation(); resolveAlert(alert.id).then((updated) => { setAlerts((prev) => prev.map((a) => a.id === alert.id ? { ...a, status: updated.status || "resolved" } : a)); setSelectedAlert(null); }).catch(() => {}); }}
                              className="btn-secondary !py-1.5 !px-3 !text-xs"
                            >Resolve</button>
                          )}
                          <button
                            onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(alert.id); }}
                            className="btn-ghost !py-1.5 !px-3 !text-xs"
                          >Copy ID</button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer stats */}
      {!loading && alerts.length > 0 && (
        <div className="flex items-center justify-between rounded-xl bg-gray-50 px-6 py-3 text-xs text-gray-500">
          <span>Showing {alerts.length} alerts</span>
          <div className="flex gap-4">
            <span>{statusCounts.pending || 0} pending</span>
            <span>{statusCounts.acknowledged || 0} acknowledged</span>
            <span>{statusCounts.resolved || 0} resolved</span>
          </div>
        </div>
      )}
    </div>
  );
}
