"use client";

import { useState, useEffect } from "react";
import { fetchDashboardSummary, type DashboardSummary } from "@/lib/api";

export function VitalsSummaryCards() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    fetchDashboardSummary()
      .then(setData)
      .catch(() => {});
  }, []);

  const cards = data
    ? [
        { label: "Active Patients", value: data.active_patients.toLocaleString(), change: "Enrolled in monitoring", color: "text-healthos-600" },
        { label: "Vitals Today", value: data.vitals_today.toLocaleString(), change: "Readings recorded", color: "text-green-600" },
        { label: "Open Alerts", value: data.open_alerts.toLocaleString(), change: `${data.critical_alerts} critical, ${data.high_alerts} high`, color: "text-orange-600" },
        { label: "Agent Decisions", value: data.agent_decisions.toLocaleString(), change: "Today", color: "text-purple-600" },
      ]
    : [
        { label: "Active Patients", value: "—", change: "Loading...", color: "text-gray-400" },
        { label: "Vitals Today", value: "—", change: "Loading...", color: "text-gray-400" },
        { label: "Open Alerts", value: "—", change: "Loading...", color: "text-gray-400" },
        { label: "Agent Decisions", value: "—", change: "Loading...", color: "text-gray-400" },
      ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="card">
          <p className="text-sm font-medium text-gray-500">{card.label}</p>
          <p className={`mt-1 text-2xl font-bold ${card.color}`}>{card.value}</p>
          <p className="mt-1 text-xs text-gray-400">{card.change}</p>
        </div>
      ))}
    </div>
  );
}
