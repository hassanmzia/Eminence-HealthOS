"use client";

import { useState } from "react";

const COHORT_TEMPLATES = [
  { key: "high_risk_chronic", name: "High-Risk Chronic", patients: 524, criteria: 2 },
  { key: "diabetes_management", name: "Diabetes Management", patients: 412, criteria: 2 },
  { key: "heart_failure", name: "Heart Failure", patients: 186, criteria: 2 },
  { key: "readmission_risk", name: "30-Day Readmission Risk", patients: 93, criteria: 2 },
  { key: "rising_risk", name: "Rising Risk", patients: 247, criteria: 3 },
  { key: "frequent_utilizers", name: "Frequent Utilizers", patients: 68, criteria: 2 },
  { key: "care_gap", name: "Care Gaps", patients: 341, criteria: 2 },
];

const ACTIVE_COHORTS = [
  {
    id: "COH-20260310",
    name: "Q1 Diabetes Intervention",
    patients: 185,
    avgRisk: 0.58,
    trend: "improving",
    created: "2026-01-15",
  },
  {
    id: "COH-20260222",
    name: "Post-Discharge Monitoring",
    patients: 42,
    avgRisk: 0.72,
    trend: "stable",
    created: "2026-02-22",
  },
  {
    id: "COH-20260301",
    name: "CHF Remote Monitoring",
    patients: 96,
    avgRisk: 0.65,
    trend: "improving",
    created: "2026-03-01",
  },
];

export function CohortSummary() {
  const [tab, setTab] = useState<"active" | "templates">("active");

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Cohort Management</h2>
        <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
          <button
            onClick={() => setTab("active")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${tab === "active" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
          >
            Active Cohorts
          </button>
          <button
            onClick={() => setTab("templates")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${tab === "templates" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
          >
            Templates
          </button>
        </div>
      </div>

      {tab === "active" ? (
        <div className="space-y-2">
          {ACTIVE_COHORTS.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{c.name}</span>
                  <span className={`rounded px-1.5 py-0.5 text-xs ${
                    c.trend === "improving" ? "bg-green-50 text-green-600" : "bg-gray-100 text-gray-500"
                  }`}>
                    {c.trend}
                  </span>
                </div>
                <div className="mt-1 flex gap-4 text-xs text-gray-500">
                  <span>{c.patients} patients</span>
                  <span>Avg risk: {(c.avgRisk * 100).toFixed(0)}%</span>
                  <span>Created: {c.created}</span>
                </div>
              </div>
              <button className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">
                Analyze
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {COHORT_TEMPLATES.map((t) => (
            <div key={t.key} className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
              <div>
                <span className="text-sm font-medium text-gray-900">{t.name}</span>
                <p className="text-xs text-gray-500">{t.patients} patients match</p>
              </div>
              <button className="rounded bg-healthos-600 px-2 py-1 text-xs text-white hover:bg-healthos-700">
                Create
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
