"use client";

import { useState, useEffect } from "react";
import { fetchPatients, createPatient, type PatientData } from "@/lib/api";

const RISK_BADGE: Record<string, { class: string; dot: string }> = {
  critical: { class: "badge-critical", dot: "bg-red-500" },
  high: { class: "badge-high", dot: "bg-orange-500" },
  moderate: { class: "badge-moderate", dot: "bg-yellow-500" },
  low: { class: "badge-low", dot: "bg-emerald-500" },
};

function patientName(p: PatientData): string {
  const demo = p.demographics as Record<string, unknown>;
  return (demo?.name as string) || p.mrn || "Unknown";
}

function patientInitials(name: string): string {
  return name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);
}

function conditionLabels(p: PatientData): string[] {
  return p.conditions.map((c) => (c.display as string) || (c.code as string) || "").filter(Boolean);
}

export default function PatientsPage() {
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [patients, setPatients] = useState<PatientData[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [showAdd, setShowAdd] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addForm, setAddForm] = useState({ firstName: "", lastName: "", dob: "", gender: "male", mrn: "" });

  const handleAddPatient = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await createPatient({
        mrn: addForm.mrn || undefined,
        demographics: {
          first_name: addForm.firstName,
          last_name: addForm.lastName,
          date_of_birth: addForm.dob,
          gender: addForm.gender,
        },
        conditions: [],
        medications: [],
      });
      setShowAdd(false);
      setAddForm({ firstName: "", lastName: "", dob: "", gender: "male", mrn: "" });
      setLoading(true);
      fetchPatients({ page: 1 }).then((res) => setPatients(res.patients)).catch(() => {}).finally(() => setLoading(false));
    } catch {
      // silently handle
    } finally {
      setAdding(false);
    }
  };

  useEffect(() => {
    fetchPatients({ page: 1 })
      .then((res) => setPatients(res.patients))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = patients.filter((p) => {
    const name = patientName(p).toLowerCase();
    const matchesSearch = !search || name.includes(search.toLowerCase()) || (p.mrn && p.mrn.toLowerCase().includes(search.toLowerCase()));
    const matchesRisk = riskFilter === "all" || p.risk_level === riskFilter;
    return matchesSearch && matchesRisk;
  });

  // Risk distribution
  const distribution = patients.reduce<Record<string, number>>((acc, p) => {
    acc[p.risk_level] = (acc[p.risk_level] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Patients</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{patients.length} patients enrolled across monitoring programs</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary w-fit">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add Patient
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Total", value: patients.length, color: "text-gray-900 dark:text-gray-100", bg: "bg-gray-50 dark:bg-gray-800" },
          { label: "Critical", value: distribution.critical || 0, color: "text-red-700", bg: "bg-red-50" },
          { label: "High Risk", value: distribution.high || 0, color: "text-orange-700", bg: "bg-orange-50" },
          { label: "Stable", value: (distribution.low || 0) + (distribution.moderate || 0), color: "text-emerald-700", bg: "bg-emerald-50" },
        ].map((stat) => (
          <div key={stat.label} className="card !p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{stat.label}</p>
            <p className={`mt-1 text-2xl font-bold tabular-nums ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              type="text"
              placeholder="Search by name or MRN..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input !pl-10"
            />
          </div>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="select !w-auto"
          >
            <option value="all">All Risk Levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="moderate">Moderate</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* View toggle */}
        <div className="flex items-center rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-0.5">
          <button
            onClick={() => setViewMode("grid")}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
              viewMode === "grid" ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
            }`}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
              viewMode === "list" ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
            }`}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </div>
      </div>

      {/* Patient grid / list */}
      {loading ? (
        <div className={viewMode === "grid" ? "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" : "space-y-2"}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-center gap-3">
                <div className="skeleton-circle h-12 w-12" />
                <div className="flex-1 space-y-2">
                  <div className="skeleton-text w-32" />
                  <div className="skeleton-text w-24" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-8 sm:py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
            <svg className="h-7 w-7 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
          </div>
          <p className="mt-4 text-sm font-medium text-gray-900 dark:text-gray-100">No patients found</p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Try adjusting your search or filter criteria</p>
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((patient, i) => {
            const name = patientName(patient);
            const conditions = conditionLabels(patient);
            const cfg = RISK_BADGE[patient.risk_level] || RISK_BADGE.low;
            const meds = patient.medications?.length || 0;
            return (
              <a
                key={patient.id}
                href={`/patients/${patient.id}`}
                className="card card-hover group animate-fade-in-up"
                style={{ animationDelay: `${i * 0.04}s`, animationFillMode: "both" }}
              >
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${
                    patient.risk_level === "critical" ? "from-red-400 to-red-600" :
                    patient.risk_level === "high" ? "from-orange-400 to-orange-600" :
                    patient.risk_level === "moderate" ? "from-yellow-400 to-yellow-600" :
                    "from-emerald-400 to-emerald-600"
                  } text-sm font-bold text-white shadow-sm transition-transform group-hover:scale-105`}>
                    {patientInitials(name)}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 group-hover:text-healthos-700">{name}</p>
                        {patient.mrn && (
                          <p className="text-xs text-gray-500 dark:text-gray-400">MRN: {patient.mrn}</p>
                        )}
                      </div>
                      <span className={cfg.class}>{patient.risk_level}</span>
                    </div>

                    {/* Conditions */}
                    <div className="mt-3 flex flex-wrap gap-1">
                      {conditions.length > 0 ? conditions.slice(0, 2).map((c) => (
                        <span key={c} className="badge-neutral">{c}</span>
                      )) : (
                        <span className="text-xs text-gray-500 dark:text-gray-400">No conditions</span>
                      )}
                      {conditions.length > 2 && (
                        <span className="badge-neutral">+{conditions.length - 2}</span>
                      )}
                    </div>

                    {/* Meta row */}
                    <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                      <span className="flex items-center gap-1">
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-1.47 4.41a2.25 2.25 0 01-2.133 1.59H8.603a2.25 2.25 0 01-2.134-1.59L5 14.5m14 0H5" />
                        </svg>
                        {meds} med{meds !== 1 ? "s" : ""}
                      </span>
                      <span className="flex items-center gap-1">
                        <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                        {patient.risk_level} risk
                      </span>
                    </div>
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      ) : (
        /* List view */
        <div className="card !p-0 overflow-hidden">
          <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full">
            <thead>
              <tr className="table-header">
                <th className="px-6 py-3">Patient</th>
                <th className="px-6 py-3">MRN</th>
                <th className="px-6 py-3">Conditions</th>
                <th className="px-6 py-3">Medications</th>
                <th className="px-6 py-3">Risk</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((patient, i) => {
                const name = patientName(patient);
                const conditions = conditionLabels(patient);
                const cfg = RISK_BADGE[patient.risk_level] || RISK_BADGE.low;
                return (
                  <tr
                    key={patient.id}
                    className="table-row animate-fade-in"
                    style={{ animationDelay: `${i * 0.03}s`, animationFillMode: "both" }}
                  >
                    <td className="px-6 py-3.5">
                      <a href={`/patients/${patient.id}`} className="flex items-center gap-3 hover:text-healthos-700">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                          patient.risk_level === "critical" ? "bg-red-100 text-red-700" :
                          patient.risk_level === "high" ? "bg-orange-100 text-orange-700" :
                          "bg-emerald-100 text-emerald-700"
                        } text-xs font-bold`}>
                          {patientInitials(name)}
                        </div>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{name}</span>
                      </a>
                    </td>
                    <td className="px-6 py-3.5 text-sm text-gray-500 dark:text-gray-400">{patient.mrn || "—"}</td>
                    <td className="px-6 py-3.5">
                      <div className="flex gap-1">
                        {conditions.slice(0, 2).map((c) => (
                          <span key={c} className="badge-neutral">{c}</span>
                        ))}
                        {conditions.length > 2 && <span className="text-xs text-gray-500 dark:text-gray-400">+{conditions.length - 2}</span>}
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-sm tabular-nums text-gray-500 dark:text-gray-400">{patient.medications?.length || 0}</td>
                    <td className="px-6 py-3.5">
                      <span className={cfg.class}>{patient.risk_level}</span>
                    </td>
                    <td className="px-6 py-3.5">
                      <a href={`/patients/${patient.id}`} className="text-healthos-600 hover:text-healthos-700">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                        </svg>
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table></div>
        </div>
      )}

      {/* Add Patient Modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4" onClick={() => setShowAdd(false)}>
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-gray-900 p-4 sm:p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Add New Patient</h2>
              <button onClick={() => setShowAdd(false)} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleAddPatient} className="space-y-4">
              <div className="grid grid-cols-1 xs:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">First Name *</label>
                  <input required value={addForm.firstName} onChange={(e) => setAddForm({ ...addForm, firstName: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Last Name *</label>
                  <input required value={addForm.lastName} onChange={(e) => setAddForm({ ...addForm, lastName: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
              </div>
              <div className="grid grid-cols-1 xs:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Date of Birth *</label>
                  <input required type="date" value={addForm.dob} onChange={(e) => setAddForm({ ...addForm, dob: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Gender *</label>
                  <select required value={addForm.gender} onChange={(e) => setAddForm({ ...addForm, gender: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">MRN</label>
                <input value={addForm.mrn} onChange={(e) => setAddForm({ ...addForm, mrn: e.target.value })} placeholder="e.g. MRN-10042" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowAdd(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
                <button type="submit" disabled={adding} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50">{adding ? "Adding..." : "Add Patient"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Results count */}
      {!loading && filtered.length > 0 && (
        <p className="text-center text-xs text-gray-500 dark:text-gray-400">
          Showing {filtered.length} of {patients.length} patients
        </p>
      )}
    </div>
  );
}
