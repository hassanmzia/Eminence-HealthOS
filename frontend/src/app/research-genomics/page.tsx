"use client";

import { useState } from "react";

const SAMPLE_TRIALS = [
  {
    nctId: "NCT05001234",
    title: "SGLT2 Inhibitor for CKD Stage 3-4 with Type 2 Diabetes",
    phase: "Phase III",
    status: "Recruiting",
    enrolled: 312,
    target: 500,
    sites: 24,
    matchScore: 0.92,
  },
  {
    nctId: "NCT05005678",
    title: "GLP-1 Receptor Agonist for Obesity and CV Risk Reduction",
    phase: "Phase III",
    status: "Recruiting",
    enrolled: 678,
    target: 1000,
    sites: 40,
    matchScore: 0.78,
  },
  {
    nctId: "NCT05009012",
    title: "AI-Assisted Diabetic Retinopathy Screening in Primary Care",
    phase: "Phase II",
    status: "Recruiting",
    enrolled: 142,
    target: 300,
    sites: 15,
    matchScore: 0.65,
  },
  {
    nctId: "NCT05012345",
    title: "Pharmacogenomic-Guided Warfarin Dosing",
    phase: "Phase IV",
    status: "Recruiting",
    enrolled: 87,
    target: 200,
    sites: 10,
    matchScore: 0.71,
  },
];

const PGX_GENES = [
  { gene: "CYP2D6", phenotype: "Normal Metabolizer", drugs: 6, status: "normal" },
  { gene: "CYP2C19", phenotype: "Intermediate Metabolizer", drugs: 4, status: "actionable" },
  { gene: "VKORC1", phenotype: "High Sensitivity", drugs: 1, status: "actionable" },
  { gene: "HLA-B*5701", phenotype: "Negative", drugs: 1, status: "normal" },
  { gene: "SLCO1B1", phenotype: "Normal Function", drugs: 3, status: "normal" },
];

const PRS_SCORES = [
  { condition: "Coronary Artery Disease", percentile: 82, risk: "elevated", snps: "6.6M" },
  { condition: "Type 2 Diabetes", percentile: 91, risk: "high", snps: "1.3M" },
  { condition: "Breast Cancer", percentile: 45, risk: "average", snps: "313" },
  { condition: "Alzheimer's Disease", percentile: 68, risk: "average", snps: "84" },
  { condition: "Atrial Fibrillation", percentile: 34, risk: "low", snps: "142" },
];

const COHORT_TEMPLATES = [
  { key: "diabetes_ckd", name: "Type 2 Diabetes with CKD", size: 1643, criteria: 5 },
  { key: "heart_failure", name: "Heart Failure Population", size: 2105, criteria: 3 },
  { key: "hypertension_uncontrolled", name: "Uncontrolled Hypertension", size: 987, criteria: 2 },
];

const riskColor = (risk: string) =>
  risk === "high" ? "text-red-600 bg-red-50" : risk === "elevated" ? "text-orange-600 bg-orange-50" : risk === "low" ? "text-green-600 bg-green-50" : "text-gray-600 bg-gray-100";

const statusColor = (status: string) =>
  status === "actionable" ? "text-amber-700 bg-amber-50" : "text-green-700 bg-green-50";

type Tab = "trials" | "genomics" | "cohorts" | "deidentify";

export default function ResearchGenomicsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("trials");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Research & Genomics</h1>
          <p className="text-sm text-gray-500">Clinical trials, pharmacogenomics, genetic risk, cohort management, and de-identification</p>
        </div>
        <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
          + New Research Study
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: "Active Trials", value: SAMPLE_TRIALS.length.toString() },
          { label: "PGx Genes Tested", value: PGX_GENES.length.toString() },
          { label: "PRS Conditions", value: PRS_SCORES.length.toString() },
          { label: "Research Cohorts", value: COHORT_TEMPLATES.length.toString() },
          { label: "Datasets Exported", value: "12" },
        ].map((s) => (
          <div key={s.label} className="card text-center">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
        {([
          { key: "trials", label: "Clinical Trials" },
          { key: "genomics", label: "Pharmacogenomics & PRS" },
          { key: "cohorts", label: "Research Cohorts" },
          { key: "deidentify", label: "De-Identification" },
        ] as const).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium ${
              activeTab === tab.key ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Clinical Trials Tab */}
      {activeTab === "trials" && (
        <div className="space-y-3">
          {SAMPLE_TRIALS.map((trial) => (
            <div key={trial.nctId} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">{trial.title}</span>
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-700">{trial.phase}</span>
                    <span className="rounded bg-green-50 px-1.5 py-0.5 text-xs font-medium text-green-700">{trial.status}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {trial.nctId} — {trial.sites} sites — Enrolled {trial.enrolled}/{trial.target} ({Math.round(trial.enrolled / trial.target * 100)}%)
                  </p>
                  <div className="mt-2 h-1.5 w-64 rounded-full bg-gray-100">
                    <div
                      className="h-1.5 rounded-full bg-healthos-500"
                      style={{ width: `${Math.round(trial.enrolled / trial.target * 100)}%` }}
                    />
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-lg font-bold text-healthos-700">{(trial.matchScore * 100).toFixed(0)}%</span>
                  <p className="text-xs text-gray-500">Match Score</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Genomics Tab */}
      {activeTab === "genomics" && (
        <div className="grid grid-cols-2 gap-6">
          {/* PGx Profile */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-700">Pharmacogenomic Profile</h3>
            {PGX_GENES.map((gene) => (
              <div key={gene.gene} className="card flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">{gene.gene}</span>
                    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${statusColor(gene.status)}`}>
                      {gene.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">{gene.phenotype} — {gene.drugs} drugs affected</p>
                </div>
              </div>
            ))}
          </div>

          {/* PRS Scores */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-700">Polygenic Risk Scores</h3>
            {PRS_SCORES.map((prs) => (
              <div key={prs.condition} className="card">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-900">{prs.condition}</span>
                    <p className="text-xs text-gray-500">{prs.snps} SNPs analyzed</p>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold text-gray-900">{prs.percentile}th</span>
                    <span className={`ml-2 rounded px-1.5 py-0.5 text-xs font-medium ${riskColor(prs.risk)}`}>
                      {prs.risk}
                    </span>
                  </div>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-gray-100">
                  <div
                    className={`h-1.5 rounded-full ${
                      prs.risk === "high" ? "bg-red-400" : prs.risk === "elevated" ? "bg-orange-400" : prs.risk === "low" ? "bg-green-400" : "bg-gray-400"
                    }`}
                    style={{ width: `${prs.percentile}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cohorts Tab */}
      {activeTab === "cohorts" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Research Cohort Templates</h3>
            <button className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
              + Custom Cohort
            </button>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {COHORT_TEMPLATES.map((cohort) => (
              <div key={cohort.key} className="card">
                <h4 className="text-sm font-semibold text-gray-900">{cohort.name}</h4>
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-gray-500">Cohort Size: <span className="font-medium text-gray-900">{cohort.size.toLocaleString()}</span></p>
                  <p className="text-xs text-gray-500">Criteria: <span className="font-medium text-gray-900">{cohort.criteria}</span></p>
                </div>
                <div className="mt-3 flex gap-2">
                  <button className="rounded bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700">Build</button>
                  <button className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">Details</button>
                </div>
              </div>
            ))}
          </div>

          {/* Cohort Comparison */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Cohort Balance Check (Treatment vs Control)</h3>
            <div className="space-y-2">
              {[
                { variable: "Mean Age", a: "62.1", b: "62.5", p: 0.72 },
                { variable: "Female %", a: "47.8%", b: "48.6%", p: 0.81 },
                { variable: "Mean HbA1c", a: "7.9", b: "7.7", p: 0.15 },
                { variable: "Mean eGFR", a: "43.2", b: "41.8", p: 0.22 },
                { variable: "Statin Use %", a: "80.5%", b: "81.9%", p: 0.58 },
              ].map((row) => (
                <div key={row.variable} className="flex items-center gap-4 text-xs">
                  <span className="w-28 font-medium text-gray-700">{row.variable}</span>
                  <span className="w-16 text-center text-gray-900">{row.a}</span>
                  <span className="w-16 text-center text-gray-900">{row.b}</span>
                  <span className={`w-16 text-center font-medium ${row.p < 0.05 ? "text-red-600" : "text-green-600"}`}>
                    p={row.p.toFixed(2)}
                  </span>
                  <span className="rounded bg-green-50 px-1.5 py-0.5 text-xs text-green-700">balanced</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* De-Identification Tab */}
      {activeTab === "deidentify" && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="card text-center">
              <p className="text-xs font-medium text-gray-500">Records Processed</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">4,250</p>
            </div>
            <div className="card text-center">
              <p className="text-xs font-medium text-gray-500">PHI Instances Redacted</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">38,720</p>
            </div>
            <div className="card text-center">
              <p className="text-xs font-medium text-gray-500">HIPAA Compliance</p>
              <p className="mt-1 text-2xl font-bold text-green-600">100%</p>
            </div>
          </div>

          {/* Recent Jobs */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Recent De-Identification Jobs</h3>
            <div className="space-y-3">
              {[
                { dataset: "Diabetes CKD Cohort Export", records: 1643, redactions: 14820, status: "verified", date: "2026-03-11" },
                { dataset: "Heart Failure Population Study", records: 2105, redactions: 19450, status: "verified", date: "2026-03-10" },
                { dataset: "Pharmacogenomic Research Data", records: 502, redactions: 4450, status: "pending", date: "2026-03-12" },
              ].map((job) => (
                <div key={job.dataset} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                  <div>
                    <span className="text-sm font-medium text-gray-900">{job.dataset}</span>
                    <p className="text-xs text-gray-500">{job.records.toLocaleString()} records — {job.redactions.toLocaleString()} PHI redacted — {job.date}</p>
                  </div>
                  <span className={`rounded px-2 py-1 text-xs font-medium ${
                    job.status === "verified" ? "bg-green-50 text-green-700" : "bg-yellow-50 text-yellow-700"
                  }`}>
                    {job.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* HIPAA Safe Harbor Checklist */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">HIPAA Safe Harbor — 18 Identifier Compliance</h3>
            <div className="grid grid-cols-3 gap-2">
              {[
                "Names", "Geographic data", "Dates", "Phone numbers", "Fax numbers",
                "Email addresses", "SSN", "MRN", "Health plan IDs",
                "Account numbers", "Certificates/Licenses", "Vehicle IDs",
                "Device IDs", "URLs", "IP addresses", "Biometric IDs",
                "Full-face photos", "Other unique IDs",
              ].map((id) => (
                <div key={id} className="flex items-center gap-2 text-xs">
                  <span className="h-4 w-4 rounded-full bg-green-500 flex items-center justify-center text-white text-[8px]">&#10003;</span>
                  <span className="text-gray-700">{id}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
