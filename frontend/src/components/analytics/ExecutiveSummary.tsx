"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchExecutiveSummary } from "@/lib/api";

const MOCK_ACHIEVEMENTS = [
  "30-day readmission rate decreased to 8.2% (target: <10%)",
  "SLA compliance at 91.7%, up 3.4% from prior period",
  "PMPM cost down to $262, first time below $270 target",
  "RPM program delivering 128.9% ROI",
];

const MOCK_CONCERNS = [
  "Prior auth approval rate at 82.8% — below 90% target",
  "Referral completion rate at 78.6% — specialist response delays",
  "6 overdue SLA tasks in billing review queue",
];

const MOCK_RECOMMENDATIONS = [
  "Expand RPM enrollment to capture additional 200 high-risk patients",
  "Implement dedicated prior auth specialist for top 3 payers",
  "Launch pharmacy optimization program for $95K potential savings",
];

const MOCK_HEADLINE_KPIS = [
  { label: "Patients", value: "2,847" },
  { label: "PMPM Cost", value: "$262" },
  { label: "Quality", value: "0.82" },
  { label: "Net Margin", value: "27.8%" },
  { label: "RPM ROI", value: "128.9%" },
];

export function ExecutiveSummary() {
  const [achievements, setAchievements] = useState(MOCK_ACHIEVEMENTS);
  const [concerns, setConcerns] = useState(MOCK_CONCERNS);
  const [recommendations, setRecommendations] = useState(MOCK_RECOMMENDATIONS);
  const [headlineKpis, setHeadlineKpis] = useState(MOCK_HEADLINE_KPIS);
  const [headline, setHeadline] = useState("Platform performance improving across key metrics with 8.1% cost reduction");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchExecutiveSummary();
      const data = res as Record<string, unknown>;

      if (data.headline) setHeadline(data.headline as string);

      const kpis = data.headline_kpis as Array<Record<string, unknown>> | undefined;
      if (kpis && kpis.length > 0) {
        setHeadlineKpis(kpis.map((k) => ({ label: k.label as string, value: k.value as string })));
      }

      const ach = data.achievements as string[] | undefined;
      if (ach && ach.length > 0) setAchievements(ach);

      const con = data.concerns as string[] | undefined;
      if (con && con.length > 0) setConcerns(con);

      const rec = data.recommendations as string[] | undefined;
      if (rec && rec.length > 0) setRecommendations(rec);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load executive summary");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-gray-900">Executive Summary</h2>
        <div className="animate-pulse">
          <div className="mt-2 h-4 w-3/4 rounded bg-gray-200" />
          <div className="my-4 grid grid-cols-5 gap-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 rounded-lg bg-gray-100" />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 w-24 rounded bg-gray-200" />
                <div className="h-3 w-full rounded bg-gray-100" />
                <div className="h-3 w-full rounded bg-gray-100" />
                <div className="h-3 w-3/4 rounded bg-gray-100" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-gray-900">Executive Summary</h2>
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
      <h2 className="text-lg font-semibold text-gray-900">Executive Summary</h2>
      <p className="mt-1 text-sm text-healthos-600 font-medium">{headline}</p>

      {/* KPI strip */}
      <div className="my-4 grid grid-cols-5 gap-3">
        {headlineKpis.map((kpi) => (
          <div key={kpi.label} className="rounded-lg bg-gray-50 p-3 text-center">
            <p className="text-xs text-gray-500">{kpi.label}</p>
            <p className="mt-0.5 text-xl font-bold text-gray-900">{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-green-700">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            Key Achievements
          </h3>
          <ul className="space-y-1.5">
            {achievements.map((a, i) => (
              <li key={i} className="text-xs text-gray-700 leading-relaxed">{a}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-red-700">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            Areas of Concern
          </h3>
          <ul className="space-y-1.5">
            {concerns.map((c, i) => (
              <li key={i} className="text-xs text-gray-700 leading-relaxed">{c}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-blue-700">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            Recommendations
          </h3>
          <ul className="space-y-1.5">
            {recommendations.map((r, i) => (
              <li key={i} className="text-xs text-gray-700 leading-relaxed">{r}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
