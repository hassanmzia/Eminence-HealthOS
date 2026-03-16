import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchAlerts,
  fetchAlertSummary,
  fetchAlertRules,
  acknowledgeAlert,
  resolveAlert,
  bulkAcknowledgeAlerts,
  initializeDefaultRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  type Alert,
  type AlertRule,
  VITAL_TYPES,
  CONDITIONS,
  SEVERITIES,
  getVitalTypeLabel,
  getVitalTypeUnit,
  getSeverityColor,
  formatDuration,
} from "../lib/alertsApi";

type TabView = "active" | "history" | "rules";

export function AlertsDashboard() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabView>("active");
  const [selectedAlerts, setSelectedAlerts] = useState<number[]>([]);
  const [acknowledgeUser, setAcknowledgeUser] = useState("");
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);

  // Queries
  const summaryQuery = useQuery({
    queryKey: ["alert-summary"],
    queryFn: fetchAlertSummary,
    refetchInterval: 10000,
  });

  const activeAlertsQuery = useQuery({
    queryKey: ["alerts", "active"],
    queryFn: () => fetchAlerts({ active_only: true, limit: 100 }),
    refetchInterval: 5000,
  });

  const historyQuery = useQuery({
    queryKey: ["alerts", "history"],
    queryFn: () => fetchAlerts({ limit: 100 }),
    enabled: activeTab === "history",
  });

  const rulesQuery = useQuery({
    queryKey: ["alert-rules"],
    queryFn: () => fetchAlertRules(),
    enabled: activeTab === "rules",
  });

  // Mutations
  const acknowledgeMutation = useMutation({
    mutationFn: ({ alertId, data }: { alertId: number; data: { acknowledged_by: string } }) =>
      acknowledgeAlert(alertId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alert-summary"] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: ({ alertId, data }: { alertId: number; data: { resolved_by: string; resolution_notes?: string } }) =>
      resolveAlert(alertId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alert-summary"] });
    },
  });

  const bulkAckMutation = useMutation({
    mutationFn: ({ alertIds, acknowledgedBy }: { alertIds: number[]; acknowledgedBy: string }) =>
      bulkAcknowledgeAlerts(alertIds, acknowledgedBy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alert-summary"] });
      setSelectedAlerts([]);
    },
  });

  const initRulesMutation = useMutation({
    mutationFn: initializeDefaultRules,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
  });

  const summary = summaryQuery.data;
  const activeAlerts = activeAlertsQuery.data?.results || [];

  const tabStyle = (active: boolean) => ({
    padding: "10px 20px",
    border: "none",
    borderBottom: active ? "3px solid #2563eb" : "3px solid transparent",
    background: "transparent",
    color: active ? "#2563eb" : "#666",
    cursor: "pointer",
    fontWeight: active ? 600 : 400,
    fontSize: 15,
  });

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Alerts & Notifications</h2>
        <div style={{ fontSize: 12, color: "#666" }}>
          Auto-refresh: {activeAlertsQuery.isFetching ? "updating..." : "ready"}
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16, marginBottom: 24 }}>
          <SummaryCard
            label="Active Alerts"
            value={summary.total_active}
            color={summary.total_active > 0 ? "#ef4444" : "#059669"}
            highlight={summary.total_active > 0}
          />
          <SummaryCard label="Critical" value={summary.critical_count} color="#ef4444" />
          <SummaryCard label="Warning" value={summary.warning_count} color="#f59e0b" />
          <SummaryCard label="Info" value={summary.info_count} color="#3b82f6" />
          <SummaryCard
            label="Avg Response"
            value={summary.average_response_time_seconds ? formatDuration(summary.average_response_time_seconds) : "—"}
            color="#7c3aed"
            isText
          />
        </div>
      )}

      {/* Tabs */}
      <div style={{ borderBottom: "1px solid #eee", marginBottom: 16 }}>
        <button style={tabStyle(activeTab === "active")} onClick={() => setActiveTab("active")}>
          Active Alerts ({activeAlerts.length})
        </button>
        <button style={tabStyle(activeTab === "history")} onClick={() => setActiveTab("history")}>
          Alert History
        </button>
        <button style={tabStyle(activeTab === "rules")} onClick={() => setActiveTab("rules")}>
          Alert Rules
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "active" && (
        <ActiveAlertsTab
          alerts={activeAlerts}
          selectedAlerts={selectedAlerts}
          setSelectedAlerts={setSelectedAlerts}
          acknowledgeUser={acknowledgeUser}
          setAcknowledgeUser={setAcknowledgeUser}
          onAcknowledge={(alertId) => {
            if (!acknowledgeUser) return;
            acknowledgeMutation.mutate({ alertId, data: { acknowledged_by: acknowledgeUser } });
          }}
          onResolve={(alertId) => {
            if (!acknowledgeUser) return;
            resolveMutation.mutate({ alertId, data: { resolved_by: acknowledgeUser } });
          }}
          onBulkAcknowledge={() => {
            if (!acknowledgeUser || selectedAlerts.length === 0) return;
            bulkAckMutation.mutate({ alertIds: selectedAlerts, acknowledgedBy: acknowledgeUser });
          }}
          isLoading={acknowledgeMutation.isPending || resolveMutation.isPending || bulkAckMutation.isPending}
        />
      )}

      {activeTab === "history" && (
        <AlertHistoryTab alerts={historyQuery.data?.results || []} isLoading={historyQuery.isLoading} />
      )}

      {activeTab === "rules" && (
        <AlertRulesTab
          rules={rulesQuery.data?.results || []}
          isLoading={rulesQuery.isLoading}
          onInitDefaults={() => initRulesMutation.mutate()}
          onCreateRule={() => {
            setEditingRule(null);
            setShowRuleForm(true);
          }}
          onEditRule={(rule) => {
            setEditingRule(rule);
            setShowRuleForm(true);
          }}
          onDeleteRule={(ruleId) => {
            if (confirm("Are you sure you want to delete this rule?")) {
              deleteAlertRule(ruleId).then(() => {
                queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
              });
            }
          }}
          onToggleRule={(rule) => {
            updateAlertRule(rule.id, { is_active: !rule.is_active }).then(() => {
              queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
            });
          }}
        />
      )}

      {/* Rule Form Modal */}
      {showRuleForm && (
        <AlertRuleForm
          rule={editingRule}
          onClose={() => {
            setShowRuleForm(false);
            setEditingRule(null);
          }}
          onSuccess={() => {
            setShowRuleForm(false);
            setEditingRule(null);
            queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
          }}
        />
      )}
    </div>
  );
}

function SummaryCard({ label, value, color, highlight, isText }: { label: string; value: number | string; color: string; highlight?: boolean; isText?: boolean }) {
  return (
    <div style={{
      padding: 16,
      borderRadius: 12,
      background: highlight ? color : "#f9fafb",
      border: `1px solid ${highlight ? color : "#eee"}`,
      textAlign: "center",
    }}>
      <div style={{
        fontSize: isText ? 20 : 28,
        fontWeight: 700,
        color: highlight ? "white" : color,
      }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: highlight ? "rgba(255,255,255,0.8)" : "#666", marginTop: 4 }}>{label}</div>
    </div>
  );
}

function ActiveAlertsTab({
  alerts,
  selectedAlerts,
  setSelectedAlerts,
  acknowledgeUser,
  setAcknowledgeUser,
  onAcknowledge,
  onResolve,
  onBulkAcknowledge,
  isLoading,
}: {
  alerts: Alert[];
  selectedAlerts: number[];
  setSelectedAlerts: (ids: number[]) => void;
  acknowledgeUser: string;
  setAcknowledgeUser: (user: string) => void;
  onAcknowledge: (id: number) => void;
  onResolve: (id: number) => void;
  onBulkAcknowledge: () => void;
  isLoading: boolean;
}) {
  const toggleSelect = (id: number) => {
    setSelectedAlerts(
      selectedAlerts.includes(id)
        ? selectedAlerts.filter(a => a !== id)
        : [...selectedAlerts, id]
    );
  };

  const selectAll = () => {
    if (selectedAlerts.length === alerts.length) {
      setSelectedAlerts([]);
    } else {
      setSelectedAlerts(alerts.map(a => a.id));
    }
  };

  if (alerts.length === 0) {
    return (
      <div style={{ padding: 60, textAlign: "center", color: "#059669" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
        <h3 style={{ margin: 0 }}>No Active Alerts</h3>
        <p style={{ color: "#666", marginTop: 8 }}>All systems are operating normally</p>
      </div>
    );
  }

  return (
    <div>
      {/* Bulk Actions */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, padding: 12, background: "#f9fafb", borderRadius: 8 }}>
        <input
          type="text"
          placeholder="Your name (required)"
          value={acknowledgeUser}
          onChange={(e) => setAcknowledgeUser(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", width: 200 }}
        />
        <button
          onClick={selectAll}
          style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", background: "white", cursor: "pointer" }}
        >
          {selectedAlerts.length === alerts.length ? "Deselect All" : "Select All"}
        </button>
        <button
          onClick={onBulkAcknowledge}
          disabled={isLoading || !acknowledgeUser || selectedAlerts.length === 0}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "none",
            background: selectedAlerts.length > 0 && acknowledgeUser ? "#2563eb" : "#ccc",
            color: "white",
            cursor: selectedAlerts.length > 0 && acknowledgeUser ? "pointer" : "not-allowed",
          }}
        >
          Acknowledge Selected ({selectedAlerts.length})
        </button>
      </div>

      {/* Alert List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {alerts.map((alert) => (
          <AlertCard
            key={alert.id}
            alert={alert}
            selected={selectedAlerts.includes(alert.id)}
            onToggleSelect={() => toggleSelect(alert.id)}
            onAcknowledge={() => onAcknowledge(alert.id)}
            onResolve={() => onResolve(alert.id)}
            canAcknowledge={!!acknowledgeUser}
            isLoading={isLoading}
          />
        ))}
      </div>
    </div>
  );
}

function AlertCard({
  alert,
  selected,
  onToggleSelect,
  onAcknowledge,
  onResolve,
  canAcknowledge,
  isLoading,
}: {
  alert: Alert;
  selected: boolean;
  onToggleSelect: () => void;
  onAcknowledge: () => void;
  onResolve: () => void;
  canAcknowledge: boolean;
  isLoading: boolean;
}) {
  const severityStyle = getSeverityColor(alert.severity);

  return (
    <div style={{
      border: `2px solid ${selected ? "#2563eb" : severityStyle.color}`,
      borderRadius: 12,
      overflow: "hidden",
      background: "white",
    }}>
      <div style={{
        padding: 16,
        background: severityStyle.bg,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
      }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggleSelect}
            style={{ marginTop: 4, cursor: "pointer", width: 18, height: 18 }}
          />
          <div>
            <div style={{ fontWeight: 600, fontSize: 15, color: severityStyle.color }}>{alert.title}</div>
            <div style={{ fontSize: 13, color: "#333", marginTop: 4 }}>
              Patient: <strong>{alert.patient_name}</strong> (MRN: {alert.patient_mrn})
            </div>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{
            padding: "4px 12px",
            borderRadius: 999,
            background: severityStyle.color,
            color: "white",
            fontSize: 12,
            fontWeight: 600,
            display: "inline-block",
          }}>
            {alert.severity.toUpperCase()}
          </div>
          <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
            {formatDuration(alert.duration_seconds || 0)} ago
          </div>
        </div>
      </div>

      <div style={{ padding: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: "#666" }}>Vital Sign</div>
            <div style={{ fontSize: 15, fontWeight: 500 }}>
              {getVitalTypeLabel(alert.vital_type)}: {alert.vital_value} {getVitalTypeUnit(alert.vital_type)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#666" }}>Threshold</div>
            <div style={{ fontSize: 15, fontWeight: 500 }}>
              {alert.threshold_value} {getVitalTypeUnit(alert.vital_type)}
            </div>
          </div>
        </div>

        {alert.message && (
          <div style={{ marginTop: 12, padding: 12, background: "#f9fafb", borderRadius: 6, fontSize: 13 }}>
            {alert.message}
          </div>
        )}

        <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
          {alert.status === "active" && (
            <>
              <button
                onClick={onAcknowledge}
                disabled={!canAcknowledge || isLoading}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "none",
                  background: canAcknowledge ? "#2563eb" : "#ccc",
                  color: "white",
                  cursor: canAcknowledge ? "pointer" : "not-allowed",
                }}
              >
                Acknowledge
              </button>
              <button
                onClick={onResolve}
                disabled={!canAcknowledge || isLoading}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid #059669",
                  background: "white",
                  color: "#059669",
                  cursor: canAcknowledge ? "pointer" : "not-allowed",
                }}
              >
                Resolve
              </button>
            </>
          )}
          {alert.status === "acknowledged" && (
            <button
              onClick={onResolve}
              disabled={!canAcknowledge || isLoading}
              style={{
                padding: "8px 16px",
                borderRadius: 6,
                border: "none",
                background: "#059669",
                color: "white",
                cursor: canAcknowledge ? "pointer" : "not-allowed",
              }}
            >
              Resolve
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function AlertHistoryTab({ alerts, isLoading }: { alerts: Alert[]; isLoading: boolean }) {
  if (isLoading) return <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading...</div>;

  return (
    <div className="table-responsive" style={{ border: "1px solid #eee", borderRadius: 12, overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#f9fafb" }}>
            <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Time</th>
            <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Patient</th>
            <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Alert</th>
            <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Value</th>
            <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Severity</th>
            <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Status</th>
            <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Acknowledged By</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => {
            const severityStyle = getSeverityColor(alert.severity);
            return (
              <tr key={alert.id}>
                <td style={{ padding: 12, borderBottom: "1px solid #eee", fontSize: 13 }}>
                  {new Date(alert.triggered_at).toLocaleString()}
                </td>
                <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                  <div style={{ fontWeight: 500 }}>{alert.patient_name}</div>
                  <div style={{ fontSize: 12, color: "#666" }}>{alert.patient_mrn}</div>
                </td>
                <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>{alert.title}</td>
                <td style={{ padding: 12, borderBottom: "1px solid #eee", fontFamily: "monospace" }}>
                  {alert.vital_value} {getVitalTypeUnit(alert.vital_type)}
                </td>
                <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 999,
                    background: severityStyle.bg,
                    color: severityStyle.color,
                    fontSize: 11,
                    fontWeight: 600,
                  }}>
                    {alert.severity.toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 999,
                    background: alert.status === "resolved" ? "#dcfce7" : alert.status === "acknowledged" ? "#dbeafe" : "#f3f4f6",
                    color: alert.status === "resolved" ? "#166534" : alert.status === "acknowledged" ? "#1d4ed8" : "#666",
                    fontSize: 11,
                    fontWeight: 600,
                  }}>
                    {alert.status.toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: 12, borderBottom: "1px solid #eee", fontSize: 13 }}>
                  {alert.acknowledged_by || "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AlertRulesTab({
  rules,
  isLoading,
  onInitDefaults,
  onCreateRule,
  onEditRule,
  onDeleteRule,
  onToggleRule,
}: {
  rules: AlertRule[];
  isLoading: boolean;
  onInitDefaults: () => void;
  onCreateRule: () => void;
  onEditRule: (rule: AlertRule) => void;
  onDeleteRule: (id: number) => void;
  onToggleRule: (rule: AlertRule) => void;
}) {
  if (isLoading) return <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading...</div>;

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <button
          onClick={onCreateRule}
          style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: "pointer" }}
        >
          + Create Rule
        </button>
        {rules.length === 0 && (
          <button
            onClick={onInitDefaults}
            style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}
          >
            Initialize Default Rules
          </button>
        )}
      </div>

      {rules.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#666", background: "#f9fafb", borderRadius: 12 }}>
          No alert rules configured. Click "Initialize Default Rules" to add standard clinical thresholds.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {rules.map((rule) => {
            const severityStyle = getSeverityColor(rule.severity);
            return (
              <div
                key={rule.id}
                style={{
                  padding: 16,
                  border: "1px solid #eee",
                  borderRadius: 8,
                  background: rule.is_active ? "white" : "#f9fafb",
                  opacity: rule.is_active ? 1 : 0.7,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 600 }}>{rule.name}</span>
                      <span style={{
                        padding: "2px 8px",
                        borderRadius: 999,
                        background: severityStyle.bg,
                        color: severityStyle.color,
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {rule.severity.toUpperCase()}
                      </span>
                      {!rule.is_active && (
                        <span style={{ padding: "2px 8px", borderRadius: 999, background: "#f3f4f6", color: "#666", fontSize: 11 }}>
                          DISABLED
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
                      {getVitalTypeLabel(rule.vital_type)} {CONDITIONS.find(c => c.value === rule.condition)?.symbol} {rule.threshold_value}
                      {rule.threshold_value_high && ` - ${rule.threshold_value_high}`}
                      {" "}{getVitalTypeUnit(rule.vital_type)}
                    </div>
                    {rule.description && (
                      <div style={{ fontSize: 12, color: "#999", marginTop: 4 }}>{rule.description}</div>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={() => onToggleRule(rule)}
                      style={{ padding: "4px 12px", borderRadius: 4, border: "1px solid #ddd", background: "white", cursor: "pointer", fontSize: 12 }}
                    >
                      {rule.is_active ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => onEditRule(rule)}
                      style={{ padding: "4px 12px", borderRadius: 4, border: "1px solid #ddd", background: "white", cursor: "pointer", fontSize: 12 }}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => onDeleteRule(rule.id)}
                      style={{ padding: "4px 12px", borderRadius: 4, border: "1px solid #dc2626", background: "white", color: "#dc2626", cursor: "pointer", fontSize: 12 }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AlertRuleForm({ rule, onClose, onSuccess }: { rule: AlertRule | null; onClose: () => void; onSuccess: () => void }) {
  const isEditing = !!rule;
  const [formData, setFormData] = useState({
    name: rule?.name || "",
    description: rule?.description || "",
    vital_type: rule?.vital_type || "heart_rate",
    condition: rule?.condition || "gt",
    threshold_value: rule?.threshold_value?.toString() || "",
    threshold_value_high: rule?.threshold_value_high?.toString() || "",
    severity: rule?.severity || "warning",
    cooldown_minutes: rule?.cooldown_minutes || 15,
    is_active: rule?.is_active ?? true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const data = {
      ...formData,
      threshold_value: parseFloat(formData.threshold_value),
      threshold_value_high: formData.threshold_value_high ? parseFloat(formData.threshold_value_high) : undefined,
    };

    if (isEditing) {
      await updateAlertRule(rule!.id, data);
    } else {
      await createAlertRule(data);
    }
    onSuccess();
  };

  const inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", fontSize: 14 };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 500, padding: 24 }}>
        <h3 style={{ marginTop: 0 }}>{isEditing ? "Edit Alert Rule" : "Create Alert Rule"}</h3>

        <form onSubmit={handleSubmit}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Rule Name *</label>
              <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required style={inputStyle} />
            </div>

            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Description</label>
              <input value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} style={inputStyle} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Vital Type *</label>
                <select value={formData.vital_type} onChange={(e) => setFormData({ ...formData, vital_type: e.target.value })} style={inputStyle}>
                  {VITAL_TYPES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Condition *</label>
                <select value={formData.condition} onChange={(e) => setFormData({ ...formData, condition: e.target.value })} style={inputStyle}>
                  {CONDITIONS.map(c => <option key={c.value} value={c.value}>{c.label} ({c.symbol})</option>)}
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Threshold Value *</label>
                <input type="number" step="0.01" value={formData.threshold_value} onChange={(e) => setFormData({ ...formData, threshold_value: e.target.value })} required style={inputStyle} />
              </div>
              {formData.condition === "range_outside" && (
                <div>
                  <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Upper Threshold</label>
                  <input type="number" step="0.01" value={formData.threshold_value_high} onChange={(e) => setFormData({ ...formData, threshold_value_high: e.target.value })} style={inputStyle} />
                </div>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Severity *</label>
                <select value={formData.severity} onChange={(e) => setFormData({ ...formData, severity: e.target.value as "info" | "warning" | "critical" })} style={inputStyle}>
                  {SEVERITIES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Cooldown (minutes)</label>
                <input type="number" value={formData.cooldown_minutes} onChange={(e) => setFormData({ ...formData, cooldown_minutes: parseInt(e.target.value) })} style={inputStyle} />
              </div>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })} />
              <span>Rule is active</span>
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 24 }}>
            <button type="button" onClick={onClose} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}>
              Cancel
            </button>
            <button type="submit" style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: "pointer" }}>
              {isEditing ? "Update Rule" : "Create Rule"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
