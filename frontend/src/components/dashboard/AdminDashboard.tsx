"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchProviderDashboard, type ProviderDashboard } from "@/lib/platform-api";
import { PatientRiskHeatmap } from "@/components/dashboard/PatientRiskHeatmap";
import { CriticalAlertsBanner } from "@/components/dashboard/CriticalAlertsBanner";
import { AgentActivityFeed } from "@/components/dashboard/AgentActivityFeed";
import { SystemHealthWidget } from "@/components/dashboard/SystemHealthWidget";
import { VitalsSummaryCards } from "@/components/dashboard/VitalsSummaryCards";

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

const ML_MODELS = [
  { name: "BiLSTM Glucose", accuracy: 94.2, predictions: 1247, status: "active", color: "bg-indigo-500" },
  { name: "XGBoost Risk", accuracy: 91.8, predictions: 3521, status: "active", color: "bg-emerald-500" },
  { name: "Random Forest", accuracy: 89.5, predictions: 2183, status: "active", color: "bg-amber-500" },
  { name: "Digital Twin", accuracy: 96.1, predictions: 842, status: "active", color: "bg-purple-500" },
  { name: "HMM Lifestyle", accuracy: 87.3, predictions: 1560, status: "training", color: "bg-pink-500" },
  { name: "Multimodal Fusion", accuracy: 93.7, predictions: 956, status: "active", color: "bg-cyan-500" },
];

const PLATFORM_FEATURES = [
  { label: "Clinical RAG", href: "/clinical-intelligence", description: "AI-powered clinical search", icon: "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z", color: "text-healthos-600 bg-healthos-50", stat: "4 collections" },
  { label: "Knowledge Graph", href: "/knowledge-graph", description: "Clinical relationship explorer", icon: "M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z", color: "text-violet-600 bg-violet-50", stat: "12.4K nodes" },
  { label: "ML Models", href: "/ml-models", description: "Model performance & predictions", icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z", color: "text-amber-600 bg-amber-50", stat: "6 active" },
  { label: "EHR Connect", href: "/ehr-connect", description: "FHIR & HL7v2 interoperability", icon: "M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244", color: "text-teal-600 bg-teal-50", stat: "3 connectors" },
  { label: "AI Orchestration", href: "/agents", description: "Agent pipelines & HITL", icon: "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z", color: "text-rose-600 bg-rose-50", stat: "14 agents" },
  { label: "Admin Panel", href: "/admin", description: "User & org management", icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75", color: "text-gray-600 bg-gray-50", stat: "Full access" },
];

export function AdminDashboard() {
  const [providerStats, setProviderStats] = useState<ProviderDashboard | null>(null);

  useEffect(() => {
    fetchProviderDashboard().then(setProviderStats).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Admin Command Center</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Full platform administration and clinical operations overview</p>
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

      {providerStats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Role</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100 capitalize">{providerStats.role}</p>
          </div>
          <div className="card !p-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">Total Patients</p>
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
        </div>
      )}

      <VitalsSummaryCards />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 animate-fade-in-up stagger-1">
          <PatientRiskHeatmap />
        </div>
        <div className="space-y-6 animate-fade-in-up stagger-2">
          <SystemHealthWidget />
          <AgentActivityFeed />
        </div>
      </div>

      {/* ML Models */}
      <div className="animate-fade-in-up stagger-3">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">ML Model Performance</h2>
          <Link href="/ml-models" className="text-xs font-medium text-healthos-600 hover:text-healthos-700">View All &rarr;</Link>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {ML_MODELS.map((model) => (
            <Link key={model.name} href="/ml-models" className="card card-hover !p-3 group">
              <div className="flex items-center gap-2 mb-2">
                <div className={`h-2 w-2 rounded-full ${model.color}`} />
                <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 truncate">{model.name}</span>
              </div>
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{model.accuracy}%</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">accuracy</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{model.predictions.toLocaleString()}</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">predictions</p>
                </div>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                <div className={`h-full rounded-full ${model.color} transition-all duration-500`} style={{ width: `${model.accuracy}%` }} />
              </div>
              {model.status === "training" && (
                <span className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-amber-600">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
                  Training
                </span>
              )}
            </Link>
          ))}
        </div>
      </div>

      {/* Platform Features */}
      <div className="animate-fade-in-up stagger-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Platform Features</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {PLATFORM_FEATURES.map((feature) => (
            <Link key={feature.label} href={feature.href} className="group card card-hover flex flex-col gap-2 !p-4">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${feature.color} transition-transform group-hover:scale-110`}>
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={feature.icon} />
                </svg>
              </div>
              <div>
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{feature.label}</span>
                <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-tight mt-0.5">{feature.description}</p>
              </div>
              <span className="text-[11px] font-medium text-healthos-600 bg-healthos-50 rounded-full px-2 py-0.5 self-start">{feature.stat}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Federated Learning & EHR Status */}
      <div className="animate-fade-in-up stagger-6">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Federated Learning</h3>
              <span className="text-[11px] font-medium text-emerald-600 bg-emerald-50 rounded-full px-2 py-0.5">Active</span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Round Progress</span>
                <span className="font-medium text-gray-700 dark:text-gray-300">Round 7 / 10</span>
              </div>
              <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-healthos-400 to-healthos-600 w-[70%] transition-all" />
              </div>
              <div className="flex justify-between text-[11px] text-gray-500 dark:text-gray-400 pt-1">
                <span>3 tenants participating</span>
                <span>Privacy budget: 62% remaining</span>
              </div>
            </div>
          </div>
          <div className="card !p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">EHR Interoperability</h3>
              <Link href="/ehr-connect" className="text-[11px] font-medium text-healthos-600 hover:text-healthos-700">Manage &rarr;</Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { label: "FHIR R4", status: "connected", syncs: 1284 },
                { label: "HL7v2", status: "connected", syncs: 856 },
                { label: "MCP Bridge", status: "connected", syncs: 342 },
              ].map((conn) => (
                <div key={conn.label} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1.5 mb-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{conn.label}</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{conn.syncs.toLocaleString()}</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">syncs today</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
