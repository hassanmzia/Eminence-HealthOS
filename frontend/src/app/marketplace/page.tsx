"use client";

import { useState, useEffect } from "react";
import {
  fetchMarketplaceAgents,
  installMarketplaceAgent,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface MarketplaceAgent {
  id: string;
  name: string;
  author: string;
  version: string;
  description: string;
  category: string;
  tier: string;
  rating: number;
  installs: number;
  status: string;
}

// ── Sample Data ──────────────────────────────────────────────────────────────

const DEMO_AGENTS: MarketplaceAgent[] = [
  {
    id: "sepsis-early-warning",
    name: "Sepsis Early Warning",
    author: "ClinicalAI Corp",
    version: "2.1.0",
    description:
      "Detects early signs of sepsis using SOFA scoring, vital trend analysis, and lab correlation. Reduces time-to-treatment by 40%.",
    category: "Clinical",
    tier: "interpretation",
    rating: 4.8,
    installs: 342,
    status: "published",
  },
  {
    id: "smart-scheduling-optimizer",
    name: "Smart Scheduling Optimizer",
    author: "OptiHealth Labs",
    version: "3.0.1",
    description:
      "AI-driven appointment scheduling that maximizes provider utilization while minimizing patient wait times. Supports multi-location.",
    category: "Operations",
    tier: "decisioning",
    rating: 4.9,
    installs: 567,
    status: "published",
  },
  {
    id: "revenue-leakage-detector",
    name: "Revenue Leakage Detector",
    author: "FinHealth Analytics",
    version: "1.3.0",
    description:
      "Identifies missed charges, under-coding, and revenue cycle inefficiencies using pattern analysis across claims data.",
    category: "Operations",
    tier: "measurement",
    rating: 4.5,
    installs: 189,
    status: "published",
  },
  {
    id: "clinical-note-enhancer",
    name: "Clinical Note Enhancer",
    author: "DocuMed AI",
    version: "2.0.0",
    description:
      "Enhances clinical documentation with suggested ICD-10 codes, missing diagnoses, and quality improvement recommendations.",
    category: "Clinical",
    tier: "decisioning",
    rating: 4.6,
    installs: 412,
    status: "published",
  },
  {
    id: "population-risk-stratifier",
    name: "Population Risk Stratifier",
    author: "HealthMetrics Inc",
    version: "1.5.2",
    description:
      "Advanced population health analytics with social determinant integration, risk cohort identification, and intervention targeting.",
    category: "Analytics",
    tier: "measurement",
    rating: 4.7,
    installs: 231,
    status: "published",
  },
  {
    id: "fhir-bridge-connector",
    name: "FHIR Bridge Connector",
    author: "InteropWorks",
    version: "4.1.0",
    description:
      "Seamless FHIR R4 integration with Epic, Cerner, and Meditech. Supports bulk data export, CDS Hooks, and SMART on FHIR.",
    category: "Integration",
    tier: "sensing",
    rating: 4.4,
    installs: 678,
    status: "published",
  },
];

const CATEGORIES = ["All", "Clinical", "Operations", "Analytics", "Integration"];

const TIER_COLORS: Record<string, string> = {
  sensing: "bg-blue-100 text-blue-700",
  interpretation: "bg-purple-100 text-purple-700",
  decisioning: "bg-amber-100 text-amber-700",
  action: "bg-red-100 text-red-700",
  measurement: "bg-emerald-100 text-emerald-700",
};

// ── Components ───────────────────────────────────────────────────────────────

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
            <linearGradient id="halfStar">
              <stop offset="50%" stopColor="currentColor" />
              <stop offset="50%" stopColor="#D1D5DB" />
            </linearGradient>
          </defs>
          <path
            fill="url(#halfStar)"
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

function AgentCard({
  agent,
  onInstall,
}: {
  agent: MarketplaceAgent;
  onInstall: (id: string) => void;
}) {
  const tierClass = TIER_COLORS[agent.tier] || "bg-gray-100 text-gray-700";

  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-gray-900">
            {agent.name}
          </h3>
          <p className="text-sm text-gray-500">{agent.author}</p>
        </div>
        <span className={`ml-2 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${tierClass}`}>
          {agent.tier}
        </span>
      </div>

      {/* Description */}
      <p className="mb-4 line-clamp-3 flex-1 text-sm text-gray-600">
        {agent.description}
      </p>

      {/* Stats */}
      <div className="mb-4 flex items-center gap-4">
        <StarRating rating={agent.rating} />
        <span className="text-sm text-gray-500">
          {agent.installs.toLocaleString()} installs
        </span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-gray-100 pt-3">
        <span className="text-xs text-gray-400">v{agent.version}</span>
        <button
          onClick={() => onInstall(agent.id)}
          className="rounded-lg bg-healthos-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-healthos-700"
        >
          Install
        </button>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function MarketplacePage() {
  const [agents, setAgents] = useState<MarketplaceAgent[]>(DEMO_AGENTS);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [tab, setTab] = useState<"browse" | "installed" | "published">("browse");

  // Attempt to fetch from backend; fall back to demo data silently
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
  }, []);

  const handleInstall = (agentId: string) => {
    installMarketplaceAgent(agentId).catch(() => {
      // Demo mode — silently ignore
    });
    setAgents((prev) =>
      prev.map((a) =>
        a.id === agentId ? { ...a, installs: a.installs + 1 } : a,
      ),
    );
  };

  // Filter agents
  const filtered = agents.filter((a) => {
    const matchesSearch =
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.description.toLowerCase().includes(search.toLowerCase()) ||
      a.author.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      category === "All" || a.category === category;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          AI Agent Marketplace
        </h1>
        <p className="mt-1 text-base text-gray-500">
          Discover, install, and manage third-party AI agents built on HealthOS
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {(["browse", "installed", "published"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Search & Filters */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents by name, description, or author..."
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
        </div>

        <div className="flex gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                category === cat
                  ? "bg-healthos-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Agent Grid */}
      {tab === "browse" && (
        <>
          {filtered.length === 0 ? (
            <div className="py-16 text-center">
              <p className="text-lg text-gray-400">
                No agents found matching your criteria.
              </p>
            </div>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onInstall={handleInstall}
                />
              ))}
            </div>
          )}
        </>
      )}

      {tab === "installed" && (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-lg font-medium text-gray-400">
            No agents installed yet
          </p>
          <p className="mt-1 text-sm text-gray-400">
            Browse the marketplace to discover and install agents
          </p>
        </div>
      )}

      {tab === "published" && (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-lg font-medium text-gray-400">
            No agents published yet
          </p>
          <p className="mt-1 text-sm text-gray-400">
            Build and publish your own agents for the HealthOS ecosystem
          </p>
        </div>
      )}
    </div>
  );
}
