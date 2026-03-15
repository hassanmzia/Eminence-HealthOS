"use client";

import React, { useState, useCallback, useMemo } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

// ─── Shared Types ────────────────────────────────────────────────────────────

interface DrillDownDataItem {
  name: string;
  value: number;
  children?: DrillDownDataItem[];
}

interface LineConfig {
  key: string;
  color: string;
  label: string;
}

interface PieDataItem {
  name: string;
  value: number;
  color?: string;
  details?: { label: string; value: string | number }[];
}

// ─── Default Colors ──────────────────────────────────────────────────────────

const PALETTE = [
  "#6366f1",
  "#22d3ee",
  "#f59e0b",
  "#ef4444",
  "#10b981",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
];

// ─── Demo Data ───────────────────────────────────────────────────────────────

const defaultBarData: DrillDownDataItem[] = [
  {
    name: "Cardiology",
    value: 420,
    children: [
      { name: "Consultations", value: 180 },
      { name: "Procedures", value: 120 },
      { name: "Follow-ups", value: 80 },
      { name: "Emergencies", value: 40 },
    ],
  },
  {
    name: "Neurology",
    value: 310,
    children: [
      { name: "Consultations", value: 140 },
      { name: "Imaging", value: 90 },
      { name: "Therapy", value: 50 },
      { name: "Emergencies", value: 30 },
    ],
  },
  {
    name: "Orthopedics",
    value: 275,
    children: [
      { name: "Surgeries", value: 100 },
      { name: "Rehab", value: 85 },
      { name: "Consultations", value: 60 },
      { name: "Imaging", value: 30 },
    ],
  },
  {
    name: "Pediatrics",
    value: 390,
    children: [
      { name: "Well-child Visits", value: 160 },
      { name: "Sick Visits", value: 120 },
      { name: "Vaccinations", value: 70 },
      { name: "Emergencies", value: 40 },
    ],
  },
  {
    name: "Oncology",
    value: 200,
    children: [
      { name: "Chemotherapy", value: 80 },
      { name: "Consultations", value: 60 },
      { name: "Radiation", value: 40 },
      { name: "Follow-ups", value: 20 },
    ],
  },
];

const defaultLineData = Array.from({ length: 30 }, (_, i) => ({
  date: `Mar ${i + 1}`,
  admissions: Math.floor(40 + Math.random() * 30),
  discharges: Math.floor(35 + Math.random() * 28),
  occupancy: Math.floor(70 + Math.random() * 25),
}));

const defaultLineLines: LineConfig[] = [
  { key: "admissions", color: "#6366f1", label: "Admissions" },
  { key: "discharges", color: "#22d3ee", label: "Discharges" },
  { key: "occupancy", color: "#f59e0b", label: "Occupancy %" },
];

const defaultPieData: PieDataItem[] = [
  {
    name: "Insurance",
    value: 45,
    color: "#6366f1",
    details: [
      { label: "Claims Processed", value: 1240 },
      { label: "Avg. Reimbursement", value: "$3,200" },
      { label: "Denial Rate", value: "4.2%" },
    ],
  },
  {
    name: "Self-Pay",
    value: 20,
    color: "#22d3ee",
    details: [
      { label: "Patients", value: 540 },
      { label: "Avg. Bill", value: "$1,800" },
      { label: "Collection Rate", value: "78%" },
    ],
  },
  {
    name: "Medicare",
    value: 18,
    color: "#10b981",
    details: [
      { label: "Beneficiaries", value: 480 },
      { label: "Avg. Reimbursement", value: "$2,900" },
      { label: "Compliance Score", value: "97%" },
    ],
  },
  {
    name: "Medicaid",
    value: 12,
    color: "#f59e0b",
    details: [
      { label: "Beneficiaries", value: 320 },
      { label: "Avg. Reimbursement", value: "$1,600" },
      { label: "Pending Claims", value: 45 },
    ],
  },
  {
    name: "Other",
    value: 5,
    color: "#ef4444",
    details: [
      { label: "Patients", value: 130 },
      { label: "Revenue", value: "$210K" },
      { label: "Growth", value: "+8%" },
    ],
  },
];

// ─── ChartTooltip ────────────────────────────────────────────────────────────

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

export function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-lg dark:border-gray-700 dark:bg-gray-800">
      {label && (
        <p className="mb-1.5 text-sm font-semibold text-gray-900 dark:text-gray-100">
          {label}
        </p>
      )}
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-500 dark:text-gray-400">
            {entry.name}:
          </span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {entry.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── DrillDownBarChart ───────────────────────────────────────────────────────

interface DrillDownBarChartProps {
  data?: DrillDownDataItem[];
  title?: string;
  color?: string;
}

export function DrillDownBarChart({
  data = defaultBarData,
  title = "Department Volume",
  color = "#6366f1",
}: DrillDownBarChartProps) {
  const [breadcrumbs, setBreadcrumbs] = useState<
    { label: string; data: DrillDownDataItem[] }[]
  >([{ label: "All", data }]);

  const currentLevel = breadcrumbs[breadcrumbs.length - 1];

  const handleBarClick = useCallback(
    (entry: DrillDownDataItem) => {
      if (entry.children && entry.children.length > 0) {
        setBreadcrumbs((prev) => [
          ...prev,
          { label: entry.name, data: entry.children! },
        ]);
      }
    },
    []
  );

  const navigateTo = useCallback((index: number) => {
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
  }, []);

  return (
    <div className="card rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        {breadcrumbs.length > 1 && (
          <button
            onClick={() => navigateTo(0)}
            className="rounded-md bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-600 transition hover:bg-indigo-100 dark:bg-indigo-950 dark:text-indigo-400 dark:hover:bg-indigo-900"
          >
            Reset
          </button>
        )}
      </div>

      {/* Breadcrumbs */}
      <nav className="mb-4 flex items-center gap-1 text-sm">
        {breadcrumbs.map((crumb, i) => (
          <React.Fragment key={i}>
            {i > 0 && (
              <span className="text-gray-400 dark:text-gray-500">/</span>
            )}
            <button
              onClick={() => navigateTo(i)}
              className={`rounded px-1.5 py-0.5 transition ${
                i === breadcrumbs.length - 1
                  ? "font-medium text-gray-900 dark:text-gray-100"
                  : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              {crumb.label}
            </button>
          </React.Fragment>
        ))}
      </nav>

      {/* Chart */}
      <div
        className="transition-opacity duration-300"
        style={{ opacity: 1 }}
      >
        <ResponsiveContainer width="100%" height={320}>
          <BarChart
            data={currentLevel.data}
            margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
          >
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12 }}
              className="text-gray-600 dark:text-gray-400"
            />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(99,102,241,0.08)" }} />
            <Bar
              dataKey="value"
              fill={color}
              radius={[6, 6, 0, 0]}
              cursor="pointer"
              onClick={(_: unknown, index: number) =>
                handleBarClick(currentLevel.data[index])
              }
              animationDuration={400}
              animationEasing="ease-out"
            >
              {currentLevel.data.map((_, i) => (
                <Cell
                  key={i}
                  fill={PALETTE[i % PALETTE.length]}
                  className="transition-opacity hover:opacity-80"
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {breadcrumbs.length === 1 && (
        <p className="mt-2 text-center text-xs text-gray-400 dark:text-gray-500">
          Click a bar to drill down into sub-categories
        </p>
      )}
    </div>
  );
}

// ─── ZoomableLineChart ───────────────────────────────────────────────────────

interface ZoomableLineChartProps {
  data?: Record<string, unknown>[];
  lines?: LineConfig[];
  title?: string;
}

export function ZoomableLineChart({
  data = defaultLineData,
  lines = defaultLineLines,
  title = "Patient Flow Trends",
}: ZoomableLineChartProps) {
  const [zoomRange, setZoomRange] = useState<{
    start: number;
    end: number;
  } | null>(null);
  const [selecting, setSelecting] = useState(false);
  const [selStart, setSelStart] = useState<number | null>(null);
  const [crosshairIndex, setCrosshairIndex] = useState<number | null>(null);

  const displayData = useMemo(() => {
    if (!zoomRange) return data;
    return data.slice(zoomRange.start, zoomRange.end + 1);
  }, [data, zoomRange]);

  const handleMouseDown = useCallback(
    (e: { activeTooltipIndex?: number }) => {
      if (e?.activeTooltipIndex != null) {
        setSelecting(true);
        const idx = zoomRange
          ? zoomRange.start + e.activeTooltipIndex
          : e.activeTooltipIndex;
        setSelStart(idx);
      }
    },
    [zoomRange]
  );

  const handleMouseUp = useCallback(
    (e: { activeTooltipIndex?: number }) => {
      if (selecting && selStart != null && e?.activeTooltipIndex != null) {
        const endIdx = zoomRange
          ? zoomRange.start + e.activeTooltipIndex
          : e.activeTooltipIndex;
        const lo = Math.min(selStart, endIdx);
        const hi = Math.max(selStart, endIdx);
        if (hi - lo >= 2) {
          setZoomRange({ start: lo, end: hi });
        }
      }
      setSelecting(false);
      setSelStart(null);
    },
    [selecting, selStart, zoomRange]
  );

  const handleMouseMove = useCallback(
    (e: { activeTooltipIndex?: number }) => {
      if (e?.activeTooltipIndex != null) {
        setCrosshairIndex(e.activeTooltipIndex);
      }
    },
    []
  );

  const resetZoom = useCallback(() => {
    setZoomRange(null);
  }, []);

  return (
    <div className="card rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        <div className="flex items-center gap-3">
          {zoomRange && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Showing {zoomRange.end - zoomRange.start + 1} of {data.length}{" "}
              points
            </span>
          )}
          {zoomRange && (
            <button
              onClick={resetZoom}
              className="rounded-md bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-600 transition hover:bg-indigo-100 dark:bg-indigo-950 dark:text-indigo-400 dark:hover:bg-indigo-900"
            >
              Reset Zoom
            </button>
          )}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={displayData}
          margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setCrosshairIndex(null)}
        >
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip content={<ChartTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
          />
          {lines.map((line) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              stroke={line.color}
              name={line.label}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2 }}
              animationDuration={400}
            />
          ))}
          {/* Crosshair reference line */}
          {crosshairIndex != null && (
            <Line
              dataKey={() => null}
              stroke="transparent"
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      <p className="mt-2 text-center text-xs text-gray-400 dark:text-gray-500">
        Click and drag on the chart to zoom into a time range
      </p>
    </div>
  );
}

// ─── InteractivePieChart ─────────────────────────────────────────────────────

interface InteractivePieChartProps {
  data?: PieDataItem[];
  title?: string;
}

export function InteractivePieChart({
  data = defaultPieData,
  title = "Revenue by Payer Mix",
}: InteractivePieChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const total = useMemo(
    () => data.reduce((sum, d) => sum + d.value, 0),
    [data]
  );

  const activeItem = activeIndex != null ? data[activeIndex] : null;

  const handleClick = useCallback(
    (_: unknown, index: number) => {
      setActiveIndex((prev) => (prev === index ? null : index));
    },
    []
  );

  return (
    <div className="card rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
        {title}
      </h3>

      <div className="flex flex-col items-start gap-6 md:flex-row">
        {/* Pie Chart */}
        <div className="w-full md:w-1/2">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={110}
                paddingAngle={3}
                dataKey="value"
                onClick={handleClick}
                cursor="pointer"
                animationDuration={400}
                animationEasing="ease-out"
              >
                {data.map((entry, i) => {
                  const isActive = activeIndex === i;
                  return (
                    <Cell
                      key={i}
                      fill={entry.color || PALETTE[i % PALETTE.length]}
                      stroke={isActive ? "#fff" : "transparent"}
                      strokeWidth={isActive ? 3 : 0}
                      style={{
                        transform: isActive ? "scale(1.06)" : "scale(1)",
                        transformOrigin: "center",
                        transition: "transform 0.25s ease, stroke 0.25s ease",
                        filter: isActive
                          ? "drop-shadow(0 4px 12px rgba(0,0,0,0.2))"
                          : "none",
                      }}
                    />
                  );
                })}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Detail Panel */}
        <div className="w-full md:w-1/2">
          {activeItem ? (
            <div
              className="rounded-lg border border-gray-100 bg-gray-50 p-4 transition-all duration-300 dark:border-gray-700 dark:bg-gray-800"
              style={{ opacity: 1 }}
            >
              <div className="mb-3 flex items-center gap-3">
                <span
                  className="inline-block h-4 w-4 rounded-full"
                  style={{
                    backgroundColor:
                      activeItem.color ||
                      PALETTE[activeIndex! % PALETTE.length],
                  }}
                />
                <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                  {activeItem.name}
                </h4>
              </div>

              <div className="mb-4">
                <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                  {activeItem.value}%
                </span>
                <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                  of total ({total}%)
                </span>
              </div>

              {activeItem.details && (
                <div className="space-y-2.5">
                  {activeItem.details.map((detail, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded-md bg-white px-3 py-2 dark:bg-gray-900"
                    >
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {detail.label}
                      </span>
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {typeof detail.value === "number"
                          ? detail.value.toLocaleString()
                          : detail.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full min-h-[200px] items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Click a segment to view details
              </p>
            </div>
          )}

          {/* Legend list */}
          <div className="mt-4 space-y-1.5">
            {data.map((item, i) => (
              <button
                key={i}
                onClick={() =>
                  setActiveIndex((prev) => (prev === i ? null : i))
                }
                className={`flex w-full items-center justify-between rounded-md px-3 py-1.5 text-sm transition ${
                  activeIndex === i
                    ? "bg-indigo-50 dark:bg-indigo-950"
                    : "hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{
                      backgroundColor:
                        item.color || PALETTE[i % PALETTE.length],
                    }}
                  />
                  <span className="text-gray-700 dark:text-gray-300">
                    {item.name}
                  </span>
                </div>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {item.value}%
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Default Export ──────────────────────────────────────────────────────────

export default function ChartDrillDownDemo() {
  return (
    <div className="space-y-8 p-6">
      <DrillDownBarChart />
      <ZoomableLineChart />
      <InteractivePieChart />
    </div>
  );
}
