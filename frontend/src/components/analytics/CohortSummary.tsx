"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchCohortTemplates, createCohort } from "@/lib/api";

const MOCK_COHORT_TEMPLATES = [
  { key: "high_risk_chronic", name: "High-Risk Chronic", patients: 524, criteria: 2 },
  { key: "diabetes_management", name: "Diabetes Management", patients: 412, criteria: 2 },
  { key: "heart_failure", name: "Heart Failure", patients: 186, criteria: 2 },
  { key: "readmission_risk", name: "30-Day Readmission Risk", patients: 93, criteria: 2 },
  { key: "rising_risk", name: "Rising Risk", patients: 247, criteria: 3 },
  { key: "frequent_utilizers", name: "Frequent Utilizers", patients: 68, criteria: 2 },
  { key: "care_gap", name: "Care Gaps", patients: 341, criteria: 2 },
];

const MOCK_ACTIVE_COHORTS = [
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
  const [templates, setTemplates] = useState(MOCK_COHORT_TEMPLATES);
  const [activeCohorts, setActiveCohorts] = useState(MOCK_ACTIVE_COHORTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCohortTemplates();
      const data = res as Record<string, unknown>;
      const tpls = data.templates as Array<Record<string, unknown>> | undefined;
      if (tpls && tpls.length > 0) {
        setTemplates(
          tpls.map((t) => ({
            key: t.key as string,
            name: t.name as string,
            patients: t.patients as number,
            criteria: t.criteria as number,
          }))
        );
      }
      const cohorts = data.active_cohorts as Array<Record<string, unknown>> | undefined;
      if (cohorts && cohorts.length > 0) {
        setActiveCohorts(
          cohorts.map((c) => ({
            id: c.id as string,
            name: c.name as string,
            patients: c.patients as number,
            avgRisk: c.avg_risk as number,
            trend: c.trend as string,
            created: c.created as string,
          }))
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cohort data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Cohort Management</h2>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-gray-800" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Cohort Management</h2>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={loadData} className="mt-2 rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Cohort Management</h2>
        <div className="flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5">
          <button
            onClick={() => setTab("active")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${tab === "active" ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400"}`}
          >
            Active Cohorts
          </button>
          <button
            onClick={() => setTab("templates")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${tab === "templates" ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400"}`}
          >
            Templates
          </button>
        </div>
      </div>

      {tab === "active" ? (
        <div className="space-y-2">
          {activeCohorts.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 p-3">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{c.name}</span>
                  <span className={`rounded px-1.5 py-0.5 text-xs ${
                    c.trend === "improving" ? "bg-green-50 text-green-600" : "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
                  }`}>
                    {c.trend}
                  </span>
                </div>
                <div className="mt-1 flex gap-4 text-xs text-gray-500 dark:text-gray-400">
                  <span>{c.patients} patients</span>
                  <span>Avg risk: {(c.avgRisk * 100).toFixed(0)}%</span>
                  <span>Created: {c.created}</span>
                </div>
              </div>
              <button className="rounded border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
                Analyze
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {templates.map((t) => (
            <div key={t.key} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 p-3">
              <div>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{t.name}</span>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t.patients} patients match</p>
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
