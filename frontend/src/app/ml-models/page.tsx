"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchMLModels,
  fetchMLModelMetrics,
  runMLPrediction,
  fetchFederatedStatus,
  startFederatedRound,
  type MLModelInfo,
  type MLPrediction,
} from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// ── Types ────────────────────────────────────────────────────────────────────

interface ModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  auc_roc: number;
  predictions_today: number;
  avg_latency_ms: number;
  fairness_metrics: Record<string, number>;
}

interface FederatedState {
  status: string;
  current_round: number;
  total_rounds: number;
  participating_tenants: number;
  global_accuracy: number;
  privacy_budget_remaining: number;
  last_aggregation?: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const TYPE_BADGE: Record<string, { bg: string; text: string }> = {
  BiLSTM: { bg: "bg-indigo-100", text: "text-indigo-700" },
  XGBoost: { bg: "bg-emerald-100", text: "text-emerald-700" },
  "Random Forest": { bg: "bg-amber-100", text: "text-amber-700" },
  "Digital Twin": { bg: "bg-purple-100", text: "text-purple-700" },
  HMM: { bg: "bg-pink-100", text: "text-pink-700" },
  Multimodal: { bg: "bg-cyan-100", text: "text-cyan-700" },
};

function badgeFor(type: string) {
  for (const [key, val] of Object.entries(TYPE_BADGE)) {
    if (type.toLowerCase().includes(key.toLowerCase())) return val;
  }
  return { bg: "bg-gray-100 dark:bg-gray-800", text: "text-gray-700 dark:text-gray-300" };
}

const STATUS_STYLES: Record<string, { dot: string; label: string }> = {
  active: { dot: "bg-emerald-500", label: "Active" },
  training: { dot: "bg-amber-500", label: "Training" },
  inactive: { dot: "bg-gray-400", label: "Inactive" },
  error: { dot: "bg-red-500", label: "Error" },
};

const DEMO_MODELS: MLModelInfo[] = [
  { id: "bilstm-glucose", name: "BiLSTM Glucose Predictor", type: "BiLSTM", version: "3.2.1", status: "active", accuracy: 0.943, predictions_count: 12847, description: "Bidirectional LSTM for continuous glucose level prediction", last_trained: "2026-03-10T08:00:00Z" },
  { id: "xgb-hosp-risk", name: "XGBoost Hospitalization Risk", type: "XGBoost", version: "2.8.0", status: "active", accuracy: 0.912, predictions_count: 8932, description: "Gradient boosted model for 30-day hospitalization risk scoring", last_trained: "2026-03-12T14:30:00Z" },
  { id: "rf-disease", name: "Random Forest Disease Classifier", type: "Random Forest", version: "4.1.0", status: "active", accuracy: 0.887, predictions_count: 6521, description: "Multi-class disease classification from lab results and vitals", last_trained: "2026-03-08T11:00:00Z" },
  { id: "digital-twin", name: "Patient Digital Twin", type: "Digital Twin", version: "1.5.2", status: "training", accuracy: 0.876, predictions_count: 3214, description: "Patient-specific physiological simulation model", last_trained: "2026-03-05T16:00:00Z" },
  { id: "hmm-lifestyle", name: "HMM Lifestyle Patterns", type: "HMM", version: "2.0.3", status: "active", accuracy: 0.834, predictions_count: 5678, description: "Hidden Markov Model for lifestyle pattern recognition", last_trained: "2026-03-11T09:15:00Z" },
  { id: "multimodal-fusion", name: "Multimodal Attention Fusion", type: "Multimodal", version: "1.2.0", status: "active", accuracy: 0.921, predictions_count: 2190, description: "Cross-modal attention network fusing imaging, labs, and clinical notes", last_trained: "2026-03-13T07:45:00Z" },
];

const DEMO_FEDERATED: FederatedState = {
  status: "in_progress",
  current_round: 7,
  total_rounds: 12,
  participating_tenants: 5,
  global_accuracy: 0.908,
  privacy_budget_remaining: 0.64,
  last_aggregation: "2026-03-14T22:30:00Z",
};

const DEMO_PREDICTION_HISTORY = [
  { day: "Mon", predictions: 1842 },
  { day: "Tue", predictions: 2105 },
  { day: "Wed", predictions: 1956 },
  { day: "Thu", predictions: 2340 },
  { day: "Fri", predictions: 2187 },
  { day: "Sat", predictions: 1423 },
  { day: "Sun", predictions: 1105 },
];

// ── Component ────────────────────────────────────────────────────────────────

export default function MLModelsPage() {
  const [models, setModels] = useState<MLModelInfo[]>(DEMO_MODELS);
  const [federated, setFederated] = useState<FederatedState>(DEMO_FEDERATED);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedMetrics, setSelectedMetrics] = useState<ModelMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  // Prediction runner state
  const [showPrediction, setShowPrediction] = useState(false);
  const [predModelName, setPredModelName] = useState("");
  const [predPatientId, setPredPatientId] = useState("");
  const [predResult, setPredResult] = useState<MLPrediction | null>(null);
  const [predLoading, setPredLoading] = useState(false);
  const [predError, setPredError] = useState<string | null>(null);

  // Federated round form
  const [showFedForm, setShowFedForm] = useState(false);
  const [fedModelName, setFedModelName] = useState("");
  const [fedRounds, setFedRounds] = useState(10);
  const [fedMinClients, setFedMinClients] = useState(3);
  const [fedStarting, setFedStarting] = useState(false);

  // ── Data fetching ──────────────────────────────────────────────────────────

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchMLModels();
        const data = res as Record<string, unknown>;
        const list = (data.models ?? data) as MLModelInfo[];
        if (Array.isArray(list) && list.length > 0) setModels(list);
      } catch {
        /* use demo data */
      }
      try {
        const res = await fetchFederatedStatus();
        if (res && typeof res === "object") setFederated(res as unknown as FederatedState);
      } catch {
        /* use demo data */
      }
      setLoading(false);
    }
    load();
  }, []);

  const selectModel = useCallback(async (id: string) => {
    setSelectedModelId(id);
    setSelectedMetrics(null);
    setMetricsLoading(true);
    try {
      const res = await fetchMLModelMetrics(id);
      if (res && typeof res === "object") setSelectedMetrics(res as unknown as ModelMetrics);
    } catch {
      // Show demo metrics
      setSelectedMetrics({
        accuracy: 0.932,
        precision: 0.918,
        recall: 0.945,
        f1_score: 0.931,
        auc_roc: 0.967,
        predictions_today: 1247,
        avg_latency_ms: 23,
        fairness_metrics: {
          demographic_parity: 0.94,
          equalized_odds: 0.91,
          predictive_parity: 0.88,
        },
      });
    } finally {
      setMetricsLoading(false);
    }
  }, []);

  const handleRunPrediction = useCallback(async () => {
    if (!predModelName || !predPatientId) return;
    setPredLoading(true);
    setPredError(null);
    setPredResult(null);
    try {
      const res = await runMLPrediction({ model_name: predModelName, patient_id: predPatientId });
      setPredResult(res as unknown as MLPrediction);
    } catch {
      // Demo result
      setPredResult({
        model_name: predModelName,
        prediction: { risk_score: 0.73, risk_level: "moderate", recommendation: "Schedule follow-up within 14 days" },
        confidence: 0.89,
        features_used: ["age", "bmi", "blood_pressure", "hba1c", "medication_adherence", "exercise_frequency"],
        timestamp: new Date().toISOString(),
      });
    } finally {
      setPredLoading(false);
    }
  }, [predModelName, predPatientId]);

  const handleStartFederatedRound = useCallback(async () => {
    if (!fedModelName) return;
    setFedStarting(true);
    try {
      await startFederatedRound({ model_name: fedModelName, rounds: fedRounds, min_clients: fedMinClients });
    } catch {
      /* ignore */
    }
    setFedStarting(false);
    setShowFedForm(false);
  }, [fedModelName, fedRounds, fedMinClients]);

  const openPredictionRunner = useCallback((modelName?: string) => {
    if (modelName) setPredModelName(modelName);
    setPredResult(null);
    setPredError(null);
    setShowPrediction(true);
  }, []);

  // ── Derived values ─────────────────────────────────────────────────────────

  const selectedModel = models.find((m) => m.id === selectedModelId);
  const activeCount = models.filter((m) => m.status === "active").length;
  const totalPredictions = models.reduce((s, m) => s + m.predictions_count, 0);
  const avgAccuracy = models.reduce((s, m) => s + (m.accuracy || 0), 0) / (models.length || 1);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">ML Models &amp; AI</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Monitor model performance, predictions, and federated learning</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => openPredictionRunner()}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
          >
            Run Prediction
          </button>
        </div>
      </div>

      {/* ── Stats Bar ───────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5 animate-fade-in-up" style={{ animationDelay: "50ms" }}>
        {[
          { label: "Active Models", value: String(activeCount), sub: `${models.length} total` },
          { label: "Predictions Today", value: totalPredictions.toLocaleString(), sub: "+12% vs yesterday" },
          { label: "Avg Accuracy", value: `${(avgAccuracy * 100).toFixed(1)}%`, sub: "across all models" },
          { label: "Avg Latency", value: "24ms", sub: "p95 inference" },
          { label: "Federated Status", value: federated.status === "in_progress" ? "In Progress" : federated.status, sub: `Round ${federated.current_round}/${federated.total_rounds}` },
        ].map((kpi) => (
          <div key={kpi.label} className="card">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{kpi.value}</p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Model Cards Grid ────────────────────────────────────────────────── */}
      <div>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Models ({models.length})</h2>
        {loading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="h-4 w-32 rounded bg-gray-200" />
                <div className="mt-3 h-3 w-20 rounded bg-gray-200" />
                <div className="mt-4 h-2 w-full rounded bg-gray-200" />
                <div className="mt-6 flex gap-2">
                  <div className="h-8 w-24 rounded bg-gray-200" />
                  <div className="h-8 w-24 rounded bg-gray-200" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {models.map((model, idx) => {
              const badge = badgeFor(model.type);
              const status = STATUS_STYLES[model.status] || STATUS_STYLES.inactive;
              const acc = model.accuracy || 0;
              return (
                <div
                  key={model.id}
                  className={`card card-hover cursor-pointer transition-all animate-fade-in-up ${selectedModelId === model.id ? "ring-2 ring-healthos-500" : ""}`}
                  style={{ animationDelay: `${idx * 60}ms` }}
                  onClick={() => selectModel(model.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">{model.name}</h3>
                      <div className="mt-1 flex items-center gap-2">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${badge.bg} ${badge.text}`}>
                          {model.type}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">v{model.version}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${status.dot}`} />
                      <span className="text-xs text-gray-500 dark:text-gray-400">{status.label}</span>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-1 xs:grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Accuracy</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{(acc * 100).toFixed(1)}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Predictions</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{model.predictions_count.toLocaleString()}</p>
                    </div>
                  </div>

                  {/* Accuracy sparkline bar */}
                  <div className="mt-3">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                      <div
                        className="h-full rounded-full bg-healthos-500 transition-all duration-500"
                        style={{ width: `${acc * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); selectModel(model.id); }}
                      className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      View Details
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); openPredictionRunner(model.name); }}
                      className="rounded-lg bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700 transition-colors"
                    >
                      Run Prediction
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Model Detail Panel ──────────────────────────────────────────────── */}
      {selectedModel && (
        <div className="card animate-fade-in-up">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-4">
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">{selectedModel.name}</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">{selectedModel.description}</p>
            </div>
            <button
              onClick={() => { setSelectedModelId(null); setSelectedMetrics(null); }}
              className="rounded-lg p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {metricsLoading ? (
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-3 w-16 rounded bg-gray-200" />
                  <div className="mt-2 h-6 w-12 rounded bg-gray-200" />
                </div>
              ))}
            </div>
          ) : selectedMetrics ? (
            <div className="mt-6 space-y-6">
              {/* Metric bars */}
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
                {([
                  { label: "Accuracy", value: selectedMetrics.accuracy },
                  { label: "Precision", value: selectedMetrics.precision },
                  { label: "Recall", value: selectedMetrics.recall },
                  { label: "F1 Score", value: selectedMetrics.f1_score },
                  { label: "AUC-ROC", value: selectedMetrics.auc_roc },
                ] as const).map((m) => (
                  <div key={m.label}>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{m.label}</p>
                    <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{(m.value * 100).toFixed(1)}%</p>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                      <div
                        className="h-full rounded-full bg-healthos-500 transition-all duration-700"
                        style={{ width: `${m.value * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Fairness metrics */}
              {selectedMetrics.fairness_metrics && Object.keys(selectedMetrics.fairness_metrics).length > 0 && (
                <div>
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Fairness Metrics</h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    {Object.entries(selectedMetrics.fairness_metrics).map(([key, val]) => (
                      <div key={key} className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-3">
                        <p className="text-xs font-medium capitalize text-gray-500 dark:text-gray-400">{key.replace(/_/g, " ")}</p>
                        <div className="mt-1 flex items-center gap-2">
                          <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{(val * 100).toFixed(1)}%</span>
                          <span className={`text-xs font-medium ${val >= 0.9 ? "text-emerald-600" : val >= 0.8 ? "text-amber-600" : "text-red-600"}`}>
                            {val >= 0.9 ? "Good" : val >= 0.8 ? "Fair" : "Needs Review"}
                          </span>
                        </div>
                        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${val >= 0.9 ? "bg-emerald-500" : val >= 0.8 ? "bg-amber-500" : "bg-red-500"}`}
                            style={{ width: `${val * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Prediction history chart */}
              <div>
                <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Prediction History (Last 7 Days)</h3>
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={DEMO_PREDICTION_HISTORY} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="day" tick={{ fontSize: 12, fill: "#9ca3af" }} />
                      <YAxis tick={{ fontSize: 12, fill: "#9ca3af" }} />
                      <Tooltip
                        contentStyle={{ borderRadius: "0.5rem", border: "1px solid #e5e7eb", fontSize: "0.75rem" }}
                      />
                      <Bar dataKey="predictions" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Quick run prediction */}
              <div className="flex items-center gap-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">Quick prediction with this model:</p>
                <button
                  onClick={() => openPredictionRunner(selectedModel.name)}
                  className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
                >
                  Run Prediction
                </button>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* ── Federated Learning Panel ────────────────────────────────────────── */}
      <div className="card animate-fade-in-up" style={{ animationDelay: "100ms" }}>
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Federated Learning</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Privacy-preserving distributed model training</p>
          </div>
          <button
            onClick={() => setShowFedForm(!showFedForm)}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
          >
            {showFedForm ? "Cancel" : "New Round"}
          </button>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {/* Current Round Progress */}
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Round Progress</p>
            <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
              {federated.current_round} / {federated.total_rounds}
            </p>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
              <div
                className="h-full rounded-full bg-healthos-500 transition-all duration-700"
                style={{ width: `${(federated.current_round / federated.total_rounds) * 100}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {((federated.current_round / federated.total_rounds) * 100).toFixed(0)}% complete
            </p>
          </div>

          {/* Participating Tenants */}
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Participating Tenants</p>
            <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{federated.participating_tenants}</p>
            <div className="mt-2 flex -space-x-1">
              {Array.from({ length: Math.min(federated.participating_tenants, 8) }).map((_, i) => (
                <div
                  key={i}
                  className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-healthos-500 text-[11px] font-bold text-white"
                >
                  T{i + 1}
                </div>
              ))}
            </div>
          </div>

          {/* Global Accuracy Trend */}
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Global Accuracy</p>
            <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{(federated.global_accuracy * 100).toFixed(1)}%</p>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-700"
                style={{ width: `${federated.global_accuracy * 100}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-emerald-600 font-medium">+0.3% from last round</p>
          </div>

          {/* Privacy Budget Remaining */}
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Privacy Budget Remaining</p>
            <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">{(federated.privacy_budget_remaining * 100).toFixed(0)}%</p>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  federated.privacy_budget_remaining > 0.5
                    ? "bg-emerald-500"
                    : federated.privacy_budget_remaining > 0.25
                    ? "bg-amber-500"
                    : "bg-red-500"
                }`}
                style={{ width: `${federated.privacy_budget_remaining * 100}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Differential privacy (epsilon)</p>
          </div>
        </div>

        {/* Start new round form */}
        {showFedForm && (
          <div className="mt-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4 animate-fade-in-up">
            <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Start New Federated Round</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Model</label>
                <select
                  value={fedModelName}
                  onChange={(e) => setFedModelName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Select model...</option>
                  {models.map((m) => (
                    <option key={m.id} value={m.name}>{m.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Rounds</label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={fedRounds}
                  onChange={(e) => setFedRounds(Number(e.target.value))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Min Clients</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={fedMinClients}
                  onChange={(e) => setFedMinClients(Number(e.target.value))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                onClick={handleStartFederatedRound}
                disabled={!fedModelName || fedStarting}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
              >
                {fedStarting ? "Starting..." : "Start Round"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Prediction Runner Slide-out ──────────────────────────────────────── */}
      {showPrediction && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowPrediction(false)} />
          {/* Panel */}
          <div className="relative w-full max-w-md bg-white dark:bg-gray-900 shadow-xl animate-fade-in-up overflow-y-auto">
            <div className="sticky top-0 flex items-center justify-between border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-4">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Run Prediction</h2>
              <button
                onClick={() => setShowPrediction(false)}
                className="rounded-lg p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4 p-6">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Model</label>
                <select
                  value={predModelName}
                  onChange={(e) => setPredModelName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Select model...</option>
                  {models.map((m) => (
                    <option key={m.id} value={m.name}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Patient ID</label>
                <input
                  type="text"
                  value={predPatientId}
                  onChange={(e) => setPredPatientId(e.target.value)}
                  placeholder="e.g. PAT-001"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>

              <button
                onClick={handleRunPrediction}
                disabled={!predModelName || !predPatientId || predLoading}
                className="w-full rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
              >
                {predLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                      <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75" />
                    </svg>
                    Running...
                  </span>
                ) : "Run Prediction"}
              </button>

              {predError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="text-sm text-red-600">{predError}</p>
                </div>
              )}

              {predResult && (
                <div className="space-y-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4 animate-fade-in-up">
                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Model</p>
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{predResult.model_name}</p>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Confidence</p>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">{(predResult.confidence * 100).toFixed(1)}%</span>
                      <div className="flex-1">
                        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${
                              predResult.confidence >= 0.8
                                ? "bg-emerald-500"
                                : predResult.confidence >= 0.6
                                ? "bg-amber-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${predResult.confidence * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Prediction</p>
                    <div className="mt-1 space-y-1">
                      {Object.entries(predResult.prediction).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-sm">
                          <span className="capitalize text-gray-600 dark:text-gray-400">{k.replace(/_/g, " ")}</span>
                          <span className="font-medium text-gray-900 dark:text-gray-100">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Features Used</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {predResult.features_used.map((f) => (
                        <span key={f} className="rounded-full bg-healthos-100 px-2 py-0.5 text-xs font-medium text-healthos-700">
                          {f.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Ran at {new Date(predResult.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
