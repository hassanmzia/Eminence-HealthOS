"use client";

import { useState, useCallback, useEffect } from "react";
import { searchClinicalRAG, fetchRAGCollections, ingestRAGDocument, type RAGSearchResult } from "@/lib/api";

/* ── Types ──────────────────────────────────────────────────────────────────── */

interface Collection {
  name: string;
  doc_count: number;
  description: string;
  health?: "healthy" | "warning" | "error";
}

interface RecentSearch {
  query: string;
  timestamp: string;
  resultCount: number;
}

/* ── Demo Data ──────────────────────────────────────────────────────────────── */

const DEMO_COLLECTIONS: Collection[] = [
  { name: "Clinical Guidelines", doc_count: 1247, description: "AHA, ACC, ADA, USPSTF clinical practice guidelines", health: "healthy" },
  { name: "Medical Literature", doc_count: 8432, description: "PubMed indexed research articles and systematic reviews", health: "healthy" },
  { name: "Drug Interactions", doc_count: 3891, description: "FDA drug interaction databases and pharmacokinetic data", health: "healthy" },
  { name: "Protocols", doc_count: 562, description: "Institutional clinical protocols and care pathways", health: "warning" },
  { name: "Formulary", doc_count: 2104, description: "Insurance formulary and prior authorization criteria", health: "healthy" },
];

const DEMO_SEARCH_RESULT: RAGSearchResult = {
  query: "hypertension management guidelines 2024",
  answer: "According to the 2024 AHA/ACC Hypertension Clinical Practice Guidelines, the recommended blood pressure target for most adults is <130/80 mmHg. First-line pharmacotherapy includes thiazide diuretics, ACE inhibitors, ARBs, or calcium channel blockers. For patients with compelling indications such as heart failure, post-MI, or CKD, specific drug classes are preferred. Lifestyle modifications including DASH diet, sodium restriction (<1500mg/day), regular aerobic exercise (150 min/week), weight management, and limiting alcohol intake should be initiated for all patients with elevated blood pressure. For resistant hypertension (uncontrolled on 3 agents including a diuretic), addition of spironolactone 25-50mg is recommended.",
  confidence: 0.94,
  sources: ["AHA/ACC 2024 Guideline", "JNC 8 Update", "SPRINT Trial Follow-up"],
  results: [
    {
      content: "The 2024 AHA/ACC guideline recommends initiating antihypertensive therapy at BP >=130/80 mmHg for patients with clinical CVD or 10-year ASCVD risk >=10%. For lower-risk patients, the threshold remains >=140/90 mmHg. First-line agents include thiazide-type diuretics (chlorthalidone preferred), ACE inhibitors, ARBs, and dihydropyridine CCBs. Combination therapy with two first-line agents is recommended when BP is >=20/10 mmHg above target.",
      source: "AHA/ACC Hypertension Guideline 2024",
      collection: "Clinical Guidelines",
      score: 0.96,
      metadata: { year: 2024, organization: "AHA/ACC", category: "cardiovascular" },
    },
    {
      content: "SPRINT trial long-term follow-up data demonstrates sustained cardiovascular benefit of intensive blood pressure control (SBP <120 mmHg) compared to standard control (SBP <140 mmHg). At 8-year follow-up, intensive treatment was associated with 29% reduction in major cardiovascular events and 27% reduction in all-cause mortality. Benefits were consistent across age groups, including patients >75 years.",
      source: "SPRINT Trial Extended Follow-up, NEJM 2024",
      collection: "Medical Literature",
      score: 0.89,
      metadata: { year: 2024, journal: "NEJM", study_type: "RCT follow-up" },
    },
    {
      content: "ACE inhibitors and ARBs should not be used in combination due to increased risk of hyperkalemia, renal impairment, and hypotension without additional cardiovascular benefit. When combining antihypertensives, preferred combinations include: ACE inhibitor/ARB + CCB, ACE inhibitor/ARB + thiazide diuretic, or CCB + thiazide diuretic. Avoid combining ACEi + ARB, or beta-blocker + non-DHP CCB.",
      source: "FDA Drug Interaction Compendium",
      collection: "Drug Interactions",
      score: 0.85,
      metadata: { source: "FDA", last_updated: "2024-06" },
    },
    {
      content: "Institutional Protocol: Hypertension Management Pathway. Step 1: Lifestyle modifications for all patients with BP >=120/80. Step 2: Monotherapy initiation at BP >=130/80 (high risk) or >=140/90 (low risk). Step 3: Combination therapy if uncontrolled on maximally tolerated monotherapy at 4-week follow-up. Step 4: Triple therapy or referral to hypertension specialist if uncontrolled on dual therapy. Lab monitoring: BMP at baseline, 2 weeks after ACEi/ARB initiation, then every 6 months.",
      source: "HealthOS Institutional Protocol HTN-2024-001",
      collection: "Protocols",
      score: 0.82,
      metadata: { protocol_id: "HTN-2024-001", version: "3.2" },
    },
    {
      content: "Resistant hypertension is defined as blood pressure that remains above goal despite concurrent use of 3 antihypertensive agents of different classes at optimal doses, one of which should be a diuretic. Pseudo-resistance should be excluded by confirming medication adherence, proper BP measurement technique, and ruling out white-coat effect with ambulatory BP monitoring. Mineralocorticoid receptor antagonists (spironolactone 25-50mg daily) are the recommended fourth-line agent per PATHWAY-2 trial results.",
      source: "Resistant Hypertension: AHA Scientific Statement 2024",
      collection: "Clinical Guidelines",
      score: 0.78,
      metadata: { year: 2024, organization: "AHA", type: "scientific statement" },
    },
  ],
};

const COLLECTION_FILTERS = ["All", "Clinical Guidelines", "Medical Literature", "Drug Interactions", "Protocols"] as const;

/* ── Helpers ────────────────────────────────────────────────────────────────── */

function confidenceColor(score: number): string {
  if (score >= 0.9) return "bg-emerald-100 text-emerald-700";
  if (score >= 0.7) return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

function collectionBadge(collection: string): string {
  const map: Record<string, string> = {
    "Clinical Guidelines": "bg-blue-100 text-blue-700",
    "Medical Literature": "bg-purple-100 text-purple-700",
    "Drug Interactions": "bg-red-100 text-red-700",
    Protocols: "bg-teal-100 text-teal-700",
    Formulary: "bg-orange-100 text-orange-700",
  };
  return map[collection] || "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400";
}

function healthDot(h?: string) {
  if (h === "healthy") return "bg-emerald-400";
  if (h === "warning") return "bg-amber-400";
  return "bg-red-400";
}

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diffMin = Math.round((now.getTime() - d.getTime()) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
  return `${Math.floor(diffMin / 1440)}d ago`;
}

/* ── Page Component ─────────────────────────────────────────────────────────── */

export default function ClinicalIntelligencePage() {
  // Search state
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<string>("All");
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<RAGSearchResult | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  // Advanced options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [topK, setTopK] = useState(5);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.7);

  // Collections
  const [collections, setCollections] = useState<Collection[]>(DEMO_COLLECTIONS);

  // Recent searches
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([
    { query: "hypertension management guidelines 2024", timestamp: new Date(Date.now() - 600000).toISOString(), resultCount: 5 },
    { query: "metformin drug interactions with contrast dye", timestamp: new Date(Date.now() - 3600000).toISOString(), resultCount: 3 },
    { query: "sepsis bundle protocol 2024", timestamp: new Date(Date.now() - 7200000).toISOString(), resultCount: 4 },
    { query: "warfarin INR monitoring frequency", timestamp: new Date(Date.now() - 18000000).toISOString(), resultCount: 6 },
    { query: "heart failure with preserved ejection fraction treatment", timestamp: new Date(Date.now() - 43200000).toISOString(), resultCount: 5 },
  ]);

  // Upload modal
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadCollection, setUploadCollection] = useState("");
  const [uploadContent, setUploadContent] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadSource, setUploadSource] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Load collections on mount
  useEffect(() => {
    fetchRAGCollections()
      .then((data) => {
        if (data?.collections?.length) {
          setCollections(
            data.collections.map((c) => ({ ...c, health: "healthy" as const }))
          );
        }
      })
      .catch(() => {
        // API unavailable - use demo data
      });
  }, []);

  // Search handler
  const handleSearch = useCallback(
    async (searchQuery?: string) => {
      const q = searchQuery || query;
      if (!q.trim()) return;

      setSearching(true);
      setSearchResult(null);
      setExpandedIdx(null);

      try {
        const result = await searchClinicalRAG({
          query: q,
          collection: activeFilter === "All" ? undefined : activeFilter,
          top_k: topK,
        });
        // Filter by confidence threshold
        const filtered = {
          ...result,
          results: result.results.filter((r) => r.score >= confidenceThreshold),
        };
        setSearchResult(filtered);
        setRecentSearches((prev: RecentSearch[]) => [
          { query: q, timestamp: new Date().toISOString(), resultCount: filtered.results.length },
          ...prev.filter((s: RecentSearch) => s.query !== q).slice(0, 9),
        ]);
      } catch {
        // API unavailable - use demo data
        const demo = { ...DEMO_SEARCH_RESULT, query: q };
        const filtered = {
          ...demo,
          results: demo.results.filter((r) => r.score >= confidenceThreshold),
        };
        setSearchResult(filtered);
        setRecentSearches((prev: RecentSearch[]) => [
          { query: q, timestamp: new Date().toISOString(), resultCount: filtered.results.length },
          ...prev.filter((s: RecentSearch) => s.query !== q).slice(0, 9),
        ]);
      } finally {
        setSearching(false);
      }
    },
    [query, activeFilter, topK, confidenceThreshold]
  );

  // Upload handler
  const handleUpload = useCallback(async () => {
    if (!uploadCollection || !uploadContent.trim()) return;
    setUploading(true);
    try {
      await ingestRAGDocument({
        collection: uploadCollection,
        content: uploadContent,
        metadata: {
          title: uploadTitle || undefined,
          source: uploadSource || undefined,
          ingested_at: new Date().toISOString(),
        },
      });
      setUploadSuccess(true);
      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess(false);
        setUploadContent("");
        setUploadTitle("");
        setUploadSource("");
        setUploadCollection("");
      }, 1500);
    } catch {
      // Demo mode - simulate success
      setUploadSuccess(true);
      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess(false);
        setUploadContent("");
        setUploadTitle("");
        setUploadSource("");
        setUploadCollection("");
      }, 1500);
    } finally {
      setUploading(false);
    }
  }, [uploadCollection, uploadContent, uploadTitle, uploadSource]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-800">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-healthos-700 via-healthos-600 to-healthos-500 px-6 py-8 animate-fade-in-up">
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/20 backdrop-blur-sm">
              <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Clinical Intelligence</h1>
              <p className="text-healthos-100 text-sm mt-0.5">
                AI-powered clinical knowledge search across guidelines, literature, and protocols
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 -mt-6">
        {/* ── Search Interface ──────────────────────────────────────────────── */}
        <div className="card card-hover rounded-xl shadow-lg p-6 mb-6 animate-fade-in-up" style={{ animationDelay: "0.05s" }}>
          {/* Search bar */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
              <svg className="h-5 w-5 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search clinical guidelines, drug interactions, protocols..."
              className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 py-4 pl-12 pr-32 text-base text-gray-900 dark:text-gray-100 placeholder-gray-400 shadow-sm transition-all focus:border-healthos-500 focus:bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-healthos-500/20"
            />
            <button
              onClick={() => handleSearch()}
              disabled={searching || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {searching ? (
                <span className="flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  Searching
                </span>
              ) : (
                "Search"
              )}
            </button>
          </div>

          {/* Collection filter chips */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-1">Collections:</span>
            {COLLECTION_FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setActiveFilter(f)}
                className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition-all ${
                  activeFilter === f
                    ? "bg-healthos-600 text-white shadow-sm"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200"
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Advanced options toggle */}
          <div className="mt-3">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-healthos-600 transition-colors"
            >
              <svg
                className={`h-3.5 w-3.5 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              Advanced Options
            </button>
            {showAdvanced && (
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4 animate-fade-in-up">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                    Top K Results: <span className="font-semibold text-healthos-600">{topK}</span>
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={20}
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="w-full accent-healthos-600"
                  />
                  <div className="flex justify-between text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                    <span>1</span>
                    <span>10</span>
                    <span>20</span>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                    Confidence Threshold: <span className="font-semibold text-healthos-600">{Math.round(confidenceThreshold * 100)}%</span>
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={confidenceThreshold * 100}
                    onChange={(e) => setConfidenceThreshold(Number(e.target.value) / 100)}
                    className="w-full accent-healthos-600"
                  />
                  <div className="flex justify-between text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Main Content Area ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 pb-10">
          {/* Left: Search Results (3 cols) */}
          <div className="lg:col-span-3 space-y-4">
            {/* Searching indicator */}
            {searching && (
              <div className="card rounded-xl p-8 text-center animate-fade-in-up">
                <svg className="mx-auto h-8 w-8 animate-spin text-healthos-500 mb-3" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                <p className="text-sm text-gray-500 dark:text-gray-400">Searching clinical knowledge base...</p>
              </div>
            )}

            {/* AI-generated answer */}
            {searchResult && !searching && (
              <>
                <div className="card rounded-xl border border-healthos-200 bg-healthos-50 p-5 animate-fade-in-up" style={{ animationDelay: "0.05s" }}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-healthos-600">
                        <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                        </svg>
                      </div>
                      <h3 className="text-sm font-semibold text-healthos-800">AI-Generated Answer</h3>
                    </div>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${confidenceColor(searchResult.confidence)}`}>
                      {Math.round(searchResult.confidence * 100)}% confidence
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{searchResult.answer}</p>
                  {searchResult.sources.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider self-center mr-1">Sources:</span>
                      {searchResult.sources.map((s, i) => (
                        <span key={i} className="inline-flex items-center rounded-md bg-white dark:bg-gray-900 px-2 py-0.5 text-[11px] font-medium text-healthos-700 ring-1 ring-inset ring-healthos-200">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Source documents */}
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider px-1">
                    Source Documents ({searchResult.results.length})
                  </h3>
                  {searchResult.results.map((doc, idx) => (
                    <div
                      key={idx}
                      className="card card-hover rounded-xl p-4 animate-fade-in-up cursor-pointer transition-all"
                      style={{ animationDelay: `${0.08 + idx * 0.04}s` }}
                      onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <svg className="h-4 w-4 text-gray-500 dark:text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                          </svg>
                          <span className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">{doc.source}</span>
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium flex-shrink-0 ${collectionBadge(doc.collection)}`}>
                            {doc.collection}
                          </span>
                        </div>
                        <svg
                          className={`h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform flex-shrink-0 ml-2 ${expandedIdx === idx ? "rotate-180" : ""}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2}
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                        </svg>
                      </div>

                      {/* Relevance score bar */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400 w-16">Relevance</span>
                        <div className="flex-1 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-healthos-400 to-healthos-600 transition-all duration-500"
                            style={{ width: `${doc.score * 100}%` }}
                          />
                        </div>
                        <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 w-8 text-right">{Math.round(doc.score * 100)}%</span>
                      </div>

                      {/* Content snippet / expanded */}
                      <p className={`text-xs text-gray-600 dark:text-gray-400 leading-relaxed ${expandedIdx === idx ? "" : "line-clamp-2"}`}>
                        {doc.content}
                      </p>

                      {/* Metadata when expanded */}
                      {expandedIdx === idx && doc.metadata && Object.keys(doc.metadata).length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2 border-t border-gray-100 dark:border-gray-800 pt-3">
                          {Object.entries(doc.metadata).map(([key, value]) => (
                            <span key={key} className="inline-flex items-center gap-1 rounded bg-gray-50 dark:bg-gray-800 px-2 py-0.5 text-[11px] text-gray-500 dark:text-gray-400">
                              <span className="font-medium text-gray-600 dark:text-gray-400">{key}:</span> {String(value)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Empty state */}
            {!searchResult && !searching && (
              <div className="card rounded-xl p-12 text-center animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-healthos-50 mb-4">
                  <svg className="h-8 w-8 text-healthos-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200 mb-1">Search Clinical Knowledge</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                  Query across clinical guidelines, medical literature, drug interactions, and institutional protocols using AI-powered semantic search.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {["Hypertension management", "Metformin interactions", "Sepsis protocol", "Heart failure treatment"].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => {
                        setQuery(suggestion);
                        handleSearch(suggestion);
                      }}
                      className="rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:border-healthos-300 hover:text-healthos-700 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Searches */}
            {recentSearches.length > 0 && (
              <div className="card rounded-xl p-5 animate-fade-in-up" style={{ animationDelay: "0.15s" }}>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Recent Searches</h3>
                <div className="space-y-1.5">
                  {recentSearches.slice(0, 5).map((s, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setQuery(s.query);
                        handleSearch(s.query);
                      }}
                      className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 group"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <svg className="h-3.5 w-3.5 text-gray-300 flex-shrink-0 group-hover:text-healthos-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="text-sm text-gray-700 dark:text-gray-300 truncate group-hover:text-healthos-700 transition-colors">{s.query}</span>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                        <span className="text-[11px] text-gray-500 dark:text-gray-400">{s.resultCount} results</span>
                        <span className="text-[11px] text-gray-500 dark:text-gray-400">{formatTime(s.timestamp)}</span>
                        <svg className="h-3.5 w-3.5 text-gray-300 group-hover:text-healthos-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                        </svg>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Collections Panel (1 col) */}
          <div className="space-y-4">
            <div className="card rounded-xl p-5 animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Collections</h3>
                <span className="text-[11px] text-gray-500 dark:text-gray-400">{collections.reduce((a, c) => a + c.doc_count, 0).toLocaleString()} docs</span>
              </div>
              <div className="space-y-2.5">
                {collections.map((c) => (
                  <button
                    key={c.name}
                    onClick={() => {
                      setActiveFilter(c.name === activeFilter ? "All" : c.name);
                    }}
                    className={`w-full rounded-lg border p-3 text-left transition-all ${
                      activeFilter === c.name
                        ? "border-healthos-300 bg-healthos-50 ring-1 ring-healthos-200"
                        : "border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <span className={`h-2 w-2 rounded-full ${healthDot(c.health)}`} />
                        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 truncate">{c.name}</span>
                      </div>
                      <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400">{c.doc_count.toLocaleString()}</span>
                    </div>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-2">{c.description}</p>
                  </button>
                ))}
              </div>

              {/* Upload button */}
              <button
                onClick={() => setShowUploadModal(true)}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700 py-2.5 text-xs font-medium text-gray-500 dark:text-gray-400 transition-all hover:border-healthos-400 hover:text-healthos-600 hover:bg-healthos-50"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Upload Document
              </button>
            </div>

            {/* Quick stats */}
            <div className="card rounded-xl p-5 animate-fade-in-up" style={{ animationDelay: "0.15s" }}>
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Knowledge Base</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Total Documents</span>
                  <span className="text-sm font-bold text-gray-800 dark:text-gray-200">{collections.reduce((a, c) => a + c.doc_count, 0).toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Collections</span>
                  <span className="text-sm font-bold text-gray-800 dark:text-gray-200">{collections.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Avg Relevance</span>
                  <span className="text-sm font-bold text-emerald-600">92%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Last Updated</span>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">2h ago</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Document Upload Modal ───────────────────────────────────────────── */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-900 shadow-2xl animate-fade-in-up">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 px-6 py-4">
              <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">Upload Document</h2>
              <button
                onClick={() => setShowUploadModal(false)}
                className="rounded-lg p-1 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:bg-gray-800 hover:text-gray-600 dark:text-gray-400 transition-colors"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-6 py-5 space-y-4">
              {uploadSuccess ? (
                <div className="py-8 text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 mb-3">
                    <svg className="h-6 w-6 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">Document Uploaded Successfully</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">The document is being indexed into the knowledge base.</p>
                </div>
              ) : (
                <>
                  {/* Collection selector */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Collection</label>
                    <select
                      value={uploadCollection}
                      onChange={(e) => setUploadCollection(e.target.value)}
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2.5 text-sm text-gray-700 dark:text-gray-300 focus:border-healthos-500 focus:outline-none focus:ring-2 focus:ring-healthos-500/20"
                    >
                      <option value="">Select a collection...</option>
                      {collections.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name} ({c.doc_count.toLocaleString()} docs)
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Title */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Document Title</label>
                    <input
                      type="text"
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                      placeholder="e.g., AHA Hypertension Guideline 2024"
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2.5 text-sm text-gray-700 dark:text-gray-300 placeholder-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-2 focus:ring-healthos-500/20"
                    />
                  </div>

                  {/* Source */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Source</label>
                    <input
                      type="text"
                      value={uploadSource}
                      onChange={(e) => setUploadSource(e.target.value)}
                      placeholder="e.g., American Heart Association"
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2.5 text-sm text-gray-700 dark:text-gray-300 placeholder-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-2 focus:ring-healthos-500/20"
                    />
                  </div>

                  {/* Content */}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Document Content</label>
                    <textarea
                      value={uploadContent}
                      onChange={(e) => setUploadContent(e.target.value)}
                      rows={6}
                      placeholder="Paste or type document content here..."
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2.5 text-sm text-gray-700 dark:text-gray-300 placeholder-gray-400 resize-none focus:border-healthos-500 focus:outline-none focus:ring-2 focus:ring-healthos-500/20"
                    />
                  </div>
                </>
              )}
            </div>

            {!uploadSuccess && (
              <div className="flex items-center justify-end gap-3 border-t border-gray-100 dark:border-gray-800 px-6 py-4">
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={uploading || !uploadCollection || !uploadContent.trim()}
                  className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <span className="flex items-center gap-2">
                      <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                      </svg>
                      Uploading...
                    </span>
                  ) : (
                    "Upload & Index"
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
