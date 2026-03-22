"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchAlerts, type AlertData } from "@/lib/api";

const PRIORITY_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  moderate: "badge-moderate",
  low: "badge-low",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "text-red-600",
  acknowledged: "text-yellow-600",
  resolved: "text-green-600",
};

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function AlertsTable({
  priority,
  status,
}: {
  priority?: string;
  status?: string;
}) {
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    fetchAlerts({
      priority: priority || undefined,
      status: status || undefined,
    })
      .then(setAlerts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [priority, status]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="card overflow-hidden p-0">
      <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Priority</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Type</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Message</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
          {loading ? (
            <tr>
              <td colSpan={5} className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                Loading alerts...
              </td>
            </tr>
          ) : alerts.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                No alerts found
              </td>
            </tr>
          ) : (
            alerts.map((alert) => (
              <tr key={alert.id} className="transition-colors hover:bg-gray-50 dark:hover:bg-gray-800">
                <td className="px-6 py-4">
                  <span className={PRIORITY_BADGE[alert.priority]}>{alert.priority}</span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  {alert.alert_type.replace(/_/g, " ")}
                </td>
                <td className="max-w-xs px-6 py-4 text-sm text-gray-700 dark:text-gray-300 truncate">
                  {alert.message || "—"}
                </td>
                <td className="px-6 py-4">
                  <span className={`text-sm font-medium ${STATUS_COLORS[alert.status] || "text-gray-500 dark:text-gray-400"}`}>
                    {alert.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {alert.created_at ? timeAgo(alert.created_at) : "—"}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table></div>
    </div>
  );
}
