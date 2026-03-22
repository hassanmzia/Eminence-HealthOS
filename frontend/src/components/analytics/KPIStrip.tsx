"use client";

import { useState, useEffect, useCallback } from "react";
import { analyzePopulationHealth } from "@/lib/api";

const MOCK_KPIS = [
  { label: "Total Patients", value: "2,847", change: "+12%", positive: true },
  { label: "PMPM Cost", value: "$262", change: "-8.1%", positive: true },
  { label: "Quality Score", value: "0.82", change: "+0.04", positive: true },
  { label: "Readmission Rate", value: "8.2%", change: "-1.3%", positive: true },
  { label: "RPM ROI", value: "128.9%", change: "+22%", positive: true },
];

export function KPIStrip() {
  const [kpis, setKpis] = useState(MOCK_KPIS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyzePopulationHealth({ summary: true });
      const data = res as Record<string, unknown>;
      const items = data.kpis as Array<Record<string, unknown>> | undefined;
      if (items && items.length > 0) {
        setKpis(
          items.map((k) => ({
            label: k.label as string,
            value: k.value as string,
            change: k.change as string,
            positive: k.positive as boolean,
          }))
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load KPIs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="animate-pulse rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
            <div className="h-3 w-16 rounded bg-gray-200" />
            <div className="mt-2 h-7 w-20 rounded bg-gray-200" />
            <div className="mt-2 h-3 w-24 rounded bg-gray-200" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
        <p className="text-sm text-red-600">{error}</p>
        <button onClick={loadData} className="mt-2 rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{kpi.label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{kpi.value}</p>
          <p className={`mt-1 text-xs font-medium ${kpi.positive ? "text-green-600" : "text-red-600"}`}>
            {kpi.change} vs prior period
          </p>
        </div>
      ))}
    </div>
  );
}
