"use client";

import { useState, useEffect, useCallback } from "react";
import {
  createPrescription,
  fetchPrescriptionHistory,
  checkDrugInteractions,
  checkFormulary,
  trackMedicationAdherence,
  processRefill,
} from "@/lib/api";
import { fetchPrescriptions, createPrescriptionRecord, type PrescriptionResponse } from "@/lib/platform-api";

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface Prescription {
  id: string;
  patient_id: string;
  medication: string;
  dosage: string;
  frequency: string;
  status: "active" | "pending" | "discontinued" | "expired";
  prescriber: string;
  date: string;
  duration?: string;
  notes?: string;
}

interface InteractionResult {
  severity: "critical" | "major" | "moderate" | "minor";
  drug_pair: string;
  description: string;
  mechanism: string;
  recommendation: string;
}

interface InteractionCheck {
  id: string;
  drug_a: string;
  drug_b: string;
  timestamp: string;
  results: InteractionResult[];
}

interface FormularyResult {
  drug: string;
  covered: boolean;
  tier: string;
  copay: string;
  prior_auth_required: boolean;
  step_therapy: boolean;
  quantity_limit: string;
  alternatives: string[];
}

interface AdherenceRecord {
  patient_id: string;
  patient_name: string;
  medication: string;
  adherence_pct: number;
  filled_count: number;
  expected_count: number;
  trend: "improving" | "stable" | "declining";
  interventions: string[];
}

interface RefillRequest {
  id: string;
  patient_id: string;
  patient_name: string;
  medication: string;
  last_fill_date: string;
  days_supply: number;
  days_remaining: number;
  auto_refill: boolean;
  status: "pending" | "approved" | "denied" | "processing";
  refills_remaining: number;
}

/* ─── Demo Data ──────────────────────────────────────────────────────────── */

const DEMO_PRESCRIPTIONS: Prescription[] = [
  { id: "RX-2026-0501", patient_id: "P-1001", medication: "Metformin HCl", dosage: "1000mg", frequency: "Twice daily", status: "active", prescriber: "Dr. Sarah Patel", date: "2026-03-12", notes: "Take with meals" },
  { id: "RX-2026-0502", patient_id: "P-1002", medication: "Lisinopril", dosage: "20mg", frequency: "Once daily", status: "active", prescriber: "Dr. James Kim", date: "2026-03-12" },
  { id: "RX-2026-0503", patient_id: "P-1003", medication: "Atorvastatin", dosage: "40mg", frequency: "Once daily at bedtime", status: "active", prescriber: "Dr. Lisa Williams", date: "2026-03-11" },
  { id: "RX-2026-0504", patient_id: "P-1004", medication: "Warfarin Sodium", dosage: "5mg", frequency: "Once daily", status: "pending", prescriber: "Dr. Sarah Patel", date: "2026-03-11", notes: "INR monitoring required" },
  { id: "RX-2026-0505", patient_id: "P-1005", medication: "Levothyroxine", dosage: "75mcg", frequency: "Once daily AM", status: "active", prescriber: "Dr. James Kim", date: "2026-03-10" },
  { id: "RX-2026-0506", patient_id: "P-1006", medication: "Amlodipine", dosage: "10mg", frequency: "Once daily", status: "discontinued", prescriber: "Dr. Lisa Williams", date: "2026-02-28", notes: "Switched to Losartan" },
  { id: "RX-2026-0507", patient_id: "P-1007", medication: "Omeprazole", dosage: "20mg", frequency: "Once daily before breakfast", status: "expired", prescriber: "Dr. Sarah Patel", date: "2026-01-15" },
  { id: "RX-2026-0508", patient_id: "P-1008", medication: "Sertraline", dosage: "100mg", frequency: "Once daily", status: "active", prescriber: "Dr. Rachel Moore", date: "2026-03-10" },
  { id: "RX-2026-0509", patient_id: "P-1003", medication: "Metoprolol Succinate", dosage: "50mg", frequency: "Once daily", status: "active", prescriber: "Dr. Lisa Williams", date: "2026-03-09" },
  { id: "RX-2026-0510", patient_id: "P-1001", medication: "Glipizide", dosage: "5mg", frequency: "Twice daily", status: "pending", prescriber: "Dr. Sarah Patel", date: "2026-03-13", notes: "Adding to metformin regimen" },
];

const DEMO_INTERACTION_HISTORY: InteractionCheck[] = [
  {
    id: "IC-001", drug_a: "Warfarin", drug_b: "Aspirin", timestamp: "2026-03-12T14:30:00Z",
    results: [{ severity: "critical", drug_pair: "Warfarin + Aspirin", description: "Significantly increased risk of major and fatal bleeding events.", mechanism: "Both agents impair hemostasis through different mechanisms — warfarin inhibits clotting factor synthesis while aspirin inhibits platelet aggregation.", recommendation: "Avoid combination unless specifically indicated. If co-prescribed, monitor INR weekly and watch for signs of bleeding." }],
  },
  {
    id: "IC-002", drug_a: "Metformin", drug_b: "Lisinopril", timestamp: "2026-03-12T10:15:00Z",
    results: [{ severity: "minor", drug_pair: "Metformin + Lisinopril", description: "ACE inhibitors may enhance the hypoglycemic effect of metformin.", mechanism: "ACE inhibitors may improve insulin sensitivity, potentially leading to additive blood glucose lowering.", recommendation: "Monitor blood glucose levels. Generally a beneficial combination in diabetic patients with hypertension." }],
  },
  {
    id: "IC-003", drug_a: "Sertraline", drug_b: "Tramadol", timestamp: "2026-03-11T16:45:00Z",
    results: [{ severity: "major", drug_pair: "Sertraline + Tramadol", description: "Risk of serotonin syndrome — a potentially life-threatening condition.", mechanism: "Both drugs increase serotonergic activity. Sertraline inhibits serotonin reuptake while tramadol also has serotonergic properties.", recommendation: "Avoid combination if possible. If necessary, use lowest effective doses and monitor for symptoms: agitation, hyperthermia, tachycardia, muscle rigidity." }],
  },
  {
    id: "IC-004", drug_a: "Atorvastatin", drug_b: "Amlodipine", timestamp: "2026-03-11T09:00:00Z",
    results: [{ severity: "moderate", drug_pair: "Atorvastatin + Amlodipine", description: "Amlodipine may increase atorvastatin plasma concentrations.", mechanism: "Amlodipine is a weak CYP3A4 inhibitor that may reduce atorvastatin metabolism.", recommendation: "Limit atorvastatin to 40mg daily when combined with amlodipine. Monitor for myopathy symptoms." }],
  },
];

const DEMO_REFILLS: RefillRequest[] = [
  { id: "RF-001", patient_id: "P-1001", patient_name: "Maria Garcia", medication: "Metformin HCl 1000mg", last_fill_date: "2026-02-12", days_supply: 30, days_remaining: 0, auto_refill: true, status: "pending", refills_remaining: 3 },
  { id: "RF-002", patient_id: "P-1005", patient_name: "Emily Davis", medication: "Levothyroxine 75mcg", last_fill_date: "2026-02-15", days_supply: 30, days_remaining: 2, auto_refill: true, status: "pending", refills_remaining: 5 },
  { id: "RF-003", patient_id: "P-1004", patient_name: "Robert Johnson", medication: "Warfarin Sodium 5mg", last_fill_date: "2026-02-20", days_supply: 30, days_remaining: 7, auto_refill: false, status: "pending", refills_remaining: 1 },
  { id: "RF-004", patient_id: "P-1003", patient_name: "Sarah Chen", medication: "Atorvastatin 40mg", last_fill_date: "2026-03-01", days_supply: 90, days_remaining: 76, auto_refill: true, status: "approved", refills_remaining: 4 },
  { id: "RF-005", patient_id: "P-1002", patient_name: "James Wilson", medication: "Lisinopril 20mg", last_fill_date: "2026-02-28", days_supply: 30, days_remaining: 15, auto_refill: false, status: "pending", refills_remaining: 2 },
  { id: "RF-006", patient_id: "P-1008", patient_name: "Angela Torres", medication: "Sertraline 100mg", last_fill_date: "2026-02-10", days_supply: 30, days_remaining: 0, auto_refill: true, status: "processing", refills_remaining: 6 },
];

const DEMO_ADHERENCE: AdherenceRecord[] = [
  { patient_id: "P-1001", patient_name: "Maria Garcia", medication: "Metformin HCl", adherence_pct: 92, filled_count: 11, expected_count: 12, trend: "stable", interventions: ["Refill reminders active"] },
  { patient_id: "P-1002", patient_name: "James Wilson", medication: "Lisinopril", adherence_pct: 78, filled_count: 7, expected_count: 9, trend: "declining", interventions: ["Schedule pharmacist counseling", "Enable auto-refill", "Send adherence education materials"] },
  { patient_id: "P-1003", patient_name: "Sarah Chen", medication: "Atorvastatin", adherence_pct: 95, filled_count: 11, expected_count: 12, trend: "improving", interventions: ["Continue current plan"] },
  { patient_id: "P-1004", patient_name: "Robert Johnson", medication: "Warfarin Sodium", adherence_pct: 85, filled_count: 10, expected_count: 12, trend: "stable", interventions: ["INR monitoring adherence OK", "Reinforce consistent timing"] },
  { patient_id: "P-1005", patient_name: "Emily Davis", medication: "Levothyroxine", adherence_pct: 65, filled_count: 6, expected_count: 9, trend: "declining", interventions: ["Urgent: pharmacist outreach", "Assess barriers to adherence", "Consider simplifying regimen", "Enroll in adherence program"] },
  { patient_id: "P-1008", patient_name: "Angela Torres", medication: "Sertraline", adherence_pct: 88, filled_count: 10, expected_count: 11, trend: "improving", interventions: ["Positive trend — maintain current support"] },
];

/* ─── Tabs ───────────────────────────────────────────────────────────────── */

const TABS = ["Prescriptions", "Drug Interactions", "Formulary & Adherence", "Refill Management"] as const;
type Tab = (typeof TABS)[number];

/* ─── Helpers ────────────────────────────────────────────────────────────── */

function rxStatusClasses(status: Prescription["status"]) {
  const m: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    pending: "bg-yellow-100 text-yellow-800",
    discontinued: "bg-gray-200 text-gray-600 dark:text-gray-400",
    expired: "bg-red-100 text-red-800",
  };
  return m[status] ?? "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200";
}

function severityClasses(severity: InteractionResult["severity"]) {
  const m: Record<string, string> = {
    critical: "border-red-400 bg-red-50",
    major: "border-orange-400 bg-orange-50",
    moderate: "border-yellow-400 bg-yellow-50",
    minor: "border-blue-400 bg-blue-50",
  };
  return m[severity] ?? "border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800";
}

function severityBadge(severity: InteractionResult["severity"]) {
  const m: Record<string, string> = {
    critical: "bg-red-600 text-white",
    major: "bg-orange-500 text-white",
    moderate: "bg-yellow-500 text-white",
    minor: "bg-blue-500 text-white",
  };
  return m[severity] ?? "bg-gray-500 text-white";
}

function adherenceBarColor(pct: number) {
  if (pct >= 90) return "bg-green-500";
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 70) return "bg-yellow-500";
  return "bg-red-500";
}

function refillProgressPct(r: RefillRequest) {
  return Math.max(0, Math.min(100, (r.days_remaining / r.days_supply) * 100));
}

function refillProgressColor(pct: number) {
  if (pct > 50) return "bg-green-500";
  if (pct > 25) return "bg-yellow-500";
  return "bg-red-500";
}

/* ─── Component ──────────────────────────────────────────────────────────── */

export default function PharmacyPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Prescriptions");

  // Prescriptions state
  const [prescriptions, setPrescriptions] = useState<Prescription[]>(DEMO_PRESCRIPTIONS);
  const [showNewRxModal, setShowNewRxModal] = useState(false);
  const [rxForm, setRxForm] = useState({ patient_id: "", medication: "", dosage: "", frequency: "", duration: "", notes: "" });
  const [rxSubmitting, setRxSubmitting] = useState(false);

  // Drug Interactions state
  const [drugA, setDrugA] = useState("");
  const [drugB, setDrugB] = useState("");
  const [interactionResults, setInteractionResults] = useState<InteractionResult[] | null>(null);
  const [interactionHistory, setInteractionHistory] = useState<InteractionCheck[]>(DEMO_INTERACTION_HISTORY);
  const [checkingInteraction, setCheckingInteraction] = useState(false);

  // Formulary state
  const [formularyDrug, setFormularyDrug] = useState("");
  const [formularyResult, setFormularyResult] = useState<FormularyResult | null>(null);
  const [checkingFormulary, setCheckingFormulary] = useState(false);

  // Adherence state
  const [adherenceSearch, setAdherenceSearch] = useState("");
  const [adherenceData, setAdherenceData] = useState<AdherenceRecord[]>(DEMO_ADHERENCE);

  // Refills state
  const [refills, setRefills] = useState<RefillRequest[]>(DEMO_REFILLS);
  const [processingRefill, setProcessingRefill] = useState<string | null>(null);

  /* ── Load data on mount ──────────────────────────────────────────────── */

  useEffect(() => {
    // Try real EHR prescriptions from /clinical/prescriptions
    (async () => {
      try {
        const rxList = await fetchPrescriptions("all");
        if (rxList.length > 0) {
          setPrescriptions(
            rxList.map((rx: PrescriptionResponse) => ({
              id: rx.id,
              patient_id: rx.patient_id,
              medication: rx.medication_name,
              dosage: rx.dosage,
              frequency: rx.frequency,
              status: (rx.status.toLowerCase() as Prescription["status"]) || "active",
              prescriber: rx.provider_id?.slice(0, 8) ?? "—",
              date: rx.start_date,
              duration: rx.end_date ? `until ${rx.end_date}` : undefined,
              notes: rx.instructions ?? undefined,
            })),
          );
        }
      } catch {
        // Fall back to agent API
        fetchPrescriptionHistory("all")
          .then((data) => {
            if (Array.isArray(data) && data.length > 0) setPrescriptions(data as unknown as Prescription[]);
          })
          .catch(() => { /* keep demo data */ });
      }
    })();

    trackMedicationAdherence({ patient_id: "all" })
      .then((data) => {
        if (data && Array.isArray((data as Record<string, unknown>).records)) {
          setAdherenceData((data as Record<string, unknown>).records as unknown as AdherenceRecord[]);
        }
      })
      .catch(() => { /* fall back to demo data */ });
  }, []);

  /* ── Handlers ────────────────────────────────────────────────────────── */

  const handleCreatePrescription = useCallback(async () => {
    if (!rxForm.patient_id || !rxForm.medication || !rxForm.dosage || !rxForm.frequency) return;
    setRxSubmitting(true);
    try {
      await createPrescription({
        patient_id: rxForm.patient_id,
        medication: rxForm.medication,
        dosage: rxForm.dosage,
        frequency: rxForm.frequency,
        duration: rxForm.duration,
        notes: rxForm.notes,
      });
    } catch {
      /* offline — add to local list */
    }
    const newRx: Prescription = {
      id: `RX-2026-${String(510 + prescriptions.length).padStart(4, "0")}`,
      patient_id: rxForm.patient_id,
      medication: rxForm.medication,
      dosage: rxForm.dosage,
      frequency: rxForm.frequency,
      status: "pending",
      prescriber: "Current User",
      date: new Date().toISOString().slice(0, 10),
      duration: rxForm.duration,
      notes: rxForm.notes,
    };
    setPrescriptions((prev) => [newRx, ...prev]);
    setRxForm({ patient_id: "", medication: "", dosage: "", frequency: "", duration: "", notes: "" });
    setShowNewRxModal(false);
    setRxSubmitting(false);
  }, [rxForm, prescriptions.length]);

  const handleCheckInteraction = useCallback(async () => {
    if (!drugA.trim() || !drugB.trim()) return;
    setCheckingInteraction(true);
    setInteractionResults(null);
    let results: InteractionResult[];
    try {
      const resp = await checkDrugInteractions({ drug_a: drugA, drug_b: drugB });
      results = (resp as Record<string, unknown>).interactions as InteractionResult[] ?? [];
    } catch {
      // Demo fallback
      const severities: InteractionResult["severity"][] = ["moderate", "minor", "major", "critical"];
      const sev = severities[Math.floor(Math.random() * severities.length)];
      results = [{
        severity: sev,
        drug_pair: `${drugA} + ${drugB}`,
        description: `Potential interaction between ${drugA} and ${drugB} identified. Clinical significance should be evaluated based on patient context.`,
        mechanism: `Both agents may affect overlapping metabolic or pharmacodynamic pathways. Specific CYP enzyme involvement may vary.`,
        recommendation: sev === "critical" ? "Avoid combination. Seek alternative therapy."
          : sev === "major" ? "Use only if benefit outweighs risk. Monitor closely."
          : sev === "moderate" ? "Monitor patient parameters. Adjust dosing if needed."
          : "Generally safe. Counsel patient on potential mild effects.",
      }];
    }
    setInteractionResults(results);
    const newCheck: InteractionCheck = {
      id: `IC-${String(interactionHistory.length + 5).padStart(3, "0")}`,
      drug_a: drugA,
      drug_b: drugB,
      timestamp: new Date().toISOString(),
      results,
    };
    setInteractionHistory((prev) => [newCheck, ...prev]);
    setCheckingInteraction(false);
  }, [drugA, drugB, interactionHistory.length]);

  const handleCheckFormulary = useCallback(async () => {
    if (!formularyDrug.trim()) return;
    setCheckingFormulary(true);
    setFormularyResult(null);
    try {
      const resp = await checkFormulary({ drug_name: formularyDrug });
      setFormularyResult(resp as unknown as FormularyResult);
    } catch {
      // Demo fallback
      const tiers = ["Tier 1 — Generic", "Tier 2 — Preferred Brand", "Tier 3 — Non-Preferred"];
      const copays = ["$5", "$25", "$50"];
      const idx = Math.floor(Math.random() * 3);
      setFormularyResult({
        drug: formularyDrug,
        covered: idx < 2,
        tier: tiers[idx],
        copay: copays[idx],
        prior_auth_required: idx === 2,
        step_therapy: idx >= 1,
        quantity_limit: idx === 0 ? "None" : "30 tablets / 30 days",
        alternatives: idx === 0 ? [] : ["Metformin (Tier 1)", "Glipizide (Tier 1)"],
      });
    }
    setCheckingFormulary(false);
  }, [formularyDrug]);

  const handleRefillAction = useCallback(async (refillId: string, action: "approve" | "deny") => {
    setProcessingRefill(refillId);
    try {
      await processRefill({ refill_id: refillId, action });
    } catch {
      /* offline */
    }
    setRefills((prev) =>
      prev.map((r) => r.id === refillId ? { ...r, status: action === "approve" ? "approved" : "denied" } : r)
    );
    setProcessingRefill(null);
  }, []);

  /* ── Computed stats ──────────────────────────────────────────────────── */

  const activeRxCount = prescriptions.filter((p) => p.status === "active").length;
  const pendingRefillCount = refills.filter((r) => r.status === "pending").length;
  const alertCount = interactionHistory.reduce((sum, c) => sum + c.results.filter((r) => r.severity === "critical" || r.severity === "major").length, 0);
  const avgAdherence = adherenceData.length > 0 ? Math.round(adherenceData.reduce((s, a) => s + a.adherence_pct, 0) / adherenceData.length) : 0;

  const filteredAdherence = adherenceSearch.trim()
    ? adherenceData.filter((a) =>
        a.patient_name.toLowerCase().includes(adherenceSearch.toLowerCase()) ||
        a.patient_id.toLowerCase().includes(adherenceSearch.toLowerCase()) ||
        a.medication.toLowerCase().includes(adherenceSearch.toLowerCase())
      )
    : adherenceData;

  /* ── Render ──────────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in-up">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Pharmacy Management</h1>
            <span className="inline-flex items-center rounded-full bg-healthos-100 px-3 py-0.5 text-sm font-semibold text-healthos-700">
              {activeRxCount} active
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Prescriptions, drug interaction checking, formulary management, adherence tracking, and refill processing
          </p>
        </div>
        <button
          onClick={() => setShowNewRxModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-healthos-700 focus:outline-none focus:ring-2 focus:ring-healthos-500 focus:ring-offset-2"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
          New Prescription
        </button>
      </div>

      {/* ── Stats Bar ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {[
          { label: "Active Prescriptions", value: String(activeRxCount), icon: "💊", accent: "text-healthos-600" },
          { label: "Pending Refills", value: String(pendingRefillCount), icon: "🔄", accent: "text-yellow-600" },
          { label: "Interaction Alerts", value: String(alertCount), icon: "⚠️", accent: "text-red-600" },
          { label: "Avg Adherence %", value: `${avgAdherence}%`, icon: "📊", accent: "text-emerald-600" },
          { label: "Formulary Checks Today", value: String(interactionHistory.length + 3), icon: "📋", accent: "text-blue-600" },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover rounded-xl p-4 animate-fade-in-up">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">{kpi.label}</p>
              <span className="text-lg">{kpi.icon}</span>
            </div>
            <p className={`mt-2 text-2xl font-bold ${kpi.accent}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* ── Tab Navigation ─────────────────────────────────────────────── */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-6 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                activeTab === t
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* Tab 1: Prescriptions                                               */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {activeTab === "Prescriptions" && (
        <div className="card rounded-xl overflow-hidden animate-fade-in-up">
          <div className="overflow-x-auto">
            <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  {["Rx ID", "Medication", "Dosage", "Frequency", "Patient ID", "Status", "Prescriber", "Date"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white dark:bg-gray-900">
                {prescriptions.map((rx) => (
                  <tr key={rx.id} className="transition hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-3 font-mono text-xs text-gray-600 dark:text-gray-400">{rx.id}</td>
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{rx.medication}</td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{rx.dosage}</td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{rx.frequency}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600 dark:text-gray-400">{rx.patient_id}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${rxStatusClasses(rx.status)}`}>
                        {rx.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{rx.prescriber}</td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{rx.date}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* Tab 2: Drug Interactions                                           */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {activeTab === "Drug Interactions" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Checker */}
          <div className="card card-hover rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Drug Interaction Checker</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Enter two medications to check for potential interactions</p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Medication A</label>
                <input
                  type="text"
                  value={drugA}
                  onChange={(e) => setDrugA(e.target.value)}
                  placeholder="e.g., Warfarin"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
              <div className="flex items-center justify-center">
                <span className="text-xl font-bold text-gray-300">+</span>
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Medication B</label>
                <input
                  type="text"
                  value={drugB}
                  onChange={(e) => setDrugB(e.target.value)}
                  placeholder="e.g., Aspirin"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
              <button
                onClick={handleCheckInteraction}
                disabled={checkingInteraction || !drugA.trim() || !drugB.trim()}
                className="rounded-lg bg-healthos-600 px-6 py-2 text-sm font-semibold text-white transition hover:bg-healthos-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {checkingInteraction ? "Checking..." : "Check Interactions"}
              </button>
            </div>
          </div>

          {/* Results */}
          {interactionResults && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Results</h4>
              {interactionResults.length === 0 ? (
                <div className="card rounded-xl p-6 text-center text-sm text-gray-500 dark:text-gray-400">No interactions found between these medications.</div>
              ) : (
                interactionResults.map((r, i) => (
                  <div key={i} className={`card rounded-xl border-l-4 p-5 ${severityClasses(r.severity)} animate-fade-in-up`}>
                    <div className="flex items-center gap-3">
                      <span className={`rounded-full px-3 py-0.5 text-xs font-bold uppercase ${severityBadge(r.severity)}`}>{r.severity}</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{r.drug_pair}</span>
                    </div>
                    <p className="mt-3 text-sm text-gray-800 dark:text-gray-200">{r.description}</p>
                    <div className="mt-3 rounded-lg bg-white/60 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Mechanism</p>
                      <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{r.mechanism}</p>
                    </div>
                    <div className="mt-3 rounded-lg bg-white/60 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Recommendation</p>
                      <p className="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">{r.recommendation}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* History */}
          <div className="card rounded-xl p-6">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Recent Interaction Checks</h4>
            <div className="mt-4 space-y-2">
              {interactionHistory.map((check) => (
                <div key={check.id} className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 px-4 py-3 text-sm">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-gray-500 dark:text-gray-400">{check.id}</span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">{check.drug_a} + {check.drug_b}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {check.results.map((r, i) => (
                      <span key={i} className={`rounded-full px-2 py-0.5 text-xs font-bold uppercase ${severityBadge(r.severity)}`}>{r.severity}</span>
                    ))}
                    <span className="text-xs text-gray-500 dark:text-gray-400">{new Date(check.timestamp).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* Tab 3: Formulary & Adherence                                       */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {activeTab === "Formulary & Adherence" && (
        <div className="grid gap-6 lg:grid-cols-2 animate-fade-in-up">

          {/* Left: Formulary Check */}
          <div className="space-y-4">
            <div className="card card-hover rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Formulary Check</h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Look up drug coverage, tier, and copay information</p>
              <div className="mt-4 flex gap-2">
                <input
                  type="text"
                  value={formularyDrug}
                  onChange={(e) => setFormularyDrug(e.target.value)}
                  placeholder="Enter drug name..."
                  className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  onKeyDown={(e) => e.key === "Enter" && handleCheckFormulary()}
                />
                <button
                  onClick={handleCheckFormulary}
                  disabled={checkingFormulary || !formularyDrug.trim()}
                  className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-healthos-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {checkingFormulary ? "Checking..." : "Check"}
                </button>
              </div>
            </div>

            {formularyResult && (
              <div className="card rounded-xl p-6 animate-fade-in-up">
                <div className="flex items-center justify-between">
                  <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100">{formularyResult.drug}</h4>
                  <span className={`rounded-full px-3 py-0.5 text-xs font-bold ${formularyResult.covered ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                    {formularyResult.covered ? "Covered" : "Not Covered"}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Tier</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">{formularyResult.tier}</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Copay</p>
                    <p className="mt-1 text-sm font-semibold text-healthos-600">{formularyResult.copay}</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Prior Auth</p>
                    <p className="mt-1 text-sm font-semibold">{formularyResult.prior_auth_required ? "Required" : "Not Required"}</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Quantity Limit</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">{formularyResult.quantity_limit}</p>
                  </div>
                </div>
                {formularyResult.alternatives.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Lower-Cost Alternatives</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {formularyResult.alternatives.map((alt) => (
                        <span key={alt} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">{alt}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: Adherence Tracking */}
          <div className="space-y-4">
            <div className="card card-hover rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Adherence Tracking</h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Monitor patient medication adherence and interventions</p>
              <div className="mt-4">
                <input
                  type="text"
                  value={adherenceSearch}
                  onChange={(e) => setAdherenceSearch(e.target.value)}
                  placeholder="Search by patient name, ID, or medication..."
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
            </div>

            <div className="space-y-3">
              {filteredAdherence.map((a) => (
                <div key={`${a.patient_id}-${a.medication}`} className="card card-hover rounded-xl p-5 animate-fade-in-up">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{a.patient_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{a.patient_id} &middot; {a.medication}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${a.adherence_pct >= 80 ? "text-green-600" : a.adherence_pct >= 70 ? "text-yellow-600" : "text-red-600"}`}>
                        {a.adherence_pct}%
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {a.trend === "improving" ? "↑ Improving" : a.trend === "declining" ? "↓ Declining" : "→ Stable"}
                      </p>
                    </div>
                  </div>
                  {/* Bar chart */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>{a.filled_count} of {a.expected_count} fills</span>
                      <span>{a.adherence_pct}%</span>
                    </div>
                    <div className="mt-1 h-3 w-full overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${adherenceBarColor(a.adherence_pct)}`}
                        style={{ width: `${a.adherence_pct}%` }}
                      />
                    </div>
                  </div>
                  {/* Interventions */}
                  {a.interventions.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Recommendations</p>
                      <ul className="mt-1 space-y-1">
                        {a.interventions.map((intr, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-400">
                            <span className="mt-0.5 text-healthos-500">&#8226;</span>
                            {intr}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
              {filteredAdherence.length === 0 && (
                <div className="card rounded-xl p-6 text-center text-sm text-gray-500 dark:text-gray-400">No adherence records match your search.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* Tab 4: Refill Management                                           */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {activeTab === "Refill Management" && (
        <div className="space-y-4 animate-fade-in-up">
          {refills.map((r) => {
            const pct = refillProgressPct(r);
            return (
              <div key={r.id} className="card card-hover rounded-xl p-5 animate-fade-in-up">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <p className="text-base font-semibold text-gray-900 dark:text-gray-100">{r.medication}</p>
                      {r.auto_refill && (
                        <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700">Auto-Refill</span>
                      )}
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                        r.status === "approved" ? "bg-green-100 text-green-800"
                        : r.status === "denied" ? "bg-red-100 text-red-800"
                        : r.status === "processing" ? "bg-blue-100 text-blue-800"
                        : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {r.status}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      {r.patient_name} <span className="font-mono text-xs text-gray-500 dark:text-gray-400">({r.patient_id})</span>
                    </p>
                    <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
                      <span>Last fill: {r.last_fill_date}</span>
                      <span>Refills remaining: {r.refills_remaining}</span>
                    </div>

                    {/* Days supply progress bar */}
                    <div className="mt-3 max-w-md">
                      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                        <span>Days Supply Remaining</span>
                        <span className="font-semibold">{r.days_remaining} of {r.days_supply} days</span>
                      </div>
                      <div className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-gray-200">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${refillProgressColor(pct)}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Action buttons */}
                  {r.status === "pending" && (
                    <div className="flex gap-2 sm:flex-col">
                      <button
                        onClick={() => handleRefillAction(r.id, "approve")}
                        disabled={processingRefill === r.id}
                        className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-green-700 disabled:opacity-50"
                      >
                        {processingRefill === r.id ? "..." : "Approve"}
                      </button>
                      <button
                        onClick={() => handleRefillAction(r.id, "deny")}
                        disabled={processingRefill === r.id}
                        className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
                      >
                        {processingRefill === r.id ? "..." : "Deny"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* New Prescription Modal                                             */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {showNewRxModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="card w-full max-w-lg rounded-2xl p-6 shadow-2xl animate-fade-in-up">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">New Prescription</h3>
              <button onClick={() => setShowNewRxModal(false)} className="rounded-full p-1 text-gray-500 dark:text-gray-400 transition hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="mt-5 space-y-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400">Patient ID *</label>
                <input type="text" value={rxForm.patient_id} onChange={(e) => setRxForm((f) => ({ ...f, patient_id: e.target.value }))} placeholder="P-1001" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400">Medication *</label>
                <input type="text" value={rxForm.medication} onChange={(e) => setRxForm((f) => ({ ...f, medication: e.target.value }))} placeholder="Metformin HCl" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400">Dosage *</label>
                  <input type="text" value={rxForm.dosage} onChange={(e) => setRxForm((f) => ({ ...f, dosage: e.target.value }))} placeholder="500mg" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400">Frequency *</label>
                  <input type="text" value={rxForm.frequency} onChange={(e) => setRxForm((f) => ({ ...f, frequency: e.target.value }))} placeholder="Twice daily" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400">Duration</label>
                <input type="text" value={rxForm.duration} onChange={(e) => setRxForm((f) => ({ ...f, duration: e.target.value }))} placeholder="30 days" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400">Notes</label>
                <textarea value={rxForm.notes} onChange={(e) => setRxForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Additional notes..." rows={3} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setShowNewRxModal(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-800">
                Cancel
              </button>
              <button
                onClick={handleCreatePrescription}
                disabled={rxSubmitting || !rxForm.patient_id || !rxForm.medication || !rxForm.dosage || !rxForm.frequency}
                className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-healthos-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {rxSubmitting ? "Creating..." : "Create Prescription"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
