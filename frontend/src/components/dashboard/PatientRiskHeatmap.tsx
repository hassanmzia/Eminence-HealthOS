"use client";

import { useState, useEffect } from "react";
import { fetchPatients, type PatientData } from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-400",
  moderate: "bg-yellow-300",
  low: "bg-green-300",
};

const RISK_ORDER: Record<string, number> = {
  critical: 4,
  high: 3,
  moderate: 2,
  low: 1,
};

function patientName(p: PatientData): string {
  const demo = p.demographics as Record<string, unknown>;
  return (demo?.name as string) || p.mrn || "Unknown";
}

function conditionLabels(p: PatientData): string[] {
  return p.conditions.map((c) => (c.display as string) || (c.code as string) || "");
}

export function PatientRiskHeatmap() {
  const [patients, setPatients] = useState<PatientData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPatients({ page: 1 })
      .then((res) => setPatients(res.patients))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const sorted = [...patients].sort(
    (a, b) => (RISK_ORDER[b.risk_level] || 0) - (RISK_ORDER[a.risk_level] || 0)
  );

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Patient Risk Heatmap</h2>
        <div className="flex gap-2 text-xs text-gray-500">
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <span key={level} className="flex items-center gap-1">
              <span className={`inline-block h-2.5 w-2.5 rounded-sm ${color}`} />
              {level}
            </span>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">Loading patients...</p>
      ) : sorted.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">No patients found</p>
      ) : (
        <div className="space-y-2">
          {sorted.map((patient) => {
            const conditions = conditionLabels(patient);
            return (
              <a
                key={patient.id}
                href={`/patients/${patient.id}`}
                className="flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-gray-50"
              >
                <div
                  className={`h-8 w-8 rounded-lg ${RISK_COLORS[patient.risk_level] || "bg-gray-300"} flex items-center justify-center text-xs font-bold text-white`}
                >
                  {patient.risk_level[0]?.toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{patientName(patient)}</p>
                  <p className="text-xs text-gray-500">
                    {conditions.length > 0 ? conditions.join(", ") : "No active conditions"}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`badge-${patient.risk_level}`}>{patient.risk_level}</span>
                  {patient.mrn && (
                    <p className="mt-0.5 text-xs text-gray-400">MRN: {patient.mrn}</p>
                  )}
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
