"use client";

import { useState, useEffect } from "react";

interface AlertItem {
  id: string;
  patient_name: string;
  patient_id: string;
  alert_type: string;
  priority: string;
  status: string;
  message: string;
  created_at: string;
  assigned_to: string;
}

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

const DEMO_ALERTS: AlertItem[] = [
  { id: "1", patient_name: "J. Smith", patient_id: "1", alert_type: "physician_review", priority: "critical", status: "pending", message: "HR >110 bpm sustained 30 min", created_at: "5 min ago", assigned_to: "Dr. Patel" },
  { id: "2", patient_name: "K. Wilson", patient_id: "6", alert_type: "emergency", priority: "critical", status: "pending", message: "SpO2 dropped to 88%", created_at: "8 min ago", assigned_to: "Unassigned" },
  { id: "3", patient_name: "R. Williams", patient_id: "3", alert_type: "nurse_review", priority: "high", status: "pending", message: "Respiratory rate elevated to 28/min", created_at: "15 min ago", assigned_to: "RN Lee" },
  { id: "4", patient_name: "M. Johnson", patient_id: "2", alert_type: "nurse_review", priority: "high", status: "acknowledged", message: "BP 165/95 above threshold", created_at: "22 min ago", assigned_to: "RN Lee" },
  { id: "5", patient_name: "S. Brown", patient_id: "4", alert_type: "patient_notification", priority: "moderate", status: "acknowledged", message: "Glucose 185 mg/dL above target", created_at: "45 min ago", assigned_to: "Dr. Kim" },
  { id: "6", patient_name: "J. Smith", patient_id: "1", alert_type: "telehealth_trigger", priority: "high", status: "resolved", message: "Risk score exceeded 0.8 threshold", created_at: "1h ago", assigned_to: "Dr. Patel" },
];

export function AlertsTable() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useEffect(() => {
    // TODO: Replace with fetchAlerts() API call
    setAlerts(DEMO_ALERTS);
  }, []);

  return (
    <div className="card overflow-hidden p-0">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Priority</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Patient</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Type</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Message</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Assigned</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {alerts.map((alert) => (
            <tr key={alert.id} className="transition-colors hover:bg-gray-50">
              <td className="px-6 py-4">
                <span className={PRIORITY_BADGE[alert.priority]}>{alert.priority}</span>
              </td>
              <td className="px-6 py-4">
                <a href={`/patients/${alert.patient_id}`} className="text-sm font-medium text-healthos-600 hover:text-healthos-800">
                  {alert.patient_name}
                </a>
              </td>
              <td className="px-6 py-4 text-sm text-gray-600">{alert.alert_type.replace(/_/g, " ")}</td>
              <td className="max-w-xs px-6 py-4 text-sm text-gray-700 truncate">{alert.message}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{alert.assigned_to}</td>
              <td className="px-6 py-4">
                <span className={`text-sm font-medium ${STATUS_COLORS[alert.status]}`}>
                  {alert.status}
                </span>
              </td>
              <td className="px-6 py-4 text-sm text-gray-400">{alert.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
