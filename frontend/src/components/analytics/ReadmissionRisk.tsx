"use client";

import { useState, useEffect, useCallback } from "react";
import { predictReadmissionRisk } from "@/lib/api";

const MOCK_HIGH_RISK_PATIENTS = [
  { id: "P-1042", name: "John M.", age: 78, score: 0.82, level: "critical", topFactor: "heart_failure", daysPost: 2 },
  { id: "P-2301", name: "Maria S.", age: 72, score: 0.71, level: "critical", topFactor: "prior_admissions_6m", daysPost: 5 },
  { id: "P-0887", name: "Robert K.", age: 68, score: 0.64, level: "high", topFactor: "copd", daysPost: 3 },
  { id: "P-1555", name: "Linda W.", age: 81, score: 0.58, level: "high", topFactor: "medication_non_adherence", daysPost: 7 },
  { id: "P-3201", name: "James T.", age: 65, score: 0.52, level: "high", topFactor: "discharge_against_advice", daysPost: 1 },
];

const INTERVENTIONS = {
  critical: ["Transition care nurse within 24h", "Daily phone follow-up", "PCP within 48h"],
  high: ["Nurse call within 48h", "Twice-weekly follow-up", "PCP within 7 days"],
};

export function ReadmissionRisk() {
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null);
  const [patients, setPatients] = useState(MOCK_HIGH_RISK_PATIENTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await predictReadmissionRisk({ threshold: 0.5, limit: 10 });
      const data = res as Record<string, unknown>;
      const items = data.patients as Array<Record<string, unknown>> | undefined;
      if (items && items.length > 0) {
        setPatients(
          items.map((p) => ({
            id: p.id as string,
            name: p.name as string,
            age: p.age as number,
            score: p.score as number,
            level: p.level as string,
            topFactor: p.top_factor as string,
            daysPost: p.days_post_discharge as number,
          }))
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load readmission risk data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Readmission Risk</h2>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-14 rounded-lg bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Readmission Risk</h2>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={loadData} className="mt-2 rounded bg-red-600 px-3 py-1 text-xs text-white hover:bg-red-700">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Readmission Risk</h2>
        <span className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600">
          {patients.length} high-risk discharges
        </span>
      </div>

      <div className="space-y-2">
        {patients.map((p) => (
          <div key={p.id}>
            <button
              onClick={() => setSelectedPatient(selectedPatient === p.id ? null : p.id)}
              className="flex w-full items-center justify-between rounded-lg border border-gray-200 p-3 text-left hover:bg-gray-50"
            >
              <div className="flex items-center gap-3">
                <span className={`h-2.5 w-2.5 rounded-full ${
                  p.level === "critical" ? "bg-red-500" : "bg-orange-500"
                }`} />
                <div>
                  <span className="text-sm font-medium text-gray-900">{p.name}</span>
                  <span className="ml-2 text-xs text-gray-500">Age {p.age}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">{p.daysPost}d post-discharge</span>
                <span className={`rounded px-2 py-0.5 text-xs font-bold ${
                  p.level === "critical" ? "bg-red-100 text-red-700" : "bg-orange-100 text-orange-700"
                }`}>
                  {(p.score * 100).toFixed(0)}%
                </span>
              </div>
            </button>

            {selectedPatient === p.id && (
              <div className="ml-5 mt-1 rounded-lg border border-gray-100 bg-gray-50 p-3">
                <p className="mb-2 text-xs font-medium text-gray-700">
                  Top factor: <span className="text-gray-900">{p.topFactor.replace(/_/g, " ")}</span>
                </p>
                <p className="mb-1 text-xs font-medium text-gray-700">Recommended interventions:</p>
                <ul className="space-y-1">
                  {(INTERVENTIONS[p.level as keyof typeof INTERVENTIONS] || []).map((i, idx) => (
                    <li key={idx} className="flex items-center gap-1.5 text-xs text-gray-600">
                      <span className="h-1 w-1 rounded-full bg-gray-400" />
                      {i}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
