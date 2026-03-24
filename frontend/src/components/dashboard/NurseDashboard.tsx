"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchProviderDashboard, type ProviderDashboard } from "@/lib/platform-api";
import { CriticalAlertsBanner } from "@/components/dashboard/CriticalAlertsBanner";
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

export function NurseDashboard() {
  const { user, role } = useAuth();
  const [providerStats, setProviderStats] = useState<ProviderDashboard | null>(null);

  useEffect(() => {
    fetchProviderDashboard().then(setProviderStats).catch(() => {});
  }, []);

  const roleLabel = role === "care_manager" ? "Care Manager" : "Nurse";

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {roleLabel} Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Welcome, {user?.full_name || roleLabel} — Patient monitoring and care coordination
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LiveClock />
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 ring-1 ring-inset ring-emerald-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-emerald-700">On Shift</span>
          </div>
        </div>
      </div>

      <CriticalAlertsBanner />

      {/* Key Metrics */}
      {providerStats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Assigned Patients</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{providerStats.total_patients}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Pending Alerts</p>
            <p className="text-lg font-bold text-orange-600">{providerStats.pending_alerts}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Vitals Due</p>
            <p className="text-lg font-bold text-blue-600">{providerStats.scheduled_encounters}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Messages</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">—</p>
          </div>
        </div>
      )}

      {/* Vitals Summary */}
      <VitalsSummaryCards />

      {/* Nurse-Specific Quick Actions */}
      <div className="animate-fade-in-up stagger-2">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Record Vitals", href: "/rpm", icon: "M22 12h-4l-3 9L9 3l-3 9H2", color: "text-emerald-600 bg-emerald-50" },
            { label: "View Alerts", href: "/alerts", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0", color: "text-orange-600 bg-orange-50" },
            { label: "Patient List", href: "/patients", icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z", color: "text-healthos-600 bg-healthos-50" },
            { label: "Messages", href: "/messaging", icon: "M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z", color: "text-blue-600 bg-blue-50" },
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

      {/* Nurse-specific: Medication & Device Monitoring */}
      <div className="animate-fade-in-up stagger-3">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Medication Schedule</h3>
              <Link href="/pharmacy" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { patient: "John D.", med: "Metformin 500mg", time: "08:00 AM", status: "administered" },
                { patient: "Sarah M.", med: "Lisinopril 10mg", time: "09:00 AM", status: "pending" },
                { patient: "Robert K.", med: "Atorvastatin 20mg", time: "09:30 AM", status: "pending" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.med}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500 dark:text-gray-400">{item.time}</p>
                    <span className={`text-[11px] font-medium ${item.status === "administered" ? "text-emerald-600" : "text-orange-600"}`}>
                      {item.status === "administered" ? "Done" : "Due"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Device Monitoring</h3>
              <Link href="/rpm" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">RPM &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { patient: "John D.", device: "Blood Pressure Monitor", lastReading: "120/80", status: "normal" },
                { patient: "Sarah M.", device: "Glucose Monitor", lastReading: "142 mg/dL", status: "elevated" },
                { patient: "Robert K.", device: "Pulse Oximeter", lastReading: "97%", status: "normal" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.device}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-gray-900 dark:text-gray-100">{item.lastReading}</p>
                    <span className={`text-[11px] font-medium ${item.status === "normal" ? "text-emerald-600" : "text-orange-600"}`}>
                      {item.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
