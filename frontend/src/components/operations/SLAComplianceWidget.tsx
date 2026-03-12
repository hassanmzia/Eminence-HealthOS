"use client";

import { useState, useEffect } from "react";

interface SLAMetrics {
  compliance_rate: number;
  total_open: number;
  on_track: number;
  at_risk: number;
  overdue: number;
}

const DEMO_METRICS: SLAMetrics = {
  compliance_rate: 91.7,
  total_open: 24,
  on_track: 18,
  at_risk: 4,
  overdue: 2,
};

export function SLAComplianceWidget() {
  const [metrics, setMetrics] = useState<SLAMetrics | null>(null);

  useEffect(() => {
    setMetrics(DEMO_METRICS);
  }, []);

  if (!metrics) return null;

  const complianceColor =
    metrics.compliance_rate >= 95
      ? "text-green-600"
      : metrics.compliance_rate >= 85
        ? "text-yellow-600"
        : "text-red-600";

  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">SLA Compliance</h2>

      {/* Main compliance rate */}
      <div className="mb-4 text-center">
        <div className={`text-4xl font-bold ${complianceColor}`}>
          {metrics.compliance_rate}%
        </div>
        <div className="text-xs text-gray-500">Overall compliance rate</div>
      </div>

      {/* Progress bar */}
      <div className="mb-4 h-2 overflow-hidden rounded-full bg-gray-200">
        <div
          className="flex h-full"
          style={{ width: "100%" }}
        >
          <div
            className="bg-green-500"
            style={{ width: `${(metrics.on_track / metrics.total_open) * 100}%` }}
          />
          <div
            className="bg-yellow-500"
            style={{ width: `${(metrics.at_risk / metrics.total_open) * 100}%` }}
          />
          <div
            className="bg-red-500"
            style={{ width: `${(metrics.overdue / metrics.total_open) * 100}%` }}
          />
        </div>
      </div>

      {/* Breakdown */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-green-50 p-2">
          <div className="text-lg font-bold text-green-700">{metrics.on_track}</div>
          <div className="text-xs text-green-600">On Track</div>
        </div>
        <div className="rounded-lg bg-yellow-50 p-2">
          <div className="text-lg font-bold text-yellow-700">{metrics.at_risk}</div>
          <div className="text-xs text-yellow-600">At Risk</div>
        </div>
        <div className="rounded-lg bg-red-50 p-2">
          <div className="text-lg font-bold text-red-700">{metrics.overdue}</div>
          <div className="text-xs text-red-600">Overdue</div>
        </div>
      </div>
    </div>
  );
}
