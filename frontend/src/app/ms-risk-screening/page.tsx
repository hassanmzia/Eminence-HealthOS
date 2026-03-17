"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Activity,
  Users,
  Brain,
  Shield,
  AlertTriangle,
  Play,
  Eye,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
  Settings,
  FileSearch,
  TrendingUp,
  Layers,
  Zap,
  Scale,
  FlaskConical,
  ScrollText,
  Bell,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Sliders,
} from "lucide-react";
import clsx from "clsx";
import {
  fetchMSRiskDashboard,
  fetchMSRiskAssessments,
  fetchMSRiskWorkflows,
  fetchMSRiskPolicies,
  fetchMSRiskGovernanceRules,
  fetchMSRiskAuditLogs,
  fetchMSRiskNotifications,
  fetchMSRiskUnreadNotificationCount,
  fetchMSRiskWorkflowFairness,
  fetchMSRiskWorkflowMetrics,
  fetchMSRiskPatientRiskHistory,
  fetchMSRiskPendingReviews,
  markAllMSRiskNotificationsRead,
  markMSRiskNotificationRead,
  activateMSRiskPolicy,
  triggerMSRiskWorkflow,
  runMSRiskWhatIf,
  type MSRiskDashboard,
  type MSRiskAssessment,
  type MSRiskWorkflow,
  type MSRiskPolicy,
} from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────────────────── */

type TabId = "overview" | "assessments" | "workflows" | "policies" | "agents" | "fairness" | "what-if" | "governance" | "audit" | "patient-detail" | "workflow-detail" | "notifications";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <BarChart3 className="h-4 w-4" /> },
  { id: "assessments", label: "Assessments", icon: <FileSearch className="h-4 w-4" /> },
  { id: "workflows", label: "Workflows", icon: <Layers className="h-4 w-4" /> },
  { id: "fairness", label: "Fairness", icon: <Scale className="h-4 w-4" /> },
  { id: "what-if", label: "What-If", icon: <FlaskConical className="h-4 w-4" /> },
  { id: "policies", label: "Policies", icon: <Settings className="h-4 w-4" /> },
  { id: "governance", label: "Governance", icon: <Shield className="h-4 w-4" /> },
  { id: "audit", label: "Audit Log", icon: <ScrollText className="h-4 w-4" /> },
  { id: "notifications", label: "Alerts", icon: <Bell className="h-4 w-4" /> },
  { id: "agents", label: "Pipeline", icon: <Brain className="h-4 w-4" /> },
];

const AGENTS = [
  { name: "Retrieval Agent", description: "Fetches patient records, labs, and imaging data from the EHR", color: "bg-blue-500", tier: "Data" },
  { name: "Phenotyping Agent", description: "Computes MS risk score from clinical features and symptom patterns", color: "bg-purple-500", tier: "Analysis" },
  { name: "Notes & Imaging Agent", description: "NLP analysis of clinical notes and MRI lesion detection", color: "bg-indigo-500", tier: "Analysis" },
  { name: "Safety & Governance Agent", description: "Applies guardrails, demographic checks, and rate limits", color: "bg-amber-500", tier: "Safety" },
  { name: "Coordinator Agent", description: "Orchestrates the pipeline, determines action, and generates rationale", color: "bg-emerald-500", tier: "Orchestration" },
];

function actionBadge(action: string) {
  switch (action) {
    case "AUTO_ORDER_MRI_AND_NOTIFY_NEURO":
      return <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">Auto-Order</span>;
    case "DRAFT_MRI_ORDER":
      return <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Draft MRI</span>;
    case "RECOMMEND_NEURO_REVIEW":
      return <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">Recommend</span>;
    default:
      return <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">No Action</span>;
  }
}

function statusBadge(status: string) {
  switch (status) {
    case "COMPLETED":
      return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700"><CheckCircle2 className="h-3 w-3" /> Completed</span>;
    case "RUNNING":
      return <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700"><Activity className="h-3 w-3 animate-pulse" /> Running</span>;
    case "FAILED":
      return <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"><XCircle className="h-3 w-3" /> Failed</span>;
    default:
      return <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600"><Clock className="h-3 w-3" /> Pending</span>;
  }
}

/* ── Main Page ─────────────────────────────────────────────────────────────── */

export default function MSRiskScreeningPage() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [dashboard, setDashboard] = useState<MSRiskDashboard | null>(null);
  const [assessments, setAssessments] = useState<MSRiskAssessment[]>([]);
  const [workflows, setWorkflows] = useState<MSRiskWorkflow[]>([]);
  const [policies, setPolicies] = useState<MSRiskPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  // Detail navigation state
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [dashRes, assessRes, wfRes, polRes] = await Promise.allSettled([
        fetchMSRiskDashboard(),
        fetchMSRiskAssessments({ page_size: 20 }),
        fetchMSRiskWorkflows(),
        fetchMSRiskPolicies(),
      ]);
      if (dashRes.status === "fulfilled") setDashboard(dashRes.value);
      if (assessRes.status === "fulfilled") setAssessments(assessRes.value.results);
      if (wfRes.status === "fulfilled") setWorkflows(wfRes.value.results);
      if (polRes.status === "fulfilled") setPolicies(polRes.value.results);
    } catch {
      // individual calls handle errors
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const navigateToPatient = (patientId: string) => { setSelectedPatientId(patientId); setActiveTab("patient-detail"); };
  const navigateToWorkflow = (workflowId: string) => { setSelectedWorkflowId(workflowId); setActiveTab("workflow-detail"); };

  const visibleTabs = TABS.filter((t) => t.id !== "patient-detail" && t.id !== "workflow-detail");

  return (
    <div className="space-y-6 min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">MS Risk Screening</h1>
          <p className="text-sm text-gray-500">Multi-agent pipeline for early Multiple Sclerosis detection &amp; governance</p>
        </div>
        <button
          onClick={async () => { try { await triggerMSRiskWorkflow({}); loadData(); } catch { /* toast */ } }}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-healthos-700 transition-colors"
        >
          <Play className="h-4 w-4" /> Run Screening
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1 overflow-x-auto">
        {visibleTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all whitespace-nowrap",
              activeTab === tab.id ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            )}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && <OverviewTab dashboard={dashboard} loading={loading} />}
      {activeTab === "assessments" && <AssessmentsTab assessments={assessments} loading={loading} onPatientClick={navigateToPatient} />}
      {activeTab === "workflows" && <WorkflowsTab workflows={workflows} loading={loading} onWorkflowClick={navigateToWorkflow} />}
      {activeTab === "policies" && <PoliciesTab policies={policies} loading={loading} onRefresh={loadData} />}
      {activeTab === "agents" && <AgentsTab />}
      {activeTab === "fairness" && <FairnessTab workflows={workflows} />}
      {activeTab === "what-if" && <WhatIfTab workflows={workflows} />}
      {activeTab === "governance" && <GovernanceTab />}
      {activeTab === "audit" && <AuditTab />}
      {activeTab === "notifications" && <NotificationsTab />}
      {activeTab === "patient-detail" && selectedPatientId && (
        <PatientDetailTab patientId={selectedPatientId} onBack={() => setActiveTab("assessments")} />
      )}
      {activeTab === "workflow-detail" && selectedWorkflowId && (
        <WorkflowDetailTab workflowId={selectedWorkflowId} onBack={() => setActiveTab("workflows")} />
      )}
    </div>
  );
}

/* ── Overview Tab ──────────────────────────────────────────────────────────── */

function OverviewTab({ dashboard, loading }: { dashboard: MSRiskDashboard | null; loading: boolean }) {
  if (loading) return <LoadingSkeleton />;

  const kpis = [
    { label: "Total Patients", value: dashboard?.total_patients?.toLocaleString() ?? "—", icon: <Users className="h-5 w-5 text-blue-500" />, color: "bg-blue-50 ring-blue-500/20" },
    { label: "Assessments", value: dashboard?.total_assessments?.toLocaleString() ?? "—", icon: <FileSearch className="h-5 w-5 text-purple-500" />, color: "bg-purple-50 ring-purple-500/20" },
    { label: "Latest Precision", value: dashboard?.latest_run?.precision != null ? `${(dashboard.latest_run.precision * 100).toFixed(1)}%` : "—", icon: <TrendingUp className="h-5 w-5 text-emerald-500" />, color: "bg-emerald-50 ring-emerald-500/20" },
    { label: "Latest Recall", value: dashboard?.latest_run?.recall != null ? `${(dashboard.latest_run.recall * 100).toFixed(1)}%` : "—", icon: <Activity className="h-5 w-5 text-amber-500" />, color: "bg-amber-50 ring-amber-500/20" },
  ];

  const actions = dashboard?.action_breakdown;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className={clsx("rounded-xl p-4 ring-1 ring-inset", kpi.color)}>
            <div className="flex items-center gap-2 mb-2">{kpi.icon}<span className="text-xs font-medium text-gray-500">{kpi.label}</span></div>
            <p className="text-2xl font-bold text-gray-900">{kpi.value}</p>
          </div>
        ))}
      </div>
      {actions && (
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Action Distribution (Latest Run)</h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "No Action", count: actions.no_action, color: "bg-gray-400" },
              { label: "Recommend Review", count: actions.recommend_neuro_review, color: "bg-blue-500" },
              { label: "Draft MRI Order", count: actions.draft_mri_order, color: "bg-amber-500" },
              { label: "Auto-Order", count: actions.auto_order, color: "bg-red-500" },
            ].map((item) => (
              <div key={item.label} className="text-center">
                <div className={clsx("mx-auto h-3 w-3 rounded-full mb-2", item.color)} />
                <p className="text-lg font-bold text-gray-900">{item.count}</p>
                <p className="text-xs text-gray-500">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {dashboard?.latest_run && (
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">Latest Workflow Run</h3>
            {statusBadge(dashboard.latest_run.status)}
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div><p className="text-gray-500">Candidates Found</p><p className="font-semibold text-gray-900">{dashboard.latest_run.candidates_found}</p></div>
            <div><p className="text-gray-500">Run ID</p><p className="font-mono text-xs text-gray-600">{dashboard.latest_run.id.slice(0, 8)}</p></div>
            <div><p className="text-gray-500">Date</p><p className="text-gray-900">{new Date(dashboard.latest_run.created_at).toLocaleDateString()}</p></div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Assessments Tab ───────────────────────────────────────────────────────── */

function AssessmentsTab({ assessments, loading, onPatientClick }: { assessments: MSRiskAssessment[]; loading: boolean; onPatientClick: (id: string) => void }) {
  if (loading) return <LoadingSkeleton />;

  return (
    <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Patient</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Risk Score</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Action</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Flags</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Reviewed</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {assessments.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">No assessments yet. Run a screening workflow to generate results.</td></tr>
            ) : assessments.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => a.patient?.patient_id && onPatientClick(a.patient.patient_id)}>
                <td className="px-4 py-3 text-sm font-medium text-healthos-600 hover:text-healthos-700">
                  {a.patient?.patient_id ?? "—"}<span className="ml-1 text-xs text-gray-400">({a.patient?.age}{a.patient?.sex})</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-16 rounded-full bg-gray-200 overflow-hidden">
                      <div className={clsx("h-full rounded-full", a.risk_score >= 0.9 ? "bg-red-500" : a.risk_score >= 0.65 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${a.risk_score * 100}%` }} />
                    </div>
                    <span className="text-sm font-mono text-gray-700">{(a.risk_score * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td className="px-4 py-3">{actionBadge(a.action)}</td>
                <td className="px-4 py-3">{a.flag_count > 0 ? <span className="inline-flex items-center gap-1 text-xs text-amber-600"><AlertTriangle className="h-3 w-3" />{a.flag_count}</span> : <span className="text-xs text-gray-400">None</span>}</td>
                <td className="px-4 py-3">{a.reviewed_at ? <span className="inline-flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 className="h-3 w-3" />{a.reviewed_by || "Yes"}</span> : <span className="text-xs text-gray-400">Pending</span>}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{new Date(a.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Workflows Tab ─────────────────────────────────────────────────────────── */

function WorkflowsTab({ workflows, loading, onWorkflowClick }: { workflows: MSRiskWorkflow[]; loading: boolean; onWorkflowClick: (id: string) => void }) {
  if (loading) return <LoadingSkeleton />;

  return (
    <div className="space-y-4">
      {workflows.length === 0 ? (
        <div className="rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-gray-200">
          <Layers className="mx-auto h-10 w-10 text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">No workflow runs yet. Click &quot;Run Screening&quot; to start.</p>
        </div>
      ) : workflows.map((wf) => (
        <div key={wf.id} className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200 cursor-pointer hover:ring-gray-300 transition-all" onClick={() => onWorkflowClick(wf.id)}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm text-gray-700">{wf.id.slice(0, 8)}</span>
              {statusBadge(wf.status)}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">{new Date(wf.created_at).toLocaleString()}</span>
              <ChevronRight className="h-4 w-4 text-gray-400" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5 text-sm">
            <div><p className="text-gray-500">Patients</p><p className="font-semibold">{wf.total_patients}</p></div>
            <div><p className="text-gray-500">Candidates</p><p className="font-semibold">{wf.candidates_found}</p></div>
            <div><p className="text-gray-500">Precision</p><p className="font-semibold">{wf.precision != null ? `${(wf.precision * 100).toFixed(1)}%` : "—"}</p></div>
            <div><p className="text-gray-500">Recall</p><p className="font-semibold">{wf.recall != null ? `${(wf.recall * 100).toFixed(1)}%` : "—"}</p></div>
            <div><p className="text-gray-500">Duration</p><p className="font-semibold">{wf.duration_seconds != null ? `${wf.duration_seconds.toFixed(1)}s` : "—"}</p></div>
          </div>
          <div className="mt-3 flex h-2 rounded-full overflow-hidden bg-gray-100">
            {wf.auto_actions > 0 && <div className="bg-red-500" style={{ width: `${(wf.auto_actions / wf.total_patients) * 100}%` }} />}
            {wf.draft_actions > 0 && <div className="bg-amber-500" style={{ width: `${(wf.draft_actions / wf.total_patients) * 100}%` }} />}
            {wf.recommend_actions > 0 && <div className="bg-blue-500" style={{ width: `${(wf.recommend_actions / wf.total_patients) * 100}%` }} />}
          </div>
          <div className="mt-1 flex gap-4 text-[10px] text-gray-400">
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-red-500" />Auto: {wf.auto_actions}</span>
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-amber-500" />Draft: {wf.draft_actions}</span>
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-blue-500" />Recommend: {wf.recommend_actions}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Fairness Tab ──────────────────────────────────────────────────────────── */

function FairnessTab({ workflows }: { workflows: MSRiskWorkflow[] }) {
  const [groupBy, setGroupBy] = useState("sex");
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const completedRun = workflows.find((w) => w.status === "COMPLETED");

  useEffect(() => {
    if (!completedRun) return;
    setLoading(true);
    fetchMSRiskWorkflowFairness(completedRun.id, groupBy)
      .then((d) => setData(d as Record<string, unknown>[]))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [completedRun, groupBy]);

  if (!completedRun) {
    return (
      <div className="rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-gray-200">
        <Scale className="mx-auto h-10 w-10 text-gray-300 mb-3" />
        <p className="text-sm text-gray-500">No completed workflow runs. Run a screening workflow first to see fairness analysis.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Fairness & Equity Dashboard</h3>
        <p className="text-xs text-gray-500 mb-4">Stratified metrics by demographic and clinical groups for responsible AI monitoring</p>
        <div className="flex gap-2 mb-4">
          {[
            { key: "sex", label: "By Sex" },
            { key: "age_band", label: "By Age Band" },
            { key: "lookalike_dx", label: "By Diagnosis" },
          ].map((g) => (
            <button key={g.key} onClick={() => setGroupBy(g.key)} className={clsx("rounded-full px-3 py-1 text-xs font-semibold transition-colors", groupBy === g.key ? "bg-healthos-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200")}>{g.label}</button>
          ))}
        </div>
        {loading ? <LoadingSkeleton /> : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Group</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Count</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Flag Rate</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Avg Risk</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Precision</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Recall</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No fairness data available.</td></tr>
                ) : data.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{String(row.group ?? row.subgroup ?? `Group ${i + 1}`)}</td>
                    <td className="px-4 py-2">{String(row.count ?? "—")}</td>
                    <td className="px-4 py-2">{row.flag_rate != null ? `${(Number(row.flag_rate) * 100).toFixed(1)}%` : "—"}</td>
                    <td className="px-4 py-2">{row.avg_risk != null ? `${(Number(row.avg_risk) * 100).toFixed(1)}%` : "—"}</td>
                    <td className="px-4 py-2">{row.precision != null ? `${(Number(row.precision) * 100).toFixed(1)}%` : "—"}</td>
                    <td className="px-4 py-2">{row.recall != null ? `${(Number(row.recall) * 100).toFixed(1)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── What-If Tab ───────────────────────────────────────────────────────────── */

function WhatIfTab({ workflows }: { workflows: MSRiskWorkflow[] }) {
  const completedRun = workflows.find((w) => w.status === "COMPLETED");
  const [thresholds, setThresholds] = useState({ risk_review_threshold: 0.65, draft_order_threshold: 0.80, auto_order_threshold: 0.90, max_auto_actions_per_day: 20 });
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);

  const presets = [
    { name: "Conservative", values: { risk_review_threshold: 0.75, draft_order_threshold: 0.88, auto_order_threshold: 0.95, max_auto_actions_per_day: 10 } },
    { name: "Balanced", values: { risk_review_threshold: 0.65, draft_order_threshold: 0.80, auto_order_threshold: 0.90, max_auto_actions_per_day: 20 } },
    { name: "Aggressive", values: { risk_review_threshold: 0.50, draft_order_threshold: 0.70, auto_order_threshold: 0.85, max_auto_actions_per_day: 40 } },
    { name: "No Auto", values: { risk_review_threshold: 0.65, draft_order_threshold: 0.80, auto_order_threshold: 1.01, max_auto_actions_per_day: 0 } },
  ];

  const handleAnalyze = async () => {
    if (!completedRun) return;
    setLoading(true);
    try {
      const r = await runMSRiskWhatIf({ run_id: completedRun.id, ...thresholds });
      setResults((prev) => [...prev, r as Record<string, unknown>]);
    } catch { /* */ }
    finally { setLoading(false); }
  };

  if (!completedRun) {
    return (
      <div className="rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-gray-200">
        <FlaskConical className="mx-auto h-10 w-10 text-gray-300 mb-3" />
        <p className="text-sm text-gray-500">No completed workflow runs. Run a screening workflow first.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">What-If Policy Simulator</h3>
        <p className="text-xs text-gray-500 mb-4">Adjust thresholds and compare outcomes against the latest run</p>

        {/* Presets */}
        <div className="flex gap-2 mb-5">
          {presets.map((p) => (
            <button key={p.name} onClick={() => setThresholds(p.values)} className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 transition-colors">{p.name}</button>
          ))}
        </div>

        {/* Sliders */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 mb-5">
          {[
            { key: "risk_review_threshold" as const, label: "Review Threshold" },
            { key: "draft_order_threshold" as const, label: "Draft Order Threshold" },
            { key: "auto_order_threshold" as const, label: "Auto-Order Threshold" },
          ].map(({ key, label }) => (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-gray-600">{label}</label>
                <span className="text-xs font-mono text-gray-500">{(thresholds[key] * 100).toFixed(0)}%</span>
              </div>
              <input type="range" min={0} max={100} value={thresholds[key] * 100} onChange={(e) => setThresholds((t) => ({ ...t, [key]: Number(e.target.value) / 100 }))} className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-healthos-600" />
            </div>
          ))}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-gray-600">Max Auto/Day</label>
              <span className="text-xs font-mono text-gray-500">{thresholds.max_auto_actions_per_day}</span>
            </div>
            <input type="range" min={0} max={100} value={thresholds.max_auto_actions_per_day} onChange={(e) => setThresholds((t) => ({ ...t, max_auto_actions_per_day: Number(e.target.value) }))} className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-healthos-600" />
          </div>
        </div>

        <button onClick={handleAnalyze} disabled={loading} className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-healthos-700 disabled:opacity-50 transition-colors">
          <Sliders className="h-4 w-4" /> {loading ? "Analyzing..." : "Run Analysis"}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Scenario Comparison</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Scenario</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Flagged</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Precision</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Recall</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Auto</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Draft</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.map((r, i) => {
                  const res = (r.results ?? r) as Record<string, unknown>;
                  return (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium">Scenario {i + 1}</td>
                      <td className="px-3 py-2">{String(res.flagged ?? "—")}</td>
                      <td className="px-3 py-2">{r.precision != null ? `${(Number(r.precision) * 100).toFixed(1)}%` : "—"}</td>
                      <td className="px-3 py-2">{r.recall != null ? `${(Number(r.recall) * 100).toFixed(1)}%` : "—"}</td>
                      <td className="px-3 py-2">{String(res.auto_actions ?? "—")}</td>
                      <td className="px-3 py-2">{String(res.draft_actions ?? "—")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Governance Tab ────────────────────────────────────────────────────────── */

function GovernanceTab() {
  const [rules, setRules] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMSRiskGovernanceRules()
      .then((d) => setRules(d.results as Record<string, unknown>[]))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton />;

  const severityColor = (s: string) => {
    switch (s) { case "critical": return "bg-red-100 text-red-700"; case "blocking": return "bg-red-200 text-red-800"; case "warning": return "bg-amber-100 text-amber-700"; default: return "bg-blue-100 text-blue-700"; }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Governance Rules</h3>
        <p className="text-xs text-gray-500 mb-4">Safety and governance constraints applied during screening</p>
        {rules.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">No governance rules configured.</p>
        ) : (
          <div className="space-y-3">
            {rules.map((rule, i) => (
              <div key={String(rule.id ?? i)} className="rounded-lg border border-gray-200 p-4 hover:border-gray-300 transition-colors">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">{String(rule.name ?? "Rule")}</span>
                    <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-medium", severityColor(String(rule.severity ?? "info")))}>{String(rule.severity ?? "info")}</span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500">{String(rule.rule_type ?? "")}</span>
                  </div>
                  {rule.is_active ? <span className="text-xs text-emerald-600 font-medium">Active</span> : <span className="text-xs text-gray-400">Inactive</span>}
                </div>
                <p className="text-xs text-gray-500">{String(rule.description ?? "")}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Audit Tab ─────────────────────────────────────────────────────────────── */

function AuditTab() {
  const [logs, setLogs] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMSRiskAuditLogs({ page: 1 })
      .then((d) => setLogs(d.results as Record<string, unknown>[]))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton />;

  const typeColor = (t: string) => {
    switch (t) { case "AGENT_RUN": return "bg-purple-100 text-purple-700"; case "MANUAL_REVIEW": return "bg-blue-100 text-blue-700"; case "OVERRIDE": return "bg-amber-100 text-amber-700"; case "POLICY_CHANGE": return "bg-emerald-100 text-emerald-700"; default: return "bg-gray-100 text-gray-700"; }
  };

  return (
    <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">Audit Trail</h3>
        <p className="text-xs text-gray-500">Complete record of all actions, reviews, and policy changes</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Time</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Type</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Actor</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Target</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {logs.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No audit logs yet.</td></tr>
            ) : logs.map((log, i) => (
              <tr key={String(log.id ?? i)} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">{log.created_at ? new Date(String(log.created_at)).toLocaleString() : "—"}</td>
                <td className="px-4 py-2"><span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-medium", typeColor(String(log.action_type ?? "")))}>{String(log.action_type ?? "—")}</span></td>
                <td className="px-4 py-2 text-xs font-medium">{String(log.actor ?? "—")}</td>
                <td className="px-4 py-2 text-xs font-mono text-gray-500">{String(log.target_type ?? "")}{log.target_id ? `:${String(log.target_id).slice(0, 8)}` : ""}</td>
                <td className="px-4 py-2 text-xs text-gray-500 max-w-xs truncate">{log.details ? JSON.stringify(log.details).slice(0, 80) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Notifications Tab ─────────────────────────────────────────────────────── */

function NotificationsTab() {
  const [notifications, setNotifications] = useState<Record<string, unknown>[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nRes, cRes] = await Promise.allSettled([
        fetchMSRiskNotifications({ page: 1 }),
        fetchMSRiskUnreadNotificationCount(),
      ]);
      if (nRes.status === "fulfilled") setNotifications(nRes.value.results as Record<string, unknown>[]);
      if (cRes.status === "fulfilled") setUnread(cRes.value.unread_count);
    } catch { /* */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <LoadingSkeleton />;

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-700">Notifications</h3>
            <p className="text-xs text-gray-500">{unread} unread</p>
          </div>
          {unread > 0 && (
            <button onClick={async () => { await markAllMSRiskNotificationsRead(); load(); }} className="text-xs font-medium text-healthos-600 hover:text-healthos-700">Mark all read</button>
          )}
        </div>
        {notifications.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">No notifications.</p>
        ) : (
          <div className="space-y-2">
            {notifications.map((n, i) => (
              <div key={String(n.id ?? i)} className={clsx("rounded-lg border p-3 transition-colors", n.is_read ? "border-gray-200 bg-white" : "border-healthos-200 bg-healthos-50/30")} onClick={async () => { if (!n.is_read && n.id) { await markMSRiskNotificationRead(String(n.id)); load(); } }}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{String(n.title ?? n.message ?? "Notification")}</span>
                  <span className="text-[10px] text-gray-400">{n.created_at ? new Date(String(n.created_at)).toLocaleString() : ""}</span>
                </div>
                {n.message && <p className="text-xs text-gray-500 mt-1">{String(n.message)}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Patient Detail Tab ────────────────────────────────────────────────────── */

function PatientDetailTab({ patientId, onBack }: { patientId: string; onBack: () => void }) {
  const [history, setHistory] = useState<MSRiskAssessment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMSRiskPatientRiskHistory(patientId)
      .then((d) => setHistory(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [patientId]);

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="inline-flex items-center gap-1 text-sm text-healthos-600 hover:text-healthos-700">
        <ArrowLeft className="h-4 w-4" /> Back to Assessments
      </button>

      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-lg font-bold text-gray-900 mb-1">Patient {patientId}</h3>
        <p className="text-xs text-gray-500 mb-4">Risk assessment history across all workflow runs</p>

        {loading ? <LoadingSkeleton /> : history.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">No risk assessments found for this patient.</p>
        ) : (
          <div className="space-y-4">
            {history.map((a) => (
              <div key={a.id} className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-20 rounded-full bg-gray-200 overflow-hidden">
                        <div className={clsx("h-full rounded-full", a.risk_score >= 0.9 ? "bg-red-500" : a.risk_score >= 0.65 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${a.risk_score * 100}%` }} />
                      </div>
                      <span className="text-sm font-mono font-bold text-gray-900">{(a.risk_score * 100).toFixed(1)}%</span>
                    </div>
                    {actionBadge(a.action)}
                  </div>
                  <span className="text-xs text-gray-400">{new Date(a.created_at).toLocaleString()}</span>
                </div>
                {a.flag_count > 0 && (
                  <div className="flex items-center gap-1 mb-2"><AlertTriangle className="h-3 w-3 text-amber-500" /><span className="text-xs text-amber-600">{a.flag_count} safety flag{a.flag_count > 1 ? "s" : ""}</span></div>
                )}
                {a.llm_summary && <p className="text-xs text-gray-600 bg-gray-50 rounded p-2 mb-2">{a.llm_summary}</p>}
                {Object.keys(a.feature_contributions || {}).length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Feature Contributions</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(a.feature_contributions).sort(([, a], [, b]) => Number(b) - Number(a)).slice(0, 8).map(([k, v]) => (
                        <span key={k} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600">{k}: {Number(v).toFixed(2)}</span>
                      ))}
                    </div>
                  </div>
                )}
                {a.reviewed_at && (
                  <div className="mt-2 text-xs text-emerald-600 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Reviewed by {a.reviewed_by} {a.review_notes ? `— "${a.review_notes}"` : ""}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Workflow Detail Tab ───────────────────────────────────────────────────── */

function WorkflowDetailTab({ workflowId, onBack }: { workflowId: string; onBack: () => void }) {
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMSRiskWorkflowMetrics(workflowId)
      .then((d) => setMetrics(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [workflowId]);

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="inline-flex items-center gap-1 text-sm text-healthos-600 hover:text-healthos-700">
        <ArrowLeft className="h-4 w-4" /> Back to Workflows
      </button>

      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-lg font-bold text-gray-900 mb-1">Workflow Run <span className="font-mono text-sm text-gray-500">{workflowId.slice(0, 8)}</span></h3>
        <p className="text-xs text-gray-500 mb-4">Comprehensive metrics and confusion matrix</p>

        {loading ? <LoadingSkeleton /> : !metrics ? (
          <p className="text-sm text-gray-400 text-center py-4">Metrics not available.</p>
        ) : (
          <div className="space-y-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                { label: "Total Assessed", value: metrics.total_assessed },
                { label: "Flagged", value: metrics.flagged_count },
                { label: "Avg Risk", value: metrics.avg_risk_score != null ? `${(Number(metrics.avg_risk_score) * 100).toFixed(1)}%` : "—" },
                { label: "Safety Flag Rate", value: metrics.safety_flag_rate != null ? `${(Number(metrics.safety_flag_rate) * 100).toFixed(1)}%` : "—" },
              ].map((m) => (
                <div key={m.label} className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">{m.label}</p>
                  <p className="text-lg font-bold text-gray-900">{String(m.value ?? "—")}</p>
                </div>
              ))}
            </div>

            {/* Confusion Matrix */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Confusion Matrix</h4>
              <div className="grid grid-cols-2 gap-2 max-w-xs">
                <div className="rounded-lg bg-emerald-50 p-3 text-center ring-1 ring-inset ring-emerald-200">
                  <p className="text-[10px] text-emerald-600 font-medium uppercase">True Positive</p>
                  <p className="text-xl font-bold text-emerald-700">{String(metrics.tp ?? 0)}</p>
                </div>
                <div className="rounded-lg bg-red-50 p-3 text-center ring-1 ring-inset ring-red-200">
                  <p className="text-[10px] text-red-600 font-medium uppercase">False Positive</p>
                  <p className="text-xl font-bold text-red-700">{String(metrics.fp ?? 0)}</p>
                </div>
                <div className="rounded-lg bg-amber-50 p-3 text-center ring-1 ring-inset ring-amber-200">
                  <p className="text-[10px] text-amber-600 font-medium uppercase">False Negative</p>
                  <p className="text-xl font-bold text-amber-700">{String(metrics.fn ?? 0)}</p>
                </div>
                <div className="rounded-lg bg-blue-50 p-3 text-center ring-1 ring-inset ring-blue-200">
                  <p className="text-[10px] text-blue-600 font-medium uppercase">True Negative</p>
                  <p className="text-xl font-bold text-blue-700">{String(metrics.tn ?? 0)}</p>
                </div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Precision", value: metrics.precision, color: "text-emerald-600" },
                { label: "Recall", value: metrics.recall, color: "text-blue-600" },
                { label: "F1 Score", value: metrics.f1_score, color: "text-purple-600" },
              ].map((m) => (
                <div key={m.label} className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs text-gray-500 mb-1">{m.label}</p>
                  <p className={clsx("text-2xl font-bold", m.color)}>{m.value != null ? `${(Number(m.value) * 100).toFixed(1)}%` : "—"}</p>
                </div>
              ))}
            </div>

            {/* Action Breakdown */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Action Breakdown</h4>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  { label: "No Action", value: metrics.no_actions, color: "bg-gray-400" },
                  { label: "Recommend", value: metrics.recommend_actions, color: "bg-blue-500" },
                  { label: "Draft MRI", value: metrics.draft_actions, color: "bg-amber-500" },
                  { label: "Auto-Order", value: metrics.auto_actions, color: "bg-red-500" },
                ].map((a) => (
                  <div key={a.label} className="flex items-center gap-2 rounded-lg bg-gray-50 p-2">
                    <div className={clsx("h-3 w-3 rounded-full", a.color)} />
                    <div>
                      <p className="text-sm font-bold text-gray-900">{String(a.value ?? 0)}</p>
                      <p className="text-[10px] text-gray-500">{a.label}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Policies Tab ──────────────────────────────────────────────────────────── */

function PoliciesTab({ policies, loading, onRefresh }: { policies: MSRiskPolicy[]; loading: boolean; onRefresh: () => void }) {
  if (loading) return <LoadingSkeleton />;

  return (
    <div className="space-y-4">
      {policies.length === 0 ? (
        <div className="rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-gray-200">
          <Settings className="mx-auto h-10 w-10 text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">No policies configured yet.</p>
        </div>
      ) : policies.map((pol) => (
        <div key={pol.id} className={clsx("rounded-xl bg-white p-5 shadow-sm ring-1", pol.is_active ? "ring-emerald-300" : "ring-gray-200")}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">{pol.name}</h3>
              {pol.is_active && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">Active</span>}
            </div>
            <div className="flex items-center gap-2">
              {!pol.is_active && (
                <button onClick={async () => { await activateMSRiskPolicy(pol.id); onRefresh(); }} className="text-xs font-medium text-healthos-600 hover:text-healthos-700">Activate</button>
              )}
              <span className="text-xs text-gray-400">{new Date(pol.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
            <div><p className="text-gray-500">Review Threshold</p><p className="font-semibold">{(pol.risk_review_threshold * 100).toFixed(0)}%</p></div>
            <div><p className="text-gray-500">Draft Order</p><p className="font-semibold">{(pol.draft_order_threshold * 100).toFixed(0)}%</p></div>
            <div><p className="text-gray-500">Auto-Order</p><p className="font-semibold">{(pol.auto_order_threshold * 100).toFixed(0)}%</p></div>
            <div><p className="text-gray-500">Max Auto/Day</p><p className="font-semibold">{pol.max_auto_actions_per_day}</p></div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Agents Tab ────────────────────────────────────────────────────────────── */

function AgentsTab() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Multi-Agent Screening Pipeline</h3>
        <p className="text-xs text-gray-500 mb-6">Five specialized agents work in sequence to screen patients for MS risk, apply governance guardrails, and determine clinical actions.</p>
        <div className="flex flex-col gap-3">
          {AGENTS.map((agent, idx) => (
            <div key={agent.name} className="flex items-start gap-4">
              <div className="flex flex-col items-center">
                <div className={clsx("flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white", agent.color)}>{idx + 1}</div>
                {idx < AGENTS.length - 1 && <div className="h-6 w-0.5 bg-gray-200" />}
              </div>
              <div className="flex-1 rounded-lg border border-gray-200 p-3 hover:border-gray-300 transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm text-gray-900">{agent.name}</span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500">{agent.tier}</span>
                </div>
                <p className="text-xs text-gray-500">{agent.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2"><Shield className="h-4 w-4 text-amber-500" /> Governance Guardrails</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {[
            { name: "PHI Detection", desc: "Scans for protected health information in agent outputs" },
            { name: "Evidence Quality", desc: "Validates clinical evidence meets quality thresholds" },
            { name: "Demographic Guard", desc: "Prevents bias by monitoring subgroup disparities" },
            { name: "Contradiction Detection", desc: "Flags conflicting recommendations across agents" },
            { name: "Rate Limiting", desc: "Caps auto-actions per day to prevent runaway automation" },
            { name: "Autonomy Escalation", desc: "Steps down autonomy when safety flags are raised" },
          ].map((rule) => (
            <div key={rule.name} className="rounded-lg bg-amber-50/50 p-3 ring-1 ring-inset ring-amber-200/50">
              <p className="text-sm font-medium text-gray-900">{rule.name}</p>
              <p className="text-xs text-gray-500">{rule.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Loading Skeleton ──────────────────────────────────────────────────────── */

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="animate-pulse rounded-xl bg-gray-100 h-24" />
      ))}
    </div>
  );
}
