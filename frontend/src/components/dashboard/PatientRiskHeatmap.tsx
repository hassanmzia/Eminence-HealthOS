"use client";

import { useState, useEffect } from "react";

interface PatientRisk {
  id: string;
  name: string;
  risk_score: number;
  risk_level: string;
  conditions: string[];
  last_vital: string;
}

const RISK_COLORS: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-400",
  moderate: "bg-yellow-300",
  low: "bg-green-300",
};

// Demo data — will be replaced by real API calls
const DEMO_PATIENTS: PatientRisk[] = [
  { id: "1", name: "J. Smith", risk_score: 0.82, risk_level: "critical", conditions: ["CHF", "Diabetes"], last_vital: "5m ago" },
  { id: "2", name: "M. Johnson", risk_score: 0.67, risk_level: "high", conditions: ["Hypertension"], last_vital: "12m ago" },
  { id: "3", name: "R. Williams", risk_score: 0.55, risk_level: "high", conditions: ["COPD"], last_vital: "8m ago" },
  { id: "4", name: "S. Brown", risk_score: 0.38, risk_level: "moderate", conditions: ["Diabetes"], last_vital: "15m ago" },
  { id: "5", name: "L. Davis", risk_score: 0.22, risk_level: "low", conditions: [], last_vital: "3m ago" },
  { id: "6", name: "K. Wilson", risk_score: 0.78, risk_level: "critical", conditions: ["CHF", "CKD"], last_vital: "2m ago" },
  { id: "7", name: "A. Taylor", risk_score: 0.41, risk_level: "moderate", conditions: ["Asthma"], last_vital: "20m ago" },
  { id: "8", name: "P. Anderson", risk_score: 0.15, risk_level: "low", conditions: [], last_vital: "10m ago" },
];

export function PatientRiskHeatmap() {
  const [patients, setPatients] = useState<PatientRisk[]>([]);

  useEffect(() => {
    // TODO: Replace with fetchPatients() API call
    setPatients(DEMO_PATIENTS);
  }, []);

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

      <div className="space-y-2">
        {patients
          .sort((a, b) => b.risk_score - a.risk_score)
          .map((patient) => (
            <a
              key={patient.id}
              href={`/patients/${patient.id}`}
              className="flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-gray-50"
            >
              <div
                className={`h-8 w-8 rounded-lg ${RISK_COLORS[patient.risk_level]} flex items-center justify-center text-xs font-bold text-white`}
              >
                {Math.round(patient.risk_score * 100)}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{patient.name}</p>
                <p className="text-xs text-gray-500">
                  {patient.conditions.length > 0 ? patient.conditions.join(", ") : "No active conditions"}
                </p>
              </div>
              <div className="text-right">
                <span className={`badge-${patient.risk_level}`}>{patient.risk_level}</span>
                <p className="mt-0.5 text-xs text-gray-400">{patient.last_vital}</p>
              </div>
            </a>
          ))}
      </div>
    </div>
  );
}
