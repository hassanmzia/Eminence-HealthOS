"use client";

import { useState, useEffect } from "react";
import { fetchDashboardSummary } from "@/lib/api";

export function CriticalAlertsBanner() {
  const [critical, setCritical] = useState(0);
  const [high, setHigh] = useState(0);
  const [total, setTotal] = useState(0);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    fetchDashboardSummary()
      .then((data) => {
        setCritical(data.critical_alerts);
        setHigh(data.high_alerts);
        setTotal(data.open_alerts);
      })
      .catch(() => {});
  }, []);

  if (critical === 0 || dismissed) return null;

  return (
    <div className="animate-fade-in-up overflow-hidden rounded-xl border border-red-200/80 bg-gradient-to-r from-red-50 via-red-50 to-orange-50 shadow-sm">
      <div className="flex items-center gap-4 px-5 py-4">
        {/* Pulsing icon */}
        <div className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center">
          <span className="absolute inset-0 animate-ping rounded-full bg-red-400 opacity-20" />
          <div className="relative flex h-10 w-10 items-center justify-center rounded-full bg-red-100 ring-4 ring-red-50">
            <svg className="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
        </div>

        <div className="flex-1">
          <p className="text-sm font-semibold text-red-900">
            {critical} critical alert{critical !== 1 ? "s" : ""} require immediate attention
          </p>
          <p className="mt-0.5 text-xs text-red-600/80">
            {high} high priority &middot; {total} total pending alerts across your patients
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="/alerts?priority=critical"
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-red-700 hover:shadow-md"
          >
            Review Now
          </a>
          <button
            onClick={() => setDismissed(true)}
            className="rounded-lg p-2 text-red-400 transition-colors hover:bg-red-100 hover:text-red-600"
            aria-label="Dismiss"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Animated bottom progress bar */}
      <div className="h-1 bg-red-100">
        <div className="h-full animate-pulse bg-gradient-to-r from-red-500 via-orange-500 to-red-500" style={{ width: `${Math.min((critical / Math.max(total, 1)) * 100, 100)}%` }} />
      </div>
    </div>
  );
}
