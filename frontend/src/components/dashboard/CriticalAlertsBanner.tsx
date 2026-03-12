"use client";

import { useState, useEffect } from "react";
import { fetchDashboardSummary } from "@/lib/api";

export function CriticalAlertsBanner() {
  const [critical, setCritical] = useState(0);
  const [high, setHigh] = useState(0);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchDashboardSummary()
      .then((data) => {
        setCritical(data.critical_alerts);
        setHigh(data.high_alerts);
        setTotal(data.open_alerts);
      })
      .catch(() => {});
  }, []);

  if (critical === 0) return null;

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
      <div className="flex items-center gap-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-100">
          <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-red-800">
            {critical} critical alert{critical !== 1 ? "s" : ""} require immediate attention
          </p>
          <p className="text-xs text-red-600">
            {high} high priority &middot; {total} total pending
          </p>
        </div>
        <a href="/alerts?priority=critical" className="text-sm font-medium text-red-700 hover:text-red-900">
          View all &rarr;
        </a>
      </div>
    </div>
  );
}
