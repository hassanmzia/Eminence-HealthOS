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

export function LabTechDashboard() {
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
            Lab Technician Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Welcome, {user?.full_name || "Lab Technician"} — Laboratory results and sample management
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LiveClock />
          <div className="flex items-center gap-1.5 rounded-full bg-purple-50 dark:bg-purple-950/30 px-3 py-1 ring-1 ring-inset ring-purple-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-purple-700 dark:text-purple-300">On Duty</span>
          </div>
        </div>
      </div>

      <CriticalAlertsBanner />

      {/* Key Metrics */}
      {providerStats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Pending Samples</p>
            <p className="text-lg font-bold text-orange-600">{providerStats.pending_alerts}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Completed Today</p>
            <p className="text-lg font-bold text-emerald-600">{providerStats.scheduled_encounters}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Total Patients</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{providerStats.total_patients}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Critical Results</p>
            <p className="text-lg font-bold text-red-600">3</p>
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
            { label: "Lab Orders", href: "/labs", icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5", color: "text-purple-600 bg-purple-50" },
            { label: "View Alerts", href: "/alerts", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0", color: "text-orange-600 bg-orange-50" },
            { label: "Patient List", href: "/patients", icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z", color: "text-healthos-600 bg-healthos-50" },
            { label: "Imaging", href: "/imaging", icon: "M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z", color: "text-blue-600 bg-blue-50" },
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

      {/* Lab-Specific: Pending Orders & Recent Results */}
      <div className="animate-fade-in-up stagger-3">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Pending Lab Orders</h3>
              <Link href="/labs" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { patient: "John D.", test: "Complete Blood Count", priority: "urgent", time: "08:15 AM" },
                { patient: "Sarah M.", test: "Hemoglobin A1C", priority: "routine", time: "09:00 AM" },
                { patient: "Robert K.", test: "Lipid Panel", priority: "routine", time: "09:30 AM" },
                { patient: "Emily W.", test: "Thyroid Panel (TSH, T3, T4)", priority: "urgent", time: "10:00 AM" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.test}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500 dark:text-gray-400">{item.time}</p>
                    <span className={`text-[11px] font-medium ${item.priority === "urgent" ? "text-red-600" : "text-blue-600"}`}>
                      {item.priority === "urgent" ? "Urgent" : "Routine"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Recent Results</h3>
              <Link href="/labs" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { patient: "Alan P.", test: "Metabolic Panel", result: "Normal", time: "07:45 AM" },
                { patient: "Grace L.", test: "Urinalysis", result: "Abnormal", time: "07:30 AM" },
                { patient: "Tom B.", test: "Blood Glucose", result: "142 mg/dL", time: "07:00 AM" },
                { patient: "Maria G.", test: "CBC w/ Differential", result: "Normal", time: "06:45 AM" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.test}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500 dark:text-gray-400">{item.time}</p>
                    <span className={`text-[11px] font-medium ${item.result === "Abnormal" ? "text-red-600" : "text-emerald-600"}`}>
                      {item.result}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Equipment & QC Status */}
      <div className="animate-fade-in-up stagger-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Equipment Status</h3>
            <div className="space-y-2">
              {[
                { name: "Hematology Analyzer", model: "Sysmex XN-1000", status: "operational" },
                { name: "Chemistry Analyzer", model: "Roche Cobas 6000", status: "operational" },
                { name: "Blood Gas Analyzer", model: "Radiometer ABL800", status: "maintenance" },
                { name: "Coagulation Analyzer", model: "Stago STA-R Max", status: "operational" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.name}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.model}</p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                    item.status === "operational"
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
                      : "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300"
                  }`}>
                    {item.status === "operational" ? "Operational" : "Maintenance"}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Quality Control</h3>
            <div className="space-y-2">
              {[
                { test: "CBC QC", lastRun: "06:00 AM", status: "passed", nextDue: "02:00 PM" },
                { test: "Chemistry QC", lastRun: "06:15 AM", status: "passed", nextDue: "02:15 PM" },
                { test: "Coagulation QC", lastRun: "06:30 AM", status: "failed", nextDue: "Rerun Required" },
                { test: "Urinalysis QC", lastRun: "06:45 AM", status: "passed", nextDue: "02:45 PM" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.test}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">Last: {item.lastRun}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-[11px] font-medium ${item.status === "passed" ? "text-emerald-600" : "text-red-600"}`}>
                      {item.status === "passed" ? "Passed" : "Failed"}
                    </span>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.nextDue}</p>
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
