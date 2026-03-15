"use client";

import { useState, useEffect } from "react";
import { PatientRiskHeatmap } from "@/components/dashboard/PatientRiskHeatmap";
import { CriticalAlertsBanner } from "@/components/dashboard/CriticalAlertsBanner";
import { AgentActivityFeed } from "@/components/dashboard/AgentActivityFeed";
import { SystemHealthWidget } from "@/components/dashboard/SystemHealthWidget";
import { VitalsSummaryCards } from "@/components/dashboard/VitalsSummaryCards";

function LiveClock() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <span className="tabular-nums text-sm text-gray-400">
      {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Command Center
          </h1>
          <p className="text-sm text-gray-500">Real-time clinical operations overview</p>
        </div>
        <div className="flex items-center gap-3">
          <LiveClock />
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 ring-1 ring-inset ring-emerald-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-emerald-700">Live</span>
          </div>
        </div>
      </div>

      {/* Critical alerts banner */}
      <CriticalAlertsBanner />

      {/* KPI Summary cards */}
      <VitalsSummaryCards />

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Patient Risk Heatmap — spans 2 cols */}
        <div className="lg:col-span-2 animate-fade-in-up stagger-1">
          <PatientRiskHeatmap />
        </div>

        {/* Right column */}
        <div className="space-y-6 animate-fade-in-up stagger-2">
          <SystemHealthWidget />
          <AgentActivityFeed />
        </div>
      </div>

      {/* Quick Access */}
      <div className="animate-fade-in-up stagger-3">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "New Session", href: "/telehealth", icon: "M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z", color: "text-healthos-600 bg-healthos-50" },
            { label: "View Alerts", href: "/alerts", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0", color: "text-orange-600 bg-orange-50" },
            { label: "RPM Monitor", href: "/rpm", icon: "M22 12h-4l-3 9L9 3l-3 9H2", color: "text-emerald-600 bg-emerald-50" },
            { label: "Analytics", href: "/analytics", icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z", color: "text-purple-600 bg-purple-50" },
          ].map((action) => (
            <a
              key={action.label}
              href={action.href}
              className="group card card-hover flex items-center gap-3 !p-4"
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${action.color} transition-transform group-hover:scale-110`}>
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={action.icon} />
                </svg>
              </div>
              <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">{action.label}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
