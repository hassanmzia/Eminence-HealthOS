"use client";

import { useState, useCallback } from "react";
import { runSDOHAssessment, fetchSDOHHistory, fetchCommunityResources, type SDOHAssessment } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────────────────── */

type RiskLevel = "none" | "some" | "high";

interface DomainQuestion {
  key: string;
  label: string;
  description: string;
}

interface CommunityResource {
  name: string;
  type: string;
  distance: string;
  phone: string;
  address: string;
  services: string[];
}

/* ── Constants ─────────────────────────────────────────────────────────────── */

const DOMAINS: DomainQuestion[] = [
  { key: "housing", label: "Housing", description: "Housing stability, safety, and affordability" },
  { key: "food", label: "Food", description: "Food security, access to healthy food" },
  { key: "transportation", label: "Transportation", description: "Access to transportation for medical visits" },
  { key: "employment", label: "Employment", description: "Employment status, financial strain" },
  { key: "education", label: "Education", description: "Health literacy, language barriers" },
  { key: "social_support", label: "Social Support", description: "Isolation, caregiver status" },
  { key: "safety", label: "Safety", description: "Personal safety, domestic violence screening" },
];

const RISK_OPTIONS: { value: RiskLevel; label: string; color: string }[] = [
  { value: "none", label: "No Risk", color: "bg-green-100 text-green-700 border-green-300" },
  { value: "some", label: "Some Risk", color: "bg-yellow-100 text-yellow-700 border-yellow-300" },
  { value: "high", label: "High Risk", color: "bg-red-100 text-red-700 border-red-300" },
];

const NEEDS_OPTIONS = [
  "Housing", "Food", "Transportation", "Employment", "Education",
  "Legal Aid", "Childcare", "Mental Health", "Substance Use", "Utilities",
];

const DEMO_RESOURCES: CommunityResource[] = [
  { name: "Community Food Bank of Central TX", type: "Food Assistance", distance: "1.2 mi", phone: "(512) 555-0142", address: "2200 W Ben White Blvd", services: ["Emergency food boxes", "SNAP enrollment", "Nutrition education"] },
  { name: "Safe Harbor Housing", type: "Housing Support", distance: "2.8 mi", phone: "(512) 555-0198", address: "4501 N Lamar Blvd", services: ["Emergency shelter", "Transitional housing", "Rental assistance"] },
  { name: "Metro Health Transit Program", type: "Transportation", distance: "0.5 mi", phone: "(512) 555-0267", address: "1100 Congress Ave", services: ["Medical ride scheduling", "Bus pass program", "Wheelchair transport"] },
  { name: "Workforce Solutions Capital Area", type: "Employment", distance: "3.1 mi", phone: "(512) 555-0334", address: "6505 Airport Blvd", services: ["Job training", "Resume assistance", "Career counseling"] },
  { name: "Family Safety Center", type: "Safety", distance: "1.7 mi", phone: "(512) 555-0411", address: "8701 Research Blvd", services: ["Crisis intervention", "Safety planning", "Legal advocacy"] },
  { name: "United Way 211 Services", type: "Social Support", distance: "0.3 mi", phone: "211", address: "2000 E MLK Jr Blvd", services: ["Resource navigation", "Benefits screening", "Support groups"] },
];

const DEMO_HISTORY: SDOHAssessment[] = [
  {
    id: "SDOH-001",
    patient_id: "P-10042",
    domains: [
      { domain: "Housing", risk_level: "high", score: 85, factors: ["Unstable housing", "Affordability concern"] },
      { domain: "Food", risk_level: "some", score: 55, factors: ["Occasional food insecurity"] },
      { domain: "Transportation", risk_level: "none", score: 10, factors: [] },
      { domain: "Employment", risk_level: "high", score: 78, factors: ["Unemployed", "Financial strain"] },
      { domain: "Education", risk_level: "none", score: 15, factors: [] },
      { domain: "Social Support", risk_level: "some", score: 50, factors: ["Limited social network"] },
      { domain: "Safety", risk_level: "none", score: 5, factors: [] },
    ],
    overall_risk: "High",
    recommendations: ["Connect with housing assistance program", "Enroll in SNAP benefits", "Refer to workforce development"],
    resources: [{ name: "Safe Harbor Housing", type: "Housing Support" }, { name: "Community Food Bank", type: "Food Assistance" }],
    assessed_at: "2026-03-10T14:30:00Z",
  },
  {
    id: "SDOH-002",
    patient_id: "P-10078",
    domains: [
      { domain: "Housing", risk_level: "none", score: 10, factors: [] },
      { domain: "Food", risk_level: "none", score: 12, factors: [] },
      { domain: "Transportation", risk_level: "some", score: 45, factors: ["Limited vehicle access"] },
      { domain: "Employment", risk_level: "none", score: 8, factors: [] },
      { domain: "Education", risk_level: "some", score: 48, factors: ["Language barrier"] },
      { domain: "Social Support", risk_level: "none", score: 20, factors: [] },
      { domain: "Safety", risk_level: "none", score: 5, factors: [] },
    ],
    overall_risk: "Low",
    recommendations: ["Provide medical transportation vouchers", "Connect with interpreter services"],
    resources: [{ name: "Metro Health Transit Program", type: "Transportation" }],
    assessed_at: "2026-03-08T09:15:00Z",
  },
  {
    id: "SDOH-003",
    patient_id: "P-10091",
    domains: [
      { domain: "Housing", risk_level: "some", score: 40, factors: ["Crowded living conditions"] },
      { domain: "Food", risk_level: "high", score: 80, factors: ["Food desert area", "No transportation to grocery"] },
      { domain: "Transportation", risk_level: "high", score: 75, factors: ["No vehicle", "Limited public transit"] },
      { domain: "Employment", risk_level: "some", score: 55, factors: ["Underemployed"] },
      { domain: "Education", risk_level: "none", score: 18, factors: [] },
      { domain: "Social Support", risk_level: "high", score: 72, factors: ["Socially isolated", "Caregiver burden"] },
      { domain: "Safety", risk_level: "some", score: 42, factors: ["Neighborhood safety concerns"] },
    ],
    overall_risk: "Critical",
    recommendations: ["Urgent food assistance referral", "Transportation program enrollment", "Caregiver support services", "Community health worker visit"],
    resources: [{ name: "Community Food Bank", type: "Food Assistance" }, { name: "Metro Health Transit Program", type: "Transportation" }],
    assessed_at: "2026-03-05T11:45:00Z",
  },
  {
    id: "SDOH-004",
    patient_id: "P-10055",
    domains: [
      { domain: "Housing", risk_level: "none", score: 5, factors: [] },
      { domain: "Food", risk_level: "none", score: 8, factors: [] },
      { domain: "Transportation", risk_level: "none", score: 10, factors: [] },
      { domain: "Employment", risk_level: "some", score: 35, factors: ["Part-time only"] },
      { domain: "Education", risk_level: "none", score: 12, factors: [] },
      { domain: "Social Support", risk_level: "some", score: 40, factors: ["New to area"] },
      { domain: "Safety", risk_level: "none", score: 5, factors: [] },
    ],
    overall_risk: "Moderate",
    recommendations: ["Explore full-time employment resources", "Connect with community welcome programs"],
    resources: [{ name: "Workforce Solutions Capital Area", type: "Employment" }],
    assessed_at: "2026-03-01T16:20:00Z",
  },
];

/* ── Helpers ───────────────────────────────────────────────────────────────── */

const overallRiskBadge = (risk: string) => {
  const r = risk.toLowerCase();
  if (r === "critical") return "bg-purple-100 text-purple-800 border border-purple-300";
  if (r === "high") return "bg-red-100 text-red-700 border border-red-300";
  if (r === "moderate") return "bg-yellow-100 text-yellow-700 border border-yellow-300";
  return "bg-green-100 text-green-700 border border-green-300";
};

const riskBarColor = (level: string) => {
  const l = level.toLowerCase();
  if (l === "high") return "bg-red-500";
  if (l === "some" || l === "moderate") return "bg-yellow-500";
  return "bg-green-500";
};

const riskBarWidth = (score: number) => Math.max(8, Math.min(100, score));

const typeBadgeColor = (type: string) => {
  const t = type.toLowerCase();
  if (t.includes("food")) return "bg-orange-100 text-orange-700";
  if (t.includes("housing")) return "bg-blue-100 text-blue-700";
  if (t.includes("transport")) return "bg-purple-100 text-purple-700";
  if (t.includes("employ")) return "bg-teal-100 text-teal-700";
  if (t.includes("safety")) return "bg-red-100 text-red-700";
  if (t.includes("social")) return "bg-pink-100 text-pink-700";
  return "bg-gray-100 text-gray-700";
};

const trendIndicator = (risk: string) => {
  const r = risk.toLowerCase();
  if (r === "critical" || r === "high") return { icon: "\u2191", color: "text-red-600" };
  if (r === "moderate") return { icon: "\u2192", color: "text-yellow-600" };
  return { icon: "\u2193", color: "text-green-600" };
};

/* ── Component ─────────────────────────────────────────────────────────────── */

export default function SDOHPage() {
  /* Assessment form state */
  const [patientId, setPatientId] = useState("");
  const [responses, setResponses] = useState<Record<string, RiskLevel>>(
    Object.fromEntries(DOMAINS.map((d) => [d.key, "none" as RiskLevel]))
  );
  const [submitting, setSubmitting] = useState(false);

  /* Results state */
  const [result, setResult] = useState<SDOHAssessment | null>(null);

  /* Community resources state */
  const [selectedNeeds, setSelectedNeeds] = useState<string[]>([]);
  const [zipCode, setZipCode] = useState("");
  const [resources, setResources] = useState<CommunityResource[]>([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [referredResources, setReferredResources] = useState<Set<string>>(new Set());

  /* History state */
  const [history, setHistory] = useState<SDOHAssessment[]>(DEMO_HISTORY);

  /* ── Handlers ──────────────────────────────────────────────────────────── */

  const handleDomainChange = (domain: string, value: RiskLevel) => {
    setResponses((prev: Record<string, RiskLevel>) => ({ ...prev, [domain]: value }));
  };

  const toggleNeed = (need: string) => {
    setSelectedNeeds((prev: string[]) =>
      prev.includes(need) ? prev.filter((n: string) => n !== need) : [...prev, need]
    );
  };

  const handleSubmitAssessment = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId.trim()) return;
    setSubmitting(true);
    try {
      const assessment = await runSDOHAssessment({ patient_id: patientId, responses });
      setResult(assessment);
      setHistory((prev: SDOHAssessment[]) => [assessment, ...prev]);
    } catch {
      // API unavailable -- use demo data
      const domainResults = DOMAINS.map((d) => {
        const risk = responses[d.key];
        const score = risk === "high" ? 70 + Math.floor(Math.random() * 25) : risk === "some" ? 30 + Math.floor(Math.random() * 30) : Math.floor(Math.random() * 20);
        const factors: string[] = [];
        if (risk === "high") factors.push(`Significant ${d.label.toLowerCase()} concerns identified`);
        if (risk === "some") factors.push(`Moderate ${d.label.toLowerCase()} concerns`);
        return { domain: d.label, risk_level: risk === "none" ? "none" : risk === "some" ? "some" : "high", score, factors };
      });

      const highCount = Object.values(responses).filter((v) => v === "high").length;
      const someCount = Object.values(responses).filter((v) => v === "some").length;
      const overall = highCount >= 3 ? "Critical" : highCount >= 1 ? "High" : someCount >= 2 ? "Moderate" : "Low";

      const recs: string[] = [];
      if (responses.housing === "high") recs.push("Urgent: Connect patient with emergency housing assistance");
      if (responses.food !== "none") recs.push("Enroll patient in food assistance program (SNAP/WIC)");
      if (responses.transportation !== "none") recs.push("Arrange medical transportation services");
      if (responses.employment !== "none") recs.push("Refer to workforce development and financial counseling");
      if (responses.education !== "none") recs.push("Provide health literacy materials in preferred language");
      if (responses.social_support !== "none") recs.push("Connect with community support groups and social services");
      if (responses.safety !== "none") recs.push("Conduct detailed safety assessment; provide crisis hotline information");
      if (recs.length === 0) recs.push("No immediate social risk factors identified. Continue routine screening.");

      const matchedResources = DEMO_RESOURCES.filter((r) => {
        const rt = r.type.toLowerCase();
        if (responses.housing !== "none" && rt.includes("housing")) return true;
        if (responses.food !== "none" && rt.includes("food")) return true;
        if (responses.transportation !== "none" && rt.includes("transport")) return true;
        if (responses.employment !== "none" && rt.includes("employ")) return true;
        if (responses.safety !== "none" && rt.includes("safety")) return true;
        if (responses.social_support !== "none" && rt.includes("social")) return true;
        return false;
      });

      const demo: SDOHAssessment = {
        id: `SDOH-${Date.now().toString(36).toUpperCase()}`,
        patient_id: patientId,
        domains: domainResults,
        overall_risk: overall,
        recommendations: recs,
        resources: matchedResources.map((r) => ({ name: r.name, type: r.type, distance: r.distance, phone: r.phone, address: r.address })),
        assessed_at: new Date().toISOString(),
      };
      setResult(demo);
      setHistory((prev: SDOHAssessment[]) => [demo, ...prev]);
    } finally {
      setSubmitting(false);
    }
  }, [patientId, responses]);

  const handleFindResources = useCallback(async () => {
    if (selectedNeeds.length === 0) return;
    setLoadingResources(true);
    try {
      const data = await fetchCommunityResources({ needs: selectedNeeds, zip_code: zipCode || undefined });
      setResources(data.resources);
    } catch {
      // API unavailable -- filter demo data
      const filtered = DEMO_RESOURCES.filter((r) =>
        selectedNeeds.some((n: string) => r.type.toLowerCase().includes(n.toLowerCase()) || r.services.some((s: string) => s.toLowerCase().includes(n.toLowerCase())))
      );
      setResources(filtered.length > 0 ? filtered : DEMO_RESOURCES.slice(0, 3));
    } finally {
      setLoadingResources(false);
    }
  }, [selectedNeeds, zipCode]);

  const handleRefer = (resourceName: string) => {
    setReferredResources((prev: Set<string>) => new Set(prev).add(resourceName));
  };

  /* ── Render ────────────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Social Determinants of Health</h1>
        <p className="text-sm text-gray-500">Assess social risk factors and connect patients to community resources</p>
      </div>

      {/* Main Layout: Form + Sidebar */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left 2/3: Assessment Form + Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Assessment Form */}
          <form onSubmit={handleSubmitAssessment} className="card card-hover animate-fade-in-up">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">SDOH Screening Questionnaire</h2>

            {/* Patient ID */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">Patient ID</label>
              <input
                type="text"
                required
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                className="w-full max-w-xs rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                placeholder="e.g. P-10042"
              />
            </div>

            {/* Domain Questions */}
            <div className="space-y-4">
              {DOMAINS.map((domain, idx) => (
                <div
                  key={domain.key}
                  className="rounded-lg border border-gray-200 p-4 hover:border-healthos-200 transition-colors"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-gray-900">{domain.label}</h3>
                      <p className="text-xs text-gray-500 mt-0.5">{domain.description}</p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      {RISK_OPTIONS.map((opt) => (
                        <label
                          key={opt.value}
                          className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium cursor-pointer transition-all ${
                            responses[domain.key] === opt.value
                              ? opt.color + " ring-1 ring-offset-1 " + (opt.value === "none" ? "ring-green-400" : opt.value === "some" ? "ring-yellow-400" : "ring-red-400")
                              : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50"
                          }`}
                        >
                          <input
                            type="radio"
                            name={domain.key}
                            value={opt.value}
                            checked={responses[domain.key] === opt.value}
                            onChange={() => handleDomainChange(domain.key, opt.value)}
                            className="sr-only"
                          />
                          {opt.label}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Submit */}
            <div className="mt-6 flex justify-end">
              <button
                type="submit"
                disabled={submitting || !patientId.trim()}
                className="rounded-lg bg-healthos-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Assessing...
                  </span>
                ) : (
                  "Submit Assessment"
                )}
              </button>
            </div>
          </form>

          {/* Results Panel */}
          {result && (
            <div className="card animate-fade-in-up space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Assessment Results</h2>
                <span className={`rounded-full px-3 py-1 text-xs font-bold ${overallRiskBadge(result.overall_risk)}`}>
                  {result.overall_risk} Risk
                </span>
              </div>

              {/* Domain Risk Visualization */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Risk by Domain</h3>
                <div className="space-y-3">
                  {result.domains.map((d) => (
                    <div key={d.domain} className="flex items-center gap-3">
                      <span className="w-28 text-xs font-medium text-gray-600 text-right shrink-0">{d.domain}</span>
                      <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${riskBarColor(d.risk_level)}`}
                          style={{ width: `${riskBarWidth(d.score)}%` }}
                        />
                      </div>
                      <span className="w-10 text-xs font-semibold text-gray-700 text-right">{d.score}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Recommendations */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">AI-Generated Recommendations</h3>
                <ul className="space-y-2">
                  {result.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-healthos-100 text-healthos-700 text-xs font-bold">
                        {i + 1}
                      </span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Matched Resources */}
              {result.resources.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Matched Community Resources</h3>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {result.resources.map((r) => (
                      <div key={r.name} className="rounded-lg border border-gray-200 p-3 hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{r.name}</p>
                            <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${typeBadgeColor(r.type)}`}>
                              {r.type}
                            </span>
                          </div>
                        </div>
                        {(r.phone || r.address) && (
                          <div className="mt-2 space-y-0.5 text-xs text-gray-500">
                            {r.phone && <p>Tel: {r.phone}</p>}
                            {r.address && <p>{r.address}</p>}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Sidebar: Community Resources */}
        <div className="space-y-6">
          <div className="card card-hover animate-fade-in-up">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Community Resource Finder</h2>

            {/* Needs Checkboxes */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Select Needs</label>
              <div className="flex flex-wrap gap-2">
                {NEEDS_OPTIONS.map((need) => (
                  <label
                    key={need}
                    className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium cursor-pointer transition-all ${
                      selectedNeeds.includes(need)
                        ? "bg-healthos-100 text-healthos-700 border-healthos-300"
                        : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedNeeds.includes(need)}
                      onChange={() => toggleNeed(need)}
                      className="sr-only"
                    />
                    {need}
                  </label>
                ))}
              </div>
            </div>

            {/* Zip Code */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Zip Code</label>
              <input
                type="text"
                value={zipCode}
                onChange={(e) => setZipCode(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                placeholder="e.g. 78701"
                maxLength={5}
              />
            </div>

            <button
              onClick={handleFindResources}
              disabled={selectedNeeds.length === 0 || loadingResources}
              className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
            >
              {loadingResources ? "Searching..." : "Find Resources"}
            </button>
          </div>

          {/* Resource Cards */}
          {resources.length > 0 && (
            <div className="space-y-3 animate-fade-in-up">
              {resources.map((r) => (
                <div key={r.name} className="card card-hover">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="text-sm font-semibold text-gray-900 leading-tight">{r.name}</h3>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${typeBadgeColor(r.type)}`}>
                      {r.type}
                    </span>
                  </div>
                  <div className="space-y-1 text-xs text-gray-500 mb-3">
                    <p className="flex items-center gap-1">
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" /></svg>
                      {r.distance} &middot; {r.address}
                    </p>
                    <p className="flex items-center gap-1">
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" /></svg>
                      {r.phone}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {r.services.map((s) => (
                      <span key={s} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600">{s}</span>
                    ))}
                  </div>
                  <button
                    onClick={() => handleRefer(r.name)}
                    disabled={referredResources.has(r.name)}
                    className={`w-full rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      referredResources.has(r.name)
                        ? "bg-green-100 text-green-700 border border-green-300 cursor-default"
                        : "bg-healthos-500 text-white hover:bg-healthos-600"
                    }`}
                  >
                    {referredResources.has(r.name) ? "Referral Sent" : "Refer Patient"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Assessment History */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Assessment History</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="pb-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="pb-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Patient</th>
                <th className="pb-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Overall Risk</th>
                <th className="pb-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Key Domains</th>
                <th className="pb-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trend</th>
                <th className="pb-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {history.map((h) => {
                const keyDomains = h.domains.filter((d) => d.risk_level !== "none" && d.score > 30);
                const trend = trendIndicator(h.overall_risk);
                return (
                  <tr key={h.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 pr-4 text-gray-700 whitespace-nowrap">
                      {new Date(h.assessed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </td>
                    <td className="py-3 pr-4 font-medium text-gray-900 whitespace-nowrap">{h.patient_id}</td>
                    <td className="py-3 pr-4">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${overallRiskBadge(h.overall_risk)}`}>
                        {h.overall_risk}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex flex-wrap gap-1">
                        {keyDomains.length > 0
                          ? keyDomains.map((d) => (
                              <span key={d.domain} className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${riskBarColor(d.risk_level) === "bg-red-500" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
                                {d.domain}
                              </span>
                            ))
                          : <span className="text-xs text-gray-400">None flagged</span>
                        }
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`text-lg font-bold ${trend.color}`}>{trend.icon}</span>
                    </td>
                    <td className="py-3">
                      <button
                        onClick={() => setResult(h)}
                        className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
