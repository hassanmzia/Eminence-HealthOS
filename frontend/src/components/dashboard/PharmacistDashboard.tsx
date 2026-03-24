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

export function PharmacistDashboard() {
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
            Pharmacist Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Welcome, {user?.full_name || "Pharmacist"} — Medication dispensing and interaction management
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LiveClock />
          <div className="flex items-center gap-1.5 rounded-full bg-teal-50 dark:bg-teal-950/30 px-3 py-1 ring-1 ring-inset ring-teal-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-teal-700 dark:text-teal-300">On Duty</span>
          </div>
        </div>
      </div>

      <CriticalAlertsBanner />

      {/* Key Metrics */}
      {providerStats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Pending Prescriptions</p>
            <p className="text-lg font-bold text-orange-600">{providerStats.pending_alerts}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Dispensed Today</p>
            <p className="text-lg font-bold text-emerald-600">{providerStats.scheduled_encounters}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Active Patients</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{providerStats.total_patients}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Interaction Alerts</p>
            <p className="text-lg font-bold text-red-600">2</p>
          </div>
        </div>
      )}

      {/* Vitals Summary */}
      <VitalsSummaryCards />

      {/* Quick Actions */}
      <div className="animate-fade-in-up stagger-2">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Pharmacy Queue", href: "/pharmacy", icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5", color: "text-teal-600 bg-teal-50" },
            { label: "View Alerts", href: "/alerts", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0", color: "text-orange-600 bg-orange-50" },
            { label: "Patient List", href: "/patients", icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z", color: "text-healthos-600 bg-healthos-50" },
            { label: "Lab Results", href: "/labs", icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z", color: "text-purple-600 bg-purple-50" },
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

      {/* Pharmacist-Specific: Prescription Queue & Drug Interactions */}
      <div className="animate-fade-in-up stagger-3">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Prescription Queue</h3>
              <Link href="/pharmacy" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { patient: "John D.", med: "Metformin 500mg", prescriber: "Dr. Chen", status: "ready" },
                { patient: "Sarah M.", med: "Lisinopril 10mg", prescriber: "Dr. Patel", status: "verifying" },
                { patient: "Robert K.", med: "Atorvastatin 20mg", prescriber: "Dr. Tanaka", status: "pending" },
                { patient: "Emily W.", med: "Levothyroxine 50mcg", prescriber: "Dr. Clark", status: "pending" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.med} — {item.prescriber}</p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                    item.status === "ready"
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
                      : item.status === "verifying"
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300"
                      : "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300"
                  }`}>
                    {item.status === "ready" ? "Ready" : item.status === "verifying" ? "Verifying" : "Pending"}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Drug Interaction Alerts</h3>
              <Link href="/alerts" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { patient: "Alan P.", drugs: "Warfarin + Aspirin", severity: "high", action: "Consult physician" },
                { patient: "Grace L.", drugs: "Metformin + Contrast Dye", severity: "moderate", action: "Hold 48h pre-procedure" },
                { patient: "Tom B.", drugs: "Lisinopril + Potassium", severity: "moderate", action: "Monitor K+ levels" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.drugs}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-[11px] font-medium ${item.severity === "high" ? "text-red-600" : "text-amber-600"}`}>
                      {item.severity === "high" ? "High" : "Moderate"}
                    </span>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.action}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Inventory & Controlled Substances */}
      <div className="animate-fade-in-up stagger-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Low Stock Alerts</h3>
            <div className="space-y-2">
              {[
                { drug: "Amoxicillin 500mg", stock: 24, reorderAt: 50, unit: "capsules" },
                { drug: "Metformin 1000mg", stock: 18, reorderAt: 40, unit: "tablets" },
                { drug: "Omeprazole 20mg", stock: 32, reorderAt: 60, unit: "capsules" },
                { drug: "Albuterol Inhaler", stock: 5, reorderAt: 10, unit: "units" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.drug}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">Reorder at: {item.reorderAt} {item.unit}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-red-600">{item.stock} {item.unit}</p>
                    <div className="mt-1 h-1.5 w-16 rounded-full bg-gray-200 dark:bg-gray-700">
                      <div
                        className="h-1.5 rounded-full bg-red-500"
                        style={{ width: `${Math.min(100, (item.stock / item.reorderAt) * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Controlled Substances Log</h3>
            <div className="space-y-2">
              {[
                { drug: "Oxycodone 5mg", action: "Dispensed", patient: "John D.", time: "09:15 AM", count: "30 tabs" },
                { drug: "Lorazepam 1mg", action: "Received", patient: "—", time: "08:30 AM", count: "+100 tabs" },
                { drug: "Adderall 20mg", action: "Dispensed", patient: "Maria G.", time: "08:00 AM", count: "30 tabs" },
                { drug: "Morphine 15mg", action: "Wasted", patient: "—", time: "07:45 AM", count: "2 tabs" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.drug}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.patient} — {item.time}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-[11px] font-medium ${
                      item.action === "Dispensed" ? "text-blue-600" :
                      item.action === "Received" ? "text-emerald-600" : "text-amber-600"
                    }`}>
                      {item.action}
                    </span>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.count}</p>
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
