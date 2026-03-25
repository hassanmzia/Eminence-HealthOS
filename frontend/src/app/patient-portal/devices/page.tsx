"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchMyDevices, type PatientDevice } from "@/lib/patient-api";

const DEVICE_TYPE_ICONS: Record<string, { label: string; color: string }> = {
  Watch: { label: "W", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" },
  Ring: { label: "R", color: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400" },
  EarClip: { label: "E", color: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400" },
  Adapter: { label: "A", color: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400" },
  PulseGlucometer: { label: "G", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" },
};

const STATUS_COLORS: Record<string, string> = {
  Active: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  Inactive: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  Maintenance: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  Retired: "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400",
};

export default function DevicesPage() {
  const [devices, setDevices] = useState<PatientDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setDevices(await fetchMyDevices());
      setError("");
    } catch {
      setError("Unable to load your devices. Please try again later.");
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">My Devices</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          View your assigned health monitoring devices and their status.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-4">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
        </div>
      ) : devices.length === 0 ? (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-12 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
            <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">No devices assigned</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Your care team has not yet assigned any monitoring devices to your account.<br />
            Contact your provider if you believe this is an error.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {devices.map((d) => {
            const typeInfo = DEVICE_TYPE_ICONS[d.device_type] || { label: d.device_type[0], color: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400" };
            return (
              <div
                key={d.id}
                className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 space-y-3"
              >
                {/* Device header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-lg text-sm font-bold ${typeInfo.color}`}>
                      {typeInfo.label}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{d.device_name}</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{d.device_type}</p>
                    </div>
                  </div>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_COLORS[d.status] || STATUS_COLORS.Inactive}`}>
                    {d.status}
                  </span>
                </div>

                {/* Device details */}
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Device ID</p>
                    <p className="text-xs text-gray-700 dark:text-gray-300 mt-0.5 font-mono">{d.device_unique_id}</p>
                  </div>
                  {d.manufacturer && (
                    <div>
                      <p className="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Manufacturer</p>
                      <p className="text-xs text-gray-700 dark:text-gray-300 mt-0.5">{d.manufacturer} {d.model_number || ""}</p>
                    </div>
                  )}
                  {d.battery_level != null && (
                    <div>
                      <p className="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Battery</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <div className="h-2 w-16 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${d.battery_level > 20 ? "bg-emerald-500" : "bg-red-500"}`}
                            style={{ width: `${d.battery_level}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600 dark:text-gray-400">{d.battery_level}%</span>
                      </div>
                    </div>
                  )}
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Last Sync</p>
                    <p className="text-xs text-gray-700 dark:text-gray-300 mt-0.5">
                      {d.last_sync ? new Date(d.last_sync).toLocaleString() : "Never synced"}
                    </p>
                  </div>
                  {d.firmware_version && (
                    <div>
                      <p className="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">Firmware</p>
                      <p className="text-xs text-gray-700 dark:text-gray-300 mt-0.5">{d.firmware_version}</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
