"use client";

import { useState } from "react";

const ENCOUNTERS = [
  { id: "ENC-4821", patient: "Sarah Johnson", provider: "Dr. Williams", date: "2026-03-12", duration: "22 min", status: "attested", soapStatus: "signed", codes: 5, em: "99214" },
  { id: "ENC-4820", patient: "Michael Chen", provider: "Dr. Williams", date: "2026-03-12", duration: "15 min", status: "pending_review", soapStatus: "draft", codes: 4, em: "99213" },
  { id: "ENC-4819", patient: "Emma Davis", provider: "Dr. Patel", date: "2026-03-12", duration: "35 min", status: "in_review", soapStatus: "draft", codes: 7, em: "99215" },
  { id: "ENC-4818", patient: "Robert Wilson", provider: "Dr. Patel", date: "2026-03-11", duration: "18 min", status: "attested", soapStatus: "signed", codes: 4, em: "99213" },
  { id: "ENC-4817", patient: "Lisa Thompson", provider: "Dr. Williams", date: "2026-03-11", duration: "28 min", status: "attested", soapStatus: "signed", codes: 6, em: "99214" },
  { id: "ENC-4816", patient: "James Brown", provider: "Dr. Kim", date: "2026-03-11", duration: "12 min", status: "amended", soapStatus: "amended", codes: 3, em: "99212" },
];

const DEMO_SOAP = {
  subjective: {
    chief_complaint: "Chest tightness for 2 weeks",
    hpi: "Patient reports chest tightness, especially in the mornings, onset coinciding with medication change from lisinopril to amlodipine approximately 3 weeks ago. Also reports bilateral ankle swelling.",
    ros: "CV: Chest tightness, ankle edema. Resp: No SOB. General: No fever, no weight loss.",
  },
  objective: {
    vitals: "BP 142/88 mmHg, HR 78 bpm, RR 16/min, Temp 98.6°F, SpO2 98%",
    exam: "Bilateral pedal edema 1+. Heart sounds regular, no murmurs. Lungs clear to auscultation bilaterally.",
  },
  assessment: [
    { dx: "Peripheral edema", icd10: "R60.0", status: "new" },
    { dx: "Hypertension, uncontrolled", icd10: "I10", status: "existing" },
    { dx: "Adverse effect of CCB", icd10: "T46.1X5A", status: "new" },
  ],
  plan: [
    "Discontinue amlodipine 5mg, switch to losartan 50mg daily",
    "Order BMP and renal function panel",
    "Follow-up in 2 weeks to reassess BP and edema",
    "Patient education on signs of worsening edema",
  ],
};

const CODING_STATS = {
  totalEncounters: 1248,
  autoCodedPct: 94.2,
  avgCodingTime: "< 2 sec",
  providerEditRate: 12.8,
  codingAccuracy: 96.5,
  avgCodesPerEncounter: 4.8,
};

const ATTESTATION_QUEUE = [
  { id: "ATT-001", encounter: "ENC-4820", provider: "Dr. Williams", submitted: "10 min ago", items: 4, flags: 1 },
  { id: "ATT-002", encounter: "ENC-4819", provider: "Dr. Patel", submitted: "25 min ago", items: 7, flags: 2 },
  { id: "ATT-003", encounter: "ENC-4815", provider: "Dr. Kim", submitted: "1 hr ago", items: 3, flags: 0 },
];

const statusBadge = (s: string) => {
  const map: Record<string, string> = {
    attested: "bg-green-100 text-green-700",
    pending_review: "bg-yellow-100 text-yellow-700",
    in_review: "bg-blue-100 text-blue-700",
    amended: "bg-purple-100 text-purple-700",
    signed: "bg-green-100 text-green-700",
    draft: "bg-gray-100 text-gray-600",
  };
  return map[s] || "bg-gray-100 text-gray-600";
};

export default function AmbientAIPage() {
  const [tab, setTab] = useState<"encounters" | "soap" | "attestation">("encounters");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ambient AI Documentation</h1>
          <p className="text-sm text-gray-500">Automatic clinical documentation from patient-provider conversations</p>
        </div>
        <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
          Start Recording
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          { label: "Encounters Today", value: "24" },
          { label: "Auto-Coded", value: `${CODING_STATS.autoCodedPct}%` },
          { label: "Avg Coding Time", value: CODING_STATS.avgCodingTime },
          { label: "Provider Edit Rate", value: `${CODING_STATS.providerEditRate}%` },
          { label: "Coding Accuracy", value: `${CODING_STATS.codingAccuracy}%` },
          { label: "Avg Codes/Encounter", value: `${CODING_STATS.avgCodesPerEncounter}` },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {(["encounters", "soap", "attestation"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`border-b-2 pb-3 text-sm font-medium capitalize ${tab === t ? "border-healthos-600 text-healthos-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {t === "soap" ? "SOAP Preview" : t === "attestation" ? "Attestation Queue" : "Encounters"}
            </button>
          ))}
        </nav>
      </div>

      {/* Encounters Tab */}
      {tab === "encounters" && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["Encounter", "Patient", "Provider", "Date", "Duration", "E&M", "Codes", "SOAP", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {ENCOUNTERS.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-healthos-600">{e.id}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{e.patient}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{e.provider}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{e.date}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{e.duration}</td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-700">{e.em}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{e.codes}</td>
                  <td className="px-4 py-3"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge(e.soapStatus)}`}>{e.soapStatus}</span></td>
                  <td className="px-4 py-3"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge(e.status)}`}>{e.status.replace("_", " ")}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* SOAP Preview Tab */}
      {tab === "soap" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="text-sm font-semibold text-blue-700 uppercase">Subjective</h3>
              <div className="mt-3 space-y-2 text-sm text-gray-700">
                <p><span className="font-medium">CC:</span> {DEMO_SOAP.subjective.chief_complaint}</p>
                <p><span className="font-medium">HPI:</span> {DEMO_SOAP.subjective.hpi}</p>
                <p><span className="font-medium">ROS:</span> {DEMO_SOAP.subjective.ros}</p>
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="text-sm font-semibold text-green-700 uppercase">Objective</h3>
              <div className="mt-3 space-y-2 text-sm text-gray-700">
                <p><span className="font-medium">Vitals:</span> {DEMO_SOAP.objective.vitals}</p>
                <p><span className="font-medium">Exam:</span> {DEMO_SOAP.objective.exam}</p>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="text-sm font-semibold text-orange-700 uppercase">Assessment</h3>
              <div className="mt-3 space-y-1">
                {DEMO_SOAP.assessment.map((a, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700">{i + 1}. {a.dx}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-gray-500">{a.icd10}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs ${a.status === "new" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>{a.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="text-sm font-semibold text-purple-700 uppercase">Plan</h3>
              <ul className="mt-3 space-y-1 text-sm text-gray-700">
                {DEMO_SOAP.plan.map((p, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-purple-400" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
              <p className="text-xs font-medium text-blue-700">AI Suggested Coding</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="rounded bg-white px-2 py-1 text-xs font-mono shadow-sm">99214 (E&M)</span>
                <span className="rounded bg-white px-2 py-1 text-xs font-mono shadow-sm">R60.0</span>
                <span className="rounded bg-white px-2 py-1 text-xs font-mono shadow-sm">I10</span>
                <span className="rounded bg-white px-2 py-1 text-xs font-mono shadow-sm">T46.1X5A</span>
                <span className="rounded bg-white px-2 py-1 text-xs font-mono shadow-sm">80048 (BMP)</span>
                <span className="rounded bg-white px-2 py-1 text-xs font-mono shadow-sm">80069 (Renal)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Attestation Queue Tab */}
      {tab === "attestation" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
            <p className="text-sm font-medium text-yellow-800">{ATTESTATION_QUEUE.length} notes awaiting provider attestation</p>
            <p className="text-xs text-yellow-600 mt-1">AI-generated notes require provider review and digital signature before filing</p>
          </div>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Attestation ID", "Encounter", "Provider", "Submitted", "Items", "Flags", "Actions"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {ATTESTATION_QUEUE.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{a.id}</td>
                    <td className="px-4 py-3 text-sm text-healthos-600">{a.encounter}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{a.provider}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{a.submitted}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{a.items}</td>
                    <td className="px-4 py-3">
                      {a.flags > 0 ? (
                        <span className="inline-flex rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">{a.flags} flag{a.flags > 1 ? "s" : ""}</span>
                      ) : (
                        <span className="text-xs text-gray-400">None</span>
                      )}
                    </td>
                    <td className="px-4 py-3 flex gap-2">
                      <button className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700">Approve</button>
                      <button className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50">Review</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
