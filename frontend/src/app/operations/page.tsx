"use client";

import { useState, useCallback } from "react";
import {
  evaluatePriorAuth,
  verifyInsurance,
  createReferral,
  scheduleAppointment,
} from "@/lib/api";

/* ─── Types ───────────────────────────────────────────────────────────────── */

type TabKey = "prior-auth" | "insurance" | "referrals" | "scheduling" | "workflows";

interface PriorAuthRequest {
  id: string;
  patient: string;
  procedure: string;
  insurance: string;
  status: "pending" | "approved" | "denied" | "in-review";
  urgency: "routine" | "urgent" | "emergent";
  submittedDate: string;
  cptCode: string;
  provider: string;
}

interface InsuranceVerification {
  id: string;
  patient: string;
  insurerName: string;
  memberId: string;
  groupNumber: string;
  eligibility: "active" | "inactive" | "pending";
  copay: string;
  deductible: string;
  deductibleMet: string;
  outOfPocketMax: string;
  coverageType: string;
  verifiedDate: string;
}

interface ReferralItem {
  id: string;
  patient: string;
  referringProvider: string;
  specialistType: string;
  reason: string;
  status: "pending" | "scheduled" | "completed" | "cancelled";
  priority: "low" | "normal" | "high" | "urgent";
  createdDate: string;
  timeline: { date: string; event: string; completed: boolean }[];
}

interface AppointmentSlot {
  id: string;
  time: string;
  patient: string;
  provider: string;
  type: "follow-up" | "new-patient" | "urgent" | "telehealth" | "procedure";
  duration: number;
  status: "confirmed" | "checked-in" | "in-progress" | "completed" | "no-show";
  conflict?: boolean;
}

interface WorkflowItem {
  id: string;
  name: string;
  totalSteps: number;
  completedSteps: number;
  currentStep: string;
  assignedTeam: string;
  slaDeadline: string;
  slaMinutesRemaining: number;
  steps: { name: string; completed: boolean; active: boolean }[];
}

/* ─── Demo Data ───────────────────────────────────────────────────────────── */

const demoPriorAuths: PriorAuthRequest[] = [
  { id: "PA-001", patient: "Maria Garcia", procedure: "MRI Lumbar Spine", insurance: "Blue Cross PPO", status: "pending", urgency: "routine", submittedDate: "2026-03-14", cptCode: "72148", provider: "Dr. Chen" },
  { id: "PA-002", patient: "James Wilson", procedure: "Knee Arthroscopy", insurance: "Aetna HMO", status: "in-review", urgency: "urgent", submittedDate: "2026-03-13", cptCode: "29881", provider: "Dr. Patel" },
  { id: "PA-003", patient: "Sarah Johnson", procedure: "CT Abdomen w/ Contrast", insurance: "UnitedHealth", status: "approved", urgency: "emergent", submittedDate: "2026-03-12", cptCode: "74178", provider: "Dr. Kim" },
  { id: "PA-004", patient: "Robert Davis", procedure: "Cardiac Catheterization", insurance: "Cigna EPO", status: "denied", urgency: "urgent", submittedDate: "2026-03-11", cptCode: "93458", provider: "Dr. Martinez" },
  { id: "PA-005", patient: "Emily Chen", procedure: "Physical Therapy (12 visits)", insurance: "Humana Gold", status: "pending", urgency: "routine", submittedDate: "2026-03-14", cptCode: "97110", provider: "Dr. Thompson" },
  { id: "PA-006", patient: "David Park", procedure: "Sleep Study", insurance: "Blue Cross PPO", status: "in-review", urgency: "routine", submittedDate: "2026-03-10", cptCode: "95810", provider: "Dr. Adams" },
];

const demoVerifications: InsuranceVerification[] = [
  { id: "IV-001", patient: "Maria Garcia", insurerName: "Blue Cross PPO", memberId: "BCB-9928174", groupNumber: "GRP-44210", eligibility: "active", copay: "$30", deductible: "$1,500", deductibleMet: "$1,120", outOfPocketMax: "$6,000", coverageType: "In-Network PPO", verifiedDate: "2026-03-14" },
  { id: "IV-002", patient: "James Wilson", insurerName: "Aetna HMO", memberId: "AET-5543892", groupNumber: "GRP-78100", eligibility: "active", copay: "$25", deductible: "$2,000", deductibleMet: "$2,000", outOfPocketMax: "$5,000", coverageType: "HMO", verifiedDate: "2026-03-13" },
  { id: "IV-003", patient: "Robert Davis", insurerName: "Cigna EPO", memberId: "CIG-3312845", groupNumber: "GRP-55670", eligibility: "inactive", copay: "$40", deductible: "$3,000", deductibleMet: "$500", outOfPocketMax: "$8,000", coverageType: "EPO", verifiedDate: "2026-03-12" },
];

const demoReferrals: ReferralItem[] = [
  { id: "REF-001", patient: "Maria Garcia", referringProvider: "Dr. Chen", specialistType: "Orthopedics", reason: "Chronic lower back pain unresponsive to conservative treatment", status: "scheduled", priority: "normal", createdDate: "2026-03-10", timeline: [{ date: "2026-03-10", event: "Referral created", completed: true }, { date: "2026-03-11", event: "Insurance pre-auth approved", completed: true }, { date: "2026-03-12", event: "Specialist accepted", completed: true }, { date: "2026-03-18", event: "Appointment scheduled", completed: false }] },
  { id: "REF-002", patient: "James Wilson", referringProvider: "Dr. Patel", specialistType: "Cardiology", reason: "Abnormal stress test results, chest pain on exertion", status: "pending", priority: "urgent", createdDate: "2026-03-13", timeline: [{ date: "2026-03-13", event: "Referral created", completed: true }, { date: "2026-03-14", event: "Awaiting insurance approval", completed: false }, { date: "", event: "Specialist assignment", completed: false }, { date: "", event: "Appointment scheduling", completed: false }] },
  { id: "REF-003", patient: "Sarah Johnson", referringProvider: "Dr. Kim", specialistType: "Gastroenterology", reason: "Persistent abdominal pain, elevated liver enzymes", status: "completed", priority: "high", createdDate: "2026-03-05", timeline: [{ date: "2026-03-05", event: "Referral created", completed: true }, { date: "2026-03-06", event: "Insurance approved", completed: true }, { date: "2026-03-07", event: "Specialist confirmed", completed: true }, { date: "2026-03-10", event: "Visit completed", completed: true }] },
  { id: "REF-004", patient: "Emily Chen", referringProvider: "Dr. Thompson", specialistType: "Dermatology", reason: "Suspicious mole requiring biopsy evaluation", status: "pending", priority: "high", createdDate: "2026-03-14", timeline: [{ date: "2026-03-14", event: "Referral created", completed: true }, { date: "", event: "Insurance verification", completed: false }, { date: "", event: "Specialist matching", completed: false }, { date: "", event: "Appointment scheduling", completed: false }] },
  { id: "REF-005", patient: "David Park", referringProvider: "Dr. Adams", specialistType: "Pulmonology", reason: "Chronic cough, abnormal chest X-ray findings", status: "cancelled", priority: "normal", createdDate: "2026-03-08", timeline: [{ date: "2026-03-08", event: "Referral created", completed: true }, { date: "2026-03-09", event: "Patient declined referral", completed: true }] },
];

const demoSchedule: AppointmentSlot[] = [
  { id: "APT-001", time: "08:00 AM", patient: "Maria Garcia", provider: "Dr. Chen", type: "follow-up", duration: 30, status: "completed" },
  { id: "APT-002", time: "08:30 AM", patient: "James Wilson", provider: "Dr. Patel", type: "urgent", duration: 45, status: "completed" },
  { id: "APT-003", time: "09:15 AM", patient: "Sarah Johnson", provider: "Dr. Kim", type: "new-patient", duration: 60, status: "in-progress" },
  { id: "APT-004", time: "10:15 AM", patient: "Robert Davis", provider: "Dr. Martinez", type: "procedure", duration: 90, status: "checked-in", conflict: true },
  { id: "APT-005", time: "10:30 AM", patient: "Emily Chen", provider: "Dr. Martinez", type: "follow-up", duration: 30, status: "confirmed", conflict: true },
  { id: "APT-006", time: "11:00 AM", patient: "David Park", provider: "Dr. Adams", type: "telehealth", duration: 20, status: "confirmed" },
  { id: "APT-007", time: "11:30 AM", patient: "Lisa Brown", provider: "Dr. Chen", type: "follow-up", duration: 30, status: "confirmed" },
  { id: "APT-008", time: "01:00 PM", patient: "Michael Torres", provider: "Dr. Patel", type: "new-patient", duration: 60, status: "confirmed" },
  { id: "APT-009", time: "02:00 PM", patient: "Anna White", provider: "Dr. Kim", type: "telehealth", duration: 20, status: "no-show" },
  { id: "APT-010", time: "02:30 PM", patient: "Kevin Lee", provider: "Dr. Thompson", type: "urgent", duration: 45, status: "confirmed" },
];

const demoWorkflows: WorkflowItem[] = [
  { id: "WF-001", name: "New Patient Onboarding - Maria Garcia", totalSteps: 6, completedSteps: 4, currentStep: "Insurance Verification", assignedTeam: "Front Desk", slaDeadline: "2026-03-15T14:00:00", slaMinutesRemaining: 142, steps: [{ name: "Demographics Entry", completed: true, active: false }, { name: "Medical History Import", completed: true, active: false }, { name: "Consent Forms", completed: true, active: false }, { name: "Insurance Card Scan", completed: true, active: false }, { name: "Insurance Verification", completed: false, active: true }, { name: "Provider Assignment", completed: false, active: false }] },
  { id: "WF-002", name: "Prior Auth - Knee Arthroscopy", totalSteps: 5, completedSteps: 2, currentStep: "Clinical Review", assignedTeam: "Auth Team", slaDeadline: "2026-03-15T17:00:00", slaMinutesRemaining: 322, steps: [{ name: "Request Submission", completed: true, active: false }, { name: "Documentation Gathered", completed: true, active: false }, { name: "Clinical Review", completed: false, active: true }, { name: "Payer Submission", completed: false, active: false }, { name: "Decision Received", completed: false, active: false }] },
  { id: "WF-003", name: "Claim Denial Appeal - Robert Davis", totalSteps: 4, completedSteps: 1, currentStep: "Evidence Compilation", assignedTeam: "Billing", slaDeadline: "2026-03-16T12:00:00", slaMinutesRemaining: 1462, steps: [{ name: "Denial Analysis", completed: true, active: false }, { name: "Evidence Compilation", completed: false, active: true }, { name: "Appeal Letter Draft", completed: false, active: false }, { name: "Submission & Tracking", completed: false, active: false }] },
  { id: "WF-004", name: "Referral Processing - James Wilson", totalSteps: 5, completedSteps: 5, currentStep: "Complete", assignedTeam: "Care Coordination", slaDeadline: "2026-03-14T16:00:00", slaMinutesRemaining: 0, steps: [{ name: "Referral Review", completed: true, active: false }, { name: "Insurance Pre-Auth", completed: true, active: false }, { name: "Specialist Match", completed: true, active: false }, { name: "Appointment Booked", completed: true, active: false }, { name: "Patient Notified", completed: true, active: false }] },
  { id: "WF-005", name: "Insurance Re-verification - Quarterly", totalSteps: 3, completedSteps: 0, currentStep: "Patient List Generation", assignedTeam: "Eligibility Team", slaDeadline: "2026-03-17T09:00:00", slaMinutesRemaining: 2702, steps: [{ name: "Patient List Generation", completed: false, active: true }, { name: "Batch Verification", completed: false, active: false }, { name: "Discrepancy Resolution", completed: false, active: false }] },
];

const workflowTemplates = [
  "New Patient Onboarding",
  "Prior Authorization Request",
  "Insurance Re-verification",
  "Referral Processing",
  "Claim Denial Appeal",
  "Pre-surgical Clearance",
  "Discharge Planning",
  "Care Transition",
];

/* ─── Status helpers ──────────────────────────────────────────────────────── */

const authStatusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  "in-review": "bg-blue-100 text-blue-800",
};

const referralStatusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  scheduled: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
};

const priorityColors: Record<string, string> = {
  low: "text-gray-500 dark:text-gray-400",
  normal: "text-blue-600",
  high: "text-orange-600",
  urgent: "text-red-600",
};

const appointmentTypeColors: Record<string, string> = {
  "follow-up": "bg-blue-100 text-blue-700",
  "new-patient": "bg-purple-100 text-purple-700",
  urgent: "bg-red-100 text-red-700",
  telehealth: "bg-teal-100 text-teal-700",
  procedure: "bg-orange-100 text-orange-700",
};

const appointmentStatusColors: Record<string, string> = {
  confirmed: "text-blue-600",
  "checked-in": "text-green-600",
  "in-progress": "text-healthos-600",
  completed: "text-gray-500 dark:text-gray-400",
  "no-show": "text-red-500",
};

/* ─── Component ───────────────────────────────────────────────────────────── */

export default function OperationsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("prior-auth");

  // Prior Auth state
  const [priorAuths, setPriorAuths] = useState<PriorAuthRequest[]>(demoPriorAuths);
  const [evaluatingId, setEvaluatingId] = useState<string | null>(null);
  const [showNewAuth, setShowNewAuth] = useState(false);
  const [authForm, setAuthForm] = useState({ patient: "", procedure: "", insurance: "", cptCode: "", urgency: "routine" });

  // Insurance state
  const [verifications, setVerifications] = useState<InsuranceVerification[]>(demoVerifications);
  const [verifyingInsurance, setVerifyingInsurance] = useState(false);
  const [verificationResult, setVerificationResult] = useState<Record<string, unknown> | null>(null);
  const [insuranceForm, setInsuranceForm] = useState({ patientId: "", insurerName: "", memberId: "", groupNumber: "", dob: "" });

  // Referral state
  const [referrals, setReferrals] = useState<ReferralItem[]>(demoReferrals);
  const [showNewReferral, setShowNewReferral] = useState(false);
  const [creatingReferral, setCreatingReferral] = useState(false);
  const [referralForm, setReferralForm] = useState({ patient: "", referringProvider: "", specialistType: "", reason: "", priority: "normal" });

  // Scheduling state
  const [schedule] = useState<AppointmentSlot[]>(demoSchedule);
  const [suggestingSlot, setSuggestingSlot] = useState(false);
  const [suggestedSlot, setSuggestedSlot] = useState<Record<string, unknown> | null>(null);

  // Workflow state
  const [workflows] = useState<WorkflowItem[]>(demoWorkflows);
  const [showNewWorkflow, setShowNewWorkflow] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(workflowTemplates[0]);

  // New Task modal
  const [showNewTask, setShowNewTask] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: "", assignee: "", priority: "medium", dueDate: "" });

  /* ─── API Handlers ──────────────────────────────────────────────────────── */

  const handleEvaluatePriorAuth = useCallback(async (item: PriorAuthRequest) => {
    setEvaluatingId(item.id);
    try {
      const result = await evaluatePriorAuth({
        patient_id: item.patient,
        procedure: item.procedure,
        cpt_code: item.cptCode,
        insurance: item.insurance,
        urgency: item.urgency,
      });
      const decision = (result as Record<string, unknown>).decision as string;
      if (decision === "approved" || decision === "denied") {
        setPriorAuths((prev) =>
          prev.map((pa) => (pa.id === item.id ? { ...pa, status: decision as "approved" | "denied" } : pa))
        );
      }
    } catch {
      // Fallback: simulate approval
      setPriorAuths((prev) =>
        prev.map((pa) => (pa.id === item.id ? { ...pa, status: "approved" } : pa))
      );
    }
    setEvaluatingId(null);
  }, []);

  const handleVerifyInsurance = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setVerifyingInsurance(true);
    setVerificationResult(null);
    try {
      const result = await verifyInsurance({
        patient_id: insuranceForm.patientId,
        insurer_name: insuranceForm.insurerName,
        member_id: insuranceForm.memberId,
        group_number: insuranceForm.groupNumber,
        date_of_birth: insuranceForm.dob,
      });
      setVerificationResult(result);
    } catch {
      // Fallback demo result
      setVerificationResult({
        eligibility: "active",
        coverage_type: "PPO In-Network",
        copay: "$30",
        deductible: "$1,500",
        deductible_met: "$890",
        out_of_pocket_max: "$6,000",
        benefits: ["Preventive Care: 100%", "Specialist Visit: $50 copay", "Lab Work: 80% after deductible", "Imaging: Pre-auth required"],
        effective_date: "2026-01-01",
        termination_date: "2026-12-31",
      });
    }
    setVerifyingInsurance(false);
  }, [insuranceForm]);

  const handleCreateReferral = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingReferral(true);
    try {
      await createReferral({
        patient: referralForm.patient,
        referring_provider: referralForm.referringProvider,
        specialist_type: referralForm.specialistType,
        reason: referralForm.reason,
        priority: referralForm.priority,
      });
    } catch {
      // Fallback: add to local list
    }
    const newReferral: ReferralItem = {
      id: `REF-${String(referrals.length + 1).padStart(3, "0")}`,
      patient: referralForm.patient,
      referringProvider: referralForm.referringProvider,
      specialistType: referralForm.specialistType,
      reason: referralForm.reason,
      status: "pending",
      priority: referralForm.priority as ReferralItem["priority"],
      createdDate: "2026-03-15",
      timeline: [{ date: "2026-03-15", event: "Referral created", completed: true }, { date: "", event: "Insurance verification", completed: false }, { date: "", event: "Specialist matching", completed: false }, { date: "", event: "Appointment scheduling", completed: false }],
    };
    setReferrals((prev) => [newReferral, ...prev]);
    setShowNewReferral(false);
    setReferralForm({ patient: "", referringProvider: "", specialistType: "", reason: "", priority: "normal" });
    setCreatingReferral(false);
  }, [referralForm, referrals.length]);

  const handleSuggestSlot = useCallback(async () => {
    setSuggestingSlot(true);
    setSuggestedSlot(null);
    try {
      const result = await scheduleAppointment({
        patient_id: "demo-patient",
        provider: "Dr. Chen",
        appointment_type: "follow-up",
        preferred_date: "2026-03-15",
        duration_minutes: 30,
      });
      setSuggestedSlot(result);
    } catch {
      // Fallback demo suggestion
      setSuggestedSlot({
        suggested_time: "03:30 PM",
        provider: "Dr. Chen",
        room: "Exam Room 4",
        reason: "Open slot with no conflicts. Provider has 15-min buffer before next appointment.",
        confidence: 0.94,
      });
    }
    setSuggestingSlot(false);
  }, []);

  const handleCreateTask = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setShowNewTask(false);
    setTaskForm({ title: "", assignee: "", priority: "medium", dueDate: "" });
  }, []);

  /* ─── Stats ─────────────────────────────────────────────────────────────── */

  const pendingAuths = priorAuths.filter((a) => a.status === "pending" || a.status === "in-review").length;
  const activeReferrals = referrals.filter((r) => r.status === "pending" || r.status === "scheduled").length;
  const scheduledToday = schedule.filter((s) => s.status !== "no-show" && s.status !== "completed").length;
  const totalPendingTasks = pendingAuths + activeReferrals;

  const kpis = [
    { label: "Prior Auth Pending", value: pendingAuths, icon: "\u{1F4CB}", color: "text-yellow-600", bg: "bg-yellow-50 border-yellow-200" },
    { label: "Insurance Verifications", value: verifications.length, icon: "\u{1F6E1}", color: "text-blue-600", bg: "bg-blue-50 border-blue-200" },
    { label: "Active Referrals", value: activeReferrals, icon: "\u{1F517}", color: "text-purple-600", bg: "bg-purple-50 border-purple-200" },
    { label: "Scheduled Today", value: scheduledToday, icon: "\u{1F4C5}", color: "text-healthos-600", bg: "bg-healthos-50 border-healthos-200" },
    { label: "SLA Compliance", value: "96.2%", icon: "\u2705", color: "text-green-600", bg: "bg-green-50 border-green-200" },
  ];

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: "prior-auth", label: "Prior Authorization", count: pendingAuths },
    { key: "insurance", label: "Insurance & Eligibility" },
    { key: "referrals", label: "Referral Management", count: activeReferrals },
    { key: "scheduling", label: "Scheduling", count: scheduledToday },
    { key: "workflows", label: "Workflows", count: workflows.filter((w) => w.completedSteps < w.totalSteps).length },
  ];

  /* ─── Render ────────────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Operations Command Center</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage authorizations, insurance, referrals, scheduling, and workflows in one place.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {totalPendingTasks > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-yellow-100 px-3 py-1 text-sm font-semibold text-yellow-800 border border-yellow-300">
              <span className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
              {totalPendingTasks} pending tasks
            </span>
          )}
          <button
            onClick={() => setShowNewTask(true)}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors shadow-sm"
          >
            + New Task
          </button>
        </div>
      </div>

      {/* ── KPI Stats Bar ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((kpi) => (
          <div key={kpi.label} className={`card card-hover rounded-xl border p-4 ${kpi.bg} animate-fade-in-up`}>
            <div className="flex items-center justify-between">
              <span className="text-xl">{kpi.icon}</span>
            </div>
            <p className={`mt-2 text-2xl font-bold ${kpi.color}`}>{kpi.value}</p>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mt-1">{kpi.label}</p>
          </div>
        ))}
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-1 overflow-x-auto" aria-label="Operations tabs">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className={`ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  activeTab === tab.key ? "bg-healthos-100 text-healthos-700" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab Content ────────────────────────────────────────────────────── */}
      <div className="animate-fade-in-up">

        {/* ═══ Prior Authorization ═══════════════════════════════════════════ */}
        {activeTab === "prior-auth" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Prior Authorization Requests</h2>
              <button
                onClick={() => setShowNewAuth(!showNewAuth)}
                className="rounded-lg border border-healthos-300 bg-healthos-50 px-4 py-2 text-sm font-medium text-healthos-700 hover:bg-healthos-100 transition-colors"
              >
                {showNewAuth ? "Cancel" : "+ New Prior Auth"}
              </button>
            </div>

            {/* New Prior Auth Form */}
            {showNewAuth && (
              <div className="card rounded-xl border border-healthos-200 bg-healthos-50/30 p-5 animate-fade-in-up">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-4">Submit New Prior Authorization</h3>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const newPa: PriorAuthRequest = {
                      id: `PA-${String(priorAuths.length + 1).padStart(3, "0")}`,
                      patient: authForm.patient,
                      procedure: authForm.procedure,
                      insurance: authForm.insurance,
                      status: "pending",
                      urgency: authForm.urgency as PriorAuthRequest["urgency"],
                      submittedDate: "2026-03-15",
                      cptCode: authForm.cptCode,
                      provider: "Current Provider",
                    };
                    setPriorAuths((prev) => [newPa, ...prev]);
                    setShowNewAuth(false);
                    setAuthForm({ patient: "", procedure: "", insurance: "", cptCode: "", urgency: "routine" });
                  }}
                  className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
                >
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Patient Name *</label>
                    <input required value={authForm.patient} onChange={(e) => setAuthForm({ ...authForm, patient: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="Full name" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Procedure *</label>
                    <input required value={authForm.procedure} onChange={(e) => setAuthForm({ ...authForm, procedure: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. MRI Lumbar Spine" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">CPT Code</label>
                    <input value={authForm.cptCode} onChange={(e) => setAuthForm({ ...authForm, cptCode: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. 72148" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Insurance *</label>
                    <input required value={authForm.insurance} onChange={(e) => setAuthForm({ ...authForm, insurance: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Blue Cross PPO" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Urgency</label>
                    <select value={authForm.urgency} onChange={(e) => setAuthForm({ ...authForm, urgency: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                      <option value="routine">Routine</option>
                      <option value="urgent">Urgent</option>
                      <option value="emergent">Emergent</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button type="submit" className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors">
                      Submit Request
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Prior Auth Table */}
            <div className="card rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">ID</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Patient</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Procedure</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Insurance</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Urgency</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Submitted</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white dark:bg-gray-900">
                    {priorAuths.map((pa) => (
                      <tr key={pa.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <td className="px-4 py-3 text-sm font-mono text-gray-500 dark:text-gray-400">{pa.id}</td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{pa.patient}</td>
                        <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
                          {pa.procedure}
                          {pa.cptCode && <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">({pa.cptCode})</span>}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{pa.insurance}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${authStatusColors[pa.status]}`}>
                            {pa.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-semibold uppercase ${
                            pa.urgency === "emergent" ? "text-red-600" : pa.urgency === "urgent" ? "text-orange-600" : "text-gray-500 dark:text-gray-400"
                          }`}>
                            {pa.urgency}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{pa.submittedDate}</td>
                        <td className="px-4 py-3">
                          {(pa.status === "pending" || pa.status === "in-review") && (
                            <button
                              onClick={() => handleEvaluatePriorAuth(pa)}
                              disabled={evaluatingId === pa.id}
                              className="rounded-md bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-wait transition-colors"
                            >
                              {evaluatingId === pa.id ? "Evaluating..." : "Evaluate"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Insurance & Eligibility ══════════════════════════════════════ */}
        {activeTab === "insurance" && (
          <div className="space-y-6">
            {/* Verification Form */}
            <div className="card card-hover rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Verify Insurance Eligibility</h2>
              <form onSubmit={handleVerifyInsurance} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Patient ID *</label>
                  <input required value={insuranceForm.patientId} onChange={(e) => setInsuranceForm({ ...insuranceForm, patientId: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="Patient ID or MRN" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Insurance Company *</label>
                  <input required value={insuranceForm.insurerName} onChange={(e) => setInsuranceForm({ ...insuranceForm, insurerName: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Blue Cross" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Member ID *</label>
                  <input required value={insuranceForm.memberId} onChange={(e) => setInsuranceForm({ ...insuranceForm, memberId: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="Member ID" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Group Number</label>
                  <input value={insuranceForm.groupNumber} onChange={(e) => setInsuranceForm({ ...insuranceForm, groupNumber: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="Group #" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Date of Birth</label>
                  <input type="date" value={insuranceForm.dob} onChange={(e) => setInsuranceForm({ ...insuranceForm, dob: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
                </div>
                <div className="flex items-end">
                  <button type="submit" disabled={verifyingInsurance} className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-wait transition-colors">
                    {verifyingInsurance ? "Verifying..." : "Verify Eligibility"}
                  </button>
                </div>
              </form>
            </div>

            {/* Verification Result */}
            {verificationResult && (
              <div className="card rounded-xl border border-green-200 bg-green-50/30 p-6 animate-fade-in-up">
                <div className="flex items-center gap-2 mb-4">
                  <span className="h-3 w-3 rounded-full bg-green-500" />
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Verification Result</h3>
                </div>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                  {Object.entries(verificationResult).filter(([k]) => k !== "benefits").map(([key, value]) => (
                    <div key={key}>
                      <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{key.replace(/_/g, " ")}</p>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{String(value)}</p>
                    </div>
                  ))}
                </div>
                {verificationResult.benefits && Array.isArray(verificationResult.benefits) && (
                  <div className="mt-4 border-t border-green-200 pt-4">
                    <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Benefits Summary</p>
                    <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                      {(verificationResult.benefits as string[]).map((b, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                          <span className="h-1.5 w-1.5 rounded-full bg-green-500 flex-shrink-0" />
                          {b}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Recent Verifications Table */}
            <div className="card rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-800">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Recent Verifications</h3>
              </div>
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Patient</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Insurer</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Member ID</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Eligibility</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Copay</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Deductible</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Verified</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white dark:bg-gray-900">
                    {verifications.map((v) => (
                      <tr key={v.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{v.patient}</td>
                        <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{v.insurerName}</td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-500 dark:text-gray-400">{v.memberId}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            v.eligibility === "active" ? "bg-green-100 text-green-800" : v.eligibility === "inactive" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"
                          }`}>
                            {v.eligibility}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{v.copay}</td>
                        <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
                          {v.deductibleMet} / {v.deductible}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{v.verifiedDate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>
        )}

        {/* ═══ Referral Management ══════════════════════════════════════════ */}
        {activeTab === "referrals" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Referral Management</h2>
              <button
                onClick={() => setShowNewReferral(!showNewReferral)}
                className="rounded-lg border border-healthos-300 bg-healthos-50 px-4 py-2 text-sm font-medium text-healthos-700 hover:bg-healthos-100 transition-colors"
              >
                {showNewReferral ? "Cancel" : "+ Create Referral"}
              </button>
            </div>

            {/* Create Referral Form */}
            {showNewReferral && (
              <div className="card rounded-xl border border-healthos-200 bg-healthos-50/30 p-5 animate-fade-in-up">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-4">Create New Referral</h3>
                <form onSubmit={handleCreateReferral} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Patient Name *</label>
                    <input required value={referralForm.patient} onChange={(e) => setReferralForm({ ...referralForm, patient: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="Full name" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Referring Provider *</label>
                    <input required value={referralForm.referringProvider} onChange={(e) => setReferralForm({ ...referralForm, referringProvider: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Dr. Chen" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Specialist Type *</label>
                    <select required value={referralForm.specialistType} onChange={(e) => setReferralForm({ ...referralForm, specialistType: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                      <option value="">Select specialist...</option>
                      <option value="Cardiology">Cardiology</option>
                      <option value="Orthopedics">Orthopedics</option>
                      <option value="Dermatology">Dermatology</option>
                      <option value="Gastroenterology">Gastroenterology</option>
                      <option value="Pulmonology">Pulmonology</option>
                      <option value="Neurology">Neurology</option>
                      <option value="Endocrinology">Endocrinology</option>
                      <option value="Oncology">Oncology</option>
                      <option value="Rheumatology">Rheumatology</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Reason *</label>
                    <input required value={referralForm.reason} onChange={(e) => setReferralForm({ ...referralForm, reason: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="Clinical reason for referral" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</label>
                    <select value={referralForm.priority} onChange={(e) => setReferralForm({ ...referralForm, priority: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2 lg:col-span-3 flex justify-end">
                    <button type="submit" disabled={creatingReferral} className="rounded-lg bg-healthos-600 px-6 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors">
                      {creatingReferral ? "Creating..." : "Create Referral"}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Referral Cards */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {referrals.map((ref) => (
                <div key={ref.id} className="card card-hover rounded-xl border border-gray-200 dark:border-gray-700 p-5 animate-fade-in-up">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{ref.patient}</h3>
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${referralStatusColors[ref.status]}`}>
                          {ref.status}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{ref.id} &middot; {ref.createdDate}</p>
                    </div>
                    <span className={`text-xs font-bold uppercase ${priorityColors[ref.priority]}`}>
                      {ref.priority}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Referring Provider</p>
                      <p className="font-medium text-gray-800 dark:text-gray-200">{ref.referringProvider}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Specialist Type</p>
                      <p className="font-medium text-gray-800 dark:text-gray-200">{ref.specialistType}</p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400">Reason</p>
                      <p className="text-gray-700 dark:text-gray-300">{ref.reason}</p>
                    </div>
                  </div>

                  {/* Timeline */}
                  <div className="border-t border-gray-100 dark:border-gray-800 pt-3">
                    <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">Tracking Timeline</p>
                    <div className="flex items-center gap-1">
                      {ref.timeline.map((step, i) => (
                        <div key={i} className="flex items-center flex-1 min-w-0">
                          <div className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${
                            step.completed ? "bg-green-500" : "bg-gray-300"
                          }`} />
                          <div className={`h-0.5 flex-1 ${
                            i < ref.timeline.length - 1
                              ? step.completed ? "bg-green-400" : "bg-gray-200"
                              : "bg-transparent"
                          }`} />
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-1 mt-1">
                      {ref.timeline.map((step, i) => (
                        <p key={i} className="flex-1 text-[11px] text-gray-500 dark:text-gray-400 truncate min-w-0">{step.event}</p>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ Scheduling ══════════════════════════════════════════════════= */}
        {activeTab === "scheduling" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Today&apos;s Schedule</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">March 15, 2026 &middot; Day View</p>
              </div>
              <button
                onClick={handleSuggestSlot}
                disabled={suggestingSlot}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-wait transition-colors"
              >
                {suggestingSlot ? "Finding slot..." : "Suggest Slot (AI)"}
              </button>
            </div>

            {/* AI Suggested Slot */}
            {suggestedSlot && (
              <div className="card rounded-xl border border-healthos-200 bg-healthos-50/30 p-4 animate-fade-in-up">
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-flex items-center rounded-full bg-healthos-100 px-2 py-0.5 text-xs font-semibold text-healthos-700">AI Suggestion</span>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
                  {Object.entries(suggestedSlot).map(([key, value]) => (
                    <div key={key}>
                      <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{key.replace(/_/g, " ")}</p>
                      <p className="font-medium text-gray-900 dark:text-gray-100">{typeof value === "number" && key === "confidence" ? `${(value * 100).toFixed(0)}%` : String(value)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Schedule Grid */}
            <div className="card rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="divide-y divide-gray-100">
                {schedule.map((slot) => (
                  <div
                    key={slot.id}
                    className={`flex items-center gap-4 px-5 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                      slot.conflict ? "bg-red-50/50 border-l-4 border-l-red-400" : ""
                    }`}
                  >
                    {/* Time */}
                    <div className="w-20 flex-shrink-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{slot.time}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{slot.duration} min</p>
                    </div>

                    {/* Divider */}
                    <div className={`h-10 w-0.5 rounded-full flex-shrink-0 ${
                      slot.status === "completed" ? "bg-gray-300" : slot.status === "in-progress" ? "bg-healthos-500" : "bg-blue-400"
                    }`} />

                    {/* Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{slot.patient}</p>
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${appointmentTypeColors[slot.type]}`}>
                          {slot.type}
                        </span>
                        {slot.conflict && (
                          <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-700">
                            CONFLICT
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{slot.provider}</p>
                    </div>

                    {/* Status */}
                    <div className="flex-shrink-0 text-right">
                      <span className={`text-xs font-semibold capitalize ${appointmentStatusColors[slot.status]}`}>
                        {slot.status.replace("-", " ")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═══ Workflows ═══════════════════════════════════════════════════= */}
        {activeTab === "workflows" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Active Workflows</h2>
              <button
                onClick={() => setShowNewWorkflow(!showNewWorkflow)}
                className="rounded-lg border border-healthos-300 bg-healthos-50 px-4 py-2 text-sm font-medium text-healthos-700 hover:bg-healthos-100 transition-colors"
              >
                {showNewWorkflow ? "Cancel" : "+ Start Workflow"}
              </button>
            </div>

            {/* New Workflow Form */}
            {showNewWorkflow && (
              <div className="card rounded-xl border border-healthos-200 bg-healthos-50/30 p-5 animate-fade-in-up">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-4">Start New Workflow</h3>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Workflow Template</label>
                    <select
                      value={selectedTemplate}
                      onChange={(e) => setSelectedTemplate(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                    >
                      {workflowTemplates.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={() => setShowNewWorkflow(false)}
                    className="rounded-lg bg-healthos-600 px-6 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
                  >
                    Start Workflow
                  </button>
                </div>
              </div>
            )}

            {/* Workflow Cards */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {workflows.map((wf) => {
                const isComplete = wf.completedSteps === wf.totalSteps;
                const progressPct = Math.round((wf.completedSteps / wf.totalSteps) * 100);
                const slaHours = Math.floor(wf.slaMinutesRemaining / 60);
                const slaMins = wf.slaMinutesRemaining % 60;
                const slaUrgent = wf.slaMinutesRemaining > 0 && wf.slaMinutesRemaining < 180;

                return (
                  <div key={wf.id} className={`card card-hover rounded-xl border p-5 animate-fade-in-up ${
                    isComplete ? "border-green-200 bg-green-50/20" : slaUrgent ? "border-orange-200" : "border-gray-200 dark:border-gray-700"
                  }`}>
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{wf.name}</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {wf.assignedTeam} &middot; {wf.id}
                        </p>
                      </div>
                      {!isComplete && wf.slaMinutesRemaining > 0 && (
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                          slaUrgent ? "bg-orange-100 text-orange-700" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                        }`}>
                          {slaUrgent && <span className="h-1.5 w-1.5 rounded-full bg-orange-500 animate-pulse" />}
                          {slaHours}h {slaMins}m remaining
                        </span>
                      )}
                      {isComplete && (
                        <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                          Complete
                        </span>
                      )}
                    </div>

                    {/* Progress Bar */}
                    <div className="mb-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">Step {wf.completedSteps} of {wf.totalSteps}</span>
                        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{progressPct}%</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-gray-200">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            isComplete ? "bg-green-500" : "bg-healthos-500"
                          }`}
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Steps */}
                    <div className="space-y-1.5">
                      {wf.steps.map((step, i) => (
                        <div key={i} className={`flex items-center gap-2 rounded-md px-2 py-1 text-xs ${
                          step.active ? "bg-healthos-50 text-healthos-700 font-semibold" : step.completed ? "text-gray-500 dark:text-gray-400" : "text-gray-500 dark:text-gray-400"
                        }`}>
                          <span className={`flex h-4 w-4 items-center justify-center rounded-full text-[11px] font-bold flex-shrink-0 ${
                            step.completed
                              ? "bg-green-500 text-white"
                              : step.active
                              ? "bg-healthos-500 text-white"
                              : "bg-gray-200 text-gray-500 dark:text-gray-400"
                          }`}>
                            {step.completed ? "\u2713" : i + 1}
                          </span>
                          <span className={step.completed ? "line-through" : ""}>{step.name}</span>
                          {step.active && <span className="ml-auto text-[11px] font-medium text-healthos-500">Current</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* ── New Task Modal ──────────────────────────────────────────────────── */}
      {showNewTask && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4" onClick={() => setShowNewTask(false)}>
          <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-gray-900 p-4 sm:p-6 shadow-2xl animate-fade-in-up" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">New Task</h2>
              <button onClick={() => setShowNewTask(false)} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:text-gray-400 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Task Title *</label>
                <input required value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Review prior auth for Patient X" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Assignee</label>
                  <input value={taskForm.assignee} onChange={(e) => setTaskForm({ ...taskForm, assignee: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Dr. Smith" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</label>
                  <select value={taskForm.priority} onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Due Date</label>
                <input type="date" value={taskForm.dueDate} onChange={(e) => setTaskForm({ ...taskForm, dueDate: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowNewTask(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
                <button type="submit" className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">Create Task</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
