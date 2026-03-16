import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchOverviewStats,
  fetchVitalsAnalytics,
  fetchAlertAnalytics,
  fetchDeviceAnalytics,
  fetchPatientAnalytics,
  fetchClinicalAnalytics,
  type OverviewStats,
  type VitalsAnalytics,
  type AlertAnalytics,
  type DeviceAnalytics,
  type PatientAnalytics,
  type ClinicalAnalytics,
} from "../lib/analyticsApi";

type Tab = "overview" | "vitals" | "alerts" | "devices" | "patients" | "clinical";

// Simple bar chart component
function BarChart({ data, labelKey, valueKey, color = "#3b82f6", maxBars = 10 }: {
  data: Record<string, unknown>[];
  labelKey: string;
  valueKey: string;
  color?: string;
  maxBars?: number;
}) {
  const items = data.slice(0, maxBars);
  const maxValue = Math.max(...items.map(d => Number(d[valueKey]) || 0), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {items.map((item, idx) => (
        <div key={idx} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 100, fontSize: 12, color: "#666", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
            {String(item[labelKey])}
          </div>
          <div style={{ flex: 1, background: "#f1f5f9", borderRadius: 4, height: 20 }}>
            <div
              style={{
                width: `${(Number(item[valueKey]) / maxValue) * 100}%`,
                background: color,
                height: "100%",
                borderRadius: 4,
                minWidth: Number(item[valueKey]) > 0 ? 2 : 0,
              }}
            />
          </div>
          <div style={{ width: 40, fontSize: 12, textAlign: "right", fontWeight: 500 }}>
            {Number(item[valueKey])}
          </div>
        </div>
      ))}
    </div>
  );
}

// Simple line chart component (using SVG)
function LineChart({ data, xKey, yKeys, colors, height = 200 }: {
  data: Array<Record<string, unknown>>;
  xKey: string;
  yKeys: string[];
  colors: string[];
  height?: number;
}) {
  if (data.length === 0) {
    return <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>No data</div>;
  }

  const padding = { top: 20, right: 20, bottom: 30, left: 50 };
  const width = 600;
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Calculate scales
  const allValues = data.flatMap(d => yKeys.map(k => Number(d[k]) || 0));
  const maxY = Math.max(...allValues, 1);
  const minY = Math.min(...allValues, 0);
  const yRange = maxY - minY || 1;

  const xScale = (i: number) => padding.left + (i / Math.max(data.length - 1, 1)) * chartWidth;
  const yScale = (v: number) => padding.top + chartHeight - ((v - minY) / yRange) * chartHeight;

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: width }}>
      {/* Y axis grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
        const y = padding.top + chartHeight * (1 - pct);
        const value = minY + yRange * pct;
        return (
          <g key={i}>
            <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#e5e7eb" strokeWidth={1} />
            <text x={padding.left - 8} y={y + 4} textAnchor="end" fontSize={10} fill="#666">
              {value.toFixed(0)}
            </text>
          </g>
        );
      })}

      {/* Lines */}
      {yKeys.map((yKey, keyIdx) => {
        const points = data.map((d, i) => `${xScale(i)},${yScale(Number(d[yKey]) || 0)}`).join(" ");
        return (
          <polyline
            key={yKey}
            points={points}
            fill="none"
            stroke={colors[keyIdx]}
            strokeWidth={2}
          />
        );
      })}

      {/* X axis labels (show some) */}
      {data.filter((_, i) => i % Math.ceil(data.length / 6) === 0 || i === data.length - 1).map((d) => {
        const origIdx = data.indexOf(d);
        const label = String(d[xKey]).slice(5, 10); // MM-DD format
        return (
          <text
            key={origIdx}
            x={xScale(origIdx)}
            y={height - 8}
            textAnchor="middle"
            fontSize={10}
            fill="#666"
          >
            {label}
          </text>
        );
      })}

      {/* Legend */}
      <g transform={`translate(${padding.left}, ${padding.top - 10})`}>
        {yKeys.map((key, i) => (
          <g key={key} transform={`translate(${i * 100}, 0)`}>
            <rect width={12} height={12} fill={colors[i]} rx={2} />
            <text x={16} y={10} fontSize={10} fill="#666">{key}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}

// Distribution chart (horizontal stacked)
function DistributionChart({ data, colors }: { data: Record<string, number>; colors: Record<string, string> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return <div style={{ color: "#999", fontSize: 12 }}>No data</div>;

  return (
    <div>
      <div style={{ display: "flex", height: 24, borderRadius: 6, overflow: "hidden" }}>
        {Object.entries(data).map(([key, value]) => (
          <div
            key={key}
            style={{
              width: `${(value / total) * 100}%`,
              background: colors[key] || "#94a3b8",
              minWidth: value > 0 ? 2 : 0,
            }}
            title={`${key}: ${value} (${((value / total) * 100).toFixed(1)}%)`}
          />
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 8 }}>
        {Object.entries(data).map(([key, value]) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: colors[key] || "#94a3b8" }} />
            <span style={{ color: "#666" }}>{key}:</span>
            <span style={{ fontWeight: 500 }}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Stat card component
function StatCard({ title, value, subtitle, color = "#3b82f6" }: {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}) {
  return (
    <div style={{
      background: "white",
      border: "1px solid #e5e7eb",
      borderRadius: 12,
      padding: 16,
      display: "flex",
      flexDirection: "column",
      gap: 4,
    }}>
      <div style={{ fontSize: 12, color: "#666", fontWeight: 500 }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
      {subtitle && <div style={{ fontSize: 11, color: "#999" }}>{subtitle}</div>}
    </div>
  );
}

// Section card component
function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: "white",
      border: "1px solid #e5e7eb",
      borderRadius: 12,
      padding: 16,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 12, color: "#1f2937" }}>{title}</div>
      {children}
    </div>
  );
}

// Overview Tab
function OverviewTab({ data }: { data: OverviewStats }) {
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <StatCard title="Total Patients" value={data.patients.total} subtitle={`${data.patients.active} active`} color="#8b5cf6" />
        <StatCard title="Active Devices" value={data.devices.active} subtitle={`${data.devices.assigned} assigned`} color="#10b981" />
        <StatCard title="Active Alerts" value={data.alerts.active} subtitle={`${data.alerts.critical} critical`} color={data.alerts.critical > 0 ? "#ef4444" : "#f59e0b"} />
        <StatCard title="Active Encounters" value={data.encounters.active} subtitle={`${data.encounters.today} today`} color="#3b82f6" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        <StatCard title="New Patients This Week" value={data.patients.new_this_week} color="#8b5cf6" />
        <StatCard title="Alerts Today" value={data.alerts.today} subtitle={`${data.alerts.this_week} this week`} color="#f59e0b" />
        <StatCard title="Device Utilization" value={`${data.devices.total > 0 ? Math.round((data.devices.assigned / data.devices.total) * 100) : 0}%`} subtitle={`${data.devices.unassigned} unassigned`} color="#10b981" />
      </div>
    </div>
  );
}

// Vitals Analytics Tab
function VitalsTab({ data }: { data: VitalsAnalytics }) {
  const stats = data.statistics;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        <StatCard title="Total Readings" value={stats.total_readings} color="#3b82f6" />
        <StatCard title="Avg Heart Rate" value={stats.avg_heart_rate?.toFixed(0) ?? "-"} subtitle="bpm" color="#ef4444" />
        <StatCard title="Avg Blood Pressure" value={stats.avg_systolic && stats.avg_diastolic ? `${stats.avg_systolic.toFixed(0)}/${stats.avg_diastolic.toFixed(0)}` : "-"} subtitle="mmHg" color="#8b5cf6" />
        <StatCard title="Avg SpO2" value={stats.avg_spo2?.toFixed(1) ?? "-"} subtitle="%" color="#10b981" />
        <StatCard title="Avg Temperature" value={stats.avg_temp?.toFixed(1) ?? "-"} subtitle="C" color="#f59e0b" />
      </div>

      <SectionCard title="Abnormal Readings">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
          <div style={{ textAlign: "center", padding: 12, background: "#fef2f2", borderRadius: 8 }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#ef4444" }}>{data.abnormal_counts.high_heart_rate}</div>
            <div style={{ fontSize: 11, color: "#666" }}>High HR (&gt;100)</div>
          </div>
          <div style={{ textAlign: "center", padding: 12, background: "#fef2f2", borderRadius: 8 }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#ef4444" }}>{data.abnormal_counts.low_heart_rate}</div>
            <div style={{ fontSize: 11, color: "#666" }}>Low HR (&lt;60)</div>
          </div>
          <div style={{ textAlign: "center", padding: 12, background: "#fef2f2", borderRadius: 8 }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#ef4444" }}>{data.abnormal_counts.high_bp}</div>
            <div style={{ fontSize: 11, color: "#666" }}>High BP (&gt;140)</div>
          </div>
          <div style={{ textAlign: "center", padding: 12, background: "#fef2f2", borderRadius: 8 }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#ef4444" }}>{data.abnormal_counts.low_spo2}</div>
            <div style={{ fontSize: 11, color: "#666" }}>Low SpO2 (&lt;95%)</div>
          </div>
          <div style={{ textAlign: "center", padding: 12, background: "#fef2f2", borderRadius: 8 }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#ef4444" }}>{data.abnormal_counts.fever}</div>
            <div style={{ fontSize: 11, color: "#666" }}>Fever (&gt;38C)</div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title={`Daily Vitals Trends (${data.period_days} days)`}>
        <LineChart
          data={data.daily_trends}
          xKey="date"
          yKeys={["avg_heart_rate", "avg_spo2"]}
          colors={["#ef4444", "#10b981"]}
          height={220}
        />
      </SectionCard>
    </div>
  );
}

// Alert Analytics Tab
function AlertsTab({ data }: { data: AlertAnalytics }) {
  const severityColors: Record<string, string> = {
    critical: "#ef4444",
    warning: "#f59e0b",
    info: "#3b82f6",
  };

  const statusColors: Record<string, string> = {
    active: "#ef4444",
    acknowledged: "#f59e0b",
    resolved: "#10b981",
    escalated: "#8b5cf6",
    auto_resolved: "#6b7280",
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <StatCard title="Total Alerts" value={data.total_alerts} subtitle={`Last ${data.period_days} days`} color="#3b82f6" />
        <StatCard title="Critical" value={data.by_severity.critical || 0} color="#ef4444" />
        <StatCard title="Warning" value={data.by_severity.warning || 0} color="#f59e0b" />
        <StatCard title="Avg Response Time" value={data.response_metrics.avg_response_time_seconds ? `${Math.round(data.response_metrics.avg_response_time_seconds / 60)}m` : "-"} subtitle={`${data.response_metrics.total_acknowledged} acknowledged`} color="#10b981" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="By Severity">
          <DistributionChart data={data.by_severity} colors={severityColors} />
        </SectionCard>
        <SectionCard title="By Status">
          <DistributionChart data={data.by_status} colors={statusColors} />
        </SectionCard>
      </div>

      <SectionCard title="Alert Trends">
        <LineChart
          data={data.daily_trends}
          xKey="date"
          yKeys={["critical", "warning", "info"]}
          colors={["#ef4444", "#f59e0b", "#3b82f6"]}
          height={200}
        />
      </SectionCard>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="Top Alert Rules">
          {data.top_rules.length > 0 ? (
            <BarChart
              data={data.top_rules.map(r => ({ name: r.rule__name, count: r.count }))}
              labelKey="name"
              valueKey="count"
              color="#8b5cf6"
            />
          ) : (
            <div style={{ color: "#999", fontSize: 12 }}>No data</div>
          )}
        </SectionCard>
        <SectionCard title="Top Patients by Alerts">
          {data.top_patients.length > 0 ? (
            <BarChart
              data={data.top_patients.map(p => ({
                name: `${p.patient__first_name} ${p.patient__last_name}`,
                count: p.alert_count,
              }))}
              labelKey="name"
              valueKey="count"
              color="#ef4444"
            />
          ) : (
            <div style={{ color: "#999", fontSize: 12 }}>No data</div>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Hourly Distribution">
        <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 100 }}>
          {Array.from({ length: 24 }, (_, h) => {
            const hourData = data.hourly_distribution.find(d => d.hour === h);
            const count = hourData?.count || 0;
            const maxCount = Math.max(...data.hourly_distribution.map(d => d.count), 1);
            return (
              <div key={h} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div
                  style={{
                    width: "100%",
                    height: `${(count / maxCount) * 80}px`,
                    background: "#3b82f6",
                    borderRadius: 2,
                    minHeight: count > 0 ? 2 : 0,
                  }}
                  title={`${h}:00 - ${count} alerts`}
                />
                {h % 4 === 0 && <div style={{ fontSize: 9, color: "#999", marginTop: 4 }}>{h}</div>}
              </div>
            );
          })}
        </div>
      </SectionCard>
    </div>
  );
}

// Device Analytics Tab
function DevicesTab({ data }: { data: DeviceAnalytics }) {
  const statusColors: Record<string, string> = {
    active: "#10b981",
    inactive: "#6b7280",
    maintenance: "#f59e0b",
    retired: "#ef4444",
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <StatCard title="Total Devices" value={data.total_devices} color="#3b82f6" />
        <StatCard title="Assigned" value={data.assignment_stats.assigned} color="#10b981" />
        <StatCard title="Unassigned" value={data.assignment_stats.unassigned} color="#6b7280" />
        <StatCard title="Utilization Rate" value={`${data.assignment_stats.utilization_rate}%`} color="#8b5cf6" />
      </div>

      {data.needs_attention > 0 && (
        <div style={{ background: "#fef3c7", border: "1px solid #f59e0b", borderRadius: 8, padding: 12 }}>
          <span style={{ fontWeight: 600, color: "#92400e" }}>{data.needs_attention} device(s) need attention</span>
          <span style={{ color: "#92400e", marginLeft: 8 }}>- Inactive but still assigned to patients</span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="Status Distribution">
          <DistributionChart data={data.status_distribution} colors={statusColors} />
        </SectionCard>
        <SectionCard title="Device Types">
          <BarChart
            data={Object.entries(data.type_distribution).map(([type, count]) => ({ type, count }))}
            labelKey="type"
            valueKey="count"
            color="#3b82f6"
          />
        </SectionCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="Capabilities">
          <BarChart
            data={Object.entries(data.capability_distribution).map(([cap, count]) => ({ capability: cap, count }))}
            labelKey="capability"
            valueKey="count"
            color="#10b981"
          />
        </SectionCard>
        <SectionCard title="Most Used Devices">
          {data.most_used_devices.length > 0 ? (
            <BarChart
              data={data.most_used_devices.map(d => ({ name: d.name || d.device_id, assignments: d.assignment_count }))}
              labelKey="name"
              valueKey="assignments"
              color="#8b5cf6"
            />
          ) : (
            <div style={{ color: "#999", fontSize: 12 }}>No assignments yet</div>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Assignment Trends (30 days)">
        <LineChart
          data={data.assignment_trends}
          xKey="date"
          yKeys={["new_assignments"]}
          colors={["#3b82f6"]}
          height={180}
        />
      </SectionCard>
    </div>
  );
}

// Patient Analytics Tab
function PatientsTab({ data }: { data: PatientAnalytics }) {
  const genderColors: Record<string, string> = {
    male: "#3b82f6",
    female: "#ec4899",
    other: "#8b5cf6",
    unknown: "#6b7280",
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <StatCard title="Total Patients" value={data.total_patients} color="#8b5cf6" />
        <StatCard title="Active Patients" value={data.active_patients} color="#10b981" />
        <StatCard title="With Devices" value={data.engagement.with_devices} color="#3b82f6" />
        <StatCard title="With Active Alerts" value={data.engagement.with_active_alerts} color={data.engagement.with_active_alerts > 0 ? "#ef4444" : "#10b981"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="Gender Distribution">
          <DistributionChart data={data.gender_distribution} colors={genderColors} />
        </SectionCard>
        <SectionCard title="Age Distribution">
          <BarChart
            data={Object.entries(data.age_distribution).map(([age, count]) => ({ age, count }))}
            labelKey="age"
            valueKey="count"
            color="#8b5cf6"
          />
        </SectionCard>
      </div>

      <SectionCard title="New Patients Trend (30 days)">
        <LineChart
          data={data.new_patient_trends}
          xKey="date"
          yKeys={["count"]}
          colors={["#8b5cf6"]}
          height={180}
        />
      </SectionCard>

      <SectionCard title="Top Diagnoses">
        {data.top_diagnoses.length > 0 ? (
          <BarChart
            data={data.top_diagnoses.map(d => ({
              diagnosis: `${d.icd10_code}: ${d.description.slice(0, 30)}`,
              patients: d.patient_count,
            }))}
            labelKey="diagnosis"
            valueKey="patients"
            color="#ef4444"
          />
        ) : (
          <div style={{ color: "#999", fontSize: 12 }}>No diagnoses recorded</div>
        )}
      </SectionCard>
    </div>
  );
}

// Clinical Analytics Tab
function ClinicalTab({ data }: { data: ClinicalAnalytics }) {
  const statusColors: Record<string, string> = {
    planned: "#6b7280",
    in_progress: "#3b82f6",
    on_hold: "#f59e0b",
    completed: "#10b981",
    cancelled: "#ef4444",
    active: "#10b981",
    draft: "#6b7280",
    final: "#3b82f6",
    amended: "#f59e0b",
    resolved: "#10b981",
    inactive: "#6b7280",
    ruled_out: "#ef4444",
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <StatCard title="Total Encounters" value={data.encounters.total} subtitle={`${data.encounters.active} active`} color="#3b82f6" />
        <StatCard title="Clinical Notes" value={data.notes.total} subtitle={`${data.notes.this_week} this week`} color="#8b5cf6" />
        <StatCard title="Care Plans" value={data.care_plans.total} subtitle={`${data.care_plans.active} active`} color="#10b981" />
        <StatCard title="Diagnoses" value={data.diagnoses.total} subtitle={`${data.diagnoses.active} active`} color="#ef4444" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="Encounters by Type">
          <BarChart
            data={Object.entries(data.encounters.by_type).map(([type, count]) => ({ type, count }))}
            labelKey="type"
            valueKey="count"
            color="#3b82f6"
          />
        </SectionCard>
        <SectionCard title="Encounters by Status">
          <DistributionChart data={data.encounters.by_status} colors={statusColors} />
        </SectionCard>
      </div>

      <SectionCard title="Encounter Trends (30 days)">
        <LineChart
          data={data.encounters.trends}
          xKey="date"
          yKeys={["count"]}
          colors={["#3b82f6"]}
          height={180}
        />
      </SectionCard>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="Notes by Type">
          <BarChart
            data={Object.entries(data.notes.by_type).map(([type, count]) => ({ type, count }))}
            labelKey="type"
            valueKey="count"
            color="#8b5cf6"
          />
        </SectionCard>
        <SectionCard title="Top Note Authors">
          {data.notes.top_authors.length > 0 ? (
            <BarChart
              data={data.notes.top_authors.map(a => ({ author: a.author, notes: a.note_count }))}
              labelKey="author"
              valueKey="notes"
              color="#10b981"
            />
          ) : (
            <div style={{ color: "#999", fontSize: 12 }}>No notes recorded</div>
          )}
        </SectionCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <SectionCard title="Care Plans by Status">
          <DistributionChart data={data.care_plans.by_status} colors={statusColors} />
        </SectionCard>
        <SectionCard title="Diagnoses by Status">
          <DistributionChart data={data.diagnoses.by_status} colors={statusColors} />
        </SectionCard>
      </div>
    </div>
  );
}

export function AnalyticsDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [alertDays, setAlertDays] = useState(30);
  const [vitalsDays, setVitalsDays] = useState(7);

  const overviewQ = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: fetchOverviewStats,
    refetchInterval: 60000, // 1 minute
  });

  const vitalsQ = useQuery({
    queryKey: ["analytics", "vitals", vitalsDays],
    queryFn: () => fetchVitalsAnalytics({ days: vitalsDays }),
    enabled: activeTab === "vitals",
  });

  const alertsQ = useQuery({
    queryKey: ["analytics", "alerts", alertDays],
    queryFn: () => fetchAlertAnalytics({ days: alertDays }),
    enabled: activeTab === "alerts",
  });

  const devicesQ = useQuery({
    queryKey: ["analytics", "devices"],
    queryFn: fetchDeviceAnalytics,
    enabled: activeTab === "devices",
  });

  const patientsQ = useQuery({
    queryKey: ["analytics", "patients"],
    queryFn: fetchPatientAnalytics,
    enabled: activeTab === "patients",
  });

  const clinicalQ = useQuery({
    queryKey: ["analytics", "clinical"],
    queryFn: fetchClinicalAnalytics,
    enabled: activeTab === "clinical",
  });

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "vitals", label: "Vitals" },
    { key: "alerts", label: "Alerts" },
    { key: "devices", label: "Devices" },
    { key: "patients", label: "Patients" },
    { key: "clinical", label: "Clinical" },
  ];

  const tabButtonStyle = (active: boolean) => ({
    padding: "8px 16px",
    borderRadius: 8,
    border: "none",
    background: active ? "#3b82f6" : "transparent",
    color: active ? "white" : "#666",
    cursor: "pointer",
    fontWeight: active ? 600 : 400,
    fontSize: 14,
  });

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Analytics Dashboard</h2>
        <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "#666" }}>
          Platform-wide metrics and insights
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            style={tabButtonStyle(activeTab === tab.key)}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Period selectors for specific tabs */}
      {activeTab === "vitals" && (
        <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "#666" }}>Period:</span>
          {[7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setVitalsDays(d)}
              style={{
                padding: "4px 12px",
                borderRadius: 6,
                border: "1px solid #e5e7eb",
                background: vitalsDays === d ? "#3b82f6" : "white",
                color: vitalsDays === d ? "white" : "#666",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              {d} days
            </button>
          ))}
        </div>
      )}

      {activeTab === "alerts" && (
        <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "#666" }}>Period:</span>
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setAlertDays(d)}
              style={{
                padding: "4px 12px",
                borderRadius: 6,
                border: "1px solid #e5e7eb",
                background: alertDays === d ? "#3b82f6" : "white",
                color: alertDays === d ? "white" : "#666",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              {d} days
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div>
        {activeTab === "overview" && (
          overviewQ.isLoading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading overview...</div>
          ) : overviewQ.error ? (
            <div style={{ padding: 20, background: "#fef2f2", borderRadius: 8, color: "#ef4444" }}>
              Error loading overview: {String(overviewQ.error)}
            </div>
          ) : overviewQ.data ? (
            <OverviewTab data={overviewQ.data} />
          ) : null
        )}

        {activeTab === "vitals" && (
          vitalsQ.isLoading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading vitals analytics...</div>
          ) : vitalsQ.error ? (
            <div style={{ padding: 20, background: "#fef2f2", borderRadius: 8, color: "#ef4444" }}>
              Error loading vitals: {String(vitalsQ.error)}
            </div>
          ) : vitalsQ.data ? (
            <VitalsTab data={vitalsQ.data} />
          ) : null
        )}

        {activeTab === "alerts" && (
          alertsQ.isLoading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading alert analytics...</div>
          ) : alertsQ.error ? (
            <div style={{ padding: 20, background: "#fef2f2", borderRadius: 8, color: "#ef4444" }}>
              Error loading alerts: {String(alertsQ.error)}
            </div>
          ) : alertsQ.data ? (
            <AlertsTab data={alertsQ.data} />
          ) : null
        )}

        {activeTab === "devices" && (
          devicesQ.isLoading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading device analytics...</div>
          ) : devicesQ.error ? (
            <div style={{ padding: 20, background: "#fef2f2", borderRadius: 8, color: "#ef4444" }}>
              Error loading devices: {String(devicesQ.error)}
            </div>
          ) : devicesQ.data ? (
            <DevicesTab data={devicesQ.data} />
          ) : null
        )}

        {activeTab === "patients" && (
          patientsQ.isLoading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading patient analytics...</div>
          ) : patientsQ.error ? (
            <div style={{ padding: 20, background: "#fef2f2", borderRadius: 8, color: "#ef4444" }}>
              Error loading patients: {String(patientsQ.error)}
            </div>
          ) : patientsQ.data ? (
            <PatientsTab data={patientsQ.data} />
          ) : null
        )}

        {activeTab === "clinical" && (
          clinicalQ.isLoading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading clinical analytics...</div>
          ) : clinicalQ.error ? (
            <div style={{ padding: 20, background: "#fef2f2", borderRadius: 8, color: "#ef4444" }}>
              Error loading clinical data: {String(clinicalQ.error)}
            </div>
          ) : clinicalQ.data ? (
            <ClinicalTab data={clinicalQ.data} />
          ) : null
        )}
      </div>

      {/* Footer with last update time */}
      <div style={{ marginTop: 16, fontSize: 11, color: "#999", textAlign: "right" }}>
        {overviewQ.data && `Last updated: ${new Date(overviewQ.data.generated_at).toLocaleTimeString()}`}
      </div>
    </div>
  );
}
