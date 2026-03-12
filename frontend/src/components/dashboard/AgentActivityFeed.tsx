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

export function AgentActivityFeed() {
  const [events, setEvents] = useState<AgentAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentAgentActivity()
      .then(setEvents)
      .catch(() => {})
      .finally(() => setLoading(false));

    // Poll every 15 seconds for new activity
    const interval = setInterval(() => {
      fetchRecentAgentActivity()
        .then(setEvents)
        .catch(() => {});
    }, 15_000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Agent Activity</h2>
        <span className="flex items-center gap-1 text-xs text-green-600">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
          Live
        </span>
      </div>
      <div className="space-y-3">
        {loading ? (
          <p className="py-4 text-center text-xs text-gray-400">Loading activity...</p>
        ) : events.length === 0 ? (
          <p className="py-4 text-center text-xs text-gray-400">No recent agent activity</p>
        ) : (
          events.map((event) => (
            <div key={event.id} className="flex items-start gap-2">
              <div className="mt-0.5 h-2 w-2 rounded-full bg-healthos-400" />
              <div className="flex-1 text-xs">
                <p className="text-gray-700">
                  <span className="font-medium">{event.agent_name}</span>{" "}
                  {event.action}
                </p>
                <p className="text-gray-400">
                  {event.created_at ? timeAgo(event.created_at) : ""}
                  {event.confidence_score != null && (
                    <> &middot; {Math.round(event.confidence_score * 100)}% confidence</>
                  )}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
