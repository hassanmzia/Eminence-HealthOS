"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { fetchPatients, type PatientData } from "@/lib/api";

const RISK_BADGE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  moderate: "badge-moderate",
  low: "badge-low",
};

function patientName(p: PatientData): string {
  const d = p.demographics as Record<string, unknown>;
  return (d?.name as string) || "Unknown";
}

function patientAge(p: PatientData): string {
  const d = p.demographics as Record<string, unknown>;
  const dob = d?.dob as string;
  if (!dob) return "";
  const years = Math.floor(
    (Date.now() - new Date(dob).getTime()) / (365.25 * 24 * 60 * 60 * 1000)
  );
  return `${years}y`;
}

function patientGender(p: PatientData): string {
  const d = p.demographics as Record<string, unknown>;
  const g = (d?.gender as string) || "";
  return g.charAt(0).toUpperCase();
}

function conditionLabels(p: PatientData): string[] {
  return p.conditions.map((c) => (c.display as string) || (c.code as string) || "");
}

export function PatientList({ search }: { search?: string }) {
  const [patients, setPatients] = useState<PatientData[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    fetchPatients({ page, search: search || undefined })
      .then((res) => {
        setPatients(res.patients);
        setTotal(res.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, search]);

  useEffect(() => {
    setPage(1);
  }, [search]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="card overflow-hidden p-0">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Patient</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">MRN</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Conditions</th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Risk</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {loading ? (
            <tr>
              <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-400">
                Loading patients...
              </td>
            </tr>
          ) : patients.length === 0 ? (
            <tr>
              <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-400">
                No patients found
              </td>
            </tr>
          ) : (
            patients.map((patient) => {
              const conditions = conditionLabels(patient);
              return (
                <tr key={patient.id} className="transition-colors hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link
                      href={`/patients/${patient.id}`}
                      className="text-sm font-medium text-healthos-600 hover:text-healthos-800"
                    >
                      {patientName(patient)}
                    </Link>
                    <p className="text-xs text-gray-400">
                      {patientAge(patient)} {patientGender(patient)}
                    </p>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{patient.mrn || "—"}</td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {conditions.length > 0
                        ? conditions.map((c, i) => (
                            <span key={i} className="inline-flex rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                              {c}
                            </span>
                          ))
                        : <span className="text-xs text-gray-400">None</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={RISK_BADGE[patient.risk_level]}>{patient.risk_level}</span>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-6 py-3">
          <span className="text-sm text-gray-500">
            Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={page * 20 >= total}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
