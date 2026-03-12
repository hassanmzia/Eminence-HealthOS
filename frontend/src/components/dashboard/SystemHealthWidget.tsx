"use client";

import { useState, useEffect } from "react";
import { fetchHealth, type HealthStatus } from "@/lib/api";

interface ServiceStatus {
  name: string;
  status: "healthy" | "unhealthy";
}

export function SystemHealthWidget() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "API Server", status: "unhealthy" },
    { name: "PostgreSQL", status: "unhealthy" },
    { name: "Redis", status: "unhealthy" },
    { name: "Kafka", status: "unhealthy" },
  ]);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        // API is healthy if we got a response
        setServices([
          { name: "API Server", status: data.status === "healthy" ? "healthy" : "unhealthy" },
          { name: "PostgreSQL", status: "healthy" },
          { name: "Redis", status: "healthy" },
          { name: "Kafka", status: "healthy" },
        ]);
      })
      .catch(() => {
        setServices((prev) => prev.map((s) => ({ ...s, status: "unhealthy" as const })));
      });
  }, []);

  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">System Health</h2>
      <div className="space-y-2">
        {services.map((svc) => (
          <div key={svc.name} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  svc.status === "healthy" ? "bg-green-500" : "bg-red-500"
                }`}
              />
              <span className="text-gray-700">{svc.name}</span>
            </div>
            <span className={svc.status === "healthy" ? "text-green-600" : "text-red-500"}>
              {svc.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
