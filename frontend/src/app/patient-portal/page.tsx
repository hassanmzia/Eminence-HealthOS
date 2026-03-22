"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchPatientProfile,
  type PatientHealthSummary,
} from "@/lib/patient-api";

export default function PatientPortalHome() {
  const [data, setData] = useState<PatientHealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPatientProfile()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-healthos-200 border-t-healthos-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">Unable to load your health summary. Please try again later.</p>
      </div>
    );
  }

  const patientName = data?.patient?.name || "Patient";
  const upcomingVitals = data?.latest_vitals?.slice(0, 3) ?? [];
  const alerts = data?.active_alerts ?? [];
  const medicationCount = data?.medications?.length ?? 0;

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Welcome back, {patientName}
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Here is an overview of your health and upcoming activity.
        </p>
      </div>

      {/* Quick summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Latest Vitals"
          value={String(upcomingVitals.length)}
          subtitle="recorded recently"
          color="blue"
        />
        <SummaryCard
          title="Active Alerts"
          value={String(alerts.length)}
          subtitle="require attention"
          color={alerts.length > 0 ? "red" : "green"}
        />
        <SummaryCard
          title="Medications"
          value={String(medicationCount)}
          subtitle="active prescriptions"
          color="purple"
        />
        <SummaryCard
          title="Conditions"
          value={String(data?.conditions?.length ?? 0)}
          subtitle="on record"
          color="amber"
        />
      </div>

      {/* Notifications / Alerts */}
      {alerts.length > 0 && (
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
            Recent Notifications
          </h2>
          <ul className="space-y-3">
            {alerts.map((alert) => (
              <li
                key={alert.id}
                className="flex items-start gap-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-3"
              >
                <span
                  className={clsx(
                    "mt-0.5 h-2 w-2 shrink-0 rounded-full",
                    alert.priority === "critical"
                      ? "bg-red-500"
                      : alert.priority === "high"
                        ? "bg-orange-500"
                        : "bg-yellow-500",
                  )}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-800 dark:text-gray-200">{alert.message ?? "Health alert"}</p>
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                    {alert.created_at
                      ? new Date(alert.created_at).toLocaleDateString()
                      : ""}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Quick actions */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <QuickAction
            href="/patient-portal/appointments"
            label="Schedule Appointment"
            description="Request a visit with your provider"
          />
          <QuickAction
            href="/patient-portal/messages"
            label="Message Provider"
            description="Send a secure message"
          />
          <QuickAction
            href="/patient-portal/health"
            label="View Vitals"
            description="See your health data and trends"
          />
        </div>
      </section>

      {/* Recent vitals preview */}
      {upcomingVitals.length > 0 && (
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Latest Vitals
            </h2>
            <Link
              href="/patient-portal/health"
              className="text-sm font-medium text-healthos-600 hover:text-healthos-700"
            >
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {upcomingVitals.map((v, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4"
              >
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {v.type}
                </p>
                <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {typeof v.value === "object" ? JSON.stringify(v.value) : String(v.value)}{" "}
                  <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
                    {v.unit}
                  </span>
                </p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {v.recorded_at
                    ? new Date(v.recorded_at).toLocaleString()
                    : ""}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Helper components ────────────────────────────────────────────────────────

function clsx(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(" ");
}

function SummaryCard({
  title,
  value,
  subtitle,
  color,
}: {
  title: string;
  value: string;
  subtitle: string;
  color: "blue" | "red" | "green" | "purple" | "amber";
}) {
  const colorMap = {
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    red: "border-red-200 bg-red-50 text-red-700",
    green: "border-green-200 bg-green-50 text-green-700",
    purple: "border-purple-200 bg-purple-50 text-purple-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
  };

  return (
    <div className={`rounded-xl border p-5 ${colorMap[color]}`}>
      <p className="text-sm font-medium opacity-80">{title}</p>
      <p className="mt-1 text-xl sm:text-3xl font-bold">{value}</p>
      <p className="mt-0.5 text-xs opacity-60">{subtitle}</p>
    </div>
  );
}

function QuickAction({
  href,
  label,
  description,
}: {
  href: string;
  label: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 transition-colors hover:border-healthos-300 hover:bg-healthos-50"
    >
      <p className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-healthos-700">
        {label}
      </p>
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{description}</p>
    </Link>
  );
}
