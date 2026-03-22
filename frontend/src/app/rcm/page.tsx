"use client";

import { useState, useEffect, useCallback } from "react";
import {
  captureCharges,
  optimizeClaim,
  fetchCleanClaimRate,
  analyzeDenial,
  appealDenial,
  verifyRevenueIntegrity,
} from "@/lib/api";

/* ──────────────────────────── Demo Data ──────────────────────────── */

const DEMO_CLAIMS = [
  { id: "CLM-8921", patient: "Sarah Johnson", codes: ["99214", "80048"], amount: 425.0, payer: "Blue Cross", status: "submitted", date: "2026-03-12" },
  { id: "CLM-8920", patient: "Michael Chen", codes: ["99213", "85025"], amount: 285.5, payer: "Aetna", status: "paid", date: "2026-03-10" },
  { id: "CLM-8919", patient: "Emma Davis", codes: ["99215", "93000", "80053"], amount: 1250.0, payer: "UnitedHealth", status: "denied", date: "2026-03-08" },
  { id: "CLM-8918", patient: "Robert Wilson", codes: ["99213"], amount: 198.75, payer: "Medicare", status: "paid", date: "2026-03-07" },
  { id: "CLM-8917", patient: "Lisa Thompson", codes: ["99214", "80069"], amount: 680.0, payer: "Cigna", status: "pending", date: "2026-03-06" },
  { id: "CLM-8916", patient: "James Brown", codes: ["99212"], amount: 156.0, payer: "Medicare", status: "paid", date: "2026-03-05" },
  { id: "CLM-8915", patient: "Maria Garcia", codes: ["99214", "36415"], amount: 390.0, payer: "Aetna", status: "appealed", date: "2026-03-04" },
  { id: "CLM-8914", patient: "David Kim", codes: ["99215", "93010", "80061"], amount: 1540.0, payer: "Blue Cross", status: "submitted", date: "2026-03-03" },
];

const DEMO_DENIALS = [
  { id: "DEN-401", claimId: "CLM-8919", reason: "Prior authorization not obtained", amount: 1250.0, payer: "UnitedHealth", category: "auth", date: "2026-03-09", severity: "high" },
  { id: "DEN-400", claimId: "CLM-8910", reason: "Diagnosis code does not support medical necessity", amount: 875.0, payer: "Aetna", category: "medical_necessity", date: "2026-03-07", severity: "high" },
  { id: "DEN-399", claimId: "CLM-8905", reason: "CPT/ICD-10 code mismatch", amount: 620.0, payer: "Blue Cross", category: "coding", date: "2026-03-06", severity: "medium" },
  { id: "DEN-398", claimId: "CLM-8901", reason: "Patient not eligible on date of service", amount: 445.0, payer: "Cigna", category: "eligibility", date: "2026-03-05", severity: "medium" },
  { id: "DEN-397", claimId: "CLM-8898", reason: "Duplicate claim submission", amount: 310.0, payer: "Medicare", category: "coding", date: "2026-03-04", severity: "low" },
  { id: "DEN-396", claimId: "CLM-8895", reason: "Service not covered under plan", amount: 980.0, payer: "UnitedHealth", category: "eligibility", date: "2026-03-03", severity: "high" },
];

const DEMO_DENIAL_TRENDS = [
  { reason: "Prior Authorization", count: 28, color: "bg-red-500" },
  { reason: "Coding Errors", count: 22, color: "bg-orange-500" },
  { reason: "Eligibility Issues", count: 19, color: "bg-yellow-500" },
  { reason: "Medical Necessity", count: 15, color: "bg-blue-500" },
  { reason: "Timely Filing", count: 10, color: "bg-purple-500" },
];

const DEMO_INTEGRITY_FINDINGS = [
  { id: "INT-01", type: "HCC Gap", description: "Patient James Brown has documented Type 2 Diabetes but HCC 19 not captured in recent encounters", impact: 4200, confidence: 94, status: "open" },
  { id: "INT-02", type: "Coding Opportunity", description: "E&M level 99213 could be supported as 99214 based on documented complexity for 23 encounters", impact: 6900, confidence: 87, status: "open" },
  { id: "INT-03", type: "Leakage Detection", description: "Unbilled chronic care management (CCM) services for 18 eligible patients", impact: 8100, confidence: 91, status: "open" },
  { id: "INT-04", type: "HCC Gap", description: "CKD Stage 3 documented in labs but not coded for patient Maria Garcia", impact: 3800, confidence: 89, status: "open" },
  { id: "INT-05", type: "Coding Opportunity", description: "Missed modifier 25 on 12 office visit claims with same-day procedures", impact: 2400, confidence: 96, status: "open" },
  { id: "INT-06", type: "Leakage Detection", description: "Transitional care management not billed for 8 post-discharge patients", impact: 5600, confidence: 85, status: "open" },
];

const DEMO_AR_BUCKETS = [
  { label: "0-30 days", amount: 187500, claims: 245, color: "bg-emerald-500" },
  { label: "31-60 days", amount: 96400, claims: 128, color: "bg-blue-500" },
  { label: "61-90 days", amount: 52300, claims: 67, color: "bg-yellow-500" },
  { label: "90+ days", amount: 43900, claims: 53, color: "bg-red-500" },
];

/* ──────────────────────────── Helpers ──────────────────────────── */

type TabKey = "claims" | "denials" | "integrity" | "payments";

const STATUS_COLORS: Record<string, string> = {
  submitted: "bg-blue-100 text-blue-700 border-blue-200",
  paid: "bg-green-100 text-green-700 border-green-200",
  denied: "bg-red-100 text-red-700 border-red-200",
  appealed: "bg-orange-100 text-orange-700 border-orange-200",
  pending: "bg-yellow-100 text-yellow-700 border-yellow-200",
};

const CATEGORY_LABELS: Record<string, string> = {
  medical_necessity: "Medical Necessity",
  coding: "Coding",
  auth: "Authorization",
  eligibility: "Eligibility",
};

const CATEGORY_COLORS: Record<string, string> = {
  medical_necessity: "bg-purple-100 text-purple-700",
  coding: "bg-blue-100 text-blue-700",
  auth: "bg-orange-100 text-orange-700",
  eligibility: "bg-teal-100 text-teal-700",
};

const SEVERITY_COLORS: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-yellow-500",
  low: "bg-green-500",
};

function formatCurrency(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
}

/* ──────────────────────────── Clean Claim Gauge ──────────────────────────── */

function CleanClaimGauge({ rate }: { rate: number }) {
  const radius = 70;
  const stroke = 12;
  const circumference = Math.PI * radius;
  const offset = circumference - (rate / 100) * circumference;
  const color = rate >= 95 ? "#10b981" : rate >= 90 ? "#f59e0b" : "#ef4444";

  return (
    <div className="flex flex-col items-center">
      <svg width="160" height="90" viewBox="0 0 160 90">
        <path
          d="M 10 80 A 70 70 0 0 1 150 80"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d="M 10 80 A 70 70 0 0 1 150 80"
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000"
        />
        <text x="80" y="72" textAnchor="middle" className="fill-gray-900 text-2xl font-bold" fontSize="28">
          {rate}%
        </text>
      </svg>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Clean Claim Rate</p>
    </div>
  );
}

/* ──────────────────────────── Main Component ──────────────────────────── */

export default function RCMPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("claims");
  const [cleanClaimRate, setCleanClaimRate] = useState(94.8);

  // Claims & Billing state
  const [claims] = useState(DEMO_CLAIMS);
  const [optimizingClaim, setOptimizingClaim] = useState<string | null>(null);
  const [showChargeForm, setShowChargeForm] = useState(false);
  const [chargeForm, setChargeForm] = useState({ patient: "", payer: "", codes: "", amount: "", diagnosis: "" });
  const [submittingCharge, setSubmittingCharge] = useState(false);

  // Denial Management state
  const [denials] = useState(DEMO_DENIALS);
  const [analyzingDenial, setAnalyzingDenial] = useState<string | null>(null);
  const [denialAnalysis, setDenialAnalysis] = useState<Record<string, { rootCause: string; aiInsights: string[]; recommendedAction: string }>>({});
  const [appealingDenial, setAppealingDenial] = useState<string | null>(null);

  // Revenue Integrity state
  const [integrityFindings, setIntegrityFindings] = useState(DEMO_INTEGRITY_FINDINGS);
  const [scanRunning, setScanRunning] = useState(false);
  const [scanComplete, setScanComplete] = useState(true);

  // Payments & AR state
  const [paymentForm, setPaymentForm] = useState({ claimId: "", amount: "", method: "eft", reference: "" });
  const [postingPayment, setPostingPayment] = useState(false);

  // Load clean claim rate from API
  useEffect(() => {
    fetchCleanClaimRate()
      .then((data) => {
        if (data && typeof data === "object" && "rate" in data) {
          setCleanClaimRate(data.rate as number);
        }
      })
      .catch(() => { /* use demo data */ });
  }, []);

  // ── Handlers ──

  const handleOptimizeClaim = useCallback(async (claimId: string) => {
    setOptimizingClaim(claimId);
    try {
      await optimizeClaim({ claim_id: claimId });
    } catch {
      /* demo mode */
    } finally {
      setTimeout(() => setOptimizingClaim(null), 1200);
    }
  }, []);

  const handleCaptureCharge = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingCharge(true);
    try {
      await captureCharges({
        patient_name: chargeForm.patient,
        payer: chargeForm.payer,
        codes: chargeForm.codes.split(",").map((c) => c.trim()),
        amount: parseFloat(chargeForm.amount) || 0,
        diagnosis: chargeForm.diagnosis,
      });
    } catch {
      /* demo mode */
    } finally {
      setSubmittingCharge(false);
      setShowChargeForm(false);
      setChargeForm({ patient: "", payer: "", codes: "", amount: "", diagnosis: "" });
    }
  }, [chargeForm]);

  const handleAnalyzeDenial = useCallback(async (denialId: string, claimId: string) => {
    setAnalyzingDenial(denialId);
    try {
      await analyzeDenial({ denial_id: denialId, claim_id: claimId });
    } catch {
      /* demo fallback */
    }
    // Simulate AI analysis result
    setTimeout(() => {
      setDenialAnalysis((prev) => ({
        ...prev,
        [denialId]: {
          rootCause: "Payer requires prior authorization for CPT 93000 when billed with E&M level 5. Authorization was not obtained prior to service date.",
          aiInsights: [
            "This payer denies 34% of 99215+93000 combinations without prior auth",
            "Similar claims have 78% appeal success rate when documentation supports medical necessity",
            "Consider implementing automated prior auth checks for high-value procedure combinations",
          ],
          recommendedAction: "Submit appeal with medical necessity documentation and clinical notes supporting the urgency of the diagnostic evaluation.",
        },
      }));
      setAnalyzingDenial(null);
    }, 1500);
  }, []);

  const handleGenerateAppeal = useCallback(async (denialId: string) => {
    setAppealingDenial(denialId);
    try {
      await appealDenial({ denial_id: denialId, generate_letter: true });
    } catch {
      /* demo mode */
    }
    setTimeout(() => setAppealingDenial(null), 2000);
  }, []);

  const handleRunIntegrityScan = useCallback(async () => {
    setScanRunning(true);
    setScanComplete(false);
    try {
      await verifyRevenueIntegrity({ scan_type: "full", include_hcc: true, include_coding: true, include_leakage: true });
    } catch {
      /* demo mode */
    }
    setTimeout(() => {
      setIntegrityFindings([
        ...DEMO_INTEGRITY_FINDINGS,
        { id: "INT-07", type: "HCC Gap", description: "Obesity (BMI 35.2) documented but HCC not captured for patient David Kim", impact: 2100, confidence: 92, status: "open" },
      ]);
      setScanRunning(false);
      setScanComplete(true);
    }, 3000);
  }, []);

  const handlePostPayment = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setPostingPayment(true);
    try {
      await captureCharges({ type: "payment_posting", claim_id: paymentForm.claimId, amount: parseFloat(paymentForm.amount), method: paymentForm.method, reference: paymentForm.reference });
    } catch {
      /* demo mode */
    } finally {
      setPostingPayment(false);
      setPaymentForm({ claimId: "", amount: "", method: "eft", reference: "" });
    }
  }, [paymentForm]);

  // ── Computed metrics ──
  const totalAR = DEMO_AR_BUCKETS.reduce((s, b) => s + b.amount, 0);
  const maxBucketAmount = Math.max(...DEMO_AR_BUCKETS.map((b) => b.amount));
  const totalLeakage = integrityFindings.reduce((s, f) => s + f.impact, 0);
  const maxDenialCount = Math.max(...DEMO_DENIAL_TRENDS.map((d) => d.count));

  const TABS: { key: TabKey; label: string }[] = [
    { key: "claims", label: "Claims & Billing" },
    { key: "denials", label: "Denial Management" },
    { key: "integrity", label: "Revenue Integrity" },
    { key: "payments", label: "Payments & AR" },
  ];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Revenue Cycle Management</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">End-to-end claims lifecycle, denial recovery, and revenue integrity intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-medium text-emerald-700">Revenue Healthy</span>
          </div>
          <button
            onClick={handleRunIntegrityScan}
            disabled={scanRunning}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
          >
            {scanRunning ? (
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" /><path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4" strokeLinecap="round" className="opacity-75" /></svg>
                Scanning...
              </span>
            ) : "Run Integrity Scan"}
          </button>
        </div>
      </div>

      {/* ── Stats Bar ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 animate-fade-in-up">
        {[
          { label: "Net Revenue (MTD)", value: "$1,284,500", change: "+8.2%", positive: true },
          { label: "Clean Claim Rate", value: `${cleanClaimRate}%`, change: "+2.3%", positive: true },
          { label: "Denial Rate", value: "5.2%", change: "-1.8%", positive: true },
          { label: "Days in AR", value: "42.5", change: "-3.2 days", positive: true },
          { label: "Collection Rate", value: "96.2%", change: "+1.1%", positive: true },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{kpi.label}</p>
            <p className={`mt-2 font-bold text-gray-900 dark:text-gray-100 ${kpi.label === "Net Revenue (MTD)" ? "text-2xl" : "text-xl"}`}>{kpi.value}</p>
            <p className={`text-xs mt-1 font-medium ${kpi.positive ? "text-emerald-600" : "text-red-600"}`}>
              {kpi.change} vs last month
            </p>
          </div>
        ))}
      </div>

      {/* ── Tabs ── */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-6 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`whitespace-nowrap border-b-2 pb-3 text-sm font-medium transition-colors ${
                activeTab === t.key
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:border-gray-600"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ══════════════════ TAB 1: Claims & Billing ══════════════════ */}
      {activeTab === "claims" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Claims Table + Gauge side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Claims List */}
            <div className="lg:col-span-3 card overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Claims Pipeline</h2>
                <button onClick={() => setShowChargeForm(true)} className="rounded-lg border border-healthos-200 bg-healthos-50 px-3 py-1.5 text-xs font-medium text-healthos-700 hover:bg-healthos-100 transition-colors">
                  + Capture Charges
                </button>
              </div>
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-100">
                  <thead>
                    <tr className="bg-gray-50/50">
                      {["Claim ID", "Patient", "Procedure Codes", "Amount", "Payer", "Status", "Submitted", ""].map((h) => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {claims.map((c) => (
                      <tr key={c.id} className="hover:bg-gray-50/50 transition-colors">
                        <td className="px-4 py-3 text-sm font-semibold text-healthos-600">{c.id}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{c.patient}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {c.codes.map((code) => (
                              <span key={code} className="inline-flex rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-mono font-medium text-gray-700 dark:text-gray-300">
                                {code}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm font-semibold text-gray-900 dark:text-gray-100">${c.amount.toFixed(2)}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{c.payer}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[c.status] || "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"}`}>
                            {c.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{c.date}</td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => handleOptimizeClaim(c.id)}
                            disabled={optimizingClaim === c.id}
                            className="rounded-lg border border-healthos-200 px-3 py-1 text-xs font-medium text-healthos-700 hover:bg-healthos-50 disabled:opacity-50 transition-colors"
                          >
                            {optimizingClaim === c.id ? "Optimizing..." : "Optimize Claim"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            </div>

            {/* Clean Claim Rate Gauge */}
            <div className="card card-hover p-5 flex flex-col items-center justify-center gap-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Quality Indicator</h3>
              <CleanClaimGauge rate={cleanClaimRate} />
              <div className="w-full space-y-2 mt-2">
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>First Pass Rate</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">91.3%</span>
                </div>
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Rejection Rate</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">3.1%</span>
                </div>
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Avg Processing</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">4.2 days</span>
                </div>
              </div>
            </div>
          </div>

          {/* Capture Charges Form */}
          {showChargeForm && (
            <div className="card animate-fade-in-up">
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Capture Charges</h3>
                <button onClick={() => setShowChargeForm(false)} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
              </div>
              <form onSubmit={handleCaptureCharge} className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Patient Name</label>
                  <input required value={chargeForm.patient} onChange={(e) => setChargeForm({ ...chargeForm, patient: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Payer</label>
                  <select required value={chargeForm.payer} onChange={(e) => setChargeForm({ ...chargeForm, payer: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                    <option value="">Select Payer</option>
                    {["Blue Cross", "Aetna", "UnitedHealth", "Medicare", "Cigna", "Medicaid"].map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">CPT Codes</label>
                  <input required value={chargeForm.codes} onChange={(e) => setChargeForm({ ...chargeForm, codes: e.target.value })} placeholder="99214, 80048" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Amount ($)</label>
                  <input required type="number" step="0.01" value={chargeForm.amount} onChange={(e) => setChargeForm({ ...chargeForm, amount: e.target.value })} placeholder="425.00" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Diagnosis (ICD-10)</label>
                  <input value={chargeForm.diagnosis} onChange={(e) => setChargeForm({ ...chargeForm, diagnosis: e.target.value })} placeholder="E11.9" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div className="flex items-end">
                  <button type="submit" disabled={submittingCharge} className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors">
                    {submittingCharge ? "Submitting..." : "Submit Charges"}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════ TAB 2: Denial Management ══════════════════ */}
      {activeTab === "denials" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Summary banner */}
          <div className="card border-red-200 bg-red-50 p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-red-100 p-2">
                <svg className="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              </div>
              <div>
                <p className="text-sm font-semibold text-red-800">{denials.length} active denials totaling {formatCurrency(denials.reduce((s, d) => s + d.amount, 0))}</p>
                <p className="text-xs text-red-600 mt-0.5">AI analysis available for root cause identification and automated appeal generation</p>
              </div>
            </div>
          </div>

          {/* Denial cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {denials.map((d) => (
              <div key={d.id} className="card card-hover p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`h-3 w-3 rounded-full ${SEVERITY_COLORS[d.severity]}`} title={`${d.severity} severity`} />
                    <div>
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{d.id} <span className="text-gray-500 dark:text-gray-400 font-normal">/ {d.claimId}</span></p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{d.date}</p>
                    </div>
                  </div>
                  <span className="text-base font-bold text-red-600">{formatCurrency(d.amount)}</span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">{d.reason}</p>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${CATEGORY_COLORS[d.category]}`}>
                    {CATEGORY_LABELS[d.category]}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">{d.payer}</span>
                </div>

                {/* AI Analysis result */}
                {denialAnalysis[d.id] && (
                  <div className="mt-3 rounded-lg border border-healthos-200 bg-healthos-50/50 p-4 space-y-2 animate-fade-in-up">
                    <p className="text-xs font-semibold text-healthos-700 uppercase tracking-wide">AI Root Cause Analysis</p>
                    <p className="text-sm text-gray-800 dark:text-gray-200">{denialAnalysis[d.id].rootCause}</p>
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mt-2">Insights:</p>
                      {denialAnalysis[d.id].aiInsights.map((insight, i) => (
                        <p key={i} className="text-xs text-gray-600 dark:text-gray-400 flex gap-2">
                          <span className="text-healthos-500 mt-0.5 shrink-0">&#9656;</span>
                          {insight}
                        </p>
                      ))}
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-2"><span className="font-semibold">Recommended:</span> {denialAnalysis[d.id].recommendedAction}</p>
                  </div>
                )}

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => handleAnalyzeDenial(d.id, d.claimId)}
                    disabled={analyzingDenial === d.id}
                    className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
                  >
                    {analyzingDenial === d.id ? (
                      <span className="flex items-center gap-1">
                        <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" /><path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4" strokeLinecap="round" className="opacity-75" /></svg>
                        Analyzing...
                      </span>
                    ) : "Analyze"}
                  </button>
                  <button
                    onClick={() => handleGenerateAppeal(d.id)}
                    disabled={appealingDenial === d.id}
                    className="rounded-lg bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-700 disabled:opacity-50 transition-colors"
                  >
                    {appealingDenial === d.id ? "Generating..." : "Generate Appeal"}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Denial Trends */}
          <div className="card p-5">
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Top Denial Reasons</h3>
            <div className="space-y-3">
              {DEMO_DENIAL_TRENDS.map((t) => (
                <div key={t.reason} className="flex items-center gap-4">
                  <span className="w-36 text-sm text-gray-700 dark:text-gray-300 shrink-0">{t.reason}</span>
                  <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${t.color} rounded-full transition-all duration-700 flex items-center justify-end pr-2`}
                      style={{ width: `${(t.count / maxDenialCount) * 100}%` }}
                    >
                      <span className="text-xs font-semibold text-white">{t.count}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════ TAB 3: Revenue Integrity ══════════════════ */}
      {activeTab === "integrity" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Summary metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card card-hover p-5 text-center">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total Leakage Identified</p>
              <p className="mt-2 text-2xl font-bold text-orange-600">{formatCurrency(totalLeakage)}</p>
            </div>
            <div className="card card-hover p-5 text-center">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Opportunities Found</p>
              <p className="mt-2 text-2xl font-bold text-healthos-600">{integrityFindings.length}</p>
            </div>
            <div className="card card-hover p-5 text-center">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Estimated Recovery</p>
              <p className="mt-2 text-2xl font-bold text-emerald-600">{formatCurrency(Math.round(totalLeakage * 0.82))}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">82% projected recovery rate</p>
            </div>
          </div>

          {/* Scan status */}
          {scanRunning && (
            <div className="card border-healthos-200 bg-healthos-50 p-4 animate-fade-in-up">
              <div className="flex items-center gap-3">
                <svg className="h-5 w-5 text-healthos-600 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" /><path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4" strokeLinecap="round" className="opacity-75" /></svg>
                <p className="text-sm font-medium text-healthos-800">Running integrity scan... Analyzing HCC gaps, coding opportunities, and revenue leakage</p>
              </div>
            </div>
          )}

          {scanComplete && !scanRunning && (
            <div className="card border-emerald-200 bg-emerald-50 p-4">
              <p className="text-sm font-medium text-emerald-800">Scan complete. {integrityFindings.length} findings identified with {formatCurrency(totalLeakage)} in potential recovery.</p>
            </div>
          )}

          {/* Findings cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {integrityFindings.map((f) => (
              <div key={f.id} className="card card-hover p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      f.type === "HCC Gap" ? "bg-purple-100 text-purple-700" :
                      f.type === "Coding Opportunity" ? "bg-blue-100 text-blue-700" :
                      "bg-orange-100 text-orange-700"
                    }`}>
                      {f.type}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{f.id}</p>
                  </div>
                  <p className="text-lg font-bold text-orange-600">{formatCurrency(f.impact)}</p>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">{f.description}</p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 dark:text-gray-400">Confidence:</span>
                    <div className="w-24 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${f.confidence >= 90 ? "bg-emerald-500" : f.confidence >= 80 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${f.confidence}%` }} />
                    </div>
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{f.confidence}%</span>
                  </div>
                  <button
                    onClick={() => {
                      try { verifyRevenueIntegrity({ finding_id: f.id, action: "resolve" }); } catch { /* demo */ }
                    }}
                    className="rounded-lg bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700 transition-colors"
                  >
                    Action
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Run scan button */}
          <div className="flex justify-center">
            <button
              onClick={handleRunIntegrityScan}
              disabled={scanRunning}
              className="rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 px-6 py-3 text-sm font-medium text-gray-600 dark:text-gray-400 hover:border-healthos-400 hover:text-healthos-600 disabled:opacity-50 transition-colors"
            >
              {scanRunning ? "Scan in Progress..." : "Run New Integrity Scan"}
            </button>
          </div>
        </div>
      )}

      {/* ══════════════════ TAB 4: Payments & AR ══════════════════ */}
      {activeTab === "payments" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Collections summary */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card card-hover p-5">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total Outstanding</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">{formatCurrency(totalAR)}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">493 open claims</p>
            </div>
            <div className="card card-hover p-5">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Collected This Month</p>
              <p className="mt-2 text-2xl font-bold text-emerald-600">{formatCurrency(428000)}</p>
              <p className="text-xs text-emerald-500 mt-1">+5.7% vs last month</p>
            </div>
            <div className="card card-hover p-5">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Aging Trend</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">42.5 days</p>
              <p className="text-xs text-emerald-500 mt-1">-3.2 days improvement</p>
            </div>
          </div>

          {/* AR Aging Buckets Visualization */}
          <div className="card p-5">
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-6">Accounts Receivable Aging</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {DEMO_AR_BUCKETS.map((bucket) => (
                <div key={bucket.label} className="flex flex-col items-center">
                  {/* Column */}
                  <div className="w-full h-48 bg-gray-50 dark:bg-gray-800 rounded-t-lg relative flex items-end justify-center overflow-hidden">
                    <div
                      className={`w-full ${bucket.color} rounded-t-lg transition-all duration-700 flex items-center justify-center`}
                      style={{ height: `${(bucket.amount / maxBucketAmount) * 100}%` }}
                    >
                      <span className="text-xs font-bold text-white">{formatCurrency(bucket.amount)}</span>
                    </div>
                  </div>
                  {/* Label */}
                  <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-b-lg p-2 text-center">
                    <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">{bucket.label}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{bucket.claims} claims</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Payment Posting + Reconciliation */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Payment Posting Form */}
            <div className="card p-5">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Post Payment</h3>
              <form onSubmit={handlePostPayment} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Claim ID</label>
                  <input required value={paymentForm.claimId} onChange={(e) => setPaymentForm({ ...paymentForm, claimId: e.target.value })} placeholder="CLM-8920" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Amount ($)</label>
                  <input required type="number" step="0.01" value={paymentForm.amount} onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })} placeholder="285.50" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Payment Method</label>
                  <select value={paymentForm.method} onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                    <option value="eft">EFT</option>
                    <option value="check">Check</option>
                    <option value="credit_card">Credit Card</option>
                    <option value="cash">Cash</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Reference Number</label>
                  <input value={paymentForm.reference} onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })} placeholder="EFT-20260315-001" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <button type="submit" disabled={postingPayment} className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors">
                  {postingPayment ? "Posting..." : "Post Payment"}
                </button>
              </form>
            </div>

            {/* Reconciliation Status */}
            <div className="card p-5">
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">Reconciliation Status</h3>
              <div className="space-y-4">
                {[
                  { payer: "Blue Cross", posted: 45200, expected: 48600, status: "partial" },
                  { payer: "Aetna", posted: 32100, expected: 32100, status: "reconciled" },
                  { payer: "UnitedHealth", posted: 28400, expected: 31200, status: "partial" },
                  { payer: "Medicare", posted: 52800, expected: 52800, status: "reconciled" },
                  { payer: "Cigna", posted: 18900, expected: 22400, status: "pending" },
                ].map((r) => (
                  <div key={r.payer} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{r.payer}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{formatCurrency(r.posted)} / {formatCurrency(r.expected)}</p>
                    </div>
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      r.status === "reconciled" ? "bg-green-100 text-green-700" :
                      r.status === "partial" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                    }`}>
                      {r.status}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Overall Match Rate</p>
                  <p className="text-sm font-bold text-healthos-600">94.7%</p>
                </div>
                <div className="mt-2 h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-healthos-500 rounded-full" style={{ width: "94.7%" }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
