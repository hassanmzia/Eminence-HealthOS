"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface PatientRow {
  id: string;
  name: string;
  mrn: string;
  age: number;
  gender: string;
  conditions: string[];
  risk_level: string;
  last_vital: string;
  alert_count: number;
}

const RISK_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  moderate: "badge-moderate",
  low: "badge-low",
};

const DEMO_PATIENTS: PatientRow[] = [
  { id: "1", name: "John Smith", mrn: "MRN-10042", age: 68, gender: "M", conditions: ["CHF", "Type 2 Diabetes"], risk_level: "critical", last_vital: "5 min ago", alert_count: 3 },
  { id: "2", name: "Mary Johnson", mrn: "MRN-10078", age: 55, gender: "F", conditions: ["Hypertension"], risk_level: "high", last_vital: "12 min ago", alert_count: 1 },
  { id: "3", name: "Robert Williams", mrn: "MRN-10103", age: 72, gender: "M", conditions: ["COPD", "CKD Stage 3"], risk_level: "high", last_vital: "8 min ago", alert_count: 2 },
  { id: "4", name: "Sarah Brown", mrn: "MRN-10156", age: 45, gender: "F", conditions: ["Type 1 Diabetes"], risk_level: "moderate", last_vital: "15 min ago", alert_count: 0 },
  { id: "5", name: "Linda Davis", mrn: "MRN-10201", age: 38, gender: "F", conditions: [], risk_level: "low", last_vital: "3 min ago", alert_count: 0 },
  { id: "6", name: "Karen Wilson", mrn: "MRN-10089", age: 70, gender: "F", conditions: ["CHF", "CKD Stage 4"], risk_level: "critical", last_vital: "2 min ago", alert_count: 4 },
];

export function PatientList() {
  const [patients, setPatients] = useState<PatientRow[]>([]);

  useEffect(() => {
    // TODO: Replace with fetchPatients() API call
    setPatients(DEMO_PATIENTS);
  }, []);

  return (
    <div className="card overflow-hidden p-0">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Patient</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">MRN</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Conditions</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Risk</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Last Vital</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Alerts</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {patients.map((patient) => (
            <tr key={patient.id} className="transition-colors hover:bg-gray-50">
              <td className="px-6 py-4">
                <Link href={`/patients/${patient.id}`} className="text-sm font-medium text-healthos-600 hover:text-healthos-800">
                  {patient.name}
                </Link>
                <p className="text-xs text-gray-400">{patient.age}y {patient.gender}</p>
              </td>
              <td className="px-6 py-4 text-sm text-gray-600">{patient.mrn}</td>
              <td className="px-6 py-4">
                <div className="flex flex-wrap gap-1">
                  {patient.conditions.length > 0
                    ? patient.conditions.map((c) => (
                        <span key={c} className="inline-flex rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                          {c}
                        </span>
                      ))
                    : <span className="text-xs text-gray-400">None</span>}
                </div>
              </td>
              <td className="px-6 py-4">
                <span className={RISK_BADGE[patient.risk_level]}>{patient.risk_level}</span>
              </td>
              <td className="px-6 py-4 text-sm text-gray-500">{patient.last_vital}</td>
              <td className="px-6 py-4">
                {patient.alert_count > 0 ? (
                  <span className="inline-flex items-center justify-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                    {patient.alert_count}
                  </span>
                ) : (
                  <span className="text-xs text-gray-400">0</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
