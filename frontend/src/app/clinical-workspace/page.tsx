"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Stethoscope,
  Users,
  ClipboardCheck,
  AlertTriangle,
  Calendar,
  BrainCircuit,
  ArrowRight,
  Loader2,
} from "lucide-react";
import clsx from "clsx";

/* ── Placeholder stats ─────────────────────────────────────────────────────── */

interface WorkspaceStats {
  totalPatients: number;
  openCareGaps: number;
  todaysAppointments: number;
  criticalAlerts: number;
  riskDistribution: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
  };
}

const PLACEHOLDER_STATS: WorkspaceStats = {
  totalPatients: 2847,
  openCareGaps: 142,
  todaysAppointments: 18,
  criticalAlerts: 5,
  riskDistribution: { critical: 87, high: 234, medium: 891, low: 1635, total: 2847 },
};

/* ── Quick actions ─────────────────────────────────────────────────────────── */

interface QuickAction {
  label: string;
  desc: string;
  icon: React.ElementType;
  color: string;
  bg: string;
  href: string;
  badge?: number;
}

/* ── Page Component ────────────────────────────────────────────────────────── */

export default function ClinicalWorkspacePage() {
  const router = useRouter();
  const [stats, setStats] = useState<WorkspaceStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate loading stats
    const timer = setTimeout(() => {
      setStats(PLACEHOLDER_STATS);
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  const criticalAlertCount = stats?.criticalAlerts ?? 0;

  const QUICK_ACTIONS: QuickAction[] = [
    {
      label: "Patient Roster",
      desc: "Search and manage all patients",
      icon: Users,
      color: "text-indigo-600",
      bg: "bg-indigo-50",
      href: "/patients",
    },
    {
      label: "Care Gaps",
      desc: "Review open clinical quality measures",
      icon: ClipboardCheck,
      color: "text-amber-600",
      bg: "bg-amber-50",
      href: "/patients",
    },
    {
      label: "Critical Alerts",
      desc: "Patients needing immediate attention",
      icon: AlertTriangle,
      color: "text-red-600",
      bg: "bg-red-50",
      href: "/alerts",
      badge: criticalAlertCount,
    },
    {
      label: "Appointments",
      desc: "Today's schedule and upcoming visits",
      icon: Calendar,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
      href: "/telehealth",
    },
    {
      label: "AI Agents",
      desc: "Monitor running agents and recommendations",
      icon: BrainCircuit,
      color: "text-purple-600",
      bg: "bg-purple-50",
      href: "/agents",
    },
    {
      label: "High Risk Patients",
      desc: "Critical & high risk patients",
      icon: Stethoscope,
      color: "text-orange-600",
      bg: "bg-orange-50",
      href: "/patients",
    },
  ];

  const statCards = [
    { label: "Total Patients", value: stats?.totalPatients ?? 0, color: "text-indigo-600" },
    { label: "Critical Alerts", value: criticalAlertCount, color: "text-red-600" },
    { label: "Open Care Gaps", value: stats?.openCareGaps ?? 0, color: "text-amber-600" },
    { label: "Today's Appointments", value: stats?.todaysAppointments ?? 0, color: "text-emerald-600" },
  ];

  return (
    <div className="space-y-6 max-w-5xl animate-fade-in-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Stethoscope className="w-6 h-6 text-indigo-600" />
          Clinical Workspace
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Your clinical workflow hub
        </p>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
            ) : (
              <p
                className={clsx(
                  "text-2xl font-bold font-mono tabular-nums",
                  stat.color
                )}
              >
                {stat.value.toLocaleString()}
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Quick actions grid */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-bold text-gray-900 mb-4">Quick Access</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => router.push(action.href)}
              className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 hover:border-indigo-300 transition-all text-left group"
            >
              <div
                className={clsx(
                  "p-2 rounded-lg flex-shrink-0",
                  action.bg
                )}
              >
                <action.icon className={clsx("w-5 h-5", action.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">
                    {action.label}
                  </p>
                  {action.badge !== undefined && action.badge > 0 && (
                    <span className="text-[10px] font-bold text-white bg-red-500 rounded-full px-1.5 py-0.5">
                      {action.badge}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{action.desc}</p>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-700 transition-colors flex-shrink-0 mt-0.5" />
            </button>
          ))}
        </div>
      </div>

      {/* Risk distribution */}
      {stats?.riskDistribution && stats.riskDistribution.total > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-bold text-gray-900 mb-4">
            Risk Distribution
          </h2>
          <div className="space-y-2">
            {[
              { label: "Critical", key: "critical" as const, color: "bg-red-500" },
              { label: "High", key: "high" as const, color: "bg-orange-500" },
              { label: "Medium", key: "medium" as const, color: "bg-amber-500" },
              { label: "Low", key: "low" as const, color: "bg-emerald-500" },
            ].map(({ label, key, color }) => {
              const count = stats.riskDistribution[key];
              const total = stats.riskDistribution.total || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-xs font-medium text-gray-500 w-14">
                    {label}
                  </span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div
                      className={clsx("h-2 rounded-full transition-all", color)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-gray-900 w-10 text-right">
                    {count.toLocaleString()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
