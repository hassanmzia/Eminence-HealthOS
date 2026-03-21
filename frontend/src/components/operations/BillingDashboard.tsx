"use client";

import { useState, useEffect } from "react";
import {
  fetchInvoices,
  fetchPayments,
  type BillingResponse,
  type PaymentResponse,
} from "@/lib/platform-api";

interface BillingMetrics {
  total_encounters: number;
  billed: number;
  unbilled: number;
  billing_rate: number;
  coding_issues: number;
  documentation_gaps: number;
  estimated_revenue_at_risk: number;
  top_issues: { issue: string; count: number; impact: string }[];
}

interface Claim {
  claim_id: string;
  patient_name: string;
  payer: string;
  total_charges: number;
  status: string;
  date_of_service: string;
  cpt_codes: string[];
}

const CLAIM_STATUS_COLORS: Record<string, string> = {
  prepared: "bg-gray-100 text-gray-800",
  submitted: "bg-blue-100 text-blue-800",
  accepted: "bg-indigo-100 text-indigo-800",
  paid: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  denied: "bg-red-100 text-red-800",
};

const DEMO_METRICS: BillingMetrics = {
  total_encounters: 142,
  billed: 128,
  unbilled: 14,
  billing_rate: 90.1,
  coding_issues: 8,
  documentation_gaps: 5,
  estimated_revenue_at_risk: 12500,
  top_issues: [
    { issue: "Missing modifier on telehealth claims", count: 4, impact: "$3,200" },
    { issue: "E/M level documentation insufficient", count: 3, impact: "$4,500" },
    { issue: "Missing prior auth reference", count: 3, impact: "$8,400" },
  ],
};

const DEMO_CLAIMS: Claim[] = [
  { claim_id: "CLM-001", patient_name: "J. Smith", payer: "Aetna", total_charges: 450, status: "submitted", date_of_service: "2026-03-10", cpt_codes: ["99214", "93000"] },
  { claim_id: "CLM-002", patient_name: "M. Johnson", payer: "UnitedHealth", total_charges: 2800, status: "paid", date_of_service: "2026-03-08", cpt_codes: ["70553"] },
  { claim_id: "CLM-003", patient_name: "K. Wilson", payer: "Cigna", total_charges: 320, status: "prepared", date_of_service: "2026-03-11", cpt_codes: ["99213"] },
  { claim_id: "CLM-004", patient_name: "S. Brown", payer: "Medicare", total_charges: 1200, status: "rejected", date_of_service: "2026-03-07", cpt_codes: ["99215", "94010"] },
  { claim_id: "CLM-005", patient_name: "A. Davis", payer: "Aetna", total_charges: 550, status: "accepted", date_of_service: "2026-03-09", cpt_codes: ["99214"] },
];

export function BillingDashboard() {
  const [metrics, setMetrics] = useState<BillingMetrics | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [invoices, payments] = await Promise.all([
          fetchInvoices({ page: 1, page_size: 50 }),
          fetchPayments(),
        ]);
        if (cancelled) return;

        const totalPaid = payments.reduce((s, p) => s + p.amount, 0);
        const totalCharged = invoices.reduce((s, i) => s + i.total_amount, 0);
        const totalDue = invoices.reduce((s, i) => s + i.amount_due, 0);
        const billed = invoices.filter((i) => i.status !== "draft").length;
        const unbilled = invoices.length - billed;

        setMetrics({
          total_encounters: invoices.length,
          billed,
          unbilled,
          billing_rate: invoices.length > 0 ? Math.round((billed / invoices.length) * 1000) / 10 : 0,
          coding_issues: 0,
          documentation_gaps: 0,
          estimated_revenue_at_risk: totalDue,
          top_issues: [],
        });

        setClaims(
          invoices.slice(0, 10).map((inv) => ({
            claim_id: inv.invoice_number,
            patient_name: inv.patient_id.slice(0, 8),
            payer: "Insurance",
            total_charges: inv.total_amount,
            status: inv.status,
            date_of_service: inv.billing_date,
            cpt_codes: [],
          })),
        );
      } catch {
        // API unavailable — use demo data
        setMetrics(DEMO_METRICS);
        setClaims(DEMO_CLAIMS);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!metrics) return null;

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Billing & Claims</h2>
        <div className="flex gap-2">
          <button className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50">
            Run Audit
          </button>
          <button className="rounded bg-healthos-600 px-3 py-1 text-xs font-medium text-white hover:bg-healthos-700">
            Prepare Claim
          </button>
        </div>
      </div>

      {/* Revenue metrics */}
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-blue-50 p-3">
          <div className="text-2xl font-bold text-blue-700">{metrics.billing_rate}%</div>
          <div className="text-xs text-blue-600">Billing Rate</div>
        </div>
        <div className="rounded-lg bg-yellow-50 p-3">
          <div className="text-2xl font-bold text-yellow-700">{metrics.unbilled}</div>
          <div className="text-xs text-yellow-600">Unbilled</div>
        </div>
        <div className="rounded-lg bg-orange-50 p-3">
          <div className="text-2xl font-bold text-orange-700">{metrics.coding_issues}</div>
          <div className="text-xs text-orange-600">Coding Issues</div>
        </div>
        <div className="rounded-lg bg-red-50 p-3">
          <div className="text-2xl font-bold text-red-700">${(metrics.estimated_revenue_at_risk / 1000).toFixed(1)}k</div>
          <div className="text-xs text-red-600">Revenue at Risk</div>
        </div>
      </div>

      {/* Top issues */}
      {metrics.top_issues.length > 0 && (
        <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
          <div className="mb-2 text-xs font-semibold text-yellow-800">Top Issues</div>
          <div className="space-y-1">
            {metrics.top_issues.map((issue, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-yellow-900">{issue.issue} ({issue.count})</span>
                <span className="font-medium text-yellow-700">{issue.impact}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Claims table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
              <th className="pb-2 font-medium">Claim</th>
              <th className="pb-2 font-medium">Patient</th>
              <th className="pb-2 font-medium">Payer</th>
              <th className="pb-2 font-medium">CPT</th>
              <th className="pb-2 font-medium">Charges</th>
              <th className="pb-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {claims.map((claim) => (
              <tr key={claim.claim_id} className="cursor-pointer transition-colors hover:bg-gray-50">
                <td className="py-2.5 text-xs text-gray-500">{claim.claim_id}</td>
                <td className="py-2.5 font-medium text-gray-900">{claim.patient_name}</td>
                <td className="py-2.5 text-gray-600">{claim.payer}</td>
                <td className="py-2.5 text-xs text-gray-500">{claim.cpt_codes.join(", ")}</td>
                <td className="py-2.5 text-gray-900">${claim.total_charges.toLocaleString()}</td>
                <td className="py-2.5">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CLAIM_STATUS_COLORS[claim.status] || "bg-gray-100"}`}>
                    {claim.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
