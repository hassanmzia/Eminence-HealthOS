"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchCostDrivers } from "@/lib/api";

const MOCK_COST_DRIVERS = [
  { driver: "Inpatient Admissions", pct: 30, color: "bg-red-500" },
  { driver: "ED Visits", pct: 18, color: "bg-orange-500" },
  { driver: "Pharmacy", pct: 15, color: "bg-blue-500" },
  { driver: "Specialist Visits", pct: 12, color: "bg-purple-500" },
  { driver: "Readmissions", pct: 10, color: "bg-pink-500" },
  { driver: "Imaging", pct: 8, color: "bg-teal-500" },
  { driver: "Lab Tests", pct: 5, color: "bg-green-500" },
  { driver: "Post-Acute Care", pct: 2, color: "bg-gray-400" },
];

const DRIVER_COLORS: Record<string, string> = {
  "Inpatient Admissions": "bg-red-500",
  "ED Visits": "bg-orange-500",
  "Pharmacy": "bg-blue-500",
  "Specialist Visits": "bg-purple-500",
  "Readmissions": "bg-pink-500",
  "Imaging": "bg-teal-500",
  "Lab Tests": "bg-green-500",
  "Post-Acute Care": "bg-gray-400",
};

const FALLBACK_COLORS = [
  "bg-red-500", "bg-orange-500", "bg-blue-500", "bg-purple-500",
  "bg-pink-500", "bg-teal-500", "bg-green-500", "bg-gray-400",
];

export function CostDriverChart() {
  const [drivers, setDrivers] = useState(MOCK_COST_DRIVERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCostDrivers({ period: "current" });
      const data = res as Record<string, unknown>;
      const items = data.drivers as Array<Record<string, unknown>> | undefined;
      if (items && items.length > 0) {
        setDrivers(
          items.map((d, idx) => ({
            driver: d.driver as string,
            pct: d.pct as number,
            color: DRIVER_COLORS[d.driver as string] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length],
          }))
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cost drivers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Cost Drivers</h2>
        <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">Breakdown by category</p>
        <div className="animate-pulse">
          <div className="mb-4 h-6 rounded-full bg-gray-100 dark:bg-gray-800" />
          <div className="space-y-2">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div key={i} className="h-5 rounded bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Cost Drivers</h2>
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-center">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={loadData} className="mt-2 rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Cost Drivers</h2>
      <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">Breakdown by category</p>

      {/* Stacked bar */}
      <div className="mb-4 flex h-6 overflow-hidden rounded-full">
        {drivers.map((d) => (
          <div
            key={d.driver}
            className={d.color}
            style={{ width: `${d.pct}%` }}
            title={`${d.driver}: ${d.pct}%`}
          />
        ))}
      </div>

      <div className="space-y-2">
        {drivers.map((d) => (
          <div key={d.driver} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${d.color}`} />
              <span className="text-gray-900 dark:text-gray-100">{d.driver}</span>
            </div>
            <span className="font-medium text-gray-700 dark:text-gray-300">{d.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
