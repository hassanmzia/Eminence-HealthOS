"use client";

import { useState, useEffect } from "react";
import { fetchPrescriptionHistory, checkDrugInteractions, checkFormulary, trackMedicationAdherence, processRefill } from "@/lib/api";

const TABS = ["Prescriptions", "Interactions", "Formulary", "Refills", "Adherence"] as const;

const PRESCRIPTIONS = [
  { id: "RX-2026-0412", patient: "Maria Garcia", medication: "Metformin 1000mg", sig: "1 tab PO BID", prescriber: "Dr. Patel", status: "Transmitted", pharmacy: "CVS #4521", date: "2026-03-12" },
  { id: "RX-2026-0411", patient: "James Wilson", medication: "Lisinopril 20mg", sig: "1 tab PO daily", prescriber: "Dr. Kim", status: "Pending Review", pharmacy: "—", date: "2026-03-12" },
  { id: "RX-2026-0410", patient: "Sarah Chen", medication: "Atorvastatin 40mg", sig: "1 tab PO QHS", prescriber: "Dr. Williams", status: "Transmitted", pharmacy: "Walgreens #112", date: "2026-03-11" },
  { id: "RX-2026-0409", patient: "Robert Johnson", medication: "Warfarin 5mg", sig: "1 tab PO daily", prescriber: "Dr. Patel", status: "Requires Auth", pharmacy: "CVS #4521", date: "2026-03-11" },
  { id: "RX-2026-0408", patient: "Emily Davis", medication: "Levothyroxine 75mcg", sig: "1 tab PO AM", prescriber: "Dr. Kim", status: "Filled", pharmacy: "Walgreens #112", date: "2026-03-10" },
];

const INTERACTION_ALERTS = [
  { patient: "Robert Johnson", drugs: "Warfarin + Aspirin", severity: "Major", action: "Monitor INR closely — increased bleeding risk", status: "Acknowledged" },
  { patient: "Maria Garcia", drugs: "Metformin + Contrast Dye", severity: "Major", action: "Hold metformin 48h before/after contrast", status: "Pending" },
  { patient: "James Wilson", drugs: "Lisinopril + Potassium", severity: "Moderate", action: "Monitor potassium levels", status: "Acknowledged" },
  { patient: "Sarah Chen", drugs: "Atorvastatin + Grapefruit", severity: "Minor", action: "Counsel patient to avoid grapefruit", status: "Pending" },
];

const REFILL_QUEUE = [
  { patient: "Maria Garcia", medication: "Metformin 1000mg", refills_remaining: 3, last_fill: "2026-02-10", days_supply: 30, due_date: "2026-03-12", status: "Due Now" },
  { patient: "Emily Davis", medication: "Levothyroxine 75mcg", refills_remaining: 5, last_fill: "2026-02-15", days_supply: 30, due_date: "2026-03-17", status: "Due Soon" },
  { patient: "Robert Johnson", medication: "Warfarin 5mg", refills_remaining: 1, last_fill: "2026-02-20", days_supply: 30, due_date: "2026-03-22", status: "Low Refills" },
  { patient: "Sarah Chen", medication: "Atorvastatin 40mg", refills_remaining: 4, last_fill: "2026-03-01", days_supply: 90, due_date: "2026-05-30", status: "OK" },
];

const ADHERENCE_DATA = [
  { patient: "Maria Garcia", medication: "Metformin", pdc: 92, mpr: 0.94, status: "Adherent", trend: "Stable" },
  { patient: "James Wilson", medication: "Lisinopril", pdc: 78, mpr: 0.80, status: "At Risk", trend: "Declining" },
  { patient: "Robert Johnson", medication: "Warfarin", pdc: 85, mpr: 0.87, status: "Adherent", trend: "Stable" },
  { patient: "Emily Davis", medication: "Levothyroxine", pdc: 65, mpr: 0.68, status: "Non-Adherent", trend: "Declining" },
  { patient: "Sarah Chen", medication: "Atorvastatin", pdc: 95, mpr: 0.96, status: "Adherent", trend: "Improving" },
];

function statusColor(status: string) {
  const map: Record<string, string> = {
    Transmitted: "bg-green-100 text-green-800",
    Filled: "bg-green-100 text-green-800",
    "Pending Review": "bg-yellow-100 text-yellow-800",
    "Requires Auth": "bg-red-100 text-red-800",
    Acknowledged: "bg-blue-100 text-blue-800",
    Pending: "bg-yellow-100 text-yellow-800",
    "Due Now": "bg-red-100 text-red-800",
    "Due Soon": "bg-yellow-100 text-yellow-800",
    "Low Refills": "bg-orange-100 text-orange-800",
    OK: "bg-green-100 text-green-800",
    Adherent: "bg-green-100 text-green-800",
    "At Risk": "bg-yellow-100 text-yellow-800",
    "Non-Adherent": "bg-red-100 text-red-800",
  };
  return map[status] ?? "bg-gray-100 text-gray-800";
}

function severityColor(sev: string) {
  const map: Record<string, string> = { Major: "bg-red-100 text-red-800", Moderate: "bg-yellow-100 text-yellow-800", Minor: "bg-blue-100 text-blue-800" };
  return map[sev] ?? "bg-gray-100 text-gray-800";
}

export default function PharmacyPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const [apiPrescriptions, setApiPrescriptions] = useState<typeof PRESCRIPTIONS | null>(null);
  const [apiAdherence, setApiAdherence] = useState<typeof ADHERENCE_DATA | null>(null);

  useEffect(() => {
    fetchPrescriptionHistory("demo")
      .then((data) => { if (Array.isArray(data)) setApiPrescriptions(data as typeof PRESCRIPTIONS); })
      .catch(() => {/* use demo data */});
    trackMedicationAdherence({ patient_id: "demo" })
      .then((data) => { if (Array.isArray(data)) setApiAdherence(data as typeof ADHERENCE_DATA); })
      .catch(() => {/* use demo data */});
  }, []);

  const prescriptions = apiPrescriptions ?? PRESCRIPTIONS;
  const adherenceData = apiAdherence ?? ADHERENCE_DATA;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pharmacy</h1>
        <p className="text-sm text-gray-500">e-Prescribing, drug interactions, formulary management, refills, and adherence tracking</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Active Prescriptions", value: "1,247", sub: "+23 today" },
          { label: "Interaction Alerts", value: "4", sub: "2 pending review" },
          { label: "Refills Due", value: "38", sub: "12 due today" },
          { label: "Avg Adherence (PDC)", value: "83%", sub: "Target: 80%" },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs font-medium text-gray-500">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{kpi.value}</p>
            <p className="text-xs text-gray-400">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                tab === t ? "border-healthos-600 text-healthos-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {tab === "Prescriptions" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Rx ID", "Patient", "Medication", "Sig", "Prescriber", "Pharmacy", "Status", "Date"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {PRESCRIPTIONS.map((rx) => (
                <tr key={rx.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{rx.id}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{rx.patient}</td>
                  <td className="px-4 py-3">{rx.medication}</td>
                  <td className="px-4 py-3 text-gray-500">{rx.sig}</td>
                  <td className="px-4 py-3">{rx.prescriber}</td>
                  <td className="px-4 py-3 text-gray-500">{rx.pharmacy}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(rx.status)}`}>{rx.status}</span></td>
                  <td className="px-4 py-3 text-gray-500">{rx.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Interactions" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Patient", "Drug Pair", "Severity", "Recommended Action", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {INTERACTION_ALERTS.map((ia, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{ia.patient}</td>
                  <td className="px-4 py-3">{ia.drugs}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${severityColor(ia.severity)}`}>{ia.severity}</span></td>
                  <td className="px-4 py-3 text-gray-500">{ia.action}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(ia.status)}`}>{ia.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Formulary" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h3 className="text-sm font-semibold text-gray-900">Formulary Tier Summary</h3>
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              {[
                { tier: "Tier 1", label: "Generic", copay: "$5", count: 842 },
                { tier: "Tier 2", label: "Preferred Brand", copay: "$25", count: 456 },
                { tier: "Tier 3", label: "Non-Preferred", copay: "$50", count: 234 },
                { tier: "Tier 4", label: "Specialty", copay: "20%", count: 89 },
                { tier: "Tier 5", label: "Not Covered", copay: "100%", count: 67 },
              ].map((t) => (
                <div key={t.tier} className="rounded-lg border border-gray-100 p-3 text-center">
                  <p className="text-xs font-medium text-gray-500">{t.tier}</p>
                  <p className="text-sm font-semibold text-gray-900">{t.label}</p>
                  <p className="text-lg font-bold text-healthos-600">{t.copay}</p>
                  <p className="text-xs text-gray-400">{t.count} drugs</p>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h3 className="text-sm font-semibold text-gray-900">Recent Formulary Checks</h3>
            <div className="mt-3 space-y-2 text-sm">
              {[
                { drug: "Jardiance 25mg", tier: "Tier 3", pa: "Step therapy required", alt: "Metformin (Tier 1)" },
                { drug: "Eliquis 5mg", tier: "Tier 3", pa: "Prior auth required", alt: "Warfarin (Tier 1)" },
                { drug: "Atorvastatin 40mg", tier: "Tier 1", pa: "None", alt: "—" },
              ].map((f, i) => (
                <div key={i} className="flex items-center justify-between rounded border border-gray-100 p-3">
                  <div>
                    <p className="font-medium text-gray-900">{f.drug}</p>
                    <p className="text-xs text-gray-500">PA: {f.pa} | Alt: {f.alt}</p>
                  </div>
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">{f.tier}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "Refills" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Patient", "Medication", "Refills Left", "Last Fill", "Days Supply", "Due Date", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {REFILL_QUEUE.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.patient}</td>
                  <td className="px-4 py-3">{r.medication}</td>
                  <td className="px-4 py-3">{r.refills_remaining}</td>
                  <td className="px-4 py-3 text-gray-500">{r.last_fill}</td>
                  <td className="px-4 py-3">{r.days_supply}d</td>
                  <td className="px-4 py-3 text-gray-500">{r.due_date}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(r.status)}`}>{r.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Adherence" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Patient", "Medication", "PDC %", "MPR", "Status", "Trend"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {ADHERENCE_DATA.map((a, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.patient}</td>
                  <td className="px-4 py-3">{a.medication}</td>
                  <td className="px-4 py-3 font-mono">{a.pdc}%</td>
                  <td className="px-4 py-3 font-mono">{a.mpr}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(a.status)}`}>{a.status}</span></td>
                  <td className="px-4 py-3 text-gray-500">{a.trend}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
