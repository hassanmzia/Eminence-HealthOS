"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchProviderDashboard, type ProviderDashboard } from "@/lib/platform-api";
import { CriticalAlertsBanner } from "@/components/dashboard/CriticalAlertsBanner";
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

export function ReadOnlyDashboard() {
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
            Overview Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Welcome, {user?.full_name || "Auditor"} — Read-only access for compliance and auditing
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LiveClock />
          <div className="flex items-center gap-1.5 rounded-full bg-gray-100 dark:bg-gray-800 px-3 py-1 ring-1 ring-inset ring-gray-300 dark:ring-gray-600">
            <svg className="h-3 w-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.64 0 8.577 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.64 0-8.577-3.007-9.963-7.178z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">View Only</span>
          </div>
        </div>
      </div>

      <CriticalAlertsBanner />

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Patients</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{providerStats?.total_patients ?? "—"}</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Encounters Today</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{providerStats?.scheduled_encounters ?? "—"}</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Active Alerts</p>
          <p className="text-lg font-bold text-orange-600">{providerStats?.critical_alerts ?? "—"}</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Compliance Score</p>
          <p className="text-lg font-bold text-emerald-600">96%</p>
        </div>
      </div>

      {/* Quick Navigation */}
      <div className="animate-fade-in-up stagger-1">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Browse Data</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Patient Records", href: "/patients", icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z", color: "text-healthos-600 bg-healthos-50" },
            { label: "Compliance", href: "/compliance", icon: "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z", color: "text-purple-600 bg-purple-50" },
            { label: "Analytics", href: "/analytics", icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z", color: "text-blue-600 bg-blue-50" },
            { label: "Audit Log", href: "/audit-log", icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z", color: "text-gray-600 bg-gray-50" },
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

      {/* Summary Panels */}
      <div className="animate-fade-in-up stagger-2">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">System Activity Summary</h3>
              <Link href="/audit-log" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View Log &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { label: "Patient Records Accessed", value: "342", period: "Today" },
                { label: "Lab Orders Processed", value: "89", period: "Today" },
                { label: "Prescriptions Filled", value: "156", period: "Today" },
                { label: "Claims Submitted", value: "48", period: "Today" },
                { label: "Compliance Checks Passed", value: "24/25", period: "This Week" },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <span className="text-xs text-gray-600 dark:text-gray-400">{item.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{item.value}</span>
                    <span className="text-[11px] text-gray-400">{item.period}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Compliance Status</h3>
              <Link href="/compliance" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">Details &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { area: "HIPAA Privacy", status: "compliant", lastAudit: "Mar 20, 2026" },
                { area: "HIPAA Security", status: "compliant", lastAudit: "Mar 18, 2026" },
                { area: "CMS Billing Standards", status: "review", lastAudit: "Mar 15, 2026" },
                { area: "State Licensing", status: "compliant", lastAudit: "Mar 10, 2026" },
                { area: "Data Retention Policy", status: "compliant", lastAudit: "Mar 8, 2026" },
              ].map((item) => (
                <div key={item.area} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.area}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">Last audit: {item.lastAudit}</p>
                  </div>
                  <span className={`text-[11px] font-medium ${
                    item.status === "compliant" ? "text-emerald-600" : "text-amber-600"
                  }`}>
                    {item.status === "compliant" ? "Compliant" : "Under Review"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Read-only notice */}
      <div className="animate-fade-in-up stagger-3">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4">
          <div className="flex items-start gap-3">
            <svg className="h-5 w-5 text-gray-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
            <div>
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Read-Only Access</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                You have view-only access to system data for auditing and compliance purposes.
                To request additional permissions, contact your system administrator.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
