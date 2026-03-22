"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  queryKnowledgeGraph,
  fetchKGStats,
  fetchDrugInteractionsKG,
  fetchDiseaseRelationsKG,
  fetchPatientGraphKG,
  type KGNode,
  type KGEdge,
  type KGQueryResult,
} from "@/lib/api";

/* ────────────────────────────── Demo / Mock Data ─────────────────────────── */

const DEMO_NODES: KGNode[] = [
  { id: "n1", label: "Type 2 Diabetes", type: "Disease", properties: { icd10: "E11", prevalence: "10.5%", severity: "chronic" } },
  { id: "n2", label: "Metformin", type: "Drug", properties: { class: "Biguanide", route: "oral", dosage: "500-2000mg" } },
  { id: "n3", label: "Insulin Resistance", type: "Symptom", properties: { onset: "gradual", measurable: true } },
  { id: "n4", label: "Polyuria", type: "Symptom", properties: { onset: "early", frequency: "common" } },
  { id: "n5", label: "Patient-0042", type: "Patient", properties: { age: 58, sex: "F", risk: "moderate" } },
  { id: "n6", label: "HNF1A", type: "Gene", properties: { chromosome: "12q24.31", association: "MODY3" } },
  { id: "n7", label: "Glipizide", type: "Drug", properties: { class: "Sulfonylurea", route: "oral", dosage: "5-20mg" } },
  { id: "n8", label: "Hypertension", type: "Disease", properties: { icd10: "I10", prevalence: "47%", severity: "chronic" } },
  { id: "n9", label: "Lisinopril", type: "Drug", properties: { class: "ACE Inhibitor", route: "oral", dosage: "10-40mg" } },
  { id: "n10", label: "Fatigue", type: "Symptom", properties: { onset: "gradual", frequency: "very common" } },
  { id: "n11", label: "Patient-0178", type: "Patient", properties: { age: 71, sex: "M", risk: "high" } },
  { id: "n12", label: "Diabetic Nephropathy", type: "Disease", properties: { icd10: "E11.22", prevalence: "30% of T2D", severity: "progressive" } },
  { id: "n13", label: "SGLT2 Inhibitor", type: "Drug", properties: { class: "Gliflozin", route: "oral", dosage: "10-25mg" } },
  { id: "n14", label: "TCF7L2", type: "Gene", properties: { chromosome: "10q25.2", association: "T2D susceptibility" } },
  { id: "n15", label: "Peripheral Neuropathy", type: "Symptom", properties: { onset: "late", frequency: "common in T2D" } },
];

const DEMO_EDGES: KGEdge[] = [
  { source: "n1", target: "n2", relationship: "TREATED_BY", properties: { first_line: true } },
  { source: "n1", target: "n3", relationship: "HAS_SYMPTOM", properties: { specificity: "high" } },
  { source: "n1", target: "n4", relationship: "HAS_SYMPTOM", properties: { specificity: "moderate" } },
  { source: "n5", target: "n1", relationship: "DIAGNOSED_WITH", properties: { date: "2024-01-15" } },
  { source: "n6", target: "n1", relationship: "ASSOCIATED_WITH", properties: { evidence: "strong" } },
  { source: "n1", target: "n7", relationship: "TREATED_BY", properties: { first_line: false } },
  { source: "n2", target: "n7", relationship: "INTERACTS_WITH", properties: { severity: "moderate", type: "hypoglycemia risk" } },
  { source: "n5", target: "n8", relationship: "DIAGNOSED_WITH", properties: { date: "2022-06-10" } },
  { source: "n8", target: "n9", relationship: "TREATED_BY", properties: { first_line: true } },
  { source: "n1", target: "n10", relationship: "HAS_SYMPTOM", properties: { specificity: "low" } },
  { source: "n11", target: "n1", relationship: "DIAGNOSED_WITH", properties: { date: "2019-03-22" } },
  { source: "n11", target: "n12", relationship: "DIAGNOSED_WITH", properties: { date: "2023-11-05" } },
  { source: "n1", target: "n12", relationship: "COMPLICATION_OF", properties: { risk: "30%" } },
  { source: "n12", target: "n13", relationship: "TREATED_BY", properties: { first_line: true } },
  { source: "n14", target: "n1", relationship: "ASSOCIATED_WITH", properties: { evidence: "genome-wide significant" } },
  { source: "n1", target: "n15", relationship: "HAS_SYMPTOM", properties: { specificity: "moderate" } },
  { source: "n8", target: "n10", relationship: "HAS_SYMPTOM", properties: { specificity: "low" } },
  { source: "n9", target: "n13", relationship: "INTERACTS_WITH", properties: { severity: "low", type: "renal synergy" } },
];

const DEMO_STATS = {
  total_nodes: 12_847,
  total_edges: 48_329,
  node_types: { Disease: 2841, Drug: 4126, Symptom: 3012, Patient: 1956, Gene: 912 },
  edge_types: { TREATED_BY: 12400, HAS_SYMPTOM: 9800, DIAGNOSED_WITH: 8700, ASSOCIATED_WITH: 6200, INTERACTS_WITH: 5400, COMPLICATION_OF: 5829 },
};

/* ────────────────────────────── Color & Layout ───────────────────────────── */

const NODE_COLORS: Record<string, string> = {
  Disease: "#ef4444",
  Drug: "#3b82f6",
  Symptom: "#eab308",
  Patient: "#22c55e",
  Gene: "#a855f7",
};

const NODE_COLORS_BG: Record<string, string> = {
  Disease: "bg-red-500",
  Drug: "bg-blue-500",
  Symptom: "bg-yellow-500",
  Patient: "bg-green-500",
  Gene: "bg-purple-500",
};

const NODE_COLORS_TEXT: Record<string, string> = {
  Disease: "text-red-600",
  Drug: "text-blue-600",
  Symptom: "text-yellow-600",
  Patient: "text-green-600",
  Gene: "text-purple-600",
};

type QueryType = "drug_interactions" | "disease_relations" | "patient_graph" | "custom";

interface RecentQuery {
  type: QueryType;
  entity: string;
  timestamp: number;
}

/* ── Simple force-directed layout (iterative spring model) ────────────────── */

interface LayoutNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  label: string;
  type: string;
}

function computeLayout(nodes: KGNode[], edges: KGEdge[], width: number, height: number): LayoutNode[] {
  const cx = width / 2;
  const cy = height / 2;

  // Initial positions in a circle
  const layoutNodes: LayoutNode[] = nodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.length;
    const radius = Math.min(width, height) * 0.35;
    return {
      id: n.id,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      vx: 0,
      vy: 0,
      label: n.label,
      type: n.type,
    };
  });

  const nodeMap = new Map(layoutNodes.map((n) => [n.id, n]));

  // Run simple force simulation
  const iterations = 120;
  const repulsion = 3000;
  const attraction = 0.005;
  const damping = 0.85;
  const centerPull = 0.01;

  for (let iter = 0; iter < iterations; iter++) {
    // Repulsion between all nodes
    for (let i = 0; i < layoutNodes.length; i++) {
      for (let j = i + 1; j < layoutNodes.length; j++) {
        const a = layoutNodes[i];
        const b = layoutNodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsion / (dist * dist);
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        a.vx += dx;
        a.vy += dy;
        b.vx -= dx;
        b.vy -= dy;
      }
    }

    // Attraction along edges
    for (const edge of edges) {
      const a = nodeMap.get(edge.source);
      const b = nodeMap.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const force = attraction;
      a.vx += dx * force;
      a.vy += dy * force;
      b.vx -= dx * force;
      b.vy -= dy * force;
    }

    // Center pull
    for (const n of layoutNodes) {
      n.vx += (cx - n.x) * centerPull;
      n.vy += (cy - n.y) * centerPull;
    }

    // Apply velocity
    for (const n of layoutNodes) {
      n.vx *= damping;
      n.vy *= damping;
      n.x += n.vx;
      n.y += n.vy;
      // Keep in bounds with padding
      n.x = Math.max(50, Math.min(width - 50, n.x));
      n.y = Math.max(40, Math.min(height - 40, n.y));
    }
  }

  return layoutNodes;
}

/* ────────────────────────────── Main Component ───────────────────────────── */

export default function KnowledgeGraphPage() {
  // Stats
  const [stats, setStats] = useState(DEMO_STATS);
  const [statsLoading, setStatsLoading] = useState(true);

  // Query panel
  const [queryType, setQueryType] = useState<QueryType>("drug_interactions");
  const [entityInput, setEntityInput] = useState("");
  const [depth, setDepth] = useState(2);
  const [searching, setSearching] = useState(false);
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([]);

  // Graph data
  const [nodes, setNodes] = useState<KGNode[]>(DEMO_NODES);
  const [edges, setEdges] = useState<KGEdge[]>(DEMO_EDGES);
  const [layoutNodes, setLayoutNodes] = useState<LayoutNode[]>([]);

  // Selection
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // SVG dimensions
  const svgRef = useRef<SVGSVGElement>(null);
  const [svgSize, setSvgSize] = useState({ width: 800, height: 500 });

  /* ── Load stats on mount ──────────────────────────────────────────────── */

  useEffect(() => {
    (async () => {
      setStatsLoading(true);
      try {
        const res = await fetchKGStats();
        setStats(res as typeof DEMO_STATS);
      } catch {
        // keep demo stats
      } finally {
        setStatsLoading(false);
      }
    })();
  }, []);

  /* ── SVG resize observer ──────────────────────────────────────────────── */

  useEffect(() => {
    const container = svgRef.current?.parentElement;
    if (!container) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) setSvgSize({ width, height });
      }
    });
    obs.observe(container);
    return () => obs.disconnect();
  }, []);

  /* ── Recompute layout when data or svg size changes ─────────────────── */

  useEffect(() => {
    if (nodes.length === 0) {
      setLayoutNodes([]);
      return;
    }
    setLayoutNodes(computeLayout(nodes, edges, svgSize.width, svgSize.height));
  }, [nodes, edges, svgSize]);

  /* ── Query handler ────────────────────────────────────────────────────── */

  const handleSearch = useCallback(async () => {
    if (!entityInput.trim() && queryType !== "custom") return;
    setSearching(true);
    setSelectedNodeId(null);

    const newRecent: RecentQuery = { type: queryType, entity: entityInput.trim(), timestamp: Date.now() };
    setRecentQueries((prev: RecentQuery[]) => [newRecent, ...prev.filter((q: RecentQuery) => q.entity !== newRecent.entity || q.type !== newRecent.type).slice(0, 4)]);

    try {
      let result: KGQueryResult;
      switch (queryType) {
        case "drug_interactions":
          result = (await fetchDrugInteractionsKG(entityInput.trim())) as KGQueryResult;
          break;
        case "disease_relations":
          result = (await fetchDiseaseRelationsKG(entityInput.trim())) as KGQueryResult;
          break;
        case "patient_graph":
          result = (await fetchPatientGraphKG(entityInput.trim())) as KGQueryResult;
          break;
        default:
          result = (await queryKnowledgeGraph({ query_type: "custom", entity: entityInput.trim(), depth })) as KGQueryResult;
      }
      if (result.nodes?.length) {
        setNodes(result.nodes);
        setEdges(result.edges);
      }
    } catch {
      // keep current demo data visible
    } finally {
      setSearching(false);
    }
  }, [queryType, entityInput, depth]);

  /* ── Replay recent query ──────────────────────────────────────────────── */

  const replayQuery = useCallback((q: RecentQuery) => {
    setQueryType(q.type);
    setEntityInput(q.entity);
  }, []);

  /* ── Derived data ─────────────────────────────────────────────────────── */

  const selectedNode = nodes.find((n: KGNode) => n.id === selectedNodeId) ?? null;
  const layoutMap = new Map<string, LayoutNode>(layoutNodes.map((n: LayoutNode) => [n.id, n]));

  const connectedEdges = selectedNodeId
    ? edges.filter((e: KGEdge) => e.source === selectedNodeId || e.target === selectedNodeId)
    : [];

  const queryTypeLabels: Record<QueryType, string> = {
    drug_interactions: "Drug Interactions",
    disease_relations: "Disease Relations",
    patient_graph: "Patient Graph",
    custom: "Custom Query",
  };

  const nodeRadius = (n: LayoutNode) => {
    const connected = edges.filter((e: KGEdge) => e.source === n.id || e.target === n.id).length;
    return Math.max(18, Math.min(32, 14 + connected * 2.5));
  };

  /* ────────────────────────────── Render ──────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Knowledge Graph Explorer</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Explore clinical relationships across diseases, drugs, symptoms, and patients
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-healthos-50 px-3 py-1 text-xs font-medium text-healthos-700">
            <span className="h-2 w-2 rounded-full bg-healthos-500 animate-pulse" />
            Live Graph
          </span>
        </div>
      </div>

      {/* ── Stats Bar ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {statsLoading
          ? [1, 2, 3, 4].map((i) => (
              <div key={i} className="card animate-pulse">
                <div className="h-3 w-20 rounded bg-gray-200" />
                <div className="mt-2 h-7 w-16 rounded bg-gray-200" />
              </div>
            ))
          : [
              { label: "Total Nodes", value: stats.total_nodes.toLocaleString(), icon: "circle" },
              { label: "Total Edges", value: stats.total_edges.toLocaleString(), icon: "link" },
              { label: "Node Types", value: Object.keys(stats.node_types).length.toString(), icon: "layers" },
              { label: "Edge Types", value: Object.keys(stats.edge_types).length.toString(), icon: "git-merge" },
            ].map((kpi) => (
              <div key={kpi.label} className="card card-hover">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{kpi.label}</p>
                <p className="mt-1 text-2xl font-bold text-healthos-700">{kpi.value}</p>
              </div>
            ))}
      </div>

      {/* ── Main layout: Query + Graph ─────────────────────────────────── */}
      <div className="flex flex-col gap-6 lg:flex-row">
        {/* ── Query Panel (1/3) ────────────────────────────────────────── */}
        <div className="w-full space-y-4 lg:w-1/3">
          <div className="card space-y-4">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Query Builder</h2>

            {/* Query type */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Query Type</label>
              <select
                value={queryType}
                onChange={(e) => setQueryType(e.target.value as QueryType)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              >
                <option value="drug_interactions">Drug Interactions</option>
                <option value="disease_relations">Disease Relations</option>
                <option value="patient_graph">Patient Graph</option>
                <option value="custom">Custom Query</option>
              </select>
            </div>

            {/* Entity input */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                {queryType === "patient_graph" ? "Patient ID" : "Entity Name"}
              </label>
              <input
                type="text"
                value={entityInput}
                onChange={(e) => setEntityInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder={
                  queryType === "drug_interactions"
                    ? "e.g. Metformin"
                    : queryType === "disease_relations"
                      ? "e.g. Type 2 Diabetes"
                      : queryType === "patient_graph"
                        ? "e.g. PAT-0042"
                        : "Enter entity or CYPHER query"
                }
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-500 dark:text-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
            </div>

            {/* Depth slider */}
            <div>
              <label className="mb-1 flex items-center justify-between text-xs font-medium text-gray-600 dark:text-gray-400">
                <span>Traversal Depth</span>
                <span className="rounded bg-healthos-50 px-1.5 py-0.5 text-healthos-700 font-semibold">{depth}</span>
              </label>
              <input
                type="range"
                min={1}
                max={5}
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="w-full accent-healthos-600"
              />
              <div className="mt-1 flex justify-between text-[11px] text-gray-500 dark:text-gray-400">
                <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
              </div>
            </div>

            {/* Search button */}
            <button
              onClick={handleSearch}
              disabled={searching}
              className="w-full rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-healthos-700 disabled:opacity-50"
            >
              {searching ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  Searching...
                </span>
              ) : (
                "Search Graph"
              )}
            </button>
          </div>

          {/* ── Recent Queries ──────────────────────────────────────────── */}
          {recentQueries.length > 0 && (
            <div className="card space-y-2">
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Recent Queries</h3>
              <ul className="space-y-1">
                {recentQueries.map((q: RecentQuery, i: number) => (
                  <li key={i}>
                    <button
                      onClick={() => replayQuery(q)}
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs text-gray-700 dark:text-gray-300 hover:bg-healthos-50 transition"
                    >
                      <span className="shrink-0 rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[11px] font-medium text-gray-500 dark:text-gray-400">
                        {queryTypeLabels[q.type as QueryType].split(" ")[0]}
                      </span>
                      <span className="truncate font-medium">{q.entity}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ── Legend ──────────────────────────────────────────────────── */}
          <div className="card space-y-2">
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Node Types</h3>
            <div className="flex flex-wrap gap-3">
              {Object.entries(NODE_COLORS_BG).map(([type, bg]) => (
                <span key={type} className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300">
                  <span className={`inline-block h-3 w-3 rounded-full ${bg}`} />
                  {type}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* ── Graph Visualization + Detail (2/3) ──────────────────────── */}
        <div className="w-full space-y-4 lg:w-2/3">
          {/* SVG Graph */}
          <div className="card card-hover relative overflow-hidden" style={{ minHeight: 500 }}>
            <div className="absolute left-4 top-4 z-10 flex items-center gap-2">
              <span className="rounded-md bg-white/80 px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 shadow-sm backdrop-blur">
                {nodes.length} nodes &middot; {edges.length} edges
              </span>
            </div>

            <svg
              ref={svgRef}
              viewBox={`0 0 ${svgSize.width} ${svgSize.height}`}
              className="h-full w-full"
              style={{ minHeight: 500 }}
            >
              <defs>
                {/* Arrow marker */}
                <marker id="arrow" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8" />
                </marker>
                {/* Glow filter */}
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Edges */}
              {edges.map((edge, i) => {
                const src = layoutMap.get(edge.source);
                const tgt = layoutMap.get(edge.target);
                if (!src || !tgt) return null;

                const isHighlighted =
                  selectedNodeId === edge.source ||
                  selectedNodeId === edge.target ||
                  hoveredNodeId === edge.source ||
                  hoveredNodeId === edge.target;

                const dimmed = (selectedNodeId || hoveredNodeId) && !isHighlighted;

                // Offset target for arrowhead
                const dx = tgt.x - src.x;
                const dy = tgt.y - src.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const r = nodeRadius(tgt);
                const tx = tgt.x - (dx / dist) * r;
                const ty = tgt.y - (dy / dist) * r;

                // Midpoint for label
                const mx = (src.x + tgt.x) / 2;
                const my = (src.y + tgt.y) / 2;

                return (
                  <g key={`edge-${i}`}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={tx}
                      y2={ty}
                      stroke={isHighlighted ? "#6366f1" : "#cbd5e1"}
                      strokeWidth={isHighlighted ? 2 : 1}
                      strokeOpacity={dimmed ? 0.15 : isHighlighted ? 0.9 : 0.5}
                      markerEnd="url(#arrow)"
                    />
                    {isHighlighted && (
                      <text
                        x={mx}
                        y={my - 6}
                        textAnchor="middle"
                        className="text-[11px] font-medium fill-indigo-600"
                      >
                        {edge.relationship}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {layoutNodes.map((n) => {
                const r = nodeRadius(n);
                const color = NODE_COLORS[n.type] || "#64748b";
                const isSelected = selectedNodeId === n.id;
                const isHovered = hoveredNodeId === n.id;
                const isConnected =
                  selectedNodeId &&
                  edges.some(
                    (e) =>
                      (e.source === selectedNodeId && e.target === n.id) ||
                      (e.target === selectedNodeId && e.source === n.id)
                  );
                const dimmed = (selectedNodeId || hoveredNodeId) && !isSelected && !isHovered && !isConnected;

                return (
                  <g
                    key={n.id}
                    className="cursor-pointer"
                    onClick={() => setSelectedNodeId(isSelected ? null : n.id)}
                    onMouseEnter={() => setHoveredNodeId(n.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                  >
                    {/* Outer glow for selected */}
                    {(isSelected || isHovered) && (
                      <circle cx={n.x} cy={n.y} r={r + 6} fill={color} fillOpacity={0.15} filter="url(#glow)" />
                    )}
                    {/* Main circle */}
                    <circle
                      cx={n.x}
                      cy={n.y}
                      r={r}
                      fill={color}
                      fillOpacity={dimmed ? 0.2 : 0.85}
                      stroke={isSelected ? "#1e293b" : color}
                      strokeWidth={isSelected ? 3 : 1.5}
                      strokeOpacity={dimmed ? 0.2 : 1}
                    />
                    {/* Label */}
                    <text
                      x={n.x}
                      y={n.y + r + 14}
                      textAnchor="middle"
                      className="text-[11px] font-semibold fill-gray-700"
                      fillOpacity={dimmed ? 0.2 : 1}
                    >
                      {n.label.length > 16 ? n.label.slice(0, 14) + "..." : n.label}
                    </text>
                    {/* Type badge inside circle */}
                    <text
                      x={n.x}
                      y={n.y + 4}
                      textAnchor="middle"
                      className="text-[11px] font-bold"
                      fill="white"
                      fillOpacity={dimmed ? 0.2 : 0.95}
                    >
                      {n.type.slice(0, 3).toUpperCase()}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* ── Details Panel ──────────────────────────────────────────── */}
          {selectedNode && (
            <div className="card animate-fade-in-up border-l-4" style={{ borderLeftColor: NODE_COLORS[selectedNode.type] || "#64748b" }}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block h-3 w-3 rounded-full ${NODE_COLORS_BG[selectedNode.type] || "bg-gray-400"}`}
                    />
                    <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">{selectedNode.label}</h3>
                    <span className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-[11px] font-medium text-gray-500 dark:text-gray-400">
                      {selectedNode.type}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">ID: {selectedNode.id}</p>
                </div>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="rounded p-1 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Properties table */}
              <div className="mt-3">
                <h4 className="mb-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Properties</h4>
                <div className="rounded-lg border border-gray-100 dark:border-gray-800 divide-y divide-gray-100">
                  {Object.entries(selectedNode.properties).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between px-3 py-1.5 text-xs">
                      <span className="font-medium text-gray-600 dark:text-gray-400">{k}</span>
                      <span className="text-gray-900 dark:text-gray-100">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Connected edges */}
              {connectedEdges.length > 0 && (
                <div className="mt-3">
                  <h4 className="mb-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Connections ({connectedEdges.length})
                  </h4>
                  <div className="space-y-1">
                    {connectedEdges.map((e, i) => {
                      const otherNodeId = e.source === selectedNodeId ? e.target : e.source;
                      const otherNode = nodes.find((n) => n.id === otherNodeId);
                      return (
                        <button
                          key={i}
                          onClick={() => setSelectedNodeId(otherNodeId)}
                          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                        >
                          <span className={`h-2 w-2 rounded-full ${NODE_COLORS_BG[otherNode?.type || ""] || "bg-gray-400"}`} />
                          <span className="font-medium text-gray-800 dark:text-gray-200">{otherNode?.label || otherNodeId}</span>
                          <span className="ml-auto rounded bg-indigo-50 px-1.5 py-0.5 text-[11px] font-medium text-indigo-600">
                            {e.relationship}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Relationship Table ─────────────────────────────────────────── */}
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">All Relationships</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">{edges.length} edges</span>
        </div>
        <div className="overflow-x-auto">
          <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
                <th className="pb-2 pr-4 font-medium">Source</th>
                <th className="pb-2 pr-4 font-medium">Relationship</th>
                <th className="pb-2 pr-4 font-medium">Target</th>
                <th className="pb-2 font-medium">Properties</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {edges.map((edge, i) => {
                const srcNode = nodes.find((n) => n.id === edge.source);
                const tgtNode = nodes.find((n) => n.id === edge.target);
                return (
                  <tr
                    key={i}
                    className="hover:bg-healthos-50/50 transition cursor-pointer"
                    onClick={() => setSelectedNodeId(edge.source)}
                  >
                    <td className="py-2 pr-4">
                      <span className="flex items-center gap-1.5">
                        <span className={`h-2 w-2 rounded-full ${NODE_COLORS_BG[srcNode?.type || ""] || "bg-gray-400"}`} />
                        <span className={`font-medium ${NODE_COLORS_TEXT[srcNode?.type || ""] || "text-gray-700 dark:text-gray-300"}`}>
                          {srcNode?.label || edge.source}
                        </span>
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700">
                        {edge.relationship}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className="flex items-center gap-1.5">
                        <span className={`h-2 w-2 rounded-full ${NODE_COLORS_BG[tgtNode?.type || ""] || "bg-gray-400"}`} />
                        <span className={`font-medium ${NODE_COLORS_TEXT[tgtNode?.type || ""] || "text-gray-700 dark:text-gray-300"}`}>
                          {tgtNode?.label || edge.target}
                        </span>
                      </span>
                    </td>
                    <td className="py-2">
                      <span className="text-gray-500 dark:text-gray-400">
                        {Object.entries(edge.properties)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(", ")}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table></div>
        </div>
      </div>
    </div>
  );
}
