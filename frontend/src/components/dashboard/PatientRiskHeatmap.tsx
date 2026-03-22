"use client";

import { useState, useEffect } from "react";
import { fetchPatients, type PatientData } from "@/lib/api";

const RISK_CONFIG: Record<string, { bg: string; text: string; ring: string; badge: string; dot: string; order: number }> = {
  critical: { bg: "bg-red-500", text: "text-red-700", ring: "ring-red-500/20", badge: "badge-critical", dot: "bg-red-500", order: 4 },
  high: { bg: "bg-orange-500", text: "text-orange-700", ring: "ring-orange-500/20", badge: "badge-high", dot: "bg-orange-500", order: 3 },
  moderate: { bg: "bg-yellow-500", text: "text-yellow-700", ring: "ring-yellow-500/20", badge: "badge-moderate", dot: "bg-yellow-500", order: 2 },
  low: { bg: "bg-emerald-500", text: "text-emerald-700", ring: "ring-emerald-500/20", badge: "badge-low", dot: "bg-emerald-500", order: 1 },
};

function patientName(p: PatientData): string {
  const demo = p.demographics as Record<string, unknown>;
  return (demo?.name as string) || p.mrn || "Unknown";
}

function conditionLabels(p: PatientData): string[] {
  return p.conditions.map((c) => (c.display as string) || (c.code as string) || "").filter(Boolean);
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 rounded-lg p-3">
      <div className="skeleton h-10 w-10 rounded-xl" />
      <div className="flex-1 space-y-1.5">
        <div className="skeleton-text w-32" />
        <div className="skeleton-text w-48" />
      </div>
      <div className="skeleton h-5 w-16 rounded-full" />
    </div>
  );
}

export function PatientRiskHeatmap() {
  const [patients, setPatients] = useState<PatientData[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    fetchPatients({ page: 1 })
      .then((res) => setPatients(res.patients))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const sorted = [...patients].sort(
    (a, b) => (RISK_CONFIG[b.risk_level]?.order || 0) - (RISK_CONFIG[a.risk_level]?.order || 0)
  );

  const filtered = filter === "all" ? sorted : sorted.filter((p) => p.risk_level === filter);

  // Distribution counts
  const distribution = patients.reduce<Record<string, number>>((acc, p) => {
    acc[p.risk_level] = (acc[p.risk_level] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="card">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Patient Risk Overview</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">{patients.length} patients monitored</p>
        </div>

        {/* Risk distribution pills */}
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setFilter("all")}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
              filter === "all"
                ? "bg-gray-900 text-white shadow-sm"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200"
            }`}
          >
            All ({patients.length})
          </button>
          {Object.entries(RISK_CONFIG).map(([level, cfg]) => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all ${
                filter === level
                  ? `${cfg.bg} text-white shadow-sm`
                  : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${filter === level ? "bg-white dark:bg-gray-900" : cfg.dot}`} />
              {level.charAt(0).toUpperCase() + level.slice(1)} ({distribution[level] || 0})
            </button>
          ))}
        </div>
      </div>

      {/* Risk distribution bar */}
      {patients.length > 0 && (
        <div className="mb-5 flex h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
          {["critical", "high", "moderate", "low"].map((level) => {
            const count = distribution[level] || 0;
            const pct = (count / patients.length) * 100;
            return pct > 0 ? (
              <div
                key={level}
                className={`${RISK_CONFIG[level].bg} transition-all duration-700`}
                style={{ width: `${pct}%` }}
                title={`${level}: ${count} patients`}
              />
            ) : null;
          })}
        </div>
      )}

      {/* Patient list */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 sm:py-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
            <svg className="h-6 w-6 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
          </div>
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">No patients found</p>
        </div>
      ) : (
        <div className="space-y-1">
          {filtered.map((patient, i) => {
            const conditions = conditionLabels(patient);
            const cfg = RISK_CONFIG[patient.risk_level] || RISK_CONFIG.low;
            return (
              <a
                key={patient.id}
                href={`/patients/${patient.id}`}
                className="group flex items-center gap-3 rounded-xl p-3 transition-all duration-200 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-sm animate-fade-in"
                style={{ animationDelay: `${i * 0.03}s`, animationFillMode: "both" }}
              >
                {/* Risk indicator */}
                <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${cfg.bg} text-sm font-bold text-white shadow-sm transition-transform group-hover:scale-105`}>
                  {patient.risk_level[0]?.toUpperCase()}
                </div>

                {/* Patient info */}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100 group-hover:text-healthos-700">
                    {patientName(patient)}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-400">
                    {conditions.length > 0 ? conditions.slice(0, 2).join(", ") : "No active conditions"}
                    {conditions.length > 2 && <span className="text-gray-500 dark:text-gray-400"> +{conditions.length - 2}</span>}
                  </p>
                </div>

                {/* Right side */}
                <div className="flex flex-shrink-0 items-center gap-2">
                  <span className={cfg.badge}>{patient.risk_level}</span>
                  <svg className="h-4 w-4 text-gray-300 transition-transform group-hover:translate-x-0.5 group-hover:text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </div>
              </a>
            );
          })}
        </div>
      )}

      {/* View all link */}
      {patients.length > 0 && (
        <a
          href="/patients"
          className="mt-4 flex items-center justify-center gap-1.5 rounded-lg py-2.5 text-sm font-medium text-healthos-600 transition-colors hover:bg-healthos-50"
        >
          View all patients
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </a>
      )}
    </div>
  );
}
