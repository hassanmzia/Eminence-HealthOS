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
} from "lucide-react";
import clsx from "clsx";
import {
  fetchMSRiskDashboard,
  fetchMSRiskAssessments,
  fetchMSRiskWorkflows,
  fetchMSRiskPolicies,
  triggerMSRiskWorkflow,
  type MSRiskDashboard,
  type MSRiskAssessment,
  type MSRiskWorkflow,
  type MSRiskPolicy,
} from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────────────────── */

type TabId = "overview" | "assessments" | "workflows" | "policies" | "agents";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <BarChart3 className="h-4 w-4" /> },
  { id: "assessments", label: "Assessments", icon: <FileSearch className="h-4 w-4" /> },
  { id: "workflows", label: "Workflows", icon: <Layers className="h-4 w-4" /> },
  { id: "policies", label: "Policies", icon: <Settings className="h-4 w-4" /> },
  { id: "agents", label: "Agent Pipeline", icon: <Brain className="h-4 w-4" /> },
];

const AGENTS = [
  {
    name: "Retrieval Agent",
    description: "Fetches patient records, labs, and imaging data from the EHR",
    color: "bg-blue-500",
    tier: "Data",
  },
  {
    name: "Phenotyping Agent",
    description: "Computes MS risk score from clinical features and symptom patterns",
    color: "bg-purple-500",
    tier: "Analysis",
  },
  {
    name: "Notes & Imaging Agent",
    description: "NLP analysis of clinical notes and MRI lesion detection",
    color: "bg-indigo-500",
    tier: "Analysis",
  },
  {
    name: "Safety & Governance Agent",
    description: "Applies guardrails, demographic checks, and rate limits",
    color: "bg-amber-500",
    tier: "Safety",
  },
  {
    name: "Coordinator Agent",
    description: "Orchestrates the pipeline, determines action, and generates rationale",
    color: "bg-emerald-500",
    tier: "Orchestration",
  },
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

  return (
    <div className="space-y-6 min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">MS Risk Screening</h1>
          <p className="text-sm text-gray-500">
            Multi-agent pipeline for early Multiple Sclerosis detection &amp; governance
          </p>
        </div>
        <button
          onClick={async () => {
            try {
              await triggerMSRiskWorkflow({});
              loadData();
            } catch { /* toast */ }
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-healthos-700 transition-colors"
        >
          <Play className="h-4 w-4" /> Run Screening
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
              activeTab === tab.id
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            )}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && <OverviewTab dashboard={dashboard} loading={loading} />}
      {activeTab === "assessments" && <AssessmentsTab assessments={assessments} loading={loading} />}
      {activeTab === "workflows" && <WorkflowsTab workflows={workflows} loading={loading} />}
      {activeTab === "policies" && <PoliciesTab policies={policies} loading={loading} />}
      {activeTab === "agents" && <AgentsTab />}
    </div>
  );
}

/* ── Overview Tab ──────────────────────────────────────────────────────────── */

function OverviewTab({ dashboard, loading }: { dashboard: MSRiskDashboard | null; loading: boolean }) {
  if (loading) return <LoadingSkeleton />;

  const kpis = [
    {
      label: "Total Patients",
      value: dashboard?.total_patients?.toLocaleString() ?? "—",
      icon: <Users className="h-5 w-5 text-blue-500" />,
      color: "bg-blue-50 ring-blue-500/20",
    },
    {
      label: "Assessments",
      value: dashboard?.total_assessments?.toLocaleString() ?? "—",
      icon: <FileSearch className="h-5 w-5 text-purple-500" />,
      color: "bg-purple-50 ring-purple-500/20",
    },
    {
      label: "Latest Precision",
      value: dashboard?.latest_run?.precision != null ? `${(dashboard.latest_run.precision * 100).toFixed(1)}%` : "—",
      icon: <TrendingUp className="h-5 w-5 text-emerald-500" />,
      color: "bg-emerald-50 ring-emerald-500/20",
    },
    {
      label: "Latest Recall",
      value: dashboard?.latest_run?.recall != null ? `${(dashboard.latest_run.recall * 100).toFixed(1)}%` : "—",
      icon: <Activity className="h-5 w-5 text-amber-500" />,
      color: "bg-amber-50 ring-amber-500/20",
    },
  ];

  const actions = dashboard?.action_breakdown;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className={clsx("rounded-xl p-4 ring-1 ring-inset", kpi.color)}>
            <div className="flex items-center gap-2 mb-2">{kpi.icon}<span className="text-xs font-medium text-gray-500">{kpi.label}</span></div>
            <p className="text-2xl font-bold text-gray-900">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Action Distribution */}
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

      {/* Latest Run Info */}
      {dashboard?.latest_run && (
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">Latest Workflow Run</h3>
            {statusBadge(dashboard.latest_run.status)}
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Candidates Found</p>
              <p className="font-semibold text-gray-900">{dashboard.latest_run.candidates_found}</p>
            </div>
            <div>
              <p className="text-gray-500">Run ID</p>
              <p className="font-mono text-xs text-gray-600">{dashboard.latest_run.id.slice(0, 8)}</p>
            </div>
            <div>
              <p className="text-gray-500">Date</p>
              <p className="text-gray-900">{new Date(dashboard.latest_run.created_at).toLocaleDateString()}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Assessments Tab ───────────────────────────────────────────────────────── */

function AssessmentsTab({ assessments, loading }: { assessments: MSRiskAssessment[]; loading: boolean }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {assessments.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">No assessments yet. Run a screening workflow to generate results.</td></tr>
            ) : assessments.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                  {a.patient?.patient_id ?? "—"}
                  <span className="ml-1 text-xs text-gray-400">({a.patient?.age}{a.patient?.sex})</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-16 rounded-full bg-gray-200 overflow-hidden">
                      <div
                        className={clsx("h-full rounded-full", a.risk_score >= 0.9 ? "bg-red-500" : a.risk_score >= 0.65 ? "bg-amber-500" : "bg-emerald-500")}
                        style={{ width: `${a.risk_score * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono text-gray-700">{(a.risk_score * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td className="px-4 py-3">{actionBadge(a.action)}</td>
                <td className="px-4 py-3">
                  {a.flag_count > 0 ? (
                    <span className="inline-flex items-center gap-1 text-xs text-amber-600"><AlertTriangle className="h-3 w-3" />{a.flag_count}</span>
                  ) : (
                    <span className="text-xs text-gray-400">None</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {a.reviewed_at ? (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 className="h-3 w-3" />{a.reviewed_by || "Yes"}</span>
                  ) : (
                    <span className="text-xs text-gray-400">Pending</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{new Date(a.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <button onClick={() => setExpandedId(expandedId === a.id ? null : a.id)} className="text-xs text-healthos-600 hover:text-healthos-700">
                    <Eye className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Workflows Tab ─────────────────────────────────────────────────────────── */

function WorkflowsTab({ workflows, loading }: { workflows: MSRiskWorkflow[]; loading: boolean }) {
  if (loading) return <LoadingSkeleton />;

  return (
    <div className="space-y-4">
      {workflows.length === 0 ? (
        <div className="rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-gray-200">
          <Layers className="mx-auto h-10 w-10 text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">No workflow runs yet. Click &quot;Run Screening&quot; to start.</p>
        </div>
      ) : workflows.map((wf) => (
        <div key={wf.id} className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm text-gray-700">{wf.id.slice(0, 8)}</span>
              {statusBadge(wf.status)}
            </div>
            <span className="text-xs text-gray-400">{new Date(wf.created_at).toLocaleString()}</span>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5 text-sm">
            <div>
              <p className="text-gray-500">Patients</p>
              <p className="font-semibold">{wf.total_patients}</p>
            </div>
            <div>
              <p className="text-gray-500">Candidates</p>
              <p className="font-semibold">{wf.candidates_found}</p>
            </div>
            <div>
              <p className="text-gray-500">Precision</p>
              <p className="font-semibold">{wf.precision != null ? `${(wf.precision * 100).toFixed(1)}%` : "—"}</p>
            </div>
            <div>
              <p className="text-gray-500">Recall</p>
              <p className="font-semibold">{wf.recall != null ? `${(wf.recall * 100).toFixed(1)}%` : "—"}</p>
            </div>
            <div>
              <p className="text-gray-500">Duration</p>
              <p className="font-semibold">{wf.duration_seconds != null ? `${wf.duration_seconds.toFixed(1)}s` : "—"}</p>
            </div>
          </div>
          {/* Action breakdown bar */}
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

/* ── Policies Tab ──────────────────────────────────────────────────────────── */

function PoliciesTab({ policies, loading }: { policies: MSRiskPolicy[]; loading: boolean }) {
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
            <span className="text-xs text-gray-400">{new Date(pol.created_at).toLocaleDateString()}</span>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
            <div>
              <p className="text-gray-500">Review Threshold</p>
              <p className="font-semibold">{(pol.risk_review_threshold * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-gray-500">Draft Order</p>
              <p className="font-semibold">{(pol.draft_order_threshold * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-gray-500">Auto-Order</p>
              <p className="font-semibold">{(pol.auto_order_threshold * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-gray-500">Max Auto/Day</p>
              <p className="font-semibold">{pol.max_auto_actions_per_day}</p>
            </div>
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
        <p className="text-xs text-gray-500 mb-6">
          Five specialized agents work in sequence to screen patients for MS risk, apply governance guardrails, and determine clinical actions.
        </p>

        {/* Pipeline flow */}
        <div className="flex flex-col gap-3">
          {AGENTS.map((agent, idx) => (
            <div key={agent.name} className="flex items-start gap-4">
              {/* Step number + connector */}
              <div className="flex flex-col items-center">
                <div className={clsx("flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white", agent.color)}>
                  {idx + 1}
                </div>
                {idx < AGENTS.length - 1 && <div className="h-6 w-0.5 bg-gray-200" />}
              </div>

              {/* Agent card */}
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

      {/* Governance Guardrails */}
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Shield className="h-4 w-4 text-amber-500" /> Governance Guardrails
        </h3>
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
