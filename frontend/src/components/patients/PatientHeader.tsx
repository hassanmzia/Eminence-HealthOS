"use client";

import { useState, useEffect } from "react";

interface PatientDetail {
  name: string;
  mrn: string;
  age: number;
  gender: string;
  dob: string;
  conditions: string[];
  medications: string[];
  risk_level: string;
  care_team: string[];
}

const DEMO: PatientDetail = {
  name: "John Smith",
  mrn: "MRN-10042",
  age: 68,
  gender: "Male",
  dob: "1958-03-15",
  conditions: ["Congestive Heart Failure", "Type 2 Diabetes", "Hypertension"],
  medications: ["Metformin 500mg BID", "Lisinopril 20mg QD", "Furosemide 40mg QD"],
  risk_level: "critical",
  care_team: ["Dr. A. Patel (Cardiology)", "RN C. Lee"],
};

const RISK_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  moderate: "badge-moderate",
  low: "badge-low",
};

export function PatientHeader({ patientId }: { patientId: string }) {
  const [patient, setPatient] = useState<PatientDetail | null>(null);

  useEffect(() => {
    // TODO: Replace with fetchPatient(patientId)
    setPatient(DEMO);
  }, [patientId]);

  if (!patient) return <div className="card animate-pulse h-40" />;

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{patient.name}</h1>
            <span className={RISK_BADGE[patient.risk_level]}>{patient.risk_level} risk</span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {patient.mrn} &middot; {patient.age}y {patient.gender} &middot; DOB {patient.dob}
          </p>
        </div>
        <a href="/patients" className="text-sm text-gray-400 hover:text-gray-600">&larr; Back to patients</a>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <h3 className="text-xs font-medium uppercase text-gray-400">Conditions</h3>
          <ul className="mt-1 space-y-0.5">
            {patient.conditions.map((c) => (
              <li key={c} className="text-sm text-gray-700">{c}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-medium uppercase text-gray-400">Medications</h3>
          <ul className="mt-1 space-y-0.5">
            {patient.medications.map((m) => (
              <li key={m} className="text-sm text-gray-700">{m}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-medium uppercase text-gray-400">Care Team</h3>
          <ul className="mt-1 space-y-0.5">
            {patient.care_team.map((t) => (
              <li key={t} className="text-sm text-gray-700">{t}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
