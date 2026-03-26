"use client";

import { useEffect, useState } from "react";
import {
  fetchDoctorTreatmentPlans,
  acknowledgeTreatmentPlan,
  fetchAllPrescriptions,
  type DoctorTreatmentPlanResponse,
  type PrescriptionResponse,
} from "@/lib/platform-api";

export default function TreatmentPlansPage() {
  const [plans, setPlans] = useState<DoctorTreatmentPlanResponse[]>([]);
  const [prescriptions, setPrescriptions] = useState<PrescriptionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acknowledging, setAcknowledging] = useState<string | null>(null);
  const [expandedPlan, setExpandedPlan] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchDoctorTreatmentPlans(undefined, undefined, 1, 50).catch(() => []),
      fetchAllPrescriptions("active").catch(() => []),
    ])
      .then(([tp, rx]) => {
        setPlans((tp as DoctorTreatmentPlanResponse[]) ?? []);
        setPrescriptions((rx as PrescriptionResponse[]) ?? []);
        // Auto-expand the first plan
        if (Array.isArray(tp) && tp.length > 0) setExpandedPlan(tp[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleAcknowledge = async (planId: string) => {
    setAcknowledging(planId);
    try {
      await acknowledgeTreatmentPlan(planId);
      setPlans((prev) =>
        prev.map((p) => (p.id === planId ? { ...p, status: "acknowledged" as string } : p))
      );
    } catch {
      /* silent */
    }
    setAcknowledging(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-healthos-200 border-t-healthos-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">Unable to load treatment plans. Please try again later.</p>
      </div>
    );
  }

  const activePlans = plans.filter((p) => p.is_visible_to_patient);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">My Treatment Plans</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Physician-approved treatment plans from your clinical assessments.
          Review each plan carefully and acknowledge when you have read it.
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p className="text-2xl font-bold text-healthos-600">{activePlans.length}</p>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Active Plans</p>
        </div>
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p className="text-2xl font-bold text-violet-600">{prescriptions.length}</p>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Prescriptions</p>
        </div>
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p className="text-2xl font-bold text-amber-600">
            {activePlans.reduce((n, p) => n + (p.procedures?.length ?? 0), 0)}
          </p>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Procedures</p>
        </div>
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p className="text-2xl font-bold text-emerald-600">
            {activePlans.reduce((n, p) => n + (p.medications?.length ?? 0), 0)}
          </p>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Medications</p>
        </div>
      </div>

      {/* Treatment Plans */}
      {activePlans.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75" />
          </svg>
          <p className="mt-3 text-sm font-medium text-gray-500 dark:text-gray-400">
            No treatment plans available
          </p>
          <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
            When your physician approves an assessment, your treatment plan will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {activePlans.map((tp) => {
            const isExpanded = expandedPlan === tp.id;
            return (
              <div key={tp.id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
                {/* Plan Header — click to expand */}
                <button
                  onClick={() => setExpandedPlan(isExpanded ? null : tp.id)}
                  className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <div className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${
                    tp.status === "active" ? "bg-emerald-100 dark:bg-emerald-900/30" : "bg-blue-100 dark:bg-blue-900/30"
                  }`}>
                    <svg className={`h-5 w-5 ${tp.status === "active" ? "text-emerald-600" : "text-blue-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{tp.plan_title}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Created {new Date(tp.created_at).toLocaleDateString()} &middot;{" "}
                      {tp.medications?.length ?? 0} medications &middot;{" "}
                      {tp.procedures?.length ?? 0} procedures
                    </p>
                  </div>
                  <span className={`shrink-0 text-[10px] font-bold uppercase px-2.5 py-1 rounded-full ${
                    tp.status === "active" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  }`}>{tp.status}</span>
                  <svg className={`h-5 w-5 text-gray-400 shrink-0 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </button>

                {/* Expanded Plan Details */}
                {isExpanded && (
                  <div className="px-6 pb-6 space-y-5 border-t border-gray-100 dark:border-gray-800">
                    {/* Goals */}
                    {tp.treatment_goals && (
                      <div className="pt-4">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">Treatment Goals</h3>
                        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{tp.treatment_goals}</p>
                      </div>
                    )}

                    {/* Medications */}
                    {tp.medications && tp.medications.length > 0 && (
                      <div>
                        <h3 className="text-xs font-bold uppercase tracking-wider text-violet-600 mb-2">
                          Medications ({tp.medications.length})
                        </h3>
                        <div className="grid gap-2 sm:grid-cols-2">
                          {tp.medications.map((med, i) => {
                            const m = med as Record<string, string>;
                            return (
                              <div key={i} className="rounded-lg border border-violet-100 dark:border-violet-900 bg-violet-50 dark:bg-violet-950/20 p-3">
                                <div className="flex items-center gap-2">
                                  <svg className="h-4 w-4 text-violet-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0" />
                                  </svg>
                                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                                    {m.name || m.description || `Medication ${i + 1}`}
                                  </p>
                                </div>
                                {(m.dosage || m.frequency) && (
                                  <p className="text-xs text-gray-500 mt-1 ml-6">
                                    {[m.dosage, m.frequency].filter(Boolean).join(" — ")}
                                  </p>
                                )}
                                {m.instructions && (
                                  <p className="text-xs text-gray-500 mt-0.5 ml-6 italic">{m.instructions}</p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Procedures */}
                    {tp.procedures && tp.procedures.length > 0 && (
                      <div>
                        <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-600 mb-2">
                          Procedures & Orders ({tp.procedures.length})
                        </h3>
                        <div className="space-y-2">
                          {tp.procedures.map((proc, i) => {
                            const p = proc as Record<string, string>;
                            return (
                              <div key={i} className="rounded-lg border border-cyan-100 dark:border-cyan-900 bg-cyan-50 dark:bg-cyan-950/20 p-3 flex items-center gap-3">
                                <svg className="h-4 w-4 text-cyan-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                                </svg>
                                <div className="flex-1">
                                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{p.description || `Procedure ${i + 1}`}</p>
                                  {p.cpt_code && <p className="text-xs text-gray-500 mt-0.5">CPT: {p.cpt_code}</p>}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Lifestyle */}
                    {tp.lifestyle_modifications && tp.lifestyle_modifications.length > 0 && (
                      <div>
                        <h3 className="text-xs font-bold uppercase tracking-wider text-green-600 mb-2">Lifestyle Changes</h3>
                        <ul className="space-y-1.5">
                          {tp.lifestyle_modifications.map((item, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                              <svg className="h-4 w-4 text-green-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                              </svg>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Diet & Exercise */}
                    {(tp.dietary_recommendations || tp.exercise_recommendations) && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {tp.dietary_recommendations && (
                          <div className="rounded-lg border border-orange-100 dark:border-orange-900 bg-orange-50 dark:bg-orange-950/20 p-3">
                            <h3 className="text-xs font-bold uppercase tracking-wider text-orange-600 mb-1">Diet</h3>
                            <p className="text-sm text-gray-700 dark:text-gray-300">{tp.dietary_recommendations}</p>
                          </div>
                        )}
                        {tp.exercise_recommendations && (
                          <div className="rounded-lg border border-teal-100 dark:border-teal-900 bg-teal-50 dark:bg-teal-950/20 p-3">
                            <h3 className="text-xs font-bold uppercase tracking-wider text-teal-600 mb-1">Exercise</h3>
                            <p className="text-sm text-gray-700 dark:text-gray-300">{tp.exercise_recommendations}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Follow-up */}
                    {tp.follow_up_instructions && (
                      <div className="rounded-lg border border-amber-100 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/20 p-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-amber-600 mb-1">Follow-Up Instructions</h3>
                        <p className="text-sm text-gray-700 dark:text-gray-300">{tp.follow_up_instructions}</p>
                      </div>
                    )}

                    {/* Warning Signs */}
                    {tp.warning_signs && tp.warning_signs.length > 0 && (
                      <div className="rounded-lg border-2 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/20 p-4">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-red-600 mb-2">
                          Warning Signs — Contact Your Doctor Immediately If:
                        </h3>
                        <ul className="space-y-1">
                          {tp.warning_signs.map((sign, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-300">
                              <svg className="h-4 w-4 text-red-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                              </svg>
                              {sign}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Emergency Instructions */}
                    {tp.emergency_instructions && (
                      <div className="rounded-lg border-2 border-red-300 dark:border-red-800 bg-red-100 dark:bg-red-950/30 p-4">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-red-700 mb-1">Emergency Instructions</h3>
                        <p className="text-sm font-medium text-red-800 dark:text-red-200">{tp.emergency_instructions}</p>
                      </div>
                    )}

                    {/* Acknowledge Button */}
                    <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-800">
                      <p className="text-[10px] text-gray-400">
                        Created: {new Date(tp.created_at).toLocaleDateString()} &middot; Updated: {new Date(tp.updated_at).toLocaleDateString()}
                      </p>
                      <button
                        onClick={() => handleAcknowledge(tp.id)}
                        disabled={acknowledging === tp.id || tp.status === "acknowledged"}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          tp.status === "acknowledged"
                            ? "bg-gray-100 text-gray-500 cursor-default"
                            : "bg-healthos-600 text-white hover:bg-healthos-700 disabled:opacity-50"
                        }`}
                      >
                        {tp.status === "acknowledged"
                          ? "Acknowledged"
                          : acknowledging === tp.id
                          ? "Acknowledging..."
                          : "I Have Read This Plan"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Prescriptions Table */}
      {prescriptions.length > 0 && (
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="h-5 w-5 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5" />
            </svg>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">My Prescriptions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 text-left">
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Medication</th>
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Dosage</th>
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Frequency</th>
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Refills</th>
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {prescriptions.map((rx) => (
                  <tr key={rx.id}>
                    <td className="py-3 font-medium text-gray-900 dark:text-gray-100">{rx.medication_name}</td>
                    <td className="py-3 text-gray-600 dark:text-gray-400">{rx.dosage}</td>
                    <td className="py-3 text-gray-600 dark:text-gray-400">{rx.frequency}</td>
                    <td className="py-3 text-gray-600 dark:text-gray-400">{rx.refills ?? "—"}</td>
                    <td className="py-3">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${
                        rx.status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-600"
                      }`}>{rx.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
