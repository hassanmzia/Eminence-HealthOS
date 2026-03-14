"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchOpportunities } from "@/lib/api";

const MOCK_OPPORTUNITIES = [
  { name: "Chronic Disease Management", savings: "$320K", effort: "high", timeline: "12mo" },
  { name: "Reduce Readmissions", savings: "$270K", effort: "high", timeline: "9mo" },
  { name: "Reduce Avoidable ED", savings: "$180K", effort: "medium", timeline: "6mo" },
  { name: "Pharmacy Optimization", savings: "$95K", effort: "low", timeline: "3mo" },
  { name: "Imaging Appropriateness", savings: "$65K", effort: "low", timeline: "4mo" },
];

const EFFORT_STYLE = {
  low: "bg-green-50 text-green-700",
  medium: "bg-yellow-50 text-yellow-700",
  high: "bg-red-50 text-red-700",
} as const;

export function OpportunityList() {
  const [opportunities, setOpportunities] = useState(MOCK_OPPORTUNITIES);
  const [totalSavings, setTotalSavings] = useState("$930K");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchOpportunities({ period: "current" });
      const data = res as Record<string, unknown>;
      const items = data.opportunities as Array<Record<string, unknown>> | undefined;
      if (items && items.length > 0) {
        setOpportunities(
          items.map((o) => ({
            name: o.name as string,
            savings: o.savings as string,
            effort: o.effort as string,
            timeline: o.timeline as string,
          }))
        );
      }
      if (data.total_savings) setTotalSavings(data.total_savings as string);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load opportunities");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-gray-900">Cost Reduction Opportunities</h2>
        <p className="mb-4 text-xs text-gray-500">Loading...</p>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-gray-900">Cost Reduction Opportunities</h2>
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
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-gray-900">Cost Reduction Opportunities</h2>
      <p className="mb-4 text-xs text-gray-500">{totalSavings} total potential annual savings</p>

      <div className="space-y-3">
        {opportunities.map((o) => (
          <div key={o.name} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
            <div>
              <p className="text-sm font-medium text-gray-900">{o.name}</p>
              <div className="mt-1 flex gap-2 text-xs">
                <span className={`rounded px-1.5 py-0.5 ${EFFORT_STYLE[o.effort as keyof typeof EFFORT_STYLE] ?? "bg-gray-100 text-gray-600"}`}>
                  {o.effort} effort
                </span>
                <span className="text-gray-500">{o.timeline}</span>
              </div>
            </div>
            <span className="text-sm font-bold text-green-600">{o.savings}/yr</span>
          </div>
        ))}
      </div>
    </div>
  );
}
