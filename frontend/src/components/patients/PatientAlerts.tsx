"use client";

import { useState, useEffect } from "react";

interface AlertRow {
  id: string;
  type: string;
  priority: string;
  status: string;
  message: string;
  created_at: string;
}

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

const DEMO_ALERTS: AlertRow[] = [
  { id: "1", type: "physician_review", priority: "critical", status: "pending", message: "Heart rate sustained above 110 bpm for 30 minutes", created_at: "5 min ago" },
  { id: "2", type: "nurse_review", priority: "high", status: "pending", message: "SpO2 dropped below 92% threshold", created_at: "12 min ago" },
  { id: "3", type: "patient_notification", priority: "moderate", status: "acknowledged", message: "Glucose reading 185 mg/dL above target", created_at: "45 min ago" },
];

export function PatientAlerts({ patientId }: { patientId: string }) {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);

  useEffect(() => {
    // TODO: Replace with fetchAlerts({ patient_id: patientId })
    setAlerts(DEMO_ALERTS);
  }, [patientId]);

  return (
    <div className="card">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Active Alerts</h2>
      <div className="space-y-3">
        {alerts.map((alert) => (
          <div key={alert.id} className="flex items-start gap-3 rounded-lg border border-gray-100 p-3">
            <div className="mt-0.5">
              <span className={PRIORITY_BADGE[alert.priority]}>{alert.priority}</span>
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-800">{alert.message}</p>
              <p className="mt-0.5 text-xs text-gray-400">
                {alert.type.replace(/_/g, " ")} &middot; {alert.created_at}
              </p>
            </div>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[alert.status]}`}>
              {alert.status}
            </span>
          </div>
        ))}
        {alerts.length === 0 && (
          <p className="text-center text-sm text-gray-400">No active alerts</p>
        )}
      </div>
    </div>
  );
}
