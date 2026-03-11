"use client";

import { useState, useEffect } from "react";

interface AlertSummary {
  critical: number;
  high: number;
  pending: number;
}

export function CriticalAlertsBanner() {
  const [alerts, setAlerts] = useState<AlertSummary>({ critical: 0, high: 0, pending: 0 });

  useEffect(() => {
    // TODO: Replace with real API call
    setAlerts({ critical: 2, high: 5, pending: 12 });
  }, []);

  if (alerts.critical === 0) return null;

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
            {alerts.critical} critical alert{alerts.critical !== 1 ? "s" : ""} require immediate attention
          </p>
          <p className="text-xs text-red-600">
            {alerts.high} high priority &middot; {alerts.pending} total pending
          </p>
        </div>
        <a href="/alerts?priority=critical" className="text-sm font-medium text-red-700 hover:text-red-900">
          View all &rarr;
        </a>
      </div>
    </div>
  );
}
