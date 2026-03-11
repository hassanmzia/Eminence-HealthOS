"use client";

import { useState } from "react";

type Tab = "encounter" | "notes" | "plan";

interface EncounterNote {
  section: string;
  content: string;
}

const DEMO_SOAP: EncounterNote[] = [
  { section: "Subjective", content: "Patient reports worsening dyspnea over past 48 hours. Weight gain of 3 lbs noted. Increased lower extremity edema. Compliance with medications reported as good." },
  { section: "Objective", content: "HR 92 bpm, BP 148/92 mmHg, SpO2 91%, Weight 185 lbs (+3 lbs from baseline). AI Agent: Anomaly detected — SpO2 below threshold. Risk score: 0.78 (critical)." },
  { section: "Assessment", content: "CHF exacerbation with fluid overload. CKD stable. Pending provider assessment." },
  { section: "Plan", content: "1. Increase Furosemide to 60mg QD\n2. Restrict fluid intake to 1.5L/day\n3. Daily weight monitoring\n4. Follow-up in 3 days\n5. Patient education on fluid restriction" },
];

const DEMO_FOLLOW_UP = {
  follow_up_days: 3,
  monitoring: "Twice daily vitals (weight, BP, SpO2)",
  action_items: [
    "Increase Furosemide to 60mg QD",
    "Strict fluid restriction 1.5L/day",
    "Daily weight — report >2lb gain",
    "Follow-up telehealth in 3 days",
  ],
  patient_education: [
    "Continue monitoring for CHF",
    "Seek immediate care if symptoms worsen",
  ],
};

export function EncounterConsole() {
  const [activeTab, setActiveTab] = useState<Tab>("encounter");

  return (
    <div className="card">
      {/* Tab bar */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
        {(["encounter", "notes", "plan"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "notes" ? "Clinical Notes" : tab === "plan" ? "Follow-Up Plan" : "Encounter"}
          </button>
        ))}
      </div>

      {/* Encounter tab */}
      {activeTab === "encounter" && (
        <div className="space-y-4">
          {/* Video placeholder */}
          <div className="flex h-64 items-center justify-center rounded-lg bg-gray-900 text-gray-400">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
              </svg>
              <p className="mt-2 text-sm">Video encounter area</p>
              <p className="text-xs text-gray-500">Click "Start Visit" to begin</p>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-center gap-3">
            <button className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700">
              Start Visit
            </button>
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Mute
            </button>
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Camera
            </button>
            <button className="rounded-lg bg-red-600 px-6 py-2 text-sm font-medium text-white hover:bg-red-700">
              End Visit
            </button>
          </div>

          {/* AI Agent sidebar */}
          <div className="rounded-lg border border-healthos-100 bg-healthos-50 p-3">
            <div className="flex items-center gap-2 text-xs font-medium text-healthos-700">
              <span className="h-2 w-2 animate-pulse rounded-full bg-healthos-500" />
              AI Agent Insights
            </div>
            <div className="mt-2 space-y-1 text-xs text-gray-600">
              <p>&bull; SpO2 at 91% — below CHF monitoring threshold (92%)</p>
              <p>&bull; Weight +3lbs in 48h — fluid retention alert</p>
              <p>&bull; Risk score elevated to 0.78 (critical)</p>
              <p>&bull; Recommend: Evaluate diuretic adjustment</p>
            </div>
          </div>
        </div>
      )}

      {/* Clinical Notes tab */}
      {activeTab === "notes" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-700">SOAP Note (AI-Generated Draft)</h3>
            <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">Draft — Requires provider review</span>
          </div>
          {DEMO_SOAP.map((note) => (
            <div key={note.section}>
              <h4 className="text-xs font-medium uppercase text-gray-400">{note.section}</h4>
              <p className="mt-1 whitespace-pre-line text-sm text-gray-700">{note.content}</p>
            </div>
          ))}
          <div className="flex gap-2">
            <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
              Sign & Finalize
            </button>
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Edit Note
            </button>
          </div>
        </div>
      )}

      {/* Follow-Up Plan tab */}
      {activeTab === "plan" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-700">Follow-Up Care Plan</h3>
            <span className="text-xs text-gray-400">Follow-up in {DEMO_FOLLOW_UP.follow_up_days} days</span>
          </div>

          <div>
            <h4 className="text-xs font-medium uppercase text-gray-400">Monitoring</h4>
            <p className="mt-1 text-sm text-gray-700">{DEMO_FOLLOW_UP.monitoring}</p>
          </div>

          <div>
            <h4 className="text-xs font-medium uppercase text-gray-400">Action Items</h4>
            <ul className="mt-1 space-y-1">
              {DEMO_FOLLOW_UP.action_items.map((item) => (
                <li key={item} className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" className="h-3.5 w-3.5 rounded border-gray-300" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-medium uppercase text-gray-400">Patient Education</h4>
            <ul className="mt-1 space-y-0.5">
              {DEMO_FOLLOW_UP.patient_education.map((item) => (
                <li key={item} className="text-sm text-gray-600">&bull; {item}</li>
              ))}
            </ul>
          </div>

          <div className="flex gap-2">
            <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
              Finalize Plan
            </button>
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Send to Patient
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
