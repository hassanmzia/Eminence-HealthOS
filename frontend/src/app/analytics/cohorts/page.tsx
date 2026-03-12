"use client";

import { useState } from "react";
import Link from "next/link";

const COHORT_TEMPLATES = [
  { key: "high_risk_chronic", name: "High-Risk Chronic", patients: 524, criteria: ["Risk score > 0.7", "2+ chronic conditions"], description: "Patients with multiple chronic conditions and elevated risk scores" },
  { key: "diabetes_management", name: "Diabetes Management", patients: 412, criteria: ["HbA1c > 7.0", "Diabetes diagnosis"], description: "Active diabetes patients requiring management intervention" },
  { key: "heart_failure", name: "Heart Failure", patients: 186, criteria: ["CHF diagnosis", "LVEF < 40%"], description: "Heart failure patients with reduced ejection fraction" },
  { key: "readmission_risk", name: "30-Day Readmission Risk", patients: 93, criteria: ["Discharged < 30 days", "Risk score > 0.6"], description: "Recently discharged patients at high readmission risk" },
  { key: "rising_risk", name: "Rising Risk", patients: 247, criteria: ["Risk trend increasing", "2+ ED visits (6mo)", "No care plan"], description: "Patients with worsening risk trajectories" },
  { key: "frequent_utilizers", name: "Frequent Utilizers", patients: 68, criteria: ["4+ ED visits (12mo)", "High cost quartile"], description: "High-utilization patients for care coordination" },
  { key: "care_gap", name: "Care Gaps", patients: 341, criteria: ["Overdue screenings", "Missing follow-ups"], description: "Patients with identified gaps in preventive care" },
];

const ACTIVE_COHORTS = [
  {
    id: "COH-20260310",
    name: "Q1 Diabetes Intervention",
    patients: 185,
    avgRisk: 0.58,
    trend: "improving" as const,
    created: "2026-01-15",
    lastUpdated: "2026-03-10",
    outcomes: { improved: 72, stable: 98, declined: 15 },
  },
  {
    id: "COH-20260222",
    name: "Post-Discharge Monitoring",
    patients: 42,
    avgRisk: 0.72,
    trend: "stable" as const,
    created: "2026-02-22",
    lastUpdated: "2026-03-09",
    outcomes: { improved: 12, stable: 25, declined: 5 },
  },
  {
    id: "COH-20260301",
    name: "CHF Remote Monitoring",
    patients: 96,
    avgRisk: 0.65,
    trend: "improving" as const,
    created: "2026-03-01",
    lastUpdated: "2026-03-11",
    outcomes: { improved: 38, stable: 50, declined: 8 },
  },
  {
    id: "COH-20260205",
    name: "Medication Adherence Program",
    patients: 134,
    avgRisk: 0.45,
    trend: "improving" as const,
    created: "2026-02-05",
    lastUpdated: "2026-03-08",
    outcomes: { improved: 64, stable: 58, declined: 12 },
  },
];

const trendColor = (trend: string) =>
  trend === "improving"
    ? "bg-green-50 text-green-700"
    : trend === "stable"
    ? "bg-gray-100 text-gray-600"
    : "bg-red-50 text-red-700";

export default function CohortBuilderPage() {
  const [tab, setTab] = useState<"active" | "templates">("active");
  const [search, setSearch] = useState("");

  const filteredCohorts = ACTIVE_COHORTS.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );
  const filteredTemplates = COHORT_TEMPLATES.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Link
              href="/analytics"
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Cohort Builder</h1>
              <p className="text-sm text-gray-500">Create, manage, and analyze patient cohorts</p>
            </div>
          </div>
        </div>
        <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
          + New Cohort
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Active Cohorts", value: ACTIVE_COHORTS.length.toString() },
          { label: "Total Patients", value: ACTIVE_COHORTS.reduce((s, c) => s + c.patients, 0).toLocaleString() },
          { label: "Avg Risk Score", value: (ACTIVE_COHORTS.reduce((s, c) => s + c.avgRisk, 0) / ACTIVE_COHORTS.length * 100).toFixed(0) + "%" },
          { label: "Templates", value: COHORT_TEMPLATES.length.toString() },
        ].map((s) => (
          <div key={s.label} className="card text-center">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs + Search */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
          <button
            onClick={() => setTab("active")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              tab === "active" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
            }`}
          >
            Active Cohorts ({ACTIVE_COHORTS.length})
          </button>
          <button
            onClick={() => setTab("templates")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              tab === "templates" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
            }`}
          >
            Templates ({COHORT_TEMPLATES.length})
          </button>
        </div>
        <input
          type="text"
          placeholder="Search cohorts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
        />
      </div>

      {/* Active Cohorts */}
      {tab === "active" && (
        <div className="space-y-3">
          {filteredCohorts.map((c) => (
            <div key={c.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-gray-900">{c.name}</h3>
                    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${trendColor(c.trend)}`}>
                      {c.trend}
                    </span>
                    <span className="text-xs text-gray-400">{c.id}</span>
                  </div>
                  <div className="mt-2 flex gap-6 text-xs text-gray-500">
                    <span><span className="font-medium text-gray-700">{c.patients}</span> patients</span>
                    <span>Avg risk: <span className="font-medium text-gray-700">{(c.avgRisk * 100).toFixed(0)}%</span></span>
                    <span>Created: {c.created}</span>
                    <span>Updated: {c.lastUpdated}</span>
                  </div>
                  {/* Outcome bar */}
                  <div className="mt-3">
                    <div className="mb-1 flex items-center justify-between text-xs text-gray-500">
                      <span>Patient outcomes</span>
                      <span>{c.outcomes.improved} improved / {c.outcomes.stable} stable / {c.outcomes.declined} declined</span>
                    </div>
                    <div className="flex h-2 overflow-hidden rounded-full">
                      <div className="bg-green-400" style={{ width: `${(c.outcomes.improved / c.patients) * 100}%` }} />
                      <div className="bg-gray-300" style={{ width: `${(c.outcomes.stable / c.patients) * 100}%` }} />
                      <div className="bg-red-400" style={{ width: `${(c.outcomes.declined / c.patients) * 100}%` }} />
                    </div>
                  </div>
                </div>
                <div className="ml-4 flex gap-2">
                  <button className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
                    Analyze
                  </button>
                  <button className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
                    Export
                  </button>
                </div>
              </div>
            </div>
          ))}
          {filteredCohorts.length === 0 && (
            <p className="py-8 text-center text-sm text-gray-400">No cohorts match your search.</p>
          )}
        </div>
      )}

      {/* Templates */}
      {tab === "templates" && (
        <div className="grid grid-cols-2 gap-4">
          {filteredTemplates.map((t) => (
            <div key={t.key} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-gray-900">{t.name}</h3>
                  <p className="mt-1 text-xs text-gray-500">{t.description}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {t.criteria.map((c) => (
                      <span key={c} className="rounded bg-healthos-50 px-2 py-0.5 text-xs text-healthos-700">
                        {c}
                      </span>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-gray-400">{t.patients} patients currently match</p>
                </div>
                <button className="ml-3 rounded bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700">
                  Create
                </button>
              </div>
            </div>
          ))}
          {filteredTemplates.length === 0 && (
            <p className="col-span-2 py-8 text-center text-sm text-gray-400">No templates match your search.</p>
          )}
        </div>
      )}
    </div>
  );
}
