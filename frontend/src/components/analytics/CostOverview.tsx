"use client";

import { useState, useEffect, useCallback } from "react";
import { analyzeCosts } from "@/lib/api";

const MOCK_COST_DATA = {
  rpm_roi: {
    annual_cost: 180000,
    annual_savings: 412000,
    net_benefit: 232000,
    roi_percent: 128.9,
    payback_months: 5.2,
  },
  cost_by_risk: [
    { level: "Low", monthly: 50, patients: 1427, color: "bg-green-500" },
    { level: "Moderate", monthly: 150, patients: 896, color: "bg-yellow-500" },
    { level: "High", monthly: 400, patients: 382, color: "bg-orange-500" },
    { level: "Critical", monthly: 1200, patients: 142, color: "bg-red-500" },
  ],
  forecast: [
    { year: 1, savings: 412000 },
    { year: 2, savings: 453200 },
    { year: 3, savings: 498520 },
  ],
};

const LEVEL_COLORS: Record<string, string> = {
  Low: "bg-green-500",
  Moderate: "bg-yellow-500",
  High: "bg-orange-500",
  Critical: "bg-red-500",
};

export function CostOverview() {
  const [costData, setCostData] = useState(MOCK_COST_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyzeCosts({ include_forecast: true, include_rpm_roi: true });
      const data = res as Record<string, unknown>;

      const rpmRoi = data.rpm_roi as Record<string, unknown> | undefined;
      const costByRisk = data.cost_by_risk as Array<Record<string, unknown>> | undefined;
      const forecast = data.forecast as Array<Record<string, unknown>> | undefined;

      if (rpmRoi || costByRisk || forecast) {
        setCostData({
          rpm_roi: rpmRoi
            ? {
                annual_cost: rpmRoi.annual_cost as number,
                annual_savings: rpmRoi.annual_savings as number,
                net_benefit: rpmRoi.net_benefit as number,
                roi_percent: rpmRoi.roi_percent as number,
                payback_months: rpmRoi.payback_months as number,
              }
            : MOCK_COST_DATA.rpm_roi,
          cost_by_risk: costByRisk
            ? costByRisk.map((c) => ({
                level: c.level as string,
                monthly: c.monthly as number,
                patients: c.patients as number,
                color: LEVEL_COLORS[c.level as string] ?? "bg-gray-500",
              }))
            : MOCK_COST_DATA.cost_by_risk,
          forecast: forecast
            ? forecast.map((f) => ({
                year: f.year as number,
                savings: f.savings as number,
              }))
            : MOCK_COST_DATA.forecast,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cost data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const totalMonthly = costData.cost_by_risk.reduce((s, d) => s + d.monthly * d.patients, 0);

  if (loading) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Cost Analysis</h2>
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-6 rounded bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Cost Analysis</h2>
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
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Cost Analysis</h2>
        <span className="rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-600">
          {costData.rpm_roi.roi_percent}% RPM ROI
        </span>
      </div>

      {/* RPM ROI summary */}
      <div className="mb-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Annual RPM Cost</p>
          <p className="mt-1 text-sm font-bold text-gray-900 dark:text-gray-100">${(costData.rpm_roi.annual_cost / 1000).toFixed(0)}K</p>
        </div>
        <div className="rounded-lg bg-green-50 p-3 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Annual Savings</p>
          <p className="mt-1 text-sm font-bold text-green-700">${(costData.rpm_roi.annual_savings / 1000).toFixed(0)}K</p>
        </div>
        <div className="rounded-lg bg-healthos-50 p-3 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Net Benefit</p>
          <p className="mt-1 text-sm font-bold text-healthos-700">${(costData.rpm_roi.net_benefit / 1000).toFixed(0)}K</p>
        </div>
      </div>

      {/* Cost by risk level */}
      <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Monthly Cost by Risk Level</h3>
      <div className="space-y-2">
        {costData.cost_by_risk.map((d) => {
          const total = d.monthly * d.patients;
          const pct = (total / totalMonthly) * 100;
          return (
            <div key={d.level} className="flex items-center gap-3 text-sm">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${d.color}`} />
              <span className="w-20 font-medium text-gray-900 dark:text-gray-100">{d.level}</span>
              <div className="flex-1">
                <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800">
                  <div className={`h-2 rounded-full ${d.color}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
              <span className="w-16 text-right text-xs text-gray-500 dark:text-gray-400">
                ${(total / 1000).toFixed(0)}K
              </span>
            </div>
          );
        })}
      </div>

      {/* Savings forecast */}
      <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
        <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">3-Year Savings Forecast</h3>
        <div className="flex gap-4">
          {costData.forecast.map((f) => (
            <div key={f.year} className="flex-1 text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400">Year {f.year}</p>
              <p className="text-sm font-bold text-green-600">${(f.savings / 1000).toFixed(0)}K</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
