"use client";

import { useEffect, useState } from "react";
import {
  fetchPatientProfile,
  fetchPatientVitals,
  fetchPatientCarePlans,
  type PatientHealthSummary,
  type PatientVitalsResponse,
  type CarePlan,
} from "@/lib/patient-api";
import {
  fetchDoctorTreatmentPlans,
  fetchAllPrescriptions,
  type DoctorTreatmentPlanResponse,
  type PrescriptionResponse,
} from "@/lib/platform-api";

export default function MyHealthPage() {
  const [profile, setProfile] = useState<PatientHealthSummary | null>(null);
  const [vitals, setVitals] = useState<PatientVitalsResponse | null>(null);
  const [carePlans, setCarePlans] = useState<CarePlan[]>([]);
  const [treatmentPlans, setTreatmentPlans] = useState<DoctorTreatmentPlanResponse[]>([]);
  const [prescriptions, setPrescriptions] = useState<PrescriptionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchPatientProfile(),
      fetchPatientVitals(undefined, 30),
      fetchPatientCarePlans(),
      fetchDoctorTreatmentPlans(undefined, "active").catch(() => []),
      fetchAllPrescriptions("active").catch(() => []),
    ])
      .then(([p, v, c, tp, rx]) => {
        setProfile(p);
        setVitals(v);
        setCarePlans(c);
        let tpList = (tp as DoctorTreatmentPlanResponse[]) ?? [];
        // Fallback: read from localStorage if API returned empty
        if (tpList.length === 0) {
          try {
            const stored = JSON.parse(localStorage.getItem("healthos_treatment_plans") || "[]") as DoctorTreatmentPlanResponse[];
            if (stored.length > 0) tpList = stored;
          } catch { /* ignore */ }
        }
        setTreatmentPlans(tpList);
        setPrescriptions((rx as PrescriptionResponse[]) ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

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
        <p className="text-sm text-red-700">Unable to load your health data. Please try again later.</p>
      </div>
    );
  }

  // Derive latest vital per type
  const latestByType = new Map<string, (typeof vitals)extends { vitals: (infer V)[] } | null ? V : never>();
  for (const v of vitals?.vitals ?? []) {
    if (!latestByType.has(v.type)) {
      latestByType.set(v.type, v);
    }
  }

  const vitalTypes = ["heart_rate", "blood_pressure", "spo2", "glucose", "weight"];
  const vitalLabels: Record<string, string> = {
    heart_rate: "Heart Rate",
    blood_pressure: "Blood Pressure",
    spo2: "SpO2",
    glucose: "Glucose",
    weight: "Weight",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">My Health</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Your health summary, vitals, medications, and care plans.
        </p>
      </div>

      {/* Latest Vitals */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Latest Vitals
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {vitalTypes.map((type) => {
            const v = latestByType.get(type);
            return (
              <div
                key={type}
                className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4"
              >
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {vitalLabels[type] ?? type}
                </p>
                {v ? (
                  <>
                    <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
                      {typeof v.value === "object"
                        ? JSON.stringify(v.value)
                        : String(v.value)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{v.unit}</p>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {v.recorded_at
                        ? new Date(v.recorded_at).toLocaleDateString()
                        : ""}
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">No data</p>
                )}
              </div>
            );
          })}
        </div>
        {(vitals?.total ?? 0) > 5 && (
          <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
            Showing latest readings from the past {vitals?.period_days ?? 30} days.{" "}
            {vitals?.total} total readings on file.
          </p>
        )}
      </section>

      {/* Active Medications */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Active Medications
        </h2>
        {(profile?.medications?.length ?? 0) === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No active medications on record.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {profile?.medications?.map((med, i) => (
              <li key={i} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {(med as Record<string, string>).name ?? `Medication ${i + 1}`}
                  </p>
                  {(med as Record<string, string>).dosage && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {(med as Record<string, string>).dosage}
                    </p>
                  )}
                </div>
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                  Active
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Active Conditions */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Active Conditions
        </h2>
        {(profile?.conditions?.length ?? 0) === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No conditions on record.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {profile?.conditions?.map((cond, i) => (
              <li key={i} className="py-3">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {(cond as Record<string, string>).name ?? `Condition ${i + 1}`}
                </p>
                {(cond as Record<string, string>).onset && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Since {(cond as Record<string, string>).onset}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Care Plans */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Care Plan Summary
        </h2>
        {carePlans.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No active care plans.</p>
        ) : (
          <div className="space-y-4">
            {carePlans.map((plan) => (
              <div
                key={plan.id}
                className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 capitalize">
                    {plan.type} plan
                  </p>
                  <span className="rounded-full bg-healthos-100 px-2 py-0.5 text-xs font-medium text-healthos-700">
                    {plan.status}
                  </span>
                </div>
                {plan.goals.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Goals</p>
                    <ul className="mt-1 list-inside list-disc text-sm text-gray-700 dark:text-gray-300">
                      {plan.goals.map((g, i) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {plan.interventions.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      Interventions
                    </p>
                    <ul className="mt-1 list-inside list-disc text-sm text-gray-700 dark:text-gray-300">
                      {plan.interventions.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Physician-Approved Treatment Plans (from Clinical Assessment Workflow) ── */}
      {treatmentPlans.length > 0 && (
        <section className="rounded-xl border-2 border-healthos-200 dark:border-healthos-800 bg-white dark:bg-gray-900 p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-8 w-8 rounded-full bg-healthos-100 dark:bg-healthos-900 flex items-center justify-center">
              <svg className="h-4 w-4 text-healthos-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Your Treatment Plans
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Physician-approved plans from your clinical assessments</p>
            </div>
          </div>
          <div className="space-y-4">
            {treatmentPlans.map((tp) => (
              <div key={tp.id} className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{tp.plan_title}</p>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${
                    tp.status === "active" ? "bg-emerald-100 text-emerald-700" : tp.status === "completed" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"
                  }`}>{tp.status}</span>
                </div>
                {tp.treatment_goals && (
                  <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">{tp.treatment_goals}</p>
                )}
                {tp.medications && tp.medications.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-violet-600 mb-1">Medications</p>
                    <div className="space-y-1">
                      {tp.medications.map((med, i) => (
                        <div key={i} className="flex items-center gap-2 rounded-md bg-violet-50 dark:bg-violet-950/20 px-3 py-1.5 text-sm">
                          <svg className="h-3.5 w-3.5 text-violet-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5" />
                          </svg>
                          <span className="font-medium text-gray-800 dark:text-gray-200">
                            {(med as Record<string, string>).name || (med as Record<string, string>).description || `Medication ${i + 1}`}
                          </span>
                          {(med as Record<string, string>).dosage && (
                            <span className="text-xs text-gray-500">{(med as Record<string, string>).dosage}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {tp.procedures && tp.procedures.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-cyan-600 mb-1">Procedures & Orders</p>
                    <div className="space-y-1">
                      {tp.procedures.map((proc, i) => (
                        <div key={i} className="flex items-center gap-2 rounded-md bg-cyan-50 dark:bg-cyan-950/20 px-3 py-1.5 text-sm">
                          <span className="font-medium text-gray-800 dark:text-gray-200">
                            {(proc as Record<string, string>).description || `Procedure ${i + 1}`}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {tp.lifestyle_modifications && tp.lifestyle_modifications.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-green-600 mb-1">Lifestyle Changes</p>
                    <ul className="list-inside list-disc text-sm text-gray-700 dark:text-gray-300">
                      {tp.lifestyle_modifications.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {tp.follow_up_instructions && (
                  <div className="mb-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-amber-600 mb-1">Follow-Up</p>
                    <p className="text-sm text-gray-700 dark:text-gray-300">{tp.follow_up_instructions}</p>
                  </div>
                )}
                {tp.warning_signs && tp.warning_signs.length > 0 && (
                  <div className="rounded-md bg-red-50 dark:bg-red-950/20 border border-red-100 dark:border-red-900 p-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-red-600 mb-1">Warning Signs — Contact Your Doctor If:</p>
                    <ul className="list-inside list-disc text-sm text-red-700 dark:text-red-300">
                      {tp.warning_signs.map((sign, i) => (
                        <li key={i}>{sign}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="mt-3 text-[10px] text-gray-400">
                  Created: {new Date(tp.created_at).toLocaleDateString()} &middot; Last updated: {new Date(tp.updated_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Active Prescriptions (from Pharmacy Workflow) ── */}
      {prescriptions.length > 0 && (
        <section className="rounded-xl border-2 border-violet-200 dark:border-violet-800 bg-white dark:bg-gray-900 p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-8 w-8 rounded-full bg-violet-100 dark:bg-violet-900 flex items-center justify-center">
              <svg className="h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Prescriptions
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">E-prescriptions from your care team</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 text-left">
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Medication</th>
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Dosage</th>
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Frequency</th>
                  <th className="pb-2 font-medium text-gray-500 dark:text-gray-400">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {prescriptions.map((rx) => (
                  <tr key={rx.id}>
                    <td className="py-2.5 font-medium text-gray-900 dark:text-gray-100">{rx.medication_name}</td>
                    <td className="py-2.5 text-gray-600 dark:text-gray-400">{rx.dosage}</td>
                    <td className="py-2.5 text-gray-600 dark:text-gray-400">{rx.frequency}</td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-bold uppercase ${
                        rx.status === "active" ? "bg-emerald-100 text-emerald-700" : rx.status === "completed" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"
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
