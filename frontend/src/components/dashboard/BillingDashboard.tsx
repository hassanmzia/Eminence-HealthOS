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

export function BillingDashboard() {
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
            Billing Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Welcome, {user?.full_name || "Billing Specialist"} — Financial operations and claims management
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LiveClock />
          <div className="flex items-center gap-1.5 rounded-full bg-amber-50 dark:bg-amber-950/30 px-3 py-1 ring-1 ring-inset ring-amber-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">Active</span>
          </div>
        </div>
      </div>

      <CriticalAlertsBanner />

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Claims Pending</p>
          <p className="text-lg font-bold text-orange-600">18</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Claims Processed Today</p>
          <p className="text-lg font-bold text-emerald-600">24</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Revenue MTD</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">$142.8K</p>
        </div>
        <div className="card !p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">Denial Rate</p>
          <p className="text-lg font-bold text-red-600">4.2%</p>
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
            { label: "Analytics", href: "/analytics", icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z", color: "text-blue-600 bg-blue-50" },
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

      {/* Claims & Revenue Overview */}
      <div className="animate-fade-in-up stagger-2">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Claims Pipeline</h3>
              <Link href="/rcm" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { label: "Claims Submitted", value: "48", trend: "+12%", trendUp: true },
                { label: "Claims Approved", value: "36", trend: "+8%", trendUp: true },
                { label: "Pending Review", value: "18", trend: "-3%", trendUp: false },
                { label: "Denied / Rejected", value: "4", trend: "-50%", trendUp: false },
                { label: "Appeals In Progress", value: "3", trend: "+1", trendUp: true },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <span className="text-xs text-gray-600 dark:text-gray-400">{item.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{item.value}</span>
                    <span className={`text-[11px] font-medium ${
                      (item.label === "Denied / Rejected" || item.label === "Pending Review")
                        ? (!item.trendUp ? "text-emerald-600" : "text-red-500")
                        : (item.trendUp ? "text-emerald-600" : "text-red-500")
                    }`}>{item.trend}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Recent Claim Activity</h3>
              <Link href="/rcm" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
            </div>
            <div className="space-y-2">
              {[
                { patient: "John D.", claim: "CLM-2024-0891", amount: "$1,240", status: "approved", time: "10:15 AM" },
                { patient: "Sarah M.", claim: "CLM-2024-0890", amount: "$3,450", status: "pending", time: "09:45 AM" },
                { patient: "Robert K.", claim: "CLM-2024-0889", amount: "$890", status: "denied", time: "09:20 AM" },
                { patient: "Emily W.", claim: "CLM-2024-0888", amount: "$2,100", status: "approved", time: "08:55 AM" },
                { patient: "Alan P.", claim: "CLM-2024-0887", amount: "$675", status: "pending", time: "08:30 AM" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.patient}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.claim} — {item.time}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-gray-900 dark:text-gray-100">{item.amount}</p>
                    <span className={`text-[11px] font-medium ${
                      item.status === "approved" ? "text-emerald-600" :
                      item.status === "denied" ? "text-red-600" : "text-amber-600"
                    }`}>
                      {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Payer Mix & AR Aging */}
      <div className="animate-fade-in-up stagger-3">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Payer Mix</h3>
            <div className="space-y-2">
              {[
                { payer: "Medicare", percentage: 35, amount: "$49.9K", color: "bg-blue-500" },
                { payer: "Blue Cross Blue Shield", percentage: 28, amount: "$40.0K", color: "bg-emerald-500" },
                { payer: "Aetna", percentage: 18, amount: "$25.7K", color: "bg-purple-500" },
                { payer: "UnitedHealthcare", percentage: 12, amount: "$17.1K", color: "bg-orange-500" },
                { payer: "Self-Pay / Other", percentage: 7, amount: "$10.0K", color: "bg-gray-400" },
              ].map((item) => (
                <div key={item.payer} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-600 dark:text-gray-400">{item.payer}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-900 dark:text-gray-100">{item.amount}</span>
                      <span className="text-[11px] text-gray-500 dark:text-gray-400">{item.percentage}%</span>
                    </div>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                    <div className={`h-1.5 rounded-full ${item.color}`} style={{ width: `${item.percentage}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card !p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Accounts Receivable Aging</h3>
            <div className="space-y-2">
              {[
                { bucket: "0-30 Days", amount: "$48,200", count: 42, status: "current" },
                { bucket: "31-60 Days", amount: "$22,100", count: 18, status: "warning" },
                { bucket: "61-90 Days", amount: "$12,400", count: 9, status: "overdue" },
                { bucket: "91-120 Days", amount: "$6,800", count: 5, status: "critical" },
                { bucket: "120+ Days", amount: "$3,200", count: 3, status: "critical" },
              ].map((item) => (
                <div key={item.bucket} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.bucket}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.count} claims</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-gray-900 dark:text-gray-100">{item.amount}</p>
                    <span className={`text-[11px] font-medium ${
                      item.status === "current" ? "text-emerald-600" :
                      item.status === "warning" ? "text-amber-600" :
                      item.status === "overdue" ? "text-orange-600" : "text-red-600"
                    }`}>
                      {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
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
