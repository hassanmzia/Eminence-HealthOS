"use client";

import { useState, useCallback } from "react";
import { buildDigitalTwin, fetchTwinState, simulateScenario, predictTrajectory, recommendTreatment } from "@/lib/api";

const SAMPLE_TWINS = [
  {
    id: "DT-001",
    patient: "Maria Santos",
    age: 67,
    conditions: ["Type 2 Diabetes", "Hypertension", "CKD Stage 3"],
    healthScore: 0.62,
    lastUpdated: "2026-03-11T14:30:00Z",
    trajectory: "stable",
    vitals: { hr: 78, bp: "138/86", bmi: 29.4, hba1c: 7.2, egfr: 48 },
  },
  {
    id: "DT-002",
    patient: "James Chen",
    age: 54,
    conditions: ["CHF NYHA II", "Atrial Fibrillation"],
    healthScore: 0.55,
    lastUpdated: "2026-03-11T16:00:00Z",
    trajectory: "declining",
    vitals: { hr: 92, bp: "142/90", bmi: 31.2, hba1c: 5.8, egfr: 62 },
  },
  {
    id: "DT-003",
    patient: "Sarah Johnson",
    age: 45,
    conditions: ["Asthma", "Obesity"],
    healthScore: 0.74,
    lastUpdated: "2026-03-11T10:15:00Z",
    trajectory: "improving",
    vitals: { hr: 72, bp: "126/80", bmi: 32.1, hba1c: 5.4, egfr: 95 },
  },
  {
    id: "DT-004",
    patient: "Robert Williams",
    age: 71,
    conditions: ["COPD", "Type 2 Diabetes", "CAD"],
    healthScore: 0.48,
    lastUpdated: "2026-03-11T12:45:00Z",
    trajectory: "declining",
    vitals: { hr: 88, bp: "148/92", bmi: 27.8, hba1c: 8.1, egfr: 42 },
  },
];

const SCENARIOS = [
  { id: "SC-1", name: "Add Metformin 500mg", type: "medication", impact: "+8% health score", risk: "low" },
  { id: "SC-2", name: "Stop ACE Inhibitor", type: "medication", impact: "-15% health score", risk: "high" },
  { id: "SC-3", name: "Exercise Program (30min/day)", type: "lifestyle", impact: "+12% health score", risk: "none" },
  { id: "SC-4", name: "Dietary DASH Protocol", type: "lifestyle", impact: "+6% health score", risk: "none" },
];

const trajectoryColor = (t: string) =>
  t === "improving" ? "text-green-600 bg-green-50" : t === "stable" ? "text-gray-600 bg-gray-100" : "text-red-600 bg-red-50";

const scoreColor = (s: number) =>
  s >= 0.7 ? "text-green-600" : s >= 0.5 ? "text-yellow-600" : "text-red-600";

type Twin = typeof SAMPLE_TWINS[number];

export default function DigitalTwinPage() {
  const [twins, setTwins] = useState<Twin[]>(SAMPLE_TWINS);
  const [selectedTwin, setSelectedTwin] = useState<Twin>(SAMPLE_TWINS[0]);
  const [activeTab, setActiveTab] = useState<"overview" | "scenarios" | "trajectory">("overview");
  const [building, setBuilding] = useState(false);

  const handleSimulate = useCallback(async (scenarioId: string) => {
    try {
      await simulateScenario({ scenario_id: scenarioId, patient_id: selectedTwin.id });
    } catch {
      // API unavailable — demo mode
    }
  }, [selectedTwin.id]);

  const handleBuildTwin = useCallback(async () => {
    setBuilding(true);
    try {
      const result = await buildDigitalTwin({});
      const twinId = (result as Record<string, unknown>).twin_id as string || `DT-${String(twins.length + 1).padStart(3, "0")}`;
      const patientId = (result as Record<string, unknown>).patient_id as string || twinId;
      const healthScore = (result as Record<string, unknown>).overall_health_score as number ?? 0.75;
      const params = (result as Record<string, unknown>).physiological_parameters as Record<string, number> | undefined;
      const conditions = (result as Record<string, unknown>).active_conditions as string[] ?? [];

      const newTwin: Twin = {
        id: twinId,
        patient: `Patient ${patientId.slice(0, 8)}`,
        age: 0,
        conditions,
        healthScore,
        lastUpdated: new Date().toISOString(),
        trajectory: "stable",
        vitals: {
          hr: params?.heart_rate_baseline ?? 72,
          bp: `${Math.round(params?.bp_systolic ?? 120)}/${Math.round(params?.bp_diastolic ?? 80)}`,
          bmi: params?.bmi ?? 25.0,
          hba1c: params?.hba1c ?? 5.4,
          egfr: params?.egfr ?? 90,
        },
      };
      setTwins((prev) => [...prev, newTwin]);
      setSelectedTwin(newTwin);
    } catch {
      // API unavailable — add a demo twin as fallback
      const newTwin: Twin = {
        id: `DT-${String(twins.length + 1).padStart(3, "0")}`,
        patient: `New Patient`,
        age: 0,
        conditions: [],
        healthScore: 0.75,
        lastUpdated: new Date().toISOString(),
        trajectory: "stable",
        vitals: { hr: 72, bp: "120/80", bmi: 25.0, hba1c: 5.4, egfr: 90 },
      };
      setTwins((prev) => [...prev, newTwin]);
      setSelectedTwin(newTwin);
    } finally {
      setBuilding(false);
    }
  }, [twins.length]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Digital Twin & Simulation</h1>
          <p className="text-sm text-gray-500">Patient digital twins, what-if scenarios, and predictive trajectories</p>
        </div>
        <button onClick={handleBuildTwin} disabled={building} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50">
          {building ? "Building..." : "+ Build New Twin"}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Active Twins", value: twins.length.toString() },
          { label: "Avg Health Score", value: (twins.reduce((s, t) => s + t.healthScore, 0) / twins.length * 100).toFixed(0) + "%" },
          { label: "Scenarios Run (7d)", value: "47" },
          { label: "Predictions Active", value: "12" },
        ].map((s) => (
          <div key={s.label} className="card text-center">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Twin List */}
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-semibold text-gray-700">Patient Twins</h2>
          {twins.map((twin) => (
            <button
              key={twin.id}
              onClick={() => setSelectedTwin(twin)}
              className={`w-full rounded-lg border p-3 text-left transition-colors ${
                selectedTwin.id === twin.id ? "border-healthos-500 bg-healthos-50" : "border-gray-200 hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900">{twin.patient}</span>
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${trajectoryColor(twin.trajectory)}`}>
                  {twin.trajectory}
                </span>
              </div>
              <div className="mt-1 flex gap-3 text-xs text-gray-500">
                <span>Age {twin.age}</span>
                <span className={`font-medium ${scoreColor(twin.healthScore)}`}>
                  {(twin.healthScore * 100).toFixed(0)}% health
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {twin.conditions.map((c) => (
                  <span key={c} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600">{c}</span>
                ))}
              </div>
            </button>
          ))}
        </div>

        {/* Twin Detail */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{selectedTwin.patient}</h2>
                <p className="text-xs text-gray-500">{selectedTwin.id} — Last updated {new Date(selectedTwin.lastUpdated).toLocaleString()}</p>
              </div>
              <div className={`text-3xl font-bold ${scoreColor(selectedTwin.healthScore)}`}>
                {(selectedTwin.healthScore * 100).toFixed(0)}%
              </div>
            </div>

            {/* Tabs */}
            <div className="mt-4 flex gap-1 rounded-lg bg-gray-100 p-0.5">
              {(["overview", "scenarios", "trajectory"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize ${
                    activeTab === tab ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {activeTab === "overview" && (
            <>
              {/* Vitals Grid */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {[
                  { label: "Heart Rate", value: `${selectedTwin.vitals.hr} bpm`, normal: selectedTwin.vitals.hr < 100 },
                  { label: "Blood Pressure", value: selectedTwin.vitals.bp, normal: parseInt(selectedTwin.vitals.bp) < 140 },
                  { label: "BMI", value: selectedTwin.vitals.bmi.toFixed(1), normal: selectedTwin.vitals.bmi < 30 },
                  { label: "HbA1c", value: `${selectedTwin.vitals.hba1c}%`, normal: selectedTwin.vitals.hba1c < 7.0 },
                  { label: "eGFR", value: `${selectedTwin.vitals.egfr}`, normal: selectedTwin.vitals.egfr > 60 },
                ].map((v) => (
                  <div key={v.label} className="card text-center">
                    <p className="text-xs text-gray-500">{v.label}</p>
                    <p className={`mt-1 text-lg font-bold ${v.normal ? "text-gray-900" : "text-red-600"}`}>{v.value}</p>
                    <div className={`mt-1 h-1 rounded-full ${v.normal ? "bg-green-300" : "bg-red-300"}`} />
                  </div>
                ))}
              </div>

              {/* Conditions */}
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-700">Active Conditions</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {selectedTwin.conditions.map((c) => (
                    <span key={c} className="rounded-lg bg-healthos-50 px-3 py-1.5 text-sm font-medium text-healthos-700">{c}</span>
                  ))}
                </div>
              </div>
            </>
          )}

          {activeTab === "scenarios" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">What-If Scenarios</h3>
                <button className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
                  + New Scenario
                </button>
              </div>
              {SCENARIOS.map((sc) => (
                <div key={sc.id} className="card flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">{sc.name}</span>
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">{sc.type}</span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      Projected impact: <span className={sc.impact.startsWith("+") ? "text-green-600 font-medium" : "text-red-600 font-medium"}>{sc.impact}</span>
                      {" | "}Risk: <span className={`font-medium ${sc.risk === "high" ? "text-red-600" : sc.risk === "low" ? "text-yellow-600" : "text-green-600"}`}>{sc.risk}</span>
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleSimulate(sc.id)} className="rounded bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700">Simulate</button>
                    <button className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">Details</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === "trajectory" && (
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">30/60/90-Day Trajectory Forecast</h3>
              <div className="space-y-4">
                {[
                  { period: "30 Days", score: Math.min(1, selectedTwin.healthScore + (selectedTwin.trajectory === "improving" ? 0.04 : selectedTwin.trajectory === "declining" ? -0.06 : 0)) },
                  { period: "60 Days", score: Math.min(1, selectedTwin.healthScore + (selectedTwin.trajectory === "improving" ? 0.07 : selectedTwin.trajectory === "declining" ? -0.11 : 0.01)) },
                  { period: "90 Days", score: Math.min(1, selectedTwin.healthScore + (selectedTwin.trajectory === "improving" ? 0.10 : selectedTwin.trajectory === "declining" ? -0.15 : 0.01)) },
                ].map((f) => (
                  <div key={f.period} className="flex items-center gap-4">
                    <span className="w-20 text-sm font-medium text-gray-700">{f.period}</span>
                    <div className="flex-1">
                      <div className="h-4 rounded-full bg-gray-100">
                        <div
                          className={`h-4 rounded-full ${f.score >= 0.7 ? "bg-green-400" : f.score >= 0.5 ? "bg-yellow-400" : "bg-red-400"}`}
                          style={{ width: `${Math.max(0, f.score * 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className={`w-16 text-right text-sm font-bold ${scoreColor(f.score)}`}>
                      {(Math.max(0, f.score) * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-lg bg-gray-50 p-3">
                <p className="text-xs text-gray-600">
                  <span className="font-medium">Trajectory:</span> {selectedTwin.trajectory === "improving" ? "Patient showing positive response to current treatment plan. Health score projected to improve." : selectedTwin.trajectory === "declining" ? "Declining trend detected. Consider treatment plan review and intervention optimization." : "Patient metrics stable. Continue current care plan with regular monitoring."}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
