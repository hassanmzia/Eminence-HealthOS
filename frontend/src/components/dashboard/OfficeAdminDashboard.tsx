"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchProviderDashboard, type ProviderDashboard } from "@/lib/platform-api";
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

export function OfficeAdminDashboard() {
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Office Administration</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Welcome, {user?.full_name || "Office Admin"} — Billing, scheduling, and operations
          </p>
        </div>
        <LiveClock />
      </div>

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
          <p className="text-xs text-gray-500 dark:text-gray-400">Claims Pending</p>
          <p className="text-lg font-bold text-amber-600">12</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Revenue MTD</p>
          <p className="text-lg font-bold text-emerald-600">$24.5K</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="animate-fade-in-up stagger-1">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Revenue Cycle", href: "/rcm", icon: "M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z", color: "text-emerald-600 bg-emerald-50" },
            { label: "Patient Records", href: "/patients", icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z", color: "text-healthos-600 bg-healthos-50" },
            { label: "Compliance", href: "/compliance", icon: "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z", color: "text-purple-600 bg-purple-50" },
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

      {/* Billing & Scheduling Overview */}
      <div className="animate-fade-in-up stagger-2">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Billing Overview</h3>
              <Link href="/rcm" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">Details &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { label: "Claims Submitted", value: "48", trend: "+12%" },
                { label: "Claims Approved", value: "36", trend: "+8%" },
                { label: "Pending Review", value: "12", trend: "-3%" },
                { label: "Denied", value: "2", trend: "-50%" },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <span className="text-xs text-gray-600 dark:text-gray-400">{item.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{item.value}</span>
                    <span className={`text-[11px] font-medium ${item.trend.startsWith("+") ? "text-emerald-600" : "text-red-500"}`}>{item.trend}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Today&apos;s Schedule</h3>
              <Link href="/operations" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">Full Schedule &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { time: "09:00", patient: "John D.", type: "Follow-up", provider: "Dr. Smith" },
                { time: "10:30", patient: "Sarah M.", type: "New Patient", provider: "Dr. Johnson" },
                { time: "11:00", patient: "Robert K.", type: "Lab Review", provider: "Dr. Smith" },
                { time: "14:00", patient: "Maria L.", type: "Telehealth", provider: "Dr. Johnson" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 w-10">{item.time}</span>
                    <div>
                      <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.type}</p>
                    </div>
                  </div>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400">{item.provider}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
