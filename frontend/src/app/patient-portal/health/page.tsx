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

export default function MyHealthPage() {
  const [profile, setProfile] = useState<PatientHealthSummary | null>(null);
  const [vitals, setVitals] = useState<PatientVitalsResponse | null>(null);
  const [carePlans, setCarePlans] = useState<CarePlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchPatientProfile(),
      fetchPatientVitals(undefined, 30),
      fetchPatientCarePlans(),
    ])
      .then(([p, v, c]) => {
        setProfile(p);
        setVitals(v);
        setCarePlans(c);
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
        <h1 className="text-2xl font-bold text-gray-900">My Health</h1>
        <p className="mt-1 text-sm text-gray-500">
          Your health summary, vitals, medications, and care plans.
        </p>
      </div>

      {/* Latest Vitals */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Latest Vitals
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {vitalTypes.map((type) => {
            const v = latestByType.get(type);
            return (
              <div
                key={type}
                className="rounded-lg border border-gray-100 bg-gray-50 p-4"
              >
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  {vitalLabels[type] ?? type}
                </p>
                {v ? (
                  <>
                    <p className="mt-1 text-xl font-bold text-gray-900">
                      {typeof v.value === "object"
                        ? JSON.stringify(v.value)
                        : String(v.value)}
                    </p>
                    <p className="text-xs text-gray-500">{v.unit}</p>
                    <p className="mt-1 text-xs text-gray-400">
                      {v.recorded_at
                        ? new Date(v.recorded_at).toLocaleDateString()
                        : ""}
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-gray-400">No data</p>
                )}
              </div>
            );
          })}
        </div>
        {(vitals?.total ?? 0) > 5 && (
          <p className="mt-4 text-xs text-gray-500">
            Showing latest readings from the past {vitals?.period_days ?? 30} days.{" "}
            {vitals?.total} total readings on file.
          </p>
        )}
      </section>

      {/* Active Medications */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Active Medications
        </h2>
        {(profile?.medications?.length ?? 0) === 0 ? (
          <p className="text-sm text-gray-500">No active medications on record.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {profile?.medications?.map((med, i) => (
              <li key={i} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {(med as Record<string, string>).name ?? `Medication ${i + 1}`}
                  </p>
                  {(med as Record<string, string>).dosage && (
                    <p className="text-xs text-gray-500">
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
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Active Conditions
        </h2>
        {(profile?.conditions?.length ?? 0) === 0 ? (
          <p className="text-sm text-gray-500">No conditions on record.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {profile?.conditions?.map((cond, i) => (
              <li key={i} className="py-3">
                <p className="text-sm font-medium text-gray-900">
                  {(cond as Record<string, string>).name ?? `Condition ${i + 1}`}
                </p>
                {(cond as Record<string, string>).onset && (
                  <p className="text-xs text-gray-500">
                    Since {(cond as Record<string, string>).onset}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Care Plans */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Care Plan Summary
        </h2>
        {carePlans.length === 0 ? (
          <p className="text-sm text-gray-500">No active care plans.</p>
        ) : (
          <div className="space-y-4">
            {carePlans.map((plan) => (
              <div
                key={plan.id}
                className="rounded-lg border border-gray-100 bg-gray-50 p-4"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-gray-900 capitalize">
                    {plan.type} plan
                  </p>
                  <span className="rounded-full bg-healthos-100 px-2 py-0.5 text-xs font-medium text-healthos-700">
                    {plan.status}
                  </span>
                </div>
                {plan.goals.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-500">Goals</p>
                    <ul className="mt-1 list-inside list-disc text-sm text-gray-700">
                      {plan.goals.map((g, i) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {plan.interventions.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-500">
                      Interventions
                    </p>
                    <ul className="mt-1 list-inside list-disc text-sm text-gray-700">
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
    </div>
  );
}
