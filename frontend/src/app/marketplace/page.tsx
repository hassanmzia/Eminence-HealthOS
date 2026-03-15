"use client";

import { useState, useEffect, useMemo } from "react";
import {
  fetchMarketplaceAgents,
  fetchMarketplaceAgent,
  publishMarketplaceAgent,
  installMarketplaceAgent,
  scanMarketplaceAgent,
  fetchMarketplaceAnalytics,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

type AgentCategory = "clinical" | "operations" | "analytics" | "compliance";
type SecurityStatus = "verified" | "pending" | "unverified";
type AgentStatus = "active" | "disabled" | "update-available";
type ReviewStatus = "pending" | "approved" | "rejected";

interface MarketplaceAgent {
  id: string;
  name: string;
  publisher: string;
  version: string;
  description: string;
  category: AgentCategory;
  rating: number;
  installs: number;
  security: SecurityStatus;
  installed?: boolean;
}

interface InstalledAgent {
  id: string;
  name: string;
  version: string;
  latestVersion: string;
  status: AgentStatus;
  installedDate: string;
  callsThisMonth: number;
  errorRate: number;
  avgResponseMs: number;
  category: AgentCategory;
}

interface PublishedAgent {
  id: string;
  name: string;
  version: string;
  category: AgentCategory;
  reviewStatus: ReviewStatus;
  submittedDate: string;
  reviewNote?: string;
}

interface PublishForm {
  name: string;
  description: string;
  category: AgentCategory | "";
  version: string;
  capabilities: string[];
  permissions: string[];
  documentationUrl: string;
  fileName: string;
}

// ── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_AGENTS: MarketplaceAgent[] = [
  {
    id: "sepsis-early-warning",
    name: "Sepsis Early Warning",
    publisher: "ClinicalAI Corp",
    version: "2.1.0",
    description:
      "Detects early signs of sepsis using SOFA scoring, vital trend analysis, and lab correlation. Reduces time-to-treatment by 40%.",
    category: "clinical",
    rating: 4.8,
    installs: 1342,
    security: "verified",
    installed: true,
  },
  {
    id: "smart-scheduling-optimizer",
    name: "Smart Scheduling Optimizer",
    publisher: "OptiHealth Labs",
    version: "3.0.1",
    description:
      "AI-driven appointment scheduling that maximizes provider utilization while minimizing patient wait times. Supports multi-location facilities.",
    category: "operations",
    rating: 4.9,
    installs: 2567,
    security: "verified",
  },
  {
    id: "revenue-leakage-detector",
    name: "Revenue Leakage Detector",
    publisher: "FinHealth Analytics",
    version: "1.3.0",
    description:
      "Identifies missed charges, under-coding, and revenue cycle inefficiencies using pattern analysis across claims data.",
    category: "analytics",
    rating: 4.5,
    installs: 789,
    security: "verified",
  },
  {
    id: "clinical-note-enhancer",
    name: "Clinical Note Enhancer",
    publisher: "DocuMed AI",
    version: "2.0.0",
    description:
      "Enhances clinical documentation with suggested ICD-10 codes, missing diagnoses, and quality improvement recommendations.",
    category: "clinical",
    rating: 4.6,
    installs: 1412,
    security: "pending",
  },
  {
    id: "population-risk-stratifier",
    name: "Population Risk Stratifier",
    publisher: "HealthMetrics Inc",
    version: "1.5.2",
    description:
      "Advanced population health analytics with social determinant integration, risk cohort identification, and intervention targeting.",
    category: "analytics",
    rating: 4.7,
    installs: 931,
    security: "verified",
  },
  {
    id: "hipaa-compliance-monitor",
    name: "HIPAA Compliance Monitor",
    publisher: "ComplianceGuard",
    version: "4.1.0",
    description:
      "Real-time HIPAA compliance monitoring with automated audit trails, breach detection, and remediation recommendations.",
    category: "compliance",
    rating: 4.9,
    installs: 2178,
    security: "verified",
    installed: true,
  },
  {
    id: "bed-management-ai",
    name: "Bed Management AI",
    publisher: "OptiHealth Labs",
    version: "1.2.0",
    description:
      "Predicts patient discharge timing and optimizes bed allocation to reduce boarding and improve throughput across departments.",
    category: "operations",
    rating: 4.3,
    installs: 456,
    security: "pending",
  },
  {
    id: "clinical-trial-matcher",
    name: "Clinical Trial Matcher",
    publisher: "ResearchBridge",
    version: "2.4.1",
    description:
      "Matches patients to eligible clinical trials using NLP-powered criteria extraction and real-time trial registry integration.",
    category: "clinical",
    rating: 4.4,
    installs: 623,
    security: "verified",
  },
  {
    id: "consent-management-agent",
    name: "Consent Management Agent",
    publisher: "ComplianceGuard",
    version: "1.0.3",
    description:
      "Automates patient consent workflows, tracks consent status across encounters, and ensures regulatory compliance with state-specific requirements.",
    category: "compliance",
    rating: 4.2,
    installs: 345,
    security: "unverified",
  },
  {
    id: "readmission-predictor",
    name: "Readmission Risk Predictor",
    publisher: "HealthMetrics Inc",
    version: "3.1.0",
    description:
      "Machine learning model that predicts 30-day readmission risk using clinical, social, and behavioral factors with 92% accuracy.",
    category: "analytics",
    rating: 4.8,
    installs: 1089,
    security: "verified",
  },
  {
    id: "drug-interaction-checker",
    name: "Drug Interaction Checker",
    publisher: "PharmaSafe AI",
    version: "5.0.2",
    description:
      "Comprehensive drug-drug and drug-food interaction checking with severity grading, alternative suggestions, and pharmacogenomic considerations.",
    category: "clinical",
    rating: 4.7,
    installs: 3201,
    security: "verified",
    installed: true,
  },
  {
    id: "audit-trail-analyzer",
    name: "Audit Trail Analyzer",
    publisher: "ComplianceGuard",
    version: "2.2.0",
    description:
      "AI-powered audit trail analysis that detects anomalous access patterns, potential breaches, and generates compliance reports automatically.",
    category: "compliance",
    rating: 4.5,
    installs: 567,
    security: "verified",
  },
];

const DEMO_INSTALLED: InstalledAgent[] = [
  {
    id: "sepsis-early-warning",
    name: "Sepsis Early Warning",
    version: "2.1.0",
    latestVersion: "2.1.0",
    status: "active",
    installedDate: "2025-11-15",
    callsThisMonth: 8432,
    errorRate: 0.3,
    avgResponseMs: 145,
    category: "clinical",
  },
  {
    id: "hipaa-compliance-monitor",
    name: "HIPAA Compliance Monitor",
    version: "4.0.2",
    latestVersion: "4.1.0",
    status: "update-available",
    installedDate: "2025-09-20",
    callsThisMonth: 15200,
    errorRate: 0.1,
    avgResponseMs: 89,
    category: "compliance",
  },
  {
    id: "drug-interaction-checker",
    name: "Drug Interaction Checker",
    version: "5.0.2",
    latestVersion: "5.0.2",
    status: "active",
    installedDate: "2025-12-01",
    callsThisMonth: 22450,
    errorRate: 0.2,
    avgResponseMs: 67,
    category: "clinical",
  },
  {
    id: "revenue-analyzer",
    name: "Revenue Cycle Analyzer",
    version: "1.1.0",
    latestVersion: "1.3.0",
    status: "disabled",
    installedDate: "2025-10-10",
    callsThisMonth: 0,
    errorRate: 0,
    avgResponseMs: 0,
    category: "analytics",
  },
];

const DEMO_PUBLISHED: PublishedAgent[] = [
  {
    id: "custom-triage-agent",
    name: "Custom Triage Agent",
    version: "1.0.0",
    category: "clinical",
    reviewStatus: "approved",
    submittedDate: "2025-12-20",
  },
  {
    id: "scheduling-helper",
    name: "Scheduling Helper",
    version: "0.9.0",
    category: "operations",
    reviewStatus: "pending",
    submittedDate: "2026-01-15",
  },
  {
    id: "billing-validator",
    name: "Billing Validator",
    version: "1.0.0",
    category: "compliance",
    reviewStatus: "rejected",
    submittedDate: "2026-01-02",
    reviewNote: "Missing required HIPAA compliance documentation.",
  },
];

const CATEGORIES: { label: string; value: AgentCategory | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Clinical", value: "clinical" },
  { label: "Operations", value: "operations" },
  { label: "Analytics", value: "analytics" },
  { label: "Compliance", value: "compliance" },
];

const CATEGORY_COLORS: Record<AgentCategory, string> = {
  clinical: "bg-blue-100 text-blue-700",
  operations: "bg-emerald-100 text-emerald-700",
  analytics: "bg-purple-100 text-purple-700",
  compliance: "bg-orange-100 text-orange-700",
};

const CAPABILITIES_OPTIONS = [
  "Patient Data Analysis",
  "Clinical Decision Support",
  "Natural Language Processing",
  "Image Analysis",
  "Predictive Modeling",
  "Workflow Automation",
  "Report Generation",
  "Real-time Monitoring",
  "Data Integration",
  "Alert Management",
];

const PERMISSIONS_OPTIONS = [
  "Read Patient Records",
  "Write Patient Records",
  "Access Lab Results",
  "Access Imaging Data",
  "Send Notifications",
  "Access Billing Data",
  "Execute Clinical Actions",
  "Access Audit Logs",
  "Manage Schedules",
  "Access Pharmacy Data",
];

// ── Sub-Components ───────────────────────────────────────────────────────────

function StarRating({ rating }: { rating: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);

  return (
    <span className="inline-flex items-center gap-0.5 text-amber-400">
      {Array.from({ length: full }).map((_, i) => (
        <svg key={`f${i}`} className="h-4 w-4 fill-current" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      {half && (
        <svg className="h-4 w-4" viewBox="0 0 20 20">
          <defs>
            <linearGradient id="halfGrad">
              <stop offset="50%" stopColor="currentColor" />
              <stop offset="50%" stopColor="#D1D5DB" />
            </linearGradient>
          </defs>
          <path
            fill="url(#halfGrad)"
            d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
          />
        </svg>
      )}
      {Array.from({ length: empty }).map((_, i) => (
        <svg key={`e${i}`} className="h-4 w-4 fill-gray-300" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="ml-1 text-sm text-gray-600">{rating.toFixed(1)}</span>
    </span>
  );
}

function SecurityBadge({ status }: { status: SecurityStatus }) {
  const config = {
    verified: { color: "text-emerald-600", bg: "bg-emerald-50", label: "Verified" },
    pending: { color: "text-amber-600", bg: "bg-amber-50", label: "Pending" },
    unverified: { color: "text-gray-500", bg: "bg-gray-50", label: "Unverified" },
  }[status];

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${config.bg} ${config.color}`}>
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
      {config.label}
    </span>
  );
}

function StatusBadge({ status }: { status: AgentStatus }) {
  const config = {
    active: { bg: "bg-emerald-100", text: "text-emerald-700", label: "Active" },
    disabled: { bg: "bg-gray-100", text: "text-gray-600", label: "Disabled" },
    "update-available": { bg: "bg-blue-100", text: "text-blue-700", label: "Update Available" },
  }[status];

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
}

function ReviewBadge({ status }: { status: ReviewStatus }) {
  const config = {
    pending: { bg: "bg-amber-100", text: "text-amber-700", label: "Pending Review" },
    approved: { bg: "bg-emerald-100", text: "text-emerald-700", label: "Approved" },
    rejected: { bg: "bg-red-100", text: "text-red-700", label: "Rejected" },
  }[status];

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
}

function KPICard({
  label,
  value,
  icon,
  trend,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  trend?: string;
}) {
  return (
    <div className="card card-hover flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-healthos-50 text-healthos-600">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-xl font-bold text-gray-900">{value}</p>
        {trend && <p className="text-xs text-emerald-600">{trend}</p>}
      </div>
    </div>
  );
}

// ── Browse Tab ───────────────────────────────────────────────────────────────

function BrowseTab({
  agents,
  onInstall,
}: {
  agents: MarketplaceAgent[];
  onInstall: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<AgentCategory | "all">("all");

  const filtered = useMemo(
    () =>
      agents.filter((a) => {
        const matchSearch =
          !search ||
          a.name.toLowerCase().includes(search.toLowerCase()) ||
          a.description.toLowerCase().includes(search.toLowerCase()) ||
          a.publisher.toLowerCase().includes(search.toLowerCase());
        const matchCategory = category === "all" || a.category === category;
        return matchSearch && matchCategory;
      }),
    [agents, search, category],
  );

  return (
    <div className="animate-fade-in-up">
      {/* Search */}
      <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents by name, description, or publisher..."
            className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-4 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
        </div>
      </div>

      {/* Category filter chips */}
      <div className="mb-6 flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setCategory(cat.value)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              category === cat.value
                ? "bg-healthos-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-lg text-gray-400">No agents found matching your criteria.</p>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent, idx) => (
            <div
              key={agent.id}
              className="card card-hover animate-fade-in-up flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              {/* Top row: name + category badge */}
              <div className="mb-2 flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-base font-semibold text-gray-900">{agent.name}</h3>
                  <p className="text-sm text-gray-500">{agent.publisher}</p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${CATEGORY_COLORS[agent.category]}`}
                >
                  {agent.category}
                </span>
              </div>

              {/* Security badge */}
              <div className="mb-2">
                <SecurityBadge status={agent.security} />
              </div>

              {/* Description (2 line truncate) */}
              <p className="mb-4 line-clamp-2 flex-1 text-sm text-gray-600">{agent.description}</p>

              {/* Stats row */}
              <div className="mb-4 flex items-center gap-4">
                <StarRating rating={agent.rating} />
                <span className="text-sm text-gray-500">{agent.installs.toLocaleString()} installs</span>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between border-t border-gray-100 pt-3">
                <span className="text-xs text-gray-400">v{agent.version}</span>
                {agent.installed ? (
                  <span className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 px-4 py-1.5 text-sm font-medium text-emerald-700">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    Installed
                  </span>
                ) : (
                  <button
                    onClick={() => onInstall(agent.id)}
                    className="rounded-lg bg-healthos-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-healthos-700"
                  >
                    Install
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── My Agents Tab ────────────────────────────────────────────────────────────

function MyAgentsTab({ agents }: { agents: InstalledAgent[] }) {
  const [installed, setInstalled] = useState(agents);

  const toggleAgent = (id: string) => {
    setInstalled((prev) =>
      prev.map((a) =>
        a.id === id
          ? { ...a, status: a.status === "active" ? "disabled" : "active" as AgentStatus }
          : a,
      ),
    );
  };

  const uninstallAgent = (id: string) => {
    setInstalled((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <div className="animate-fade-in-up space-y-4">
      {installed.length === 0 ? (
        <div className="card rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-lg font-medium text-gray-400">No agents installed yet</p>
          <p className="mt-1 text-sm text-gray-400">Browse the marketplace to discover and install agents</p>
        </div>
      ) : (
        installed.map((agent, idx) => (
          <div
            key={agent.id}
            className="card card-hover animate-fade-in-up rounded-xl border border-gray-200 bg-white p-5"
            style={{ animationDelay: `${idx * 50}ms` }}
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              {/* Left: Info */}
              <div className="min-w-0 flex-1">
                <div className="mb-2 flex flex-wrap items-center gap-3">
                  <h3 className="text-base font-semibold text-gray-900">{agent.name}</h3>
                  <StatusBadge status={agent.status} />
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${CATEGORY_COLORS[agent.category]}`}>
                    {agent.category}
                  </span>
                </div>
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-500">
                  <span>v{agent.version}</span>
                  <span>Installed {agent.installedDate}</span>
                </div>

                {/* Analytics */}
                <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div>
                    <p className="text-xs text-gray-400">Calls This Month</p>
                    <p className="text-lg font-semibold text-gray-900">{agent.callsThisMonth.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Error Rate</p>
                    <p className={`text-lg font-semibold ${agent.errorRate > 1 ? "text-red-600" : "text-gray-900"}`}>
                      {agent.errorRate}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Avg Response</p>
                    <p className="text-lg font-semibold text-gray-900">{agent.avgResponseMs}ms</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400">Usage Trend</p>
                    {/* Graph placeholder */}
                    <div className="mt-1 flex h-6 items-end gap-0.5">
                      {[40, 55, 45, 70, 60, 80, 75].map((h, i) => (
                        <div
                          key={i}
                          className="w-2 rounded-sm bg-healthos-400"
                          style={{ height: `${h}%` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Right: Actions */}
              <div className="flex shrink-0 flex-wrap gap-2 lg:flex-col">
                <button
                  onClick={() => toggleAgent(agent.id)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    agent.status === "active"
                      ? "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                  }`}
                >
                  {agent.status === "active" ? "Disable" : "Enable"}
                </button>
                {agent.status === "update-available" && (
                  <button className="rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100">
                    Update to v{agent.latestVersion}
                  </button>
                )}
                <button className="rounded-lg bg-gray-50 px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100">
                  Configure
                </button>
                <button
                  onClick={() => uninstallAgent(agent.id)}
                  className="rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-100"
                >
                  Uninstall
                </button>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ── Publish Tab ──────────────────────────────────────────────────────────────

function PublishTab({
  publishedAgents,
  onPublish,
}: {
  publishedAgents: PublishedAgent[];
  onPublish: (form: PublishForm) => void;
}) {
  const [form, setForm] = useState<PublishForm>({
    name: "",
    description: "",
    category: "",
    version: "",
    capabilities: [],
    permissions: [],
    documentationUrl: "",
    fileName: "",
  });

  const [showPreview, setShowPreview] = useState(false);

  const updateField = <K extends keyof PublishForm>(key: K, value: PublishForm[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const toggleMulti = (key: "capabilities" | "permissions", value: string) => {
    setForm((prev) => ({
      ...prev,
      [key]: prev[key].includes(value)
        ? prev[key].filter((v) => v !== value)
        : [...prev[key], value],
    }));
  };

  const handleSubmit = () => {
    if (!form.name || !form.description || !form.category || !form.version) return;
    onPublish(form);
    setForm({
      name: "",
      description: "",
      category: "",
      version: "",
      capabilities: [],
      permissions: [],
      documentationUrl: "",
      fileName: "",
    });
  };

  return (
    <div className="animate-fade-in-up space-y-8">
      {/* Publishing Form */}
      <div className="card rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-6 text-lg font-semibold text-gray-900">Publish a New Agent</h3>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left: Form fields */}
          <div className="space-y-5">
            {/* Name */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Agent Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                placeholder="e.g., Sepsis Early Warning"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
            </div>

            {/* Description */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => updateField("description", e.target.value)}
                placeholder="Describe what your agent does, its key features, and benefits..."
                rows={4}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
            </div>

            {/* Category + Version row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Category</label>
                <select
                  value={form.category}
                  onChange={(e) => updateField("category", e.target.value as AgentCategory)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Select...</option>
                  <option value="clinical">Clinical</option>
                  <option value="operations">Operations</option>
                  <option value="analytics">Analytics</option>
                  <option value="compliance">Compliance</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Version</label>
                <input
                  type="text"
                  value={form.version}
                  onChange={(e) => updateField("version", e.target.value)}
                  placeholder="1.0.0"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
            </div>

            {/* Capabilities (multi-select) */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Capabilities</label>
              <div className="flex flex-wrap gap-2">
                {CAPABILITIES_OPTIONS.map((cap) => (
                  <button
                    key={cap}
                    onClick={() => toggleMulti("capabilities", cap)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      form.capabilities.includes(cap)
                        ? "bg-healthos-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {cap}
                  </button>
                ))}
              </div>
            </div>

            {/* Required Permissions (multi-select) */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Required Permissions</label>
              <div className="flex flex-wrap gap-2">
                {PERMISSIONS_OPTIONS.map((perm) => (
                  <button
                    key={perm}
                    onClick={() => toggleMulti("permissions", perm)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      form.permissions.includes(perm)
                        ? "bg-orange-500 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {perm}
                  </button>
                ))}
              </div>
            </div>

            {/* Documentation URL */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Documentation URL</label>
              <input
                type="url"
                value={form.documentationUrl}
                onChange={(e) => updateField("documentationUrl", e.target.value)}
                placeholder="https://docs.example.com/agent"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
            </div>

            {/* File upload area */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Agent Package</label>
              <div
                className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 px-6 py-8 transition-colors hover:border-healthos-400"
                onClick={() => {
                  // Simulate file selection
                  updateField("fileName", "agent-package-v1.0.0.tar.gz");
                }}
              >
                <svg className="mb-2 h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                </svg>
                {form.fileName ? (
                  <p className="text-sm font-medium text-healthos-600">{form.fileName}</p>
                ) : (
                  <>
                    <p className="text-sm text-gray-600">Click to upload or drag and drop</p>
                    <p className="mt-1 text-xs text-gray-400">.tar.gz, .zip up to 50MB</p>
                  </>
                )}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleSubmit}
                disabled={!form.name || !form.description || !form.category || !form.version}
                className="rounded-lg bg-healthos-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Submit for Review
              </button>
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="rounded-lg bg-gray-100 px-6 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-200"
              >
                {showPreview ? "Hide Preview" : "Preview Card"}
              </button>
            </div>
          </div>

          {/* Right: Card Preview */}
          <div>
            {showPreview && form.name && (
              <div className="sticky top-6">
                <p className="mb-3 text-sm font-medium text-gray-500">Card Preview</p>
                <div className="card rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-base font-semibold text-gray-900">{form.name || "Agent Name"}</h3>
                      <p className="text-sm text-gray-500">Your Organization</p>
                    </div>
                    {form.category && (
                      <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${CATEGORY_COLORS[form.category as AgentCategory]}`}>
                        {form.category}
                      </span>
                    )}
                  </div>
                  <div className="mb-2">
                    <SecurityBadge status="pending" />
                  </div>
                  <p className="mb-4 line-clamp-2 text-sm text-gray-600">
                    {form.description || "Agent description will appear here..."}
                  </p>
                  <div className="mb-4 flex items-center gap-4">
                    <StarRating rating={0} />
                    <span className="text-sm text-gray-500">0 installs</span>
                  </div>
                  <div className="flex items-center justify-between border-t border-gray-100 pt-3">
                    <span className="text-xs text-gray-400">v{form.version || "0.0.0"}</span>
                    <span className="rounded-lg bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-400">
                      Install
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Published agents list */}
      <div>
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Your Published Agents</h3>
        {publishedAgents.length === 0 ? (
          <div className="card rounded-xl border border-gray-200 bg-white py-12 text-center">
            <p className="text-gray-400">No agents published yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {publishedAgents.map((agent) => (
              <div
                key={agent.id}
                className="card card-hover flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <h4 className="font-medium text-gray-900">{agent.name}</h4>
                  <span className="text-sm text-gray-500">v{agent.version}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${CATEGORY_COLORS[agent.category]}`}>
                    {agent.category}
                  </span>
                  <ReviewBadge status={agent.reviewStatus} />
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400">Submitted {agent.submittedDate}</p>
                  {agent.reviewNote && (
                    <p className="mt-1 text-xs text-red-500">{agent.reviewNote}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function MarketplacePage() {
  const [agents, setAgents] = useState<MarketplaceAgent[]>(DEMO_AGENTS);
  const [installedAgents] = useState<InstalledAgent[]>(DEMO_INSTALLED);
  const [publishedAgents, setPublishedAgents] = useState<PublishedAgent[]>(DEMO_PUBLISHED);
  const [tab, setTab] = useState<"browse" | "my-agents" | "publish">("browse");

  // Attempt to load from API, fall back to demo data
  useEffect(() => {
    fetchMarketplaceAgents()
      .then((data: Record<string, unknown>) => {
        const fetched = data?.agents as MarketplaceAgent[] | undefined;
        if (Array.isArray(fetched) && fetched.length > 0) {
          setAgents(fetched);
        }
      })
      .catch(() => {
        // Demo mode — use sample data
      });

    fetchMarketplaceAnalytics().catch(() => {
      // Demo mode
    });
  }, []);

  const handleInstall = (agentId: string) => {
    fetchMarketplaceAgent(agentId).catch(() => {});
    installMarketplaceAgent(agentId).catch(() => {});
    scanMarketplaceAgent(agentId).catch(() => {});
    setAgents((prev) =>
      prev.map((a) =>
        a.id === agentId ? { ...a, installs: a.installs + 1, installed: true } : a,
      ),
    );
  };

  const handlePublish = (form: PublishForm) => {
    publishMarketplaceAgent({
      name: form.name,
      description: form.description,
      category: form.category,
      version: form.version,
      capabilities: form.capabilities,
      permissions: form.permissions,
      documentation_url: form.documentationUrl,
    }).catch(() => {});

    setPublishedAgents((prev) => [
      {
        id: `custom-${Date.now()}`,
        name: form.name,
        version: form.version,
        category: form.category as AgentCategory,
        reviewStatus: "pending",
        submittedDate: new Date().toISOString().split("T")[0],
      },
      ...prev,
    ]);
  };

  // Stats
  const totalAgents = agents.length;
  const installedCount = agents.filter((a) => a.installed).length + installedAgents.filter((a) => !agents.find((ma) => ma.id === a.id)).length;
  const totalDownloads = agents.reduce((sum, a) => sum + a.installs, 0);
  const avgRating = agents.length ? (agents.reduce((sum, a) => sum + a.rating, 0) / agents.length).toFixed(1) : "0";
  const securityScans = agents.filter((a) => a.security === "verified").length;

  const tabs = [
    { key: "browse" as const, label: "Browse Agents" },
    { key: "my-agents" as const, label: "My Agents" },
    { key: "publish" as const, label: "Publish" },
  ];

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">AI Agent Marketplace</h1>
            <span className="inline-flex items-center rounded-full bg-healthos-100 px-3 py-0.5 text-sm font-semibold text-healthos-700">
              {totalAgents} Available
            </span>
          </div>
          <p className="mt-1 text-base text-gray-500">
            Discover, install, and manage AI agents built on the HealthOS platform
          </p>
        </div>
        <button
          onClick={() => setTab("publish")}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-healthos-700"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Publish Agent
        </button>
      </div>

      {/* Stats Bar */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 animate-fade-in-up">
        <KPICard
          label="Available Agents"
          value={String(totalAgents)}
          trend="+3 this month"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          }
        />
        <KPICard
          label="Installed"
          value={String(installedCount)}
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          }
        />
        <KPICard
          label="Downloads This Month"
          value={totalDownloads.toLocaleString()}
          trend="+12% vs last month"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
            </svg>
          }
        />
        <KPICard
          label="Avg Rating"
          value={avgRating}
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          }
        />
        <KPICard
          label="Security Scans"
          value={`${securityScans}/${totalAgents}`}
          trend="All passing"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          }
        />
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "browse" && <BrowseTab agents={agents} onInstall={handleInstall} />}
      {tab === "my-agents" && <MyAgentsTab agents={installedAgents} />}
      {tab === "publish" && <PublishTab publishedAgents={publishedAgents} onPublish={handlePublish} />}

      {/* Security Section */}
      <div className="mt-10 animate-fade-in-up">
        <div className="card rounded-xl border border-gray-200 bg-white p-6">
          <div className="mb-4 flex items-center gap-2">
            <svg className="h-5 w-5 text-healthos-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <h3 className="text-lg font-semibold text-gray-900">Security Scan Results</h3>
          </div>
          <div className="grid gap-6 sm:grid-cols-3">
            <div className="rounded-lg bg-emerald-50 p-4">
              <p className="text-sm text-emerald-600">Agents Scanned</p>
              <p className="mt-1 text-2xl font-bold text-emerald-700">{securityScans}</p>
              <p className="mt-1 text-xs text-emerald-500">of {totalAgents} total agents</p>
            </div>
            <div className="rounded-lg bg-emerald-50 p-4">
              <p className="text-sm text-emerald-600">Vulnerabilities Found</p>
              <p className="mt-1 text-2xl font-bold text-emerald-700">0</p>
              <p className="mt-1 text-xs text-emerald-500">No critical or high issues</p>
            </div>
            <div className="rounded-lg bg-emerald-50 p-4">
              <p className="text-sm text-emerald-600">Compliance Status</p>
              <p className="mt-1 text-2xl font-bold text-emerald-700">Passing</p>
              <p className="mt-1 text-xs text-emerald-500">HIPAA, SOC 2, HITRUST compliant</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
