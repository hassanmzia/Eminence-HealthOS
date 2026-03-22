"use client";

import { useState, useEffect } from "react";
import { fetchDashboardSummary, type DashboardSummary } from "@/lib/api";

function TrendArrow({ positive }: { positive: boolean }) {
  return positive ? (
    <svg className="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
    </svg>
  ) : (
    <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6L9 12.75l4.286-4.286a11.948 11.948 0 014.306 6.43l.776 2.898m0 0l3.182-5.511m-3.182 5.51l-5.511-3.181" />
    </svg>
  );
}

function SkeletonCard() {
  return (
    <div className="metric-card">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="skeleton-text w-24" />
          <div className="skeleton h-8 w-16 rounded" />
          <div className="skeleton-text w-32" />
        </div>
        <div className="skeleton-circle h-10 w-10" />
      </div>
    </div>
  );
}

export function VitalsSummaryCards() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    fetchDashboardSummary()
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Active Patients",
      value: data.active_patients,
      subtitle: "Enrolled in monitoring",
      icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z",
      color: "text-healthos-600",
      bgColor: "bg-healthos-50",
      ringColor: "ring-healthos-500/20",
      trend: true,
    },
    {
      label: "Vitals Today",
      value: data.vitals_today,
      subtitle: "Readings recorded",
      icon: "M22 12h-4l-3 9L9 3l-3 9H2",
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
      ringColor: "ring-emerald-500/20",
      trend: true,
    },
    {
      label: "Open Alerts",
      value: data.open_alerts,
      subtitle: `${data.critical_alerts} critical \u00b7 ${data.high_alerts} high`,
      icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0",
      color: "text-orange-600",
      bgColor: "bg-orange-50",
      ringColor: "ring-orange-500/20",
      trend: false,
    },
    {
      label: "Agent Decisions",
      value: data.agent_decisions,
      subtitle: "AI-assisted today",
      icon: "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z",
      color: "text-purple-600",
      bgColor: "bg-purple-50",
      ringColor: "ring-purple-500/20",
      trend: true,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <div
          key={card.label}
          className="metric-card animate-fade-in-up"
          style={{ animationDelay: `${i * 0.08}s`, animationFillMode: "both" }}
        >
          {/* Accent gradient top bar */}
          <div className={`absolute left-0 top-0 h-1 w-full rounded-t-xl bg-gradient-to-r ${
            i === 0 ? "from-healthos-400 to-healthos-600" :
            i === 1 ? "from-emerald-400 to-emerald-600" :
            i === 2 ? "from-orange-400 to-orange-600" :
            "from-purple-400 to-purple-600"
          }`} />

          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{card.label}</p>
              <p className={`mt-2 text-3xl font-bold tabular-nums ${card.color}`}>
                {card.value.toLocaleString()}
              </p>
              <div className="mt-1.5 flex items-center gap-1.5">
                <TrendArrow positive={card.trend} />
                <span className="text-xs text-gray-500 dark:text-gray-400">{card.subtitle}</span>
              </div>
            </div>
            <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${card.bgColor} ring-1 ${card.ringColor}`}>
              <svg className={`h-5 w-5 ${card.color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={card.icon} />
              </svg>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
