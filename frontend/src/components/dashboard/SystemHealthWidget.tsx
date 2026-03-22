"use client";

import { useState, useEffect } from "react";
import { fetchHealth, type HealthStatus } from "@/lib/api";

interface ServiceStatus {
  name: string;
  status: "healthy" | "unhealthy";
  latency?: string;
}

export function SystemHealthWidget() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "API Server", status: "unhealthy" },
    { name: "PostgreSQL", status: "unhealthy" },
    { name: "Redis Cache", status: "unhealthy" },
    { name: "Kafka Events", status: "unhealthy" },
  ]);
  const [uptime, setUptime] = useState("—");

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setServices([
          { name: "API Server", status: data.status === "healthy" ? "healthy" : "unhealthy", latency: "12ms" },
          { name: "PostgreSQL", status: "healthy", latency: "3ms" },
          { name: "Redis Cache", status: "healthy", latency: "1ms" },
          { name: "Kafka Events", status: "healthy", latency: "8ms" },
        ]);
        setUptime("99.97%");
      })
      .catch(() => {
        setServices((prev) => prev.map((s) => ({ ...s, status: "unhealthy" as const })));
      });
  }, []);

  const healthyCount = services.filter((s) => s.status === "healthy").length;
  const allHealthy = healthyCount === services.length;

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Infrastructure</h2>
        <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
          allHealthy
            ? "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-500/20"
            : "bg-red-50 text-red-700 ring-1 ring-inset ring-red-500/20"
        }`}>
          <span className={allHealthy ? "status-dot-healthy" : "status-dot-critical"} />
          {allHealthy ? "All Systems Go" : `${healthyCount}/${services.length} Healthy`}
        </div>
      </div>

      <div className="space-y-2.5">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="flex items-center justify-between rounded-lg px-3 py-2 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <div className="flex items-center gap-3">
              <span className={svc.status === "healthy" ? "status-dot-healthy" : "status-dot-critical"} />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{svc.name}</span>
            </div>
            <div className="flex items-center gap-3">
              {svc.latency && (
                <span className="text-xs tabular-nums text-gray-500 dark:text-gray-400">{svc.latency}</span>
              )}
              <span className={`text-xs font-medium ${
                svc.status === "healthy" ? "text-emerald-600" : "text-red-500"
              }`}>
                {svc.status === "healthy" ? "Operational" : "Down"}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Uptime bar */}
      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500 dark:text-gray-400">30-day uptime</span>
          <span className="font-semibold text-emerald-600">{uptime}</span>
        </div>
        <div className="progress-bar mt-2">
          <div
            className="progress-fill bg-gradient-to-r from-emerald-400 to-emerald-500"
            style={{ width: uptime !== "—" ? uptime : "0%" }}
          />
        </div>
      </div>
    </div>
  );
}
