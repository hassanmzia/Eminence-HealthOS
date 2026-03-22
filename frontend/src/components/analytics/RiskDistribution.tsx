"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchRiskDistribution } from "@/lib/api";

const MOCK_RISK_DATA = [
  { level: "Critical", count: 142, pct: 5.0, color: "bg-red-500", bar: "bg-red-200" },
  { level: "High", count: 382, pct: 13.4, color: "bg-orange-500", bar: "bg-orange-200" },
  { level: "Moderate", count: 896, pct: 31.5, color: "bg-yellow-500", bar: "bg-yellow-200" },
  { level: "Low", count: 1427, pct: 50.1, color: "bg-green-500", bar: "bg-green-200" },
];

const MOCK_RECOMMENDATIONS = [
  { tier: "Critical", action: "Daily monitoring, weekly provider review", patients: 142 },
  { tier: "High", action: "Twice-weekly monitoring, bi-weekly review", patients: 382 },
  { tier: "Moderate", action: "Weekly monitoring, monthly review", patients: 896 },
  { tier: "Low", action: "Monthly check-in, quarterly review", patients: 1427 },
];

const LEVEL_COLORS: Record<string, { color: string; bar: string }> = {
  Critical: { color: "bg-red-500", bar: "bg-red-200" },
  High: { color: "bg-orange-500", bar: "bg-orange-200" },
  Moderate: { color: "bg-yellow-500", bar: "bg-yellow-200" },
  Low: { color: "bg-green-500", bar: "bg-green-200" },
};

export function RiskDistribution() {
  const [view, setView] = useState<"chart" | "recommendations">("chart");
  const [riskData, setRiskData] = useState(MOCK_RISK_DATA);
  const [recommendations, setRecommendations] = useState(MOCK_RECOMMENDATIONS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRiskDistribution({ include_recommendations: true });
      const data = res as Record<string, unknown>;
      const levels = data.risk_levels as Array<Record<string, unknown>> | undefined;
      if (levels && levels.length > 0) {
        setRiskData(
          levels.map((l) => ({
            level: l.level as string,
            count: l.count as number,
            pct: l.pct as number,
            color: LEVEL_COLORS[l.level as string]?.color ?? "bg-gray-500",
            bar: LEVEL_COLORS[l.level as string]?.bar ?? "bg-gray-200",
          }))
        );
      }
      const recs = data.recommendations as Array<Record<string, unknown>> | undefined;
      if (recs && recs.length > 0) {
        setRecommendations(
          recs.map((r) => ({
            tier: r.tier as string,
            action: r.action as string,
            patients: r.patients as number,
          }))
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load risk distribution");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const total = riskData.reduce((s, d) => s + d.count, 0);

  if (loading) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Risk Stratification</h2>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i}>
              <div className="mb-1 flex justify-between">
                <div className="h-4 w-20 rounded bg-gray-200" />
                <div className="h-4 w-16 rounded bg-gray-200" />
              </div>
              <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Risk Stratification</h2>
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
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Risk Stratification</h2>
        <div className="flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5">
          <button
            onClick={() => setView("chart")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${view === "chart" ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400"}`}
          >
            Distribution
          </button>
          <button
            onClick={() => setView("recommendations")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${view === "recommendations" ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400"}`}
          >
            Actions
          </button>
        </div>
      </div>

      {view === "chart" ? (
        <div className="space-y-3">
          {riskData.map((d) => (
            <div key={d.level}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${d.color}`} />
                  <span className="font-medium text-gray-900 dark:text-gray-100">{d.level}</span>
                </div>
                <span className="text-gray-500 dark:text-gray-400">
                  {d.count.toLocaleString()} ({d.pct}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800">
                <div
                  className={`h-2 rounded-full ${d.color}`}
                  style={{ width: `${(d.count / total) * 100}%` }}
                />
              </div>
            </div>
          ))}
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Total: {total.toLocaleString()} patients evaluated
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {recommendations.map((r) => (
            <div key={r.tier} className="flex items-start gap-3 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
              <span className={`mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full ${
                r.tier === "Critical" ? "bg-red-500" :
                r.tier === "High" ? "bg-orange-500" :
                r.tier === "Moderate" ? "bg-yellow-500" : "bg-green-500"
              }`} />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{r.tier}</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">{r.patients} patients</span>
                </div>
                <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400">{r.action}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
