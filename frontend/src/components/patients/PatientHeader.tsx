"use client";

import { useState, useEffect } from "react";
import { fetchPatient, type PatientData } from "@/lib/api";

const RISK_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  moderate: "badge-moderate",
  low: "badge-low",
};

export function PatientHeader({ patientId }: { patientId: string }) {
  const [patient, setPatient] = useState<PatientData | null>(null);

  useEffect(() => {
    fetchPatient(patientId)
      .then(setPatient)
      .catch(() => {});
  }, [patientId]);

  if (!patient) return <div className="card animate-pulse h-40" />;

  const demo = patient.demographics as Record<string, unknown>;
  const name = (demo?.name as string) || "Unknown";
  const dob = (demo?.dob as string) || "";
  const gender = (demo?.gender as string) || "";
  const age = dob
    ? Math.floor((Date.now() - new Date(dob).getTime()) / (365.25 * 24 * 60 * 60 * 1000))
    : null;

  const conditions = patient.conditions.map(
    (c) => (c.display as string) || (c.code as string) || ""
  );
  const medications = patient.medications.map((m) => {
    const mName = (m.name as string) || "";
    const dose = (m.dose as string) || "";
    const freq = (m.frequency as string) || "";
    return [mName, dose, freq].filter(Boolean).join(" ");
  });

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{name}</h1>
            <span className={RISK_BADGE[patient.risk_level]}>{patient.risk_level} risk</span>
          </div>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {patient.mrn || "No MRN"}
            {age != null && <> &middot; {age}y</>}
            {gender && <> {gender}</>}
            {dob && <> &middot; DOB {dob}</>}
          </p>
        </div>
        <a href="/patients" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:text-gray-400">&larr; Back to patients</a>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <h3 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Conditions</h3>
          <ul className="mt-1 space-y-0.5">
            {conditions.length > 0 ? (
              conditions.map((c, i) => (
                <li key={i} className="text-sm text-gray-700 dark:text-gray-300">{c}</li>
              ))
            ) : (
              <li className="text-sm text-gray-500 dark:text-gray-400">None recorded</li>
            )}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Medications</h3>
          <ul className="mt-1 space-y-0.5">
            {medications.length > 0 ? (
              medications.map((m, i) => (
                <li key={i} className="text-sm text-gray-700 dark:text-gray-300">{m}</li>
              ))
            ) : (
              <li className="text-sm text-gray-500 dark:text-gray-400">None recorded</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
