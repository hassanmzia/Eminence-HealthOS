"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchExecutiveSummary,
  fetchKPIScorecard,
  fetchTrendDigest,
  analyzePopulationHealth,
  riskStratification,
  fetchQualityMetrics,
  fetchPopulationKPIs,
  fetchCostDrivers,
  fetchOpportunities,
  predictReadmissionRisk,
  createCohort,
  fetchCohortTemplates,
  trackOutcomes,
  analyzeCosts,
  fetchRiskDistribution,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface KPIStat {
  label: string;
  value: string;
  change: string;
  up: boolean;
  icon: string;
}

interface KPICard {
  metric: string;
  value: string;
  change: string;
  up: boolean;
  sparkline: number[];
}

interface TrendInsight {
  icon: string;
  title: string;
  description: string;
  severity: "positive" | "warning" | "neutral";
}

interface DepartmentCard {
  name: string;
  patients: number;
  satisfaction: number;
  costPerVisit: string;
  trend: string;
}

interface CostDriver {
  category: string;
  amount: string;
  trend: string;
  trendUp: boolean;
  pctOfTotal: number;
}

interface Opportunity {
  title: string;
  savings: string;
  confidence: number;
  description: string;
}

interface RiskCostPoint {
  id: string;
  riskScore: number;
  cost: number;
  label: string;
}

interface OutcomeMetric {
  metric: string;
  improvement: number;
  ciLow: number;
  ciHigh: number;
  pValue: number;
}

interface AdherenceRate {
  category: string;
  rate: number;
  target: number;
}

interface CostComparison {
  category: string;
  before: number;
  after: number;
}

// ── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_STATS: KPIStat[] = [
  { label: "Population Size", value: "12,847", change: "+3.2%", up: true, icon: "👥" },
  { label: "Risk Score Avg", value: "0.34", change: "-0.05", up: false, icon: "📊" },
  { label: "Readmission Rate", value: "8.2%", change: "-1.3%", up: false, icon: "🔄" },
  { label: "Cost per Patient", value: "$4,280", change: "+2.1%", up: true, icon: "💰" },
  { label: "Quality Score", value: "0.87", change: "+0.04", up: true, icon: "⭐" },
  { label: "Active Cohorts", value: "24", change: "+6", up: true, icon: "🧬" },
];

const DEMO_KPI_SCORECARD: KPICard[] = [
  { metric: "Patient Satisfaction", value: "92.4%", change: "+3.1%", up: true, sparkline: [65, 72, 78, 80, 85, 88, 92] },
  { metric: "Avg Length of Stay", value: "4.2 days", change: "-0.8d", up: false, sparkline: [6, 5.8, 5.5, 5.0, 4.8, 4.5, 4.2] },
  { metric: "ED Wait Time", value: "18 min", change: "-12 min", up: false, sparkline: [42, 38, 35, 28, 24, 20, 18] },
  { metric: "Bed Occupancy", value: "84.6%", change: "+1.2%", up: true, sparkline: [78, 80, 82, 81, 83, 84, 85] },
  { metric: "Readmission (30d)", value: "8.2%", change: "-1.3%", up: false, sparkline: [12, 11, 10, 9.5, 9, 8.5, 8.2] },
  { metric: "Mortality Rate", value: "1.2%", change: "-0.3%", up: false, sparkline: [2.0, 1.8, 1.7, 1.5, 1.4, 1.3, 1.2] },
];

const DEMO_TREND_INSIGHTS: TrendInsight[] = [
  { icon: "📈", title: "Readmission rates declining", description: "30-day readmission has dropped 14% over the past quarter, driven by improved discharge planning protocols and post-discharge follow-up automation.", severity: "positive" },
  { icon: "⚠️", title: "Rising ED utilization in 65+ cohort", description: "Emergency department visits among patients aged 65+ increased 8% this month. Consider expanding chronic disease management outreach.", severity: "warning" },
  { icon: "✅", title: "Quality metrics on target", description: "All HEDIS measures are trending at or above 90th percentile benchmarks. HbA1c control improved 6% with AI-assisted care gap closure.", severity: "positive" },
  { icon: "📊", title: "Cost per encounter stabilizing", description: "After a 12% spike in Q3, cost per encounter has stabilized at $1,240, aligning with the annual budget forecast.", severity: "neutral" },
];

const DEMO_DEPARTMENTS: DepartmentCard[] = [
  { name: "Cardiology", patients: 2140, satisfaction: 94, costPerVisit: "$380", trend: "+2.1%" },
  { name: "Oncology", patients: 1280, satisfaction: 91, costPerVisit: "$520", trend: "-1.4%" },
  { name: "Primary Care", patients: 5420, satisfaction: 89, costPerVisit: "$180", trend: "+0.8%" },
  { name: "Orthopedics", patients: 1640, satisfaction: 93, costPerVisit: "$440", trend: "-0.5%" },
];

const DEMO_RISK_DISTRIBUTION = [
  { level: "Low", count: 7820, pct: 60.9, color: "bg-emerald-500" },
  { level: "Moderate", count: 3210, pct: 25.0, color: "bg-yellow-500" },
  { level: "High", count: 1340, pct: 10.4, color: "bg-orange-500" },
  { level: "Critical", count: 477, pct: 3.7, color: "bg-red-500" },
];

const DEMO_QUALITY_METRICS = [
  { label: "HbA1c Control (<7%)", value: 72.4, target: 75, unit: "%" },
  { label: "BP Control (<140/90)", value: 68.1, target: 70, unit: "%" },
  { label: "Preventive Screenings", value: 81.3, target: 85, unit: "%" },
];

const DEMO_COST_DRIVERS: CostDriver[] = [
  { category: "Inpatient Services", amount: "$18.4M", trend: "+3.2%", trendUp: true, pctOfTotal: 34.2 },
  { category: "Pharmaceuticals", amount: "$12.1M", trend: "+5.8%", trendUp: true, pctOfTotal: 22.5 },
  { category: "Outpatient Procedures", amount: "$8.7M", trend: "-1.4%", trendUp: false, pctOfTotal: 16.2 },
  { category: "Emergency Dept", amount: "$6.3M", trend: "+2.1%", trendUp: true, pctOfTotal: 11.7 },
  { category: "Diagnostics & Labs", amount: "$4.8M", trend: "+0.9%", trendUp: true, pctOfTotal: 8.9 },
  { category: "Administrative", amount: "$3.5M", trend: "-2.3%", trendUp: false, pctOfTotal: 6.5 },
];

const DEMO_OPPORTUNITIES: Opportunity[] = [
  { title: "Reduce avoidable ED visits", savings: "$2.4M/yr", confidence: 87, description: "Redirect non-emergent cases to urgent care and telehealth with AI triage." },
  { title: "Optimize LOS for CHF patients", savings: "$1.8M/yr", confidence: 82, description: "Implement predictive discharge planning to reduce CHF stays by 0.6 days." },
  { title: "Generic drug substitution", savings: "$1.2M/yr", confidence: 94, description: "Switch 340 patients to therapeutically equivalent generics." },
  { title: "Care gap closure automation", savings: "$890K/yr", confidence: 78, description: "Automate outreach for overdue preventive screenings and follow-ups." },
];

const DEMO_RISK_COST_POINTS: RiskCostPoint[] = [
  { id: "1", riskScore: 12, cost: 1200, label: "Low-A" },
  { id: "2", riskScore: 22, cost: 2800, label: "Low-B" },
  { id: "3", riskScore: 35, cost: 4200, label: "Mod-A" },
  { id: "4", riskScore: 48, cost: 6800, label: "Mod-B" },
  { id: "5", riskScore: 55, cost: 8200, label: "Mod-C" },
  { id: "6", riskScore: 65, cost: 12400, label: "High-A" },
  { id: "7", riskScore: 72, cost: 15600, label: "High-B" },
  { id: "8", riskScore: 80, cost: 22000, label: "Crit-A" },
  { id: "9", riskScore: 88, cost: 28400, label: "Crit-B" },
  { id: "10", riskScore: 94, cost: 34200, label: "Crit-C" },
];

const DEMO_COHORT_TEMPLATES = [
  { id: "t1", name: "Diabetes Management", description: "Patients with Type 2 Diabetes, HbA1c > 7%" },
  { id: "t2", name: "Heart Failure Risk", description: "Patients with CHF risk factors or prior events" },
  { id: "t3", name: "High-Cost Utilizers", description: "Top 5% patients by total cost of care" },
  { id: "t4", name: "Preventive Care Gaps", description: "Patients overdue for screenings or vaccines" },
  { id: "t5", name: "Readmission Risk", description: "Recently discharged with readmission risk > 30%" },
];

const DEMO_OUTCOME_METRICS: OutcomeMetric[] = [
  { metric: "HbA1c Reduction", improvement: 14.2, ciLow: 11.8, ciHigh: 16.6, pValue: 0.001 },
  { metric: "BP Control Rate", improvement: 22.5, ciLow: 18.3, ciHigh: 26.7, pValue: 0.003 },
  { metric: "Readmission Reduction", improvement: 31.0, ciLow: 24.2, ciHigh: 37.8, pValue: 0.0001 },
  { metric: "Patient Satisfaction", improvement: 8.4, ciLow: 5.6, ciHigh: 11.2, pValue: 0.012 },
];

const DEMO_ADHERENCE_RATES: AdherenceRate[] = [
  { category: "Medication", rate: 78, target: 85 },
  { category: "Appointment", rate: 82, target: 90 },
  { category: "Lab Follow-up", rate: 71, target: 80 },
  { category: "Lifestyle Changes", rate: 56, target: 70 },
  { category: "Remote Monitoring", rate: 88, target: 85 },
];

const DEMO_COST_COMPARISON: CostComparison[] = [
  { category: "ED Visits", before: 4200, after: 2800 },
  { category: "Inpatient Days", before: 8400, after: 6100 },
  { category: "Medications", before: 3200, after: 2900 },
  { category: "Specialist Visits", before: 2100, after: 1800 },
];

// ── Tabs ──────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "executive", label: "Executive Dashboard" },
  { id: "population", label: "Population Health" },
  { id: "cost-risk", label: "Cost & Risk Analysis" },
  { id: "cohort", label: "Cohort Builder" },
  { id: "outcomes", label: "Outcomes Tracking" },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ── Main Component ───────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("executive");
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [loading, setLoading] = useState(false);

  // Set initial refresh time on client only to avoid hydration mismatch
  useEffect(() => { setLastRefreshed(new Date()); }, []);

  // Executive state
  const [kpiScorecard, setKpiScorecard] = useState<KPICard[]>(DEMO_KPI_SCORECARD);
  const [trendInsights, setTrendInsights] = useState<TrendInsight[]>(DEMO_TREND_INSIGHTS);
  const [departments, setDepartments] = useState<DepartmentCard[]>(DEMO_DEPARTMENTS);

  // Population state
  const [riskDist, setRiskDist] = useState(DEMO_RISK_DISTRIBUTION);
  const [qualityMetrics, setQualityMetrics] = useState(DEMO_QUALITY_METRICS);
  const [popKpis, setPopKpis] = useState(DEMO_STATS);

  // Cost & Risk state
  const [costDrivers, setCostDrivers] = useState<CostDriver[]>(DEMO_COST_DRIVERS);
  const [opportunities, setOpportunities] = useState<Opportunity[]>(DEMO_OPPORTUNITIES);
  const [riskCostPoints] = useState<RiskCostPoint[]>(DEMO_RISK_COST_POINTS);
  const [readmissionForm, setReadmissionForm] = useState({ patientId: "", age: "", diagnosis: "", priorAdmissions: "" });
  const [readmissionResult, setReadmissionResult] = useState<{ risk: number; level: string } | null>(null);

  // Cohort state
  const [cohortTemplates] = useState(DEMO_COHORT_TEMPLATES);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [cohortFilters, setCohortFilters] = useState({ ageMin: "18", ageMax: "85", diagnosis: "", riskLevel: "all", medication: "" });
  const [cohortResult, setCohortResult] = useState<Record<string, unknown> | null>(null);

  // Outcomes state
  const [outcomeMetrics, setOutcomeMetrics] = useState<OutcomeMetric[]>(DEMO_OUTCOME_METRICS);
  const [adherenceRates, setAdherenceRates] = useState<AdherenceRate[]>(DEMO_ADHERENCE_RATES);
  const [costComparison, setCostComparison] = useState<CostComparison[]>(DEMO_COST_COMPARISON);

  // ── Data Loading ─────────────────────────────────────────────────────────

  const loadExecutiveData = useCallback(async () => {
    try {
      const [summaryRes, scorecardRes, trendsRes] = await Promise.allSettled([
        fetchExecutiveSummary(),
        fetchKPIScorecard({ period: "quarterly" }),
        fetchTrendDigest(),
      ]);
      if (scorecardRes.status === "fulfilled") {
        const d = scorecardRes.value as Record<string, unknown>;
        if (d.scorecard && Array.isArray(d.scorecard)) {
          // Map backend scorecard shape to frontend KPICard shape
          const mapped = (d.scorecard as Array<Record<string, unknown>>).map((item) => ({
            metric: (item.kpi ?? item.metric ?? "") as string,
            value: String(item.actual ?? item.value ?? ""),
            change: item.change != null ? String(item.change) : `${((item.variance as number) ?? 0) > 0 ? "+" : ""}${(((item.variance as number) ?? 0) * 100).toFixed(1)}%`,
            up: item.up != null ? Boolean(item.up) : (item.status === "on_target" || (item.variance as number) >= 0),
            sparkline: (item.sparkline as number[]) ?? [],
          }));
          setKpiScorecard(mapped);
        }
      }
      if (trendsRes.status === "fulfilled") {
        const d = trendsRes.value as Record<string, unknown>;
        if (d.insights) setTrendInsights(d.insights as TrendInsight[]);
      }
      if (summaryRes.status === "fulfilled") {
        const d = summaryRes.value as Record<string, unknown>;
        if (d.departments) setDepartments(d.departments as DepartmentCard[]);
      }
    } catch {
      // keep demo data
    }
  }, []);

  const loadPopulationData = useCallback(async () => {
    try {
      const [riskRes, qualRes, kpiRes] = await Promise.allSettled([
        fetchRiskDistribution({ period: "current" }),
        fetchQualityMetrics({ period: "quarterly" }),
        fetchPopulationKPIs(),
      ]);
      if (riskRes.status === "fulfilled") {
        const d = riskRes.value as Record<string, unknown>;
        if (Array.isArray(d.distribution)) setRiskDist(d.distribution as typeof DEMO_RISK_DISTRIBUTION);
      }
      if (qualRes.status === "fulfilled") {
        const d = qualRes.value as Record<string, unknown>;
        if (d.metrics) setQualityMetrics(d.metrics as typeof DEMO_QUALITY_METRICS);
      }
      if (kpiRes.status === "fulfilled") {
        const d = kpiRes.value as Record<string, unknown>;
        if (d.kpis) setPopKpis(d.kpis as KPIStat[]);
      }
    } catch {
      // keep demo data
    }
  }, []);

  const loadCostData = useCallback(async () => {
    try {
      const [driversRes, oppsRes] = await Promise.allSettled([
        fetchCostDrivers({ period: "quarterly" }),
        fetchOpportunities({ threshold: 0.7 }),
      ]);
      if (driversRes.status === "fulfilled") {
        const d = driversRes.value as Record<string, unknown>;
        if (d.drivers) setCostDrivers(d.drivers as CostDriver[]);
      }
      if (oppsRes.status === "fulfilled") {
        const d = oppsRes.value as Record<string, unknown>;
        if (d.opportunities) setOpportunities(d.opportunities as Opportunity[]);
      }
    } catch {
      // keep demo data
    }
  }, []);

  const loadOutcomesData = useCallback(async () => {
    try {
      const [outcomesRes, costsRes] = await Promise.allSettled([
        trackOutcomes({ period: "quarterly" }),
        analyzeCosts({ period: "quarterly" }),
      ]);
      if (outcomesRes.status === "fulfilled") {
        const d = outcomesRes.value as Record<string, unknown>;
        if (d.metrics) setOutcomeMetrics(d.metrics as OutcomeMetric[]);
        if (d.adherence) setAdherenceRates(d.adherence as AdherenceRate[]);
      }
      if (costsRes.status === "fulfilled") {
        const d = costsRes.value as Record<string, unknown>;
        if (d.comparison) setCostComparison(d.comparison as CostComparison[]);
      }
    } catch {
      // keep demo data
    }
  }, []);

  const refreshData = useCallback(async () => {
    setLoading(true);
    await Promise.allSettled([
      loadExecutiveData(),
      loadPopulationData(),
      loadCostData(),
      loadOutcomesData(),
    ]);
    setLastRefreshed(new Date());
    setLoading(false);
  }, [loadExecutiveData, loadPopulationData, loadCostData, loadOutcomesData]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleReadmissionPredict = async () => {
    try {
      const res = await predictReadmissionRisk({
        patient_id: readmissionForm.patientId,
        age: Number(readmissionForm.age),
        diagnosis: readmissionForm.diagnosis,
        prior_admissions: Number(readmissionForm.priorAdmissions),
      });
      const d = res as Record<string, unknown>;
      setReadmissionResult({
        risk: (d.risk_score as number) ?? 0.34,
        level: (d.risk_level as string) ?? "moderate",
      });
    } catch {
      setReadmissionResult({ risk: 0.34, level: "moderate" });
    }
  };

  const handleStratify = async () => {
    setLoading(true);
    try {
      await riskStratification({ recalculate: true });
      await loadPopulationData();
    } catch {
      // keep current data
    }
    setLoading(false);
  };

  const handleCreateCohort = async () => {
    try {
      const res = await createCohort({
        template: selectedTemplate || undefined,
        filters: {
          age_min: Number(cohortFilters.ageMin),
          age_max: Number(cohortFilters.ageMax),
          diagnosis: cohortFilters.diagnosis || undefined,
          risk_level: cohortFilters.riskLevel !== "all" ? cohortFilters.riskLevel : undefined,
          medication: cohortFilters.medication || undefined,
        },
      });
      setCohortResult(res as Record<string, unknown>);
    } catch {
      setCohortResult({
        cohort_id: "demo-cohort-001",
        name: selectedTemplate ? cohortTemplates.find((t) => t.id === selectedTemplate)?.name : "Custom Cohort",
        total_patients: 847,
        demographics: { avg_age: 62, male_pct: 48, female_pct: 52 },
        clinical: { avg_risk_score: 0.42, top_conditions: ["Diabetes Type 2", "Hypertension", "CHF"], avg_medications: 4.2 },
        created_at: new Date().toISOString(),
      });
    }
  };

  const handleGenerateReport = async () => {
    const { generatePDF } = await import("@/lib/pdf-export");
    await generatePDF({
      title: "Analytics Report",
      subtitle: `${activeTab === "executive" ? "Executive Dashboard" : activeTab === "cost" ? "Cost & Risk Analysis" : activeTab === "population" ? "Population Health" : "Cohort Builder"} — ${new Date().toLocaleDateString()}`,
      generatedBy: "Eminence HealthOS",
      filename: `analytics-report-${new Date().toISOString().split("T")[0]}.pdf`,
      sections: [
        {
          title: "Key Performance Indicators",
          table: {
            headers: ["Metric", "Value", "Change"],
            rows: popKpis.map((k) => [k.label, k.value, `${k.up ? "↑" : "↓"} ${k.change}`]),
          },
        },
        {
          title: "KPI Scorecard",
          table: {
            headers: ["Metric", "Value", "Change", "Status"],
            rows: kpiScorecard.map((k) => [k.metric, k.value, `${k.up ? "↑" : "↓"} ${k.change}`, k.up ? "On Track" : "Needs Attention"]),
          },
        },
        {
          title: "Cost Drivers",
          table: {
            headers: ["Category", "Amount", "Trend", "% of Total"],
            rows: costDrivers.map((c) => [c.category, c.amount, `${c.trendUp ? "↑" : "↓"} ${c.trend}`, `${c.pctOfTotal}%`]),
          },
        },
      ],
    });
  };

  // ── Render Helpers ───────────────────────────────────────────────────────

  const totalRiskPatients = riskDist.reduce((sum, r) => sum + r.count, 0);

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Analytics &amp; Intelligence</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Comprehensive insights across population health, costs, outcomes, and cohorts
          </p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Last refreshed: {lastRefreshed ? lastRefreshed.toLocaleTimeString() : "—"} &mdash;{" "}
            <button onClick={refreshData} className="text-healthos-600 hover:underline" disabled={loading}>
              {loading ? "Refreshing..." : "Refresh now"}
            </button>
          </p>
        </div>
        <button
          onClick={handleGenerateReport}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:bg-healthos-700 hover:shadow-md active:scale-[0.98]"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Generate Report
        </button>
      </div>

      {/* ── Stats Bar ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {DEMO_STATS.map((stat, i) => (
          <div key={stat.label} className="card card-hover animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 truncate">{stat.label}</p>
              <span className="text-base">{stat.icon}</span>
            </div>
            <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{stat.value}</p>
            <p className={`mt-1 text-xs font-semibold ${stat.up ? "text-emerald-600" : "text-red-500"}`}>
              {stat.up ? "↑" : "↓"} {stat.change}
            </p>
          </div>
        ))}
      </div>

      {/* ── Tabs ────────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-1 overflow-x-auto" aria-label="Analytics tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab Content ─────────────────────────────────────────────────── */}
      <div className="animate-fade-in-up">
        {activeTab === "executive" && (
          <ExecutiveDashboard
            kpiScorecard={kpiScorecard}
            trendInsights={trendInsights}
            departments={departments}
          />
        )}
        {activeTab === "population" && (
          <PopulationHealth
            riskDist={riskDist}
            totalPatients={totalRiskPatients}
            qualityMetrics={qualityMetrics}
            kpis={popKpis}
            onStratify={handleStratify}
            loading={loading}
          />
        )}
        {activeTab === "cost-risk" && (
          <CostRiskAnalysis
            costDrivers={costDrivers}
            opportunities={opportunities}
            riskCostPoints={riskCostPoints}
            readmissionForm={readmissionForm}
            setReadmissionForm={setReadmissionForm}
            readmissionResult={readmissionResult}
            onPredict={handleReadmissionPredict}
          />
        )}
        {activeTab === "cohort" && (
          <CohortBuilder
            templates={cohortTemplates}
            selectedTemplate={selectedTemplate}
            setSelectedTemplate={setSelectedTemplate}
            filters={cohortFilters}
            setFilters={setCohortFilters}
            result={cohortResult}
            onCreate={handleCreateCohort}
          />
        )}
        {activeTab === "outcomes" && (
          <OutcomesTracking
            metrics={outcomeMetrics}
            adherence={adherenceRates}
            costComparison={costComparison}
          />
        )}
      </div>
    </div>
  );
}

// ── Tab 1: Executive Dashboard ───────────────────────────────────────────────

function ExecutiveDashboard({
  kpiScorecard,
  trendInsights,
  departments,
}: {
  kpiScorecard: KPICard[];
  trendInsights: TrendInsight[];
  departments: DepartmentCard[];
}) {
  return (
    <div className="space-y-6">
      {/* KPI Scorecard */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">KPI Scorecard</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {kpiScorecard.map((kpi, i) => (
            <div key={kpi.metric} className="card card-hover animate-fade-in-up" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{kpi.metric}</p>
                  <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-gray-100">{kpi.value}</p>
                </div>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
                    kpi.up ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                  }`}
                >
                  {kpi.up ? "↑" : "↓"} {kpi.change}
                </span>
              </div>
              {/* Sparkline bar representation */}
              <div className="mt-4 flex items-end gap-1 h-8">
                {(kpi.sparkline ?? []).map((val, idx) => {
                  const max = Math.max(...(kpi.sparkline ?? [1]));
                  const heightPct = max > 0 ? (val / max) * 100 : 0;
                  return (
                    <div
                      key={idx}
                      className={`flex-1 rounded-sm transition-all ${
                        idx === (kpi.sparkline ?? []).length - 1 ? "bg-healthos-600" : "bg-healthos-200"
                      }`}
                      style={{ height: `${heightPct}%` }}
                      title={String(val)}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trend Digest */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">AI Trend Digest</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {trendInsights.map((insight, i) => (
            <div
              key={i}
              className={`card card-hover animate-fade-in-up border-l-4 ${
                insight.severity === "positive"
                  ? "border-l-emerald-500"
                  : insight.severity === "warning"
                  ? "border-l-amber-500"
                  : "border-l-blue-500"
              }`}
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="flex gap-3">
                <span className="text-xl">{insight.icon}</span>
                <div>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">{insight.title}</p>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{insight.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Departments */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Department Breakdown</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {departments.map((dept, i) => (
            <div key={dept.name} className="card card-hover animate-fade-in-up" style={{ animationDelay: `${i * 80}ms` }}>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">{dept.name}</h3>
              <div className="mt-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Patients</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{dept.patients.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Satisfaction</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{dept.satisfaction}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Cost/Visit</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{dept.costPerVisit}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Trend</span>
                  <span className={`font-semibold ${dept.trend.startsWith("+") ? "text-emerald-600" : "text-red-500"}`}>
                    {dept.trend}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Tab 2: Population Health ─────────────────────────────────────────────────

function PopulationHealth({
  riskDist,
  totalPatients,
  qualityMetrics,
  kpis,
  onStratify,
  loading,
}: {
  riskDist: typeof DEMO_RISK_DISTRIBUTION;
  totalPatients: number;
  qualityMetrics: typeof DEMO_QUALITY_METRICS;
  kpis: KPIStat[];
  onStratify: () => void;
  loading: boolean;
}) {
  return (
    <div className="space-y-6">
      {/* Risk Stratification */}
      <div className="card animate-fade-in-up">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Risk Stratification</h2>
          <button
            onClick={onStratify}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-all"
          >
            {loading ? (
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            ) : null}
            Stratify
          </button>
        </div>

        {/* Stacked horizontal bar */}
        <div className="space-y-3">
          <div className="flex h-10 w-full overflow-hidden rounded-lg">
            {riskDist.map((r) => (
              <div
                key={r.level}
                className={`${r.color} flex items-center justify-center text-xs font-semibold text-white transition-all duration-500`}
                style={{ width: `${r.pct}%` }}
                title={`${r.level}: ${r.count.toLocaleString()} (${r.pct}%)`}
              >
                {r.pct > 8 ? `${r.pct}%` : ""}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-4">
            {riskDist.map((r) => (
              <div key={r.level} className="flex items-center gap-2 text-sm">
                <span className={`h-3 w-3 rounded-full ${r.color}`} />
                <span className="text-gray-600 dark:text-gray-400">{r.level}:</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{r.count.toLocaleString()}</span>
                <span className="text-gray-500 dark:text-gray-400">({r.pct}%)</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Total population: {totalPatients.toLocaleString()}</p>
        </div>
      </div>

      {/* Quality Metrics */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Quality Metrics</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {qualityMetrics.map((m, i) => {
            const pct = Math.min(m.value, 100);
            const atTarget = m.value >= m.target;
            return (
              <div key={m.label} className="card card-hover animate-fade-in-up" style={{ animationDelay: `${i * 80}ms` }}>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{m.label}</p>
                <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-gray-100">
                  {m.value}
                  <span className="text-lg text-gray-500 dark:text-gray-400">{m.unit}</span>
                </p>
                <div className="mt-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500 dark:text-gray-400">Progress</span>
                    <span className={atTarget ? "text-emerald-600 font-medium" : "text-amber-600 font-medium"}>
                      Target: {m.target}{m.unit}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-800">
                    <div
                      className={`h-2 rounded-full transition-all duration-700 ${atTarget ? "bg-emerald-500" : "bg-amber-500"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Population KPI Tiles */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Population KPIs</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {kpis.map((kpi, i) => (
            <div key={kpi.label} className="card card-hover animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 truncate">{kpi.label}</p>
              <p className="mt-1 text-lg font-bold text-gray-900 dark:text-gray-100">{kpi.value}</p>
              <p className={`mt-1 text-xs font-semibold ${kpi.up ? "text-emerald-600" : "text-red-500"}`}>
                {kpi.up ? "↑" : "↓"} {kpi.change}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Tab 3: Cost & Risk Analysis ──────────────────────────────────────────────

function CostRiskAnalysis({
  costDrivers,
  opportunities,
  riskCostPoints,
  readmissionForm,
  setReadmissionForm,
  readmissionResult,
  onPredict,
}: {
  costDrivers: CostDriver[];
  opportunities: Opportunity[];
  riskCostPoints: RiskCostPoint[];
  readmissionForm: { patientId: string; age: string; diagnosis: string; priorAdmissions: string };
  setReadmissionForm: (f: typeof readmissionForm) => void;
  readmissionResult: { risk: number; level: string } | null;
  onPredict: () => void;
}) {
  return (
    <div className="space-y-6">
      {/* Cost Drivers Table */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Cost Drivers</h2>
        <div className="overflow-x-auto">
          <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="pb-3 text-left font-medium text-gray-500 dark:text-gray-400">Category</th>
                <th className="pb-3 text-right font-medium text-gray-500 dark:text-gray-400">Amount</th>
                <th className="pb-3 text-right font-medium text-gray-500 dark:text-gray-400">Trend</th>
                <th className="pb-3 text-right font-medium text-gray-500 dark:text-gray-400">% of Total</th>
                <th className="pb-3 text-left font-medium text-gray-500 dark:text-gray-400 pl-4">Distribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {costDrivers.map((d) => (
                <tr key={d.category} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <td className="py-3 font-medium text-gray-900 dark:text-gray-100">{d.category}</td>
                  <td className="py-3 text-right font-semibold text-gray-900 dark:text-gray-100">{d.amount}</td>
                  <td className={`py-3 text-right font-semibold ${d.trendUp ? "text-red-500" : "text-emerald-600"}`}>
                    {d.trendUp ? "↑" : "↓"} {d.trend}
                  </td>
                  <td className="py-3 text-right text-gray-600 dark:text-gray-400">{d.pctOfTotal}%</td>
                  <td className="py-3 pl-4">
                    <div className="h-2 w-full max-w-[120px] rounded-full bg-gray-100 dark:bg-gray-800">
                      <div
                        className="h-2 rounded-full bg-healthos-500 transition-all duration-500"
                        style={{ width: `${(d.pctOfTotal / 35) * 100}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      </div>

      {/* Savings Opportunities */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Savings Opportunities</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {opportunities.map((opp, i) => (
            <div key={opp.title} className="card card-hover animate-fade-in-up" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">{opp.title}</h3>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-700">
                  {opp.savings}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{opp.description}</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Confidence:</span>
                <div className="h-2 w-24 rounded-full bg-gray-100 dark:bg-gray-800">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      opp.confidence >= 85 ? "bg-emerald-500" : opp.confidence >= 70 ? "bg-amber-500" : "bg-red-500"
                    }`}
                    style={{ width: `${opp.confidence}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{opp.confidence}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Risk-Cost Correlation Scatter */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Risk-Cost Correlation</h2>
        <div className="relative h-64 w-full rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800">
          {/* Y axis label */}
          <span className="absolute -left-1 top-1/2 -translate-y-1/2 -rotate-90 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
            Cost ($)
          </span>
          {/* X axis label */}
          <span className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-5 text-xs text-gray-500 dark:text-gray-400">
            Risk Score
          </span>
          {/* Grid lines */}
          {[25, 50, 75].map((pct) => (
            <div key={`h-${pct}`} className="absolute left-0 right-0 border-t border-dashed border-gray-200 dark:border-gray-700" style={{ top: `${100 - pct}%` }} />
          ))}
          {[25, 50, 75].map((pct) => (
            <div key={`v-${pct}`} className="absolute top-0 bottom-0 border-l border-dashed border-gray-200 dark:border-gray-700" style={{ left: `${pct}%` }} />
          ))}
          {/* Dots */}
          {riskCostPoints.map((pt) => {
            const maxCost = 36000;
            const x = pt.riskScore;
            const y = (pt.cost / maxCost) * 100;
            const color =
              pt.riskScore < 30 ? "bg-emerald-500" : pt.riskScore < 60 ? "bg-amber-500" : pt.riskScore < 80 ? "bg-orange-500" : "bg-red-500";
            return (
              <div
                key={pt.id}
                className={`absolute h-4 w-4 rounded-full ${color} shadow-md transition-all duration-300 hover:scale-150 cursor-pointer`}
                style={{ left: `${x}%`, bottom: `${y}%`, transform: "translate(-50%, 50%)" }}
                title={`${pt.label}: Risk ${pt.riskScore}, Cost $${pt.cost.toLocaleString()}`}
              />
            );
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-emerald-500" /> Low Risk</div>
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-amber-500" /> Moderate</div>
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-orange-500" /> High</div>
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-red-500" /> Critical</div>
        </div>
      </div>

      {/* Readmission Risk Predictor */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Readmission Risk Predictor</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Patient ID</label>
            <input
              type="text"
              value={readmissionForm.patientId}
              onChange={(e) => setReadmissionForm({ ...readmissionForm, patientId: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              placeholder="PAT-001"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Age</label>
            <input
              type="number"
              value={readmissionForm.age}
              onChange={(e) => setReadmissionForm({ ...readmissionForm, age: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              placeholder="65"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Diagnosis</label>
            <input
              type="text"
              value={readmissionForm.diagnosis}
              onChange={(e) => setReadmissionForm({ ...readmissionForm, diagnosis: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              placeholder="CHF, Diabetes"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Prior Admissions (12mo)</label>
            <input
              type="number"
              value={readmissionForm.priorAdmissions}
              onChange={(e) => setReadmissionForm({ ...readmissionForm, priorAdmissions: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              placeholder="2"
            />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-4">
          <button
            onClick={onPredict}
            className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-all"
          >
            Predict Risk
          </button>
          {readmissionResult && (
            <div className="flex items-center gap-3">
              <span
                className={`rounded-full px-3 py-1 text-sm font-bold ${
                  readmissionResult.level === "low"
                    ? "bg-emerald-50 text-emerald-700"
                    : readmissionResult.level === "moderate"
                    ? "bg-amber-50 text-amber-700"
                    : readmissionResult.level === "high"
                    ? "bg-orange-50 text-orange-700"
                    : "bg-red-50 text-red-700"
                }`}
              >
                {readmissionResult.level.toUpperCase()}
              </span>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Score: <span className="font-bold text-gray-900 dark:text-gray-100">{(readmissionResult.risk * 100).toFixed(1)}%</span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Tab 4: Cohort Builder ────────────────────────────────────────────────────

function CohortBuilder({
  templates,
  selectedTemplate,
  setSelectedTemplate,
  filters,
  setFilters,
  result,
  onCreate,
}: {
  templates: typeof DEMO_COHORT_TEMPLATES;
  selectedTemplate: string;
  setSelectedTemplate: (v: string) => void;
  filters: { ageMin: string; ageMax: string; diagnosis: string; riskLevel: string; medication: string };
  setFilters: (f: typeof filters) => void;
  result: Record<string, unknown> | null;
  onCreate: () => void;
}) {
  const demographics = result?.demographics as Record<string, unknown> | undefined;
  const clinical = result?.clinical as Record<string, unknown> | undefined;

  return (
    <div className="space-y-6">
      {/* Template Selector */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Cohort Templates</h2>
        <select
          value={selectedTemplate}
          onChange={(e) => setSelectedTemplate(e.target.value)}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
        >
          <option value="">-- Select a template or build custom --</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} &mdash; {t.description}
            </option>
          ))}
        </select>
      </div>

      {/* Custom Filters */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Custom Cohort Filters</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Age Min</label>
            <input
              type="number"
              value={filters.ageMin}
              onChange={(e) => setFilters({ ...filters, ageMin: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Age Max</label>
            <input
              type="number"
              value={filters.ageMax}
              onChange={(e) => setFilters({ ...filters, ageMax: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Diagnosis</label>
            <input
              type="text"
              value={filters.diagnosis}
              onChange={(e) => setFilters({ ...filters, diagnosis: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              placeholder="e.g. Diabetes, CHF"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Risk Level</label>
            <select
              value={filters.riskLevel}
              onChange={(e) => setFilters({ ...filters, riskLevel: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
            >
              <option value="all">All Levels</option>
              <option value="low">Low</option>
              <option value="moderate">Moderate</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Medication</label>
            <input
              type="text"
              value={filters.medication}
              onChange={(e) => setFilters({ ...filters, medication: e.target.value })}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              placeholder="e.g. Metformin"
            />
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={onCreate}
            className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-all"
          >
            Build Cohort
          </button>
        </div>
      </div>

      {/* Cohort Results */}
      {result && (
        <div className="card animate-fade-in-up border-l-4 border-l-healthos-500">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {(result.name as string) || "Cohort Results"}
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                ID: {result.cohort_id as string} | Created: {new Date(result.created_at as string).toLocaleString()}
              </p>
            </div>
            <span className="rounded-full bg-healthos-50 px-4 py-1 text-lg font-bold text-healthos-700">
              {((result.total_patients as number) || 0).toLocaleString()} patients
            </span>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Demographics */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Demographics</h3>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Average Age</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{demographics?.avg_age as number}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Male</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{demographics?.male_pct as number}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Female</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{demographics?.female_pct as number}%</span>
                </div>
              </div>
            </div>

            {/* Clinical Characteristics */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Clinical Characteristics</h3>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Avg Risk Score</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{clinical?.avg_risk_score as number}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Avg Medications</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{clinical?.avg_medications as number}</span>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Top Conditions:</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {((clinical?.top_conditions as string[]) || []).map((c) => (
                      <span key={c} className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
            <button className="rounded-lg border border-healthos-300 px-4 py-2 text-sm font-medium text-healthos-700 hover:bg-healthos-50 transition-all">
              Compare Cohorts
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tab 5: Outcomes Tracking ─────────────────────────────────────────────────

function OutcomesTracking({
  metrics,
  adherence,
  costComparison,
}: {
  metrics: OutcomeMetric[];
  adherence: AdherenceRate[];
  costComparison: CostComparison[];
}) {
  return (
    <div className="space-y-6">
      {/* Treatment Effectiveness */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Treatment Effectiveness</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {metrics.map((m, i) => (
            <div key={m.metric} className="card card-hover animate-fade-in-up" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{m.metric}</p>
                  <p className="mt-1 text-3xl font-bold text-emerald-600">+{m.improvement}%</p>
                </div>
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                  p={m.pValue}
                </span>
              </div>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                95% CI: [{m.ciLow}%, {m.ciHigh}%]
              </p>
              {/* Outcome trend bar */}
              <div className="mt-3 h-2 w-full rounded-full bg-gray-100 dark:bg-gray-800">
                <div
                  className="h-2 rounded-full bg-emerald-500 transition-all duration-700"
                  style={{ width: `${Math.min(m.improvement * 2, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Adherence Rates */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Adherence Rates by Category</h2>
        <div className="space-y-4">
          {adherence.map((a) => {
            const atTarget = a.rate >= a.target;
            return (
              <div key={a.category}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700 dark:text-gray-300">{a.category}</span>
                  <div className="flex items-center gap-3">
                    <span className={`font-bold ${atTarget ? "text-emerald-600" : "text-amber-600"}`}>
                      {a.rate}%
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">target: {a.target}%</span>
                  </div>
                </div>
                <div className="relative h-3 w-full rounded-full bg-gray-100 dark:bg-gray-800">
                  <div
                    className={`h-3 rounded-full transition-all duration-700 ${atTarget ? "bg-emerald-500" : "bg-amber-500"}`}
                    style={{ width: `${a.rate}%` }}
                  />
                  {/* Target marker */}
                  <div
                    className="absolute top-0 h-3 w-0.5 bg-gray-400"
                    style={{ left: `${a.target}%` }}
                    title={`Target: ${a.target}%`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Cost Comparison Before/After */}
      <div className="card animate-fade-in-up">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Cost Analysis: Before vs After Intervention</h2>
        <div className="space-y-5">
          {costComparison.map((c) => {
            const maxVal = Math.max(c.before, c.after);
            const savings = c.before - c.after;
            const savingsPct = ((savings / c.before) * 100).toFixed(1);
            return (
              <div key={c.category}>
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="font-medium text-gray-700 dark:text-gray-300">{c.category}</span>
                  <span className="text-xs font-semibold text-emerald-600">
                    Saved ${savings.toLocaleString()} ({savingsPct}%)
                  </span>
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-3">
                    <span className="w-14 text-xs text-gray-500 dark:text-gray-400 text-right">Before</span>
                    <div className="flex-1 h-3 rounded-full bg-gray-100 dark:bg-gray-800">
                      <div
                        className="h-3 rounded-full bg-red-400 transition-all duration-700"
                        style={{ width: `${(c.before / maxVal) * 100}%` }}
                      />
                    </div>
                    <span className="w-16 text-xs text-gray-600 dark:text-gray-400 text-right">${c.before.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="w-14 text-xs text-gray-500 dark:text-gray-400 text-right">After</span>
                    <div className="flex-1 h-3 rounded-full bg-gray-100 dark:bg-gray-800">
                      <div
                        className="h-3 rounded-full bg-emerald-500 transition-all duration-700"
                        style={{ width: `${(c.after / maxVal) * 100}%` }}
                      />
                    </div>
                    <span className="w-16 text-xs text-gray-600 dark:text-gray-400 text-right">${c.after.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
