"use client";

import { useState, useEffect } from "react";
import { prepareVisit } from "@/lib/api";

interface PreVisitSummary {
  patient_name?: string;
  conditions: string[];
  medications: string[];
  latest_vitals: Record<string, { value: number | string; unit: string }>;
  clinical_flags: string[];
  risk_level: string;
}

const RISK_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  moderate: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

interface Props {
  sessionId?: string;
}

export function VisitPreparation({ sessionId }: Props) {
  const [summary, setSummary] = useState<PreVisitSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setSummary(null);
      return;
    }

    setLoading(true);
    setError(null);

    prepareVisit(sessionId)
      .then((data) => {
        const s: PreVisitSummary = {
          patient_name: (data.patient_name as string) || undefined,
          conditions: (data.conditions as string[]) || [],
          medications: (data.medications as string[]) || [],
          latest_vitals: (data.latest_vitals as Record<string, { value: number | string; unit: string }>) || {},
          clinical_flags: (data.clinical_flags as string[]) || [],
          risk_level: (data.risk_level as string) || "low",
        };
        setSummary(s);
      })
      .catch(() => setError("Failed to load pre-visit summary"))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (!sessionId) {
    return (
      <div className="card">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">Pre-Visit Summary</h2>
        <p className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">Select a session to view preparation</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="card">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">Pre-Visit Summary</h2>
        <div className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">Preparing visit summary...</div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="card">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">Pre-Visit Summary</h2>
        <p className="py-4 text-center text-sm text-red-400">{error || "No data available"}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Pre-Visit Summary</h2>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${RISK_BADGE[summary.risk_level] || RISK_BADGE.low}`}>
          {summary.risk_level}
        </span>
      </div>

      {summary.patient_name && (
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{summary.patient_name}</p>
      )}

      {/* Clinical flags */}
      {summary.clinical_flags.length > 0 && (
        <div className="mt-2 rounded-md bg-red-50 p-2">
          <p className="text-xs font-medium text-red-700">Clinical Flags</p>
          {summary.clinical_flags.map((flag) => (
            <p key={flag} className="mt-0.5 text-xs text-red-600">&bull; {flag}</p>
          ))}
        </div>
      )}

      {/* Vitals snapshot */}
      {Object.keys(summary.latest_vitals).length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Latest Vitals</p>
          <div className="mt-1 grid grid-cols-2 gap-1">
            {Object.entries(summary.latest_vitals).map(([type, data]) => (
              <div key={type} className="rounded bg-gray-50 dark:bg-gray-800 px-2 py-1">
                <span className="text-xs text-gray-500 dark:text-gray-400">{type.replace("_", " ")}</span>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                  {data.value} <span className="text-xs text-gray-500 dark:text-gray-400">{data.unit}</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Conditions & medications */}
      <div className="mt-3 grid grid-cols-2 gap-3">
        {summary.conditions.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Conditions</p>
            {summary.conditions.map((c) => (
              <p key={c} className="text-xs text-gray-600 dark:text-gray-400">{c}</p>
            ))}
          </div>
        )}
        {summary.medications.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Medications</p>
            {summary.medications.map((m) => (
              <p key={m} className="text-xs text-gray-600 dark:text-gray-400">{m}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
