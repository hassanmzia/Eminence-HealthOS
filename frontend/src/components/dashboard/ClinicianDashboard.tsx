"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchProviderDashboard, type ProviderDashboard } from "@/lib/platform-api";
import { PatientRiskHeatmap } from "@/components/dashboard/PatientRiskHeatmap";
import { CriticalAlertsBanner } from "@/components/dashboard/CriticalAlertsBanner";
import { AgentActivityFeed } from "@/components/dashboard/AgentActivityFeed";
import { VitalsSummaryCards } from "@/components/dashboard/VitalsSummaryCards";
import { useAuth } from "@/contexts/AuthContext";

function LiveClock() {
  const [time, setTime] = useState<Date | null>(null);
  useEffect(() => {
    setTime(new Date());
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!time) return <span className="tabular-nums text-sm text-gray-500 dark:text-gray-400">&nbsp;</span>;
  return (
    <span className="tabular-nums text-sm text-gray-500 dark:text-gray-400">
      {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  );
}

export function ClinicianDashboard() {
  const { user } = useAuth();
  const [providerStats, setProviderStats] = useState<ProviderDashboard | null>(null);

  useEffect(() => {
    fetchProviderDashboard().then(setProviderStats).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Welcome, Dr. {user?.full_name?.split(" ").pop() || "Clinician"}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Clinical operations dashboard</p>
        </div>
        <div className="flex items-center gap-3">
          <LiveClock />
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 ring-1 ring-inset ring-emerald-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-emerald-700">Live</span>
          </div>
        </div>
      </div>

      <CriticalAlertsBanner />

      {/* Provider stats */}
      {providerStats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">My Patients</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{providerStats.total_patients}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Pending Alerts</p>
            <p className="text-lg font-bold text-orange-600">{providerStats.pending_alerts}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Encounters Today</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{providerStats.scheduled_encounters}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Critical Patients</p>
            <p className="text-lg font-bold text-red-600">—</p>
          </div>
        </div>
      )}

      <VitalsSummaryCards />

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 animate-fade-in-up stagger-1">
          <PatientRiskHeatmap />
        </div>
        <div className="space-y-6 animate-fade-in-up stagger-2">
          <AgentActivityFeed />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="animate-fade-in-up stagger-3">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Clinical Workspace", href: "/clinical-workspace", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01", color: "text-healthos-600 bg-healthos-50" },
            { label: "Start Telehealth", href: "/telehealth", icon: "M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z", color: "text-blue-600 bg-blue-50" },
            { label: "View Alerts", href: "/alerts", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0", color: "text-orange-600 bg-orange-50" },
            { label: "RPM Monitor", href: "/rpm", icon: "M22 12h-4l-3 9L9 3l-3 9H2", color: "text-emerald-600 bg-emerald-50" },
          ].map((action) => (
            <Link key={action.label} href={action.href} className="group card card-hover flex items-center gap-3 !p-4">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${action.color} transition-transform group-hover:scale-110`}>
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={action.icon} />
                </svg>
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100">{action.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
