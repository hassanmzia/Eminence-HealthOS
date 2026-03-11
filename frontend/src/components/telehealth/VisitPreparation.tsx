"use client";

import { useState, useEffect } from "react";

interface PreVisitSummary {
  patient_name: string;
  conditions: string[];
  medications: string[];
  latest_vitals: Record<string, { value: number | string; unit: string }>;
  clinical_flags: string[];
  risk_level: string;
}

const DEMO_SUMMARY: PreVisitSummary = {
  patient_name: "K. Wilson",
  conditions: ["CHF", "CKD Stage 4"],
  medications: ["Furosemide 40mg QD", "Lisinopril 10mg QD", "Metoprolol 25mg BID"],
  latest_vitals: {
    heart_rate: { value: 92, unit: "bpm" },
    blood_pressure: { value: "148/92", unit: "mmHg" },
    spo2: { value: 91, unit: "%" },
    weight: { value: 185, unit: "lbs" },
  },
  clinical_flags: ["SpO2 below 92% threshold", "Weight gain +3lbs in 48h"],
  risk_level: "critical",
};

const RISK_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  moderate: "badge-moderate",
  low: "badge-low",
};

export function VisitPreparation() {
  const [summary, setSummary] = useState<PreVisitSummary | null>(null);

  useEffect(() => {
    setSummary(DEMO_SUMMARY);
  }, []);

  if (!summary) return null;

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Pre-Visit Summary</h2>
        <span className={RISK_BADGE[summary.risk_level]}>{summary.risk_level}</span>
      </div>

      <p className="text-sm font-medium text-gray-700">{summary.patient_name}</p>

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
      <div className="mt-3">
        <p className="text-xs font-medium uppercase text-gray-400">Latest Vitals</p>
        <div className="mt-1 grid grid-cols-2 gap-1">
          {Object.entries(summary.latest_vitals).map(([type, data]) => (
            <div key={type} className="rounded bg-gray-50 px-2 py-1">
              <span className="text-xs text-gray-500">{type.replace("_", " ")}</span>
              <p className="text-sm font-medium text-gray-800">{data.value} <span className="text-xs text-gray-400">{data.unit}</span></p>
            </div>
          ))}
        </div>
      </div>

      {/* Conditions & medications */}
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs font-medium uppercase text-gray-400">Conditions</p>
          {summary.conditions.map((c) => (
            <p key={c} className="text-xs text-gray-600">{c}</p>
          ))}
        </div>
        <div>
          <p className="text-xs font-medium uppercase text-gray-400">Medications</p>
          {summary.medications.map((m) => (
            <p key={m} className="text-xs text-gray-600">{m}</p>
          ))}
        </div>
      </div>
    </div>
  );
}
