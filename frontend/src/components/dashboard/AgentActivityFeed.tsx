"use client";

import { useState, useEffect } from "react";
import { fetchRecentAgentActivity, type AgentAuditEntry } from "@/lib/api";

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

const ACTION_COLORS: Record<string, string> = {
  anomaly_detection: "bg-red-500",
  risk_scoring: "bg-orange-500",
  vitals_normalization: "bg-emerald-500",
  clinical_note: "bg-healthos-500",
  scheduling: "bg-purple-500",
};

function getActionColor(action: string): string {
  for (const [key, color] of Object.entries(ACTION_COLORS)) {
    if (action.toLowerCase().includes(key)) return color;
  }
  return "bg-healthos-400";
}

export function AgentActivityFeed() {
  const [events, setEvents] = useState<AgentAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentAgentActivity()
      .then(setEvents)
      .catch(() => {})
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchRecentAgentActivity()
        .then(setEvents)
        .catch(() => {});
    }, 15_000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Agent Activity</h2>
        <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 ring-1 ring-inset ring-emerald-500/20">
          <span className="status-dot-live" />
          <span className="text-xs font-semibold text-emerald-700">Live</span>
        </div>
      </div>

      <div className="space-y-1">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-start gap-3 rounded-lg px-2 py-2.5">
              <div className="skeleton-circle mt-0.5 h-2 w-2 flex-shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="skeleton-text w-3/4" />
                <div className="skeleton-text w-1/2" />
              </div>
            </div>
          ))
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
            <p className="mt-2 text-xs text-gray-400">No recent agent activity</p>
          </div>
        ) : (
          events.slice(0, 6).map((event, i) => (
            <div
              key={event.id}
              className="flex items-start gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-gray-50 animate-fade-in"
              style={{ animationDelay: `${i * 0.05}s`, animationFillMode: "both" }}
            >
              {/* Timeline dot */}
              <div className="relative mt-1.5 flex-shrink-0">
                <span className={`block h-2 w-2 rounded-full ${getActionColor(event.action)}`} />
                {i < events.length - 1 && (
                  <span className="absolute left-[3px] top-3 h-6 w-px bg-gray-200" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold text-gray-900">{event.agent_name}</span>{" "}
                  <span className="text-gray-500">{event.action}</span>
                </p>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-400">
                  {event.created_at && <span>{timeAgo(event.created_at)}</span>}
                  {event.confidence_score != null && (
                    <>
                      <span>&middot;</span>
                      <span className="flex items-center gap-1">
                        <span className={`inline-block h-1.5 w-1.5 rounded-full ${
                          event.confidence_score >= 0.9 ? "bg-emerald-500" :
                          event.confidence_score >= 0.7 ? "bg-yellow-500" :
                          "bg-red-500"
                        }`} />
                        {Math.round(event.confidence_score * 100)}%
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {events.length > 6 && (
        <a
          href="/agents"
          className="mt-3 flex items-center justify-center gap-1 rounded-lg py-2 text-xs font-medium text-healthos-600 transition-colors hover:bg-healthos-50"
        >
          View all activity
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </a>
      )}
    </div>
  );
}
