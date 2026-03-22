"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchTrendDigest } from "@/lib/api";

const MOCK_TRENDS = [
  { metric: "PMPM Cost", direction: "down", change: "-8.1%", current: "$262", status: "ahead" },
  { metric: "Readmission Rate", direction: "down", change: "-1.3%", current: "8.2%", status: "on_target" },
  { metric: "Quality Score", direction: "up", change: "+0.04", current: "0.82", status: "on_target" },
  { metric: "SLA Compliance", direction: "up", change: "+3.4%", current: "91.7%", status: "improving" },
  { metric: "Automation Rate", direction: "up", change: "+5%", current: "62%", status: "improving" },
  { metric: "Patient Volume", direction: "up", change: "+12%", current: "2,847", status: "on_track" },
];

const MOCK_NARRATIVE = `Platform performance continues to improve across all major dimensions. Cost reduction is ahead of target with PMPM at $262 (target $280). Clinical quality metrics are on or above target. Operational efficiency is the primary area for continued investment.`;

const STATUS_STYLE = {
  ahead: "bg-green-100 text-green-700",
  on_target: "bg-green-50 text-green-600",
  on_track: "bg-blue-50 text-blue-600",
  improving: "bg-yellow-50 text-yellow-600",
} as const;

export function TrendDigest() {
  const [trends, setTrends] = useState(MOCK_TRENDS);
  const [narrative, setNarrative] = useState(MOCK_NARRATIVE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchTrendDigest();
      const data = res as Record<string, unknown>;
      const items = data.trends as Array<Record<string, unknown>> | undefined;
      if (items && items.length > 0) {
        setTrends(
          items.map((t) => ({
            metric: t.metric as string,
            direction: t.direction as string,
            change: t.change as string,
            current: t.current as string,
            status: t.status as string,
          }))
        );
      }
      if (data.narrative) setNarrative(data.narrative as string);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trend data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Trend Analysis</h2>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-10 rounded-lg bg-gray-100 dark:bg-gray-800" />
          ))}
          <div className="mt-4 h-16 rounded-lg bg-gray-100 dark:bg-gray-800" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Trend Analysis</h2>
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
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Trend Analysis</h2>
        <span className="text-xs text-gray-500 dark:text-gray-400">Last 6 months</span>
      </div>

      <div className="space-y-2">
        {trends.map((t) => (
          <div key={t.metric} className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className={t.direction === "up" ? "text-green-500" : "text-green-500"}>
                {t.direction === "up" ? "\u2191" : "\u2193"}
              </span>
              <span className="text-sm text-gray-900 dark:text-gray-100">{t.metric}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{t.current}</span>
              <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_STYLE[t.status as keyof typeof STATUS_STYLE] ?? "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"}`}>
                {t.change}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
        <p className="text-xs leading-relaxed text-gray-700 dark:text-gray-300">{narrative}</p>
      </div>
    </div>
  );
}
