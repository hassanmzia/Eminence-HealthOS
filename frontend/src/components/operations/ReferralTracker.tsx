"use client";

import { useState, useEffect } from "react";

interface Referral {
  referral_id: string;
  patient_name: string;
  specialty: string;
  urgency: string;
  status: string;
  target_date: string;
  specialist: string;
}

const STATUS_COLORS: Record<string, string> = {
  created: "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200",
  sent: "bg-blue-100 text-blue-800",
  scheduled: "bg-indigo-100 text-indigo-800",
  completed: "bg-green-100 text-green-800",
  closed: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
};

const URGENCY_DOT: Record<string, string> = {
  emergency: "bg-red-500",
  urgent: "bg-orange-500",
  soon: "bg-yellow-500",
  routine: "bg-green-500",
};

const DEMO_REFERRALS: Referral[] = [
  { referral_id: "REF-001", patient_name: "J. Smith", specialty: "Cardiology", urgency: "urgent", status: "sent", target_date: "2026-03-15", specialist: "Dr. Martinez" },
  { referral_id: "REF-002", patient_name: "M. Johnson", specialty: "Orthopedics", urgency: "routine", status: "scheduled", target_date: "2026-03-25", specialist: "Dr. Lee" },
  { referral_id: "REF-003", patient_name: "A. Davis", specialty: "Oncology", urgency: "urgent", status: "created", target_date: "2026-03-14", specialist: "Pending" },
  { referral_id: "REF-004", patient_name: "R. Garcia", specialty: "Neurology", urgency: "routine", status: "completed", target_date: "2026-03-10", specialist: "Dr. Patel" },
];

export function ReferralTracker() {
  const [referrals, setReferrals] = useState<Referral[]>([]);

  useEffect(() => {
    setReferrals(DEMO_REFERRALS);
  }, []);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Referral Tracker</h2>
        <button className="rounded bg-healthos-600 px-3 py-1 text-xs font-medium text-white hover:bg-healthos-700">
          New Referral
        </button>
      </div>

      <div className="overflow-x-auto">
        <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-xs text-gray-500 dark:text-gray-400">
              <th className="pb-2 font-medium">Patient</th>
              <th className="pb-2 font-medium">Specialty</th>
              <th className="pb-2 font-medium">Specialist</th>
              <th className="pb-2 font-medium">Target</th>
              <th className="pb-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {referrals.map((ref) => (
              <tr key={ref.referral_id} className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-800">
                <td className="py-2.5">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${URGENCY_DOT[ref.urgency] || "bg-gray-400"}`} />
                    <span className="font-medium text-gray-900 dark:text-gray-100">{ref.patient_name}</span>
                  </div>
                </td>
                <td className="py-2.5 text-gray-600 dark:text-gray-400">{ref.specialty}</td>
                <td className="py-2.5 text-gray-600 dark:text-gray-400">{ref.specialist}</td>
                <td className="py-2.5 text-gray-500 dark:text-gray-400">{ref.target_date}</td>
                <td className="py-2.5">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[ref.status]}`}>
                    {ref.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>
    </div>
  );
}
