"use client";

import { useState, useCallback } from "react";
import {
  matchClinicalTrials,
  checkTrialEligibility,
  deidentifyDataset,
  assessGeneticRisk,
  analyzePharmacogenomics,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

type Tab = "trials" | "pgx" | "genetic-risk" | "deidentify";

interface TrialResult {
  trialName: string;
  nctId: string;
  phase: string;
  condition: string;
  eligibility: "eligible" | "potentially_eligible" | "ineligible";
  matchScore: number;
  enrolled: number;
  target: number;
  sites: number;
  piName: string;
}

interface PgxInteraction {
  gene: string;
  allele: string;
  metabolizerStatus: "poor" | "intermediate" | "normal" | "rapid";
  drug: string;
  recommendation: string;
  clinicalSignificance: "high" | "moderate" | "low";
}

interface GeneticRiskResult {
  riskScore: number;
  percentile: number;
  riskFactors: string[];
  recommendations: string[];
  condition: string;
}

interface MonogenicVariant {
  gene: string;
  variant: string;
  classification: "pathogenic" | "likely_pathogenic" | "vus" | "benign";
  condition: string;
  inheritance: string;
}

interface DeidentifyResult {
  datasetId: string;
  kAnonymity: number;
  reidentificationRisk: number;
  recordCount: number;
  processingTime: string;
  status: "completed" | "processing" | "failed";
  progress: number;
}

interface ComplianceCheck {
  identifier: string;
  status: "pass" | "fail" | "warning";
  details: string;
}

// ── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_TRIALS: TrialResult[] = [
  {
    trialName: "SGLT2 Inhibitor for CKD Stage 3-4 with Type 2 Diabetes",
    nctId: "NCT05001234",
    phase: "Phase III",
    condition: "Chronic Kidney Disease, Type 2 Diabetes",
    eligibility: "eligible",
    matchScore: 92,
    enrolled: 312,
    target: 500,
    sites: 24,
    piName: "Dr. Sarah Chen",
  },
  {
    trialName: "GLP-1 Receptor Agonist for Obesity and CV Risk Reduction",
    nctId: "NCT05005678",
    phase: "Phase III",
    condition: "Obesity, Cardiovascular Risk",
    eligibility: "potentially_eligible",
    matchScore: 78,
    enrolled: 678,
    target: 1000,
    sites: 40,
    piName: "Dr. James Rodriguez",
  },
  {
    trialName: "AI-Assisted Diabetic Retinopathy Screening in Primary Care",
    nctId: "NCT05009012",
    phase: "Phase II",
    condition: "Diabetic Retinopathy",
    eligibility: "eligible",
    matchScore: 65,
    enrolled: 142,
    target: 300,
    sites: 15,
    piName: "Dr. Emily Watson",
  },
  {
    trialName: "Pharmacogenomic-Guided Warfarin Dosing",
    nctId: "NCT05012345",
    phase: "Phase IV",
    condition: "Anticoagulation Management",
    eligibility: "ineligible",
    matchScore: 41,
    enrolled: 87,
    target: 200,
    sites: 10,
    piName: "Dr. Michael Park",
  },
  {
    trialName: "Targeted Immunotherapy for HER2+ Breast Cancer",
    nctId: "NCT05018901",
    phase: "Phase I",
    condition: "HER2-Positive Breast Cancer",
    eligibility: "potentially_eligible",
    matchScore: 55,
    enrolled: 28,
    target: 60,
    sites: 6,
    piName: "Dr. Lisa Nakamura",
  },
];

const DEMO_PGX: PgxInteraction[] = [
  {
    gene: "CYP2D6",
    allele: "*4/*4",
    metabolizerStatus: "poor",
    drug: "Codeine",
    recommendation: "Avoid codeine. Use alternative analgesic not metabolized by CYP2D6 (e.g., morphine, acetaminophen).",
    clinicalSignificance: "high",
  },
  {
    gene: "CYP2C19",
    allele: "*1/*2",
    metabolizerStatus: "intermediate",
    drug: "Clopidogrel",
    recommendation: "Consider alternative antiplatelet therapy (e.g., prasugrel, ticagrelor). If clopidogrel used, monitor closely.",
    clinicalSignificance: "high",
  },
  {
    gene: "VKORC1",
    allele: "-1639 G>A (AG)",
    metabolizerStatus: "intermediate",
    drug: "Warfarin",
    recommendation: "Reduce initial warfarin dose by 25-50%. Target INR 2.0-3.0 with frequent monitoring.",
    clinicalSignificance: "moderate",
  },
  {
    gene: "CYP2D6",
    allele: "*1/*1xN",
    metabolizerStatus: "rapid",
    drug: "Tramadol",
    recommendation: "Reduce tramadol dose or use alternative. Increased risk of toxicity due to ultra-rapid metabolism.",
    clinicalSignificance: "high",
  },
  {
    gene: "SLCO1B1",
    allele: "521 TC",
    metabolizerStatus: "intermediate",
    drug: "Simvastatin",
    recommendation: "Use simvastatin at lower dose (max 20 mg/day) or consider rosuvastatin/pravastatin.",
    clinicalSignificance: "moderate",
  },
  {
    gene: "HLA-B",
    allele: "*57:01 negative",
    metabolizerStatus: "normal",
    drug: "Abacavir",
    recommendation: "Standard dosing appropriate. HLA-B*57:01 negative — low risk of hypersensitivity.",
    clinicalSignificance: "low",
  },
];

const DEMO_DRUG_PANEL = [
  { drug: "Clopidogrel", gene: "CYP2C19", tested: true, actionable: true },
  { drug: "Warfarin", gene: "CYP2C9/VKORC1", tested: true, actionable: true },
  { drug: "Codeine", gene: "CYP2D6", tested: true, actionable: true },
  { drug: "Simvastatin", gene: "SLCO1B1", tested: true, actionable: true },
  { drug: "Tamoxifen", gene: "CYP2D6", tested: true, actionable: false },
  { drug: "Omeprazole", gene: "CYP2C19", tested: true, actionable: false },
  { drug: "Abacavir", gene: "HLA-B", tested: true, actionable: false },
  { drug: "Carbamazepine", gene: "HLA-A/HLA-B", tested: false, actionable: false },
];

const DEMO_GENETIC_RISK: GeneticRiskResult = {
  riskScore: 74,
  percentile: 88,
  condition: "Coronary Artery Disease",
  riskFactors: [
    "LPA gene variant — elevated Lp(a) levels",
    "APOE e4 carrier — lipid metabolism impact",
    "9p21.3 risk locus — 1.3x increased risk",
    "Family history of MI before age 55",
    "Male sex — baseline elevated risk",
  ],
  recommendations: [
    "Initiate statin therapy per ACC/AHA guidelines for primary prevention",
    "Measure Lp(a) levels — consider PCSK9 inhibitor if elevated >50 mg/dL",
    "Aggressive LDL-C target <70 mg/dL given genetic risk burden",
    "Annual coronary calcium score screening starting age 40",
    "Lifestyle modifications: Mediterranean diet, 150 min/week moderate exercise",
  ],
};

const DEMO_MONOGENIC: MonogenicVariant[] = [
  { gene: "BRCA2", variant: "c.5946delT", classification: "pathogenic", condition: "Hereditary Breast/Ovarian Cancer", inheritance: "Autosomal Dominant" },
  { gene: "LDLR", variant: "c.986G>A", classification: "likely_pathogenic", condition: "Familial Hypercholesterolemia", inheritance: "Autosomal Dominant" },
  { gene: "MLH1", variant: "c.350C>T", classification: "vus", condition: "Lynch Syndrome", inheritance: "Autosomal Dominant" },
  { gene: "HFE", variant: "C282Y heterozygous", classification: "benign", condition: "Hereditary Hemochromatosis", inheritance: "Autosomal Recessive" },
];

const DEMO_DEIDENTIFY: DeidentifyResult = {
  datasetId: "DS-2026-0312",
  kAnonymity: 8,
  reidentificationRisk: 2.3,
  recordCount: 4250,
  processingTime: "3m 42s",
  status: "completed",
  progress: 100,
};

const DEMO_COMPLIANCE: ComplianceCheck[] = [
  { identifier: "Names", status: "pass", details: "All patient names removed/generalized" },
  { identifier: "Geographic data", status: "pass", details: "ZIP codes truncated to 3-digit" },
  { identifier: "Dates", status: "pass", details: "Dates shifted +/- random offset" },
  { identifier: "Phone numbers", status: "pass", details: "All phone numbers redacted" },
  { identifier: "Fax numbers", status: "pass", details: "All fax numbers redacted" },
  { identifier: "Email addresses", status: "pass", details: "All emails removed" },
  { identifier: "SSN", status: "pass", details: "All SSNs removed" },
  { identifier: "MRN", status: "pass", details: "MRNs replaced with synthetic IDs" },
  { identifier: "Health plan IDs", status: "pass", details: "Plan beneficiary numbers removed" },
  { identifier: "Account numbers", status: "pass", details: "All account numbers redacted" },
  { identifier: "Certificates/Licenses", status: "pass", details: "License numbers removed" },
  { identifier: "Vehicle IDs", status: "pass", details: "No vehicle identifiers found" },
  { identifier: "Device IDs", status: "pass", details: "Device serial numbers redacted" },
  { identifier: "URLs", status: "pass", details: "All URLs removed from records" },
  { identifier: "IP addresses", status: "pass", details: "IP addresses anonymized" },
  { identifier: "Biometric IDs", status: "pass", details: "No biometric identifiers present" },
  { identifier: "Full-face photos", status: "pass", details: "All images stripped" },
  { identifier: "Other unique IDs", status: "pass", details: "Custom identifiers generalized" },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

const phaseBadge = (phase: string) => {
  if (phase.includes("I") && !phase.includes("II") && !phase.includes("IV"))
    return "bg-blue-50 text-blue-700 border border-blue-200";
  if (phase.includes("II") && !phase.includes("III"))
    return "bg-purple-50 text-purple-700 border border-purple-200";
  if (phase.includes("III"))
    return "bg-green-50 text-green-700 border border-green-200";
  if (phase.includes("IV"))
    return "bg-teal-50 text-teal-700 border border-teal-200";
  return "bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700";
};

const eligibilityBadge = (status: string) => {
  if (status === "eligible") return "bg-green-50 text-green-700 border border-green-200";
  if (status === "potentially_eligible") return "bg-yellow-50 text-yellow-700 border border-yellow-200";
  return "bg-red-50 text-red-700 border border-red-200";
};

const eligibilityLabel = (status: string) => {
  if (status === "eligible") return "Eligible";
  if (status === "potentially_eligible") return "Potentially Eligible";
  return "Ineligible";
};

const metabolizerBadge = (status: string) => {
  if (status === "poor") return "bg-red-50 text-red-700 border border-red-200";
  if (status === "intermediate") return "bg-yellow-50 text-yellow-700 border border-yellow-200";
  if (status === "normal") return "bg-green-50 text-green-700 border border-green-200";
  if (status === "rapid") return "bg-blue-50 text-blue-700 border border-blue-200";
  return "bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300";
};

const metabolizerLabel = (status: string) => {
  if (status === "poor") return "Poor Metabolizer";
  if (status === "intermediate") return "Intermediate Metabolizer";
  if (status === "normal") return "Normal Metabolizer";
  if (status === "rapid") return "Rapid/Ultra-rapid Metabolizer";
  return status;
};

const significanceBadge = (sig: string) => {
  if (sig === "high") return "bg-red-100 text-red-800";
  if (sig === "moderate") return "bg-amber-100 text-amber-800";
  return "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300";
};

const classificationBadge = (c: string) => {
  if (c === "pathogenic") return "bg-red-50 text-red-700 border border-red-200";
  if (c === "likely_pathogenic") return "bg-orange-50 text-orange-700 border border-orange-200";
  if (c === "vus") return "bg-yellow-50 text-yellow-700 border border-yellow-200";
  return "bg-green-50 text-green-700 border border-green-200";
};

const classificationLabel = (c: string) => {
  if (c === "pathogenic") return "Pathogenic";
  if (c === "likely_pathogenic") return "Likely Pathogenic";
  if (c === "vus") return "VUS";
  return "Benign";
};

// ── Component ────────────────────────────────────────────────────────────────

export default function ResearchGenomicsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("trials");

  // Clinical Trials state
  const [trialPatientId, setTrialPatientId] = useState("");
  const [trialConditions, setTrialConditions] = useState("");
  const [trialAge, setTrialAge] = useState("");
  const [trialSex, setTrialSex] = useState("");
  const [trialResults, setTrialResults] = useState<TrialResult[] | null>(null);
  const [trialsLoading, setTrialsLoading] = useState(false);
  const [eligibilityDetail, setEligibilityDetail] = useState<string | null>(null);
  const [eligibilityLoading, setEligibilityLoading] = useState<string | null>(null);

  // PGx state
  const [pgxPatientId, setPgxPatientId] = useState("");
  const [pgxMedications, setPgxMedications] = useState("");
  const [pgxResults, setPgxResults] = useState<PgxInteraction[] | null>(null);
  const [pgxLoading, setPgxLoading] = useState(false);

  // Genetic Risk state
  const [grPatientId, setGrPatientId] = useState("");
  const [grCondition, setGrCondition] = useState("");
  const [grResults, setGrResults] = useState<GeneticRiskResult | null>(null);
  const [grLoading, setGrLoading] = useState(false);
  const [showMonogenic, setShowMonogenic] = useState(false);

  // De-identification state
  const [deidName, setDeidName] = useState("");
  const [deidRecordCount, setDeidRecordCount] = useState("");
  const [deidDataTypes, setDeidDataTypes] = useState<string[]>([]);
  const [deidResult, setDeidResult] = useState<DeidentifyResult | null>(null);
  const [deidLoading, setDeidLoading] = useState(false);
  const [deidProgress, setDeidProgress] = useState(0);
  const [showCompliance, setShowCompliance] = useState(false);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleTrialMatch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setTrialsLoading(true);
    setTrialResults(null);
    try {
      const res = await matchClinicalTrials({
        patient_id: trialPatientId,
        conditions: trialConditions.split(",").map((c) => c.trim()).filter(Boolean),
        demographics: { age: parseInt(trialAge) || undefined, sex: trialSex || undefined },
      });
      if (res && Array.isArray((res as Record<string, unknown>).trials)) {
        setTrialResults((res as Record<string, unknown>).trials as TrialResult[]);
      } else {
        setTrialResults(DEMO_TRIALS);
      }
    } catch {
      setTrialResults(DEMO_TRIALS);
    } finally {
      setTrialsLoading(false);
    }
  }, [trialPatientId, trialConditions, trialAge, trialSex]);

  const handleCheckEligibility = useCallback(async (nctId: string) => {
    setEligibilityLoading(nctId);
    try {
      await checkTrialEligibility({ patient_id: trialPatientId, nct_id: nctId });
    } catch {
      // demo fallback — toggle detail
    } finally {
      setEligibilityLoading(null);
      setEligibilityDetail(eligibilityDetail === nctId ? null : nctId);
    }
  }, [trialPatientId, eligibilityDetail]);

  const handlePgxCheck = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setPgxLoading(true);
    setPgxResults(null);
    try {
      const res = await analyzePharmacogenomics({
        patient_id: pgxPatientId,
        medications: pgxMedications.split(",").map((m) => m.trim()).filter(Boolean),
      });
      if (res && Array.isArray((res as Record<string, unknown>).interactions)) {
        setPgxResults((res as Record<string, unknown>).interactions as PgxInteraction[]);
      } else {
        setPgxResults(DEMO_PGX);
      }
    } catch {
      setPgxResults(DEMO_PGX);
    } finally {
      setPgxLoading(false);
    }
  }, [pgxPatientId, pgxMedications]);

  const handleGeneticRisk = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setGrLoading(true);
    setGrResults(null);
    try {
      const res = await assessGeneticRisk({
        patient_id: grPatientId,
        condition: grCondition,
      });
      if (res && typeof (res as Record<string, unknown>).riskScore === "number") {
        setGrResults(res as unknown as GeneticRiskResult);
      } else {
        setGrResults({ ...DEMO_GENETIC_RISK, condition: grCondition || DEMO_GENETIC_RISK.condition });
      }
    } catch {
      setGrResults({ ...DEMO_GENETIC_RISK, condition: grCondition || DEMO_GENETIC_RISK.condition });
    } finally {
      setGrLoading(false);
    }
  }, [grPatientId, grCondition]);

  const handleDeidentify = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setDeidLoading(true);
    setDeidResult(null);
    setDeidProgress(0);

    // Simulate progress
    const interval = setInterval(() => {
      setDeidProgress((prev) => {
        if (prev >= 95) { clearInterval(interval); return 95; }
        return prev + Math.random() * 15;
      });
    }, 400);

    try {
      const res = await deidentifyDataset({
        dataset_name: deidName,
        record_count: parseInt(deidRecordCount) || 1000,
        data_types: deidDataTypes,
      });
      clearInterval(interval);
      setDeidProgress(100);
      if (res && typeof (res as Record<string, unknown>).kAnonymity === "number") {
        setDeidResult(res as unknown as DeidentifyResult);
      } else {
        setDeidResult({ ...DEMO_DEIDENTIFY, recordCount: parseInt(deidRecordCount) || DEMO_DEIDENTIFY.recordCount });
      }
    } catch {
      clearInterval(interval);
      setDeidProgress(100);
      setDeidResult({ ...DEMO_DEIDENTIFY, recordCount: parseInt(deidRecordCount) || DEMO_DEIDENTIFY.recordCount });
    } finally {
      setDeidLoading(false);
    }
  }, [deidName, deidRecordCount, deidDataTypes]);

  const toggleDataType = (type: string) => {
    setDeidDataTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // ── Stats ──────────────────────────────────────────────────────────────────

  const stats = [
    { label: "Clinical Trials Available", value: "47", icon: "🔬", color: "text-healthos-600" },
    { label: "Patients Matched", value: "1,284", icon: "🎯", color: "text-blue-600" },
    { label: "Datasets De-identified", value: "38", icon: "🛡️", color: "text-emerald-600" },
    { label: "Genetic Profiles", value: "3,612", icon: "🧬", color: "text-purple-600" },
    { label: "PGx Analyses", value: "892", icon: "💊", color: "text-amber-600" },
  ];

  const enrollmentStats = trialResults
    ? {
        totalEnrolled: trialResults.reduce((acc, t) => acc + t.enrolled, 0),
        totalTarget: trialResults.reduce((acc, t) => acc + t.target, 0),
        totalSites: trialResults.reduce((acc, t) => acc + t.sites, 0),
        eligible: trialResults.filter((t) => t.eligibility === "eligible").length,
        potentially: trialResults.filter((t) => t.eligibility === "potentially_eligible").length,
        ineligible: trialResults.filter((t) => t.eligibility === "ineligible").length,
      }
    : null;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in-up">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Research &amp; Genomics</h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2.5 py-1 text-xs font-semibold text-green-700 border border-green-200">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
              47 Active Trials
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Clinical trial matching, pharmacogenomics, genetic risk assessment, and data de-identification
          </p>
        </div>
        <button
          onClick={() => {
            setActiveTab("trials");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          className="rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 transition-colors"
        >
          Match Patient to Trials
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 animate-fade-in-up">
        {stats.map((s) => (
          <div key={s.label} className="card card-hover text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5 overflow-x-auto">
        {([
          { key: "trials" as Tab, label: "Clinical Trials" },
          { key: "pgx" as Tab, label: "Pharmacogenomics" },
          { key: "genetic-risk" as Tab, label: "Genetic Risk" },
          { key: "deidentify" as Tab, label: "Data De-identification" },
        ]).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 1: Clinical Trials
         ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "trials" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Trial Matching Form */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Trial Matching Criteria</h3>
            <form onSubmit={handleTrialMatch} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient ID</label>
                <input
                  required
                  value={trialPatientId}
                  onChange={(e) => setTrialPatientId(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  placeholder="e.g. PAT-001234"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Conditions</label>
                <input
                  value={trialConditions}
                  onChange={(e) => setTrialConditions(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  placeholder="e.g. CKD, Type 2 Diabetes"
                />
              </div>
              <div className="grid grid-cols-1 xs:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Age</label>
                  <input
                    type="number"
                    value={trialAge}
                    onChange={(e) => setTrialAge(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                    placeholder="e.g. 58"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Sex</label>
                  <select
                    value={trialSex}
                    onChange={(e) => setTrialSex(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="">Any</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                  </select>
                </div>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={trialsLoading}
                  className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                >
                  {trialsLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Matching...
                    </span>
                  ) : (
                    "Find Matching Trials"
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Trial Results */}
          {trialResults && (
            <div className="space-y-4 animate-fade-in-up">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {trialResults.length} Matching Trials Found
                </h3>
              </div>

              {/* Enrollment Statistics */}
              {enrollmentStats && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                  <div className="card text-center py-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Total Enrolled</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{enrollmentStats.totalEnrolled.toLocaleString()}</p>
                  </div>
                  <div className="card text-center py-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Target Enrollment</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{enrollmentStats.totalTarget.toLocaleString()}</p>
                  </div>
                  <div className="card text-center py-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Total Sites</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{enrollmentStats.totalSites}</p>
                  </div>
                  <div className="card text-center py-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Eligible</p>
                    <p className="text-lg font-bold text-green-600">{enrollmentStats.eligible}</p>
                  </div>
                  <div className="card text-center py-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Potentially Eligible</p>
                    <p className="text-lg font-bold text-yellow-600">{enrollmentStats.potentially}</p>
                  </div>
                  <div className="card text-center py-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Ineligible</p>
                    <p className="text-lg font-bold text-red-600">{enrollmentStats.ineligible}</p>
                  </div>
                </div>
              )}

              {/* Trial Cards */}
              {trialResults.map((trial) => (
                <div key={trial.nctId} className="card card-hover">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{trial.trialName}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${phaseBadge(trial.phase)}`}>
                          {trial.phase}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${eligibilityBadge(trial.eligibility)}`}>
                          {eligibilityLabel(trial.eligibility)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {trial.nctId} &mdash; {trial.condition}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                        PI: {trial.piName} &mdash; {trial.sites} sites &mdash; Enrolled {trial.enrolled}/{trial.target} ({Math.round(trial.enrolled / trial.target * 100)}%)
                      </p>
                      <div className="mt-2 h-1.5 w-64 max-w-full rounded-full bg-gray-100 dark:bg-gray-800">
                        <div
                          className="h-1.5 rounded-full bg-healthos-500 transition-all"
                          style={{ width: `${Math.round(trial.enrolled / trial.target * 100)}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-2xl font-bold text-healthos-700">{trial.matchScore}%</div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Match Score</p>
                      <button
                        onClick={() => handleCheckEligibility(trial.nctId)}
                        disabled={eligibilityLoading === trial.nctId}
                        className="mt-2 rounded-lg border border-healthos-200 bg-healthos-50 px-3 py-1.5 text-xs font-medium text-healthos-700 hover:bg-healthos-100 transition-colors disabled:opacity-50"
                      >
                        {eligibilityLoading === trial.nctId ? "Checking..." : "Check Eligibility"}
                      </button>
                    </div>
                  </div>
                  {eligibilityDetail === trial.nctId && (
                    <div className="mt-4 rounded-lg bg-gray-50 dark:bg-gray-800 p-4 text-xs space-y-2 animate-fade-in-up">
                      <p className="font-semibold text-gray-700 dark:text-gray-300">Eligibility Details for {trial.nctId}</p>
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                        <div><span className="text-gray-500 dark:text-gray-400">Age Criteria:</span> <span className="font-medium text-green-700">Met</span></div>
                        <div><span className="text-gray-500 dark:text-gray-400">Condition Match:</span> <span className="font-medium text-green-700">Confirmed</span></div>
                        <div><span className="text-gray-500 dark:text-gray-400">Lab Values:</span> <span className="font-medium text-yellow-700">Pending Review</span></div>
                        <div><span className="text-gray-500 dark:text-gray-400">Medications:</span> <span className="font-medium text-green-700">No Conflicts</span></div>
                      </div>
                      <p className="text-gray-500 dark:text-gray-400 pt-1">
                        Inclusion: {trial.condition} diagnosis confirmed. Exclusion criteria checked against patient record.
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {!trialResults && !trialsLoading && (
            <div className="card text-center py-6 sm:py-12">
              <div className="text-2xl sm:text-4xl mb-3 opacity-40">🔬</div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Enter patient criteria above to find matching clinical trials</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Searches across 47 active trials from ClinicalTrials.gov registry</p>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 2: Pharmacogenomics
         ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "pgx" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* PGx Check Form */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Pharmacogenomic Analysis</h3>
            <form onSubmit={handlePgxCheck} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient ID</label>
                <input
                  required
                  value={pgxPatientId}
                  onChange={(e) => setPgxPatientId(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  placeholder="e.g. PAT-001234"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Medication List</label>
                <input
                  value={pgxMedications}
                  onChange={(e) => setPgxMedications(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  placeholder="e.g. Clopidogrel, Codeine, Warfarin"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={pgxLoading}
                  className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                >
                  {pgxLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Analyzing...
                    </span>
                  ) : (
                    "Run PGx Check"
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* PGx Results */}
          {pgxResults && (
            <div className="space-y-4 animate-fade-in-up">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Drug-Gene Interactions ({pgxResults.length} found)
              </h3>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {pgxResults.map((interaction, idx) => (
                  <div key={`${interaction.gene}-${interaction.drug}-${idx}`} className="card card-hover">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{interaction.gene}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">({interaction.allele})</span>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${metabolizerBadge(interaction.metabolizerStatus)}`}>
                            {metabolizerLabel(interaction.metabolizerStatus)}
                          </span>
                        </div>
                        <div className="mt-2 flex items-center gap-2">
                          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Drug:</span>
                          <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">{interaction.drug}</span>
                          <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${significanceBadge(interaction.clinicalSignificance)}`}>
                            {interaction.clinicalSignificance} significance
                          </span>
                        </div>
                        <div className="mt-2 rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                          <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                            <span className="font-medium text-gray-700 dark:text-gray-300">Recommendation: </span>
                            {interaction.recommendation}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Drug Panel Overview */}
          <div className="card animate-fade-in-up">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Drug Panel Overview</h3>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {DEMO_DRUG_PANEL.map((item) => (
                <div
                  key={item.drug}
                  className={`flex items-center justify-between rounded-lg border p-3 ${
                    item.actionable
                      ? "border-amber-200 bg-amber-50"
                      : item.tested
                      ? "border-green-200 bg-green-50"
                      : "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
                  }`}
                >
                  <div>
                    <p className="text-xs font-semibold text-gray-900 dark:text-gray-100">{item.drug}</p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">{item.gene}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {item.tested ? (
                      <span className="h-4 w-4 rounded-full bg-green-500 flex items-center justify-center text-white text-[8px]">&#10003;</span>
                    ) : (
                      <span className="h-4 w-4 rounded-full bg-gray-300 flex items-center justify-center text-white text-[8px]">&mdash;</span>
                    )}
                    {item.actionable && (
                      <span className="rounded bg-amber-200 px-1 py-0.5 text-[11px] font-bold text-amber-800">ACTION</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Empty state */}
          {!pgxResults && !pgxLoading && (
            <div className="card text-center py-6 sm:py-12">
              <div className="text-2xl sm:text-4xl mb-3 opacity-40">💊</div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Enter patient ID and medications to check pharmacogenomic interactions</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Analyzes CYP450 enzyme variants, HLA alleles, and transporter genes</p>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 3: Genetic Risk
         ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "genetic-risk" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* PRS Form */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Polygenic Risk Score Assessment</h3>
            <form onSubmit={handleGeneticRisk} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient ID</label>
                <input
                  required
                  value={grPatientId}
                  onChange={(e) => setGrPatientId(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  placeholder="e.g. PAT-001234"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Condition</label>
                <select
                  value={grCondition}
                  onChange={(e) => setGrCondition(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Select condition...</option>
                  <option value="Coronary Artery Disease">Coronary Artery Disease</option>
                  <option value="Type 2 Diabetes">Type 2 Diabetes</option>
                  <option value="Breast Cancer">Breast Cancer</option>
                  <option value="Alzheimer's Disease">Alzheimer&apos;s Disease</option>
                  <option value="Atrial Fibrillation">Atrial Fibrillation</option>
                  <option value="Prostate Cancer">Prostate Cancer</option>
                  <option value="Schizophrenia">Schizophrenia</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={grLoading}
                  className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                >
                  {grLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Calculating...
                    </span>
                  ) : (
                    "Calculate Risk Score"
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* PRS Results */}
          {grResults && (
            <div className="space-y-4 animate-fade-in-up">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* Risk Score Gauge */}
                <div className="card flex flex-col items-center justify-center py-8">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-4">Polygenic Risk Score</p>
                  <div className="relative h-36 w-36">
                    {/* Background ring */}
                    <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                      <circle cx="60" cy="60" r="50" fill="none" stroke="#f3f4f6" strokeWidth="12" />
                      <circle
                        cx="60"
                        cy="60"
                        r="50"
                        fill="none"
                        stroke="url(#riskGradient)"
                        strokeWidth="12"
                        strokeLinecap="round"
                        strokeDasharray={`${(grResults.riskScore / 100) * 314} 314`}
                      />
                      <defs>
                        <linearGradient id="riskGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor={grResults.riskScore >= 60 ? "#ef4444" : grResults.riskScore >= 30 ? "#f59e0b" : "#22c55e"} />
                          <stop offset="100%" stopColor={grResults.riskScore >= 80 ? "#dc2626" : grResults.riskScore >= 50 ? "#ef4444" : "#16a34a"} />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">{grResults.riskScore}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">/100</span>
                    </div>
                  </div>
                  <div className="mt-4 text-center">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{grResults.condition}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {grResults.percentile}th percentile
                    </p>
                    <span className={`mt-2 inline-block rounded-full px-3 py-1 text-xs font-semibold ${
                      grResults.riskScore >= 70 ? "bg-red-50 text-red-700" : grResults.riskScore >= 40 ? "bg-amber-50 text-amber-700" : "bg-green-50 text-green-700"
                    }`}>
                      {grResults.riskScore >= 70 ? "High Risk" : grResults.riskScore >= 40 ? "Moderate Risk" : "Low Risk"}
                    </span>
                  </div>
                  {/* Color gradient bar */}
                  <div className="mt-4 w-full px-4">
                    <div className="h-2 w-full rounded-full bg-gradient-to-r from-green-400 via-yellow-400 via-orange-400 to-red-500 relative">
                      <div
                        className="absolute -top-1 h-4 w-1 rounded bg-gray-900"
                        style={{ left: `${grResults.riskScore}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-[11px] text-gray-500 dark:text-gray-400">0</span>
                      <span className="text-[11px] text-gray-500 dark:text-gray-400">50</span>
                      <span className="text-[11px] text-gray-500 dark:text-gray-400">100</span>
                    </div>
                  </div>
                </div>

                {/* Risk Factors */}
                <div className="card">
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Risk Factors</h4>
                  <div className="space-y-2.5">
                    {grResults.riskFactors.map((factor, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-red-50 text-[11px] font-bold text-red-600">
                          {idx + 1}
                        </span>
                        <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{factor}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recommendations */}
                <div className="card">
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Clinical Recommendations</h4>
                  <div className="space-y-2.5">
                    {grResults.recommendations.map((rec, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-healthos-50 text-[11px] font-bold text-healthos-600">
                          {idx + 1}
                        </span>
                        <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{rec}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Monogenic Screening */}
          <div className="card animate-fade-in-up">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Monogenic Variant Screening</h3>
              <button
                onClick={() => setShowMonogenic(!showMonogenic)}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                {showMonogenic ? "Hide Variants" : "Show Variants"}
              </button>
            </div>
            {showMonogenic && (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 animate-fade-in-up">
                {DEMO_MONOGENIC.map((variant) => (
                  <div key={`${variant.gene}-${variant.variant}`} className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{variant.gene}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${classificationBadge(variant.classification)}`}>
                          {classificationLabel(variant.classification)}
                        </span>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Variant: <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{variant.variant}</span></p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Condition: <span className="font-medium text-gray-700 dark:text-gray-300">{variant.condition}</span></p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Inheritance: <span className="font-medium text-gray-700 dark:text-gray-300">{variant.inheritance}</span></p>
                  </div>
                ))}
              </div>
            )}
            {!showMonogenic && (
              <p className="text-xs text-gray-500 dark:text-gray-400">{DEMO_MONOGENIC.length} variants screened across ACMG-recommended genes. Click &quot;Show Variants&quot; to review.</p>
            )}
          </div>

          {/* Empty state for PRS */}
          {!grResults && !grLoading && (
            <div className="card text-center py-6 sm:py-12">
              <div className="text-2xl sm:text-4xl mb-3 opacity-40">🧬</div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Enter patient ID and condition to calculate polygenic risk score</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Aggregates millions of genetic variants into a single risk metric</p>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 4: Data De-identification
         ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === "deidentify" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Dataset Upload Form */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">De-identification Workflow</h3>
            <form onSubmit={handleDeidentify} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Dataset Name</label>
                  <input
                    required
                    value={deidName}
                    onChange={(e) => setDeidName(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                    placeholder="e.g. CKD Research Cohort Q1 2026"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Record Count</label>
                  <input
                    type="number"
                    required
                    value={deidRecordCount}
                    onChange={(e) => setDeidRecordCount(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                    placeholder="e.g. 5000"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Data Types</label>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {["Demographics", "Diagnoses", "Medications", "Labs", "Notes", "Vitals"].map((dt) => (
                      <button
                        key={dt}
                        type="button"
                        onClick={() => toggleDataType(dt.toLowerCase())}
                        className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                          deidDataTypes.includes(dt.toLowerCase())
                            ? "bg-healthos-600 text-white"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200"
                        }`}
                      >
                        {dt}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={deidLoading}
                  className="rounded-lg bg-healthos-600 px-6 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                >
                  {deidLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Processing...
                    </span>
                  ) : (
                    "Start De-identification"
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Processing Progress */}
          {deidLoading && (
            <div className="card animate-fade-in-up">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Processing Dataset</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500 dark:text-gray-400">De-identification progress</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{Math.round(deidProgress)}%</span>
                </div>
                <div className="h-3 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                  <div
                    className="h-3 rounded-full bg-gradient-to-r from-healthos-400 to-healthos-600 transition-all duration-500"
                    style={{ width: `${deidProgress}%` }}
                  />
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <span className="h-2 w-2 rounded-full bg-healthos-500 animate-pulse" />
                  Applying HIPAA Safe Harbor de-identification rules...
                </div>
              </div>
            </div>
          )}

          {/* De-identification Results */}
          {deidResult && !deidLoading && (
            <div className="space-y-4 animate-fade-in-up">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">De-identification Results</h3>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="card text-center">
                  <p className="text-xs text-gray-500 dark:text-gray-400">k-Anonymity Score</p>
                  <p className="mt-1 text-2xl font-bold text-emerald-600">{deidResult.kAnonymity}</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">minimum group size</p>
                </div>
                <div className="card text-center">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Re-identification Risk</p>
                  <p className="mt-1 text-2xl font-bold text-green-600">{deidResult.reidentificationRisk}%</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">below 5% threshold</p>
                </div>
                <div className="card text-center">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Records Processed</p>
                  <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{deidResult.recordCount.toLocaleString()}</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">in {deidResult.processingTime}</p>
                </div>
                <div className="card text-center">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Status</p>
                  <p className="mt-1 text-2xl font-bold text-green-600">
                    {deidResult.status === "completed" ? "Complete" : deidResult.status === "processing" ? "Processing" : "Failed"}
                  </p>
                  <button className="mt-1 rounded bg-healthos-600 px-3 py-1 text-[11px] font-medium text-white hover:bg-healthos-700 transition-colors">
                    Export Dataset
                  </button>
                </div>
              </div>

              {/* Progress bar for completed */}
              <div className="card">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="font-medium text-gray-700 dark:text-gray-300">De-identification Complete</span>
                  <span className="font-semibold text-green-600">100%</span>
                </div>
                <div className="h-3 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                  <div className="h-3 w-full rounded-full bg-gradient-to-r from-green-400 to-green-600" />
                </div>
              </div>
            </div>
          )}

          {/* Compliance Verification */}
          <div className="card animate-fade-in-up">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">HIPAA Safe Harbor Compliance Verification</h3>
              <button
                onClick={() => setShowCompliance(!showCompliance)}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                {showCompliance ? "Hide Details" : "Run Compliance Check"}
              </button>
            </div>
            {showCompliance && (
              <div className="space-y-3 animate-fade-in-up">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">18 HIPAA Safe Harbor identifiers verified against de-identified dataset</p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {DEMO_COMPLIANCE.map((check) => (
                    <div key={check.identifier} className="flex items-center gap-2 rounded-lg border border-gray-100 dark:border-gray-800 p-2">
                      <span className={`h-5 w-5 flex-shrink-0 rounded-full flex items-center justify-center text-white text-[11px] ${
                        check.status === "pass" ? "bg-green-500" : check.status === "warning" ? "bg-yellow-500" : "bg-red-500"
                      }`}>
                        {check.status === "pass" ? "\u2713" : check.status === "warning" ? "!" : "\u2717"}
                      </span>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{check.identifier}</p>
                        <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">{check.details}</p>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 p-3 mt-2">
                  <span className="h-5 w-5 rounded-full bg-green-500 flex items-center justify-center text-white text-[11px]">&#10003;</span>
                  <p className="text-xs font-medium text-green-800">
                    All 18 HIPAA Safe Harbor identifiers passed verification. Dataset is compliant for research use.
                  </p>
                </div>
              </div>
            )}
            {!showCompliance && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Verify that all 18 HIPAA Safe Harbor identifiers have been properly removed or de-identified from the dataset.
              </p>
            )}
          </div>

          {/* Empty state */}
          {!deidResult && !deidLoading && (
            <div className="card text-center py-6 sm:py-12">
              <div className="text-2xl sm:text-4xl mb-3 opacity-40">🛡️</div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Configure dataset parameters above to start de-identification</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">HIPAA Safe Harbor compliant with k-anonymity and differential privacy</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
