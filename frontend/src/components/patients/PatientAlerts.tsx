"use client";

import { useState, useEffect } from "react";
import { fetchAlerts, type AlertData } from "@/lib/api";

const PRIORITY_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  moderate: "badge-moderate",
  low: "badge-low",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-red-50 text-red-700",
  acknowledged: "bg-yellow-50 text-yellow-700",
  resolved: "bg-green-50 text-green-700",
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

export function PatientAlerts({ patientId }: { patientId: string }) {
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts({ patient_id: patientId })
      .then(setAlerts)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [patientId]);

  return (
    <div className="card">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Active Alerts</h2>
      <div className="space-y-3">
        {loading ? (
          <p className="text-center text-sm text-gray-400">Loading alerts...</p>
        ) : alerts.length === 0 ? (
          <p className="text-center text-sm text-gray-400">No active alerts</p>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className="flex items-start gap-3 rounded-lg border border-gray-100 p-3">
              <div className="mt-0.5">
                <span className={PRIORITY_BADGE[alert.priority]}>{alert.priority}</span>
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-800">{alert.message || "No message"}</p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {alert.alert_type.replace(/_/g, " ")}
                  {alert.created_at && <> &middot; {timeAgo(alert.created_at)}</>}
                </p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[alert.status] || ""}`}>
                {alert.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
