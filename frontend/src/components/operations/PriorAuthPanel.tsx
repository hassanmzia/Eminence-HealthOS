"use client";

import { useState, useEffect } from "react";

interface PriorAuth {
  auth_reference: string;
  patient_name: string;
  payer: string;
  procedure: string;
  status: string;
  submitted_at: string;
  estimated_cost: number;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  submitted: "bg-blue-100 text-blue-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  appealed: "bg-purple-100 text-purple-800",
};

const DEMO_AUTHS: PriorAuth[] = [
  { auth_reference: "PA-20260312-001", patient_name: "J. Smith", payer: "Aetna", procedure: "MRI Lumbar Spine", status: "submitted", submitted_at: "2026-03-10T10:00:00Z", estimated_cost: 2800 },
  { auth_reference: "PA-20260312-002", patient_name: "M. Johnson", payer: "UnitedHealth", procedure: "CT Abdomen", status: "approved", submitted_at: "2026-03-09T14:30:00Z", estimated_cost: 1500 },
  { auth_reference: "PA-20260312-003", patient_name: "K. Wilson", payer: "Cigna", procedure: "Knee Arthroplasty", status: "pending", submitted_at: "", estimated_cost: 45000 },
  { auth_reference: "PA-20260312-004", patient_name: "S. Brown", payer: "Medicare", procedure: "Genetic Testing", status: "denied", submitted_at: "2026-03-08T09:00:00Z", estimated_cost: 3200 },
];

export function PriorAuthPanel() {
  const [auths, setAuths] = useState<PriorAuth[]>([]);

  useEffect(() => {
    setAuths(DEMO_AUTHS);
  }, []);

  const counts = {
    pending: auths.filter((a) => a.status === "pending").length,
    submitted: auths.filter((a) => a.status === "submitted").length,
    approved: auths.filter((a) => a.status === "approved").length,
    denied: auths.filter((a) => a.status === "denied").length,
  };

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Prior Authorizations</h2>
        <button className="rounded bg-healthos-600 px-3 py-1 text-xs font-medium text-white hover:bg-healthos-700">
          New Request
        </button>
      </div>

      {/* Status summary */}
      <div className="mb-4 grid grid-cols-4 gap-2">
        {Object.entries(counts).map(([status, count]) => (
          <div key={status} className="rounded-lg bg-gray-50 p-2 text-center">
            <div className="text-lg font-bold text-gray-900">{count}</div>
            <div className="text-xs capitalize text-gray-500">{status}</div>
          </div>
        ))}
      </div>

      {/* Auth list */}
      <div className="space-y-2">
        {auths.map((auth) => (
          <div key={auth.auth_reference} className="rounded-lg border border-gray-200 bg-white p-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-gray-900">{auth.procedure}</span>
                <span className="ml-2 text-xs text-gray-400">{auth.auth_reference}</span>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[auth.status]}`}>
                {auth.status}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
              <span>{auth.patient_name}</span>
              <span>&middot;</span>
              <span>{auth.payer}</span>
              <span>&middot;</span>
              <span>${auth.estimated_cost.toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
