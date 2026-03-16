import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchLabOrders,
  fetchLabOrder,
  fetchLabTests,
  fetchLabPanels,
  fetchLabStats,
  createLabOrder,
  updateLabOrderStatus,
  enterLabResults,
  initializeLabCatalog,
  LAB_ORDER_STATUSES,
  LAB_PRIORITIES,
  LAB_CATEGORIES,
  FLAG_LABELS,
  type LabOrderListItem,
  type LabTest,
  type LabPanel,
} from "../lib/labsApi";
import { fetchPatients, type Patient } from "../lib/patientApi";

type Tab = "orders" | "pending" | "results" | "catalog";

// Order Form Modal
function OrderFormModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const queryClient = useQueryClient();
  const [patientId, setPatientId] = useState<number | null>(null);
  const [priority, setPriority] = useState("routine");
  const [physician, setPhysician] = useState("");
  const [clinicalNotes, setClinicalNotes] = useState("");
  const [selectedTests, setSelectedTests] = useState<string[]>([]);
  const [selectedPanels, setSelectedPanels] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [error, setError] = useState("");

  const patientsQ = useQuery({
    queryKey: ["patients-select"],
    queryFn: () => fetchPatients({ limit: 200 }),
  });

  const testsQ = useQuery({
    queryKey: ["lab-tests", searchTerm],
    queryFn: () => fetchLabTests({ search: searchTerm || undefined, limit: 100 }),
  });

  const panelsQ = useQuery({
    queryKey: ["lab-panels"],
    queryFn: fetchLabPanels,
  });

  const createMutation = useMutation({
    mutationFn: createLabOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
      onSuccess();
    },
    onError: () => setError("Failed to create order"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!patientId) {
      setError("Please select a patient");
      return;
    }
    if (!physician) {
      setError("Please enter ordering physician");
      return;
    }
    if (selectedTests.length === 0 && selectedPanels.length === 0) {
      setError("Please select at least one test or panel");
      return;
    }

    createMutation.mutate({
      patient: patientId,
      priority,
      ordering_physician: physician,
      clinical_notes: clinicalNotes,
      test_codes: selectedTests,
      panel_codes: selectedPanels,
    });
  };

  const toggleTest = (code: string) => {
    setSelectedTests((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const togglePanel = (code: string) => {
    setSelectedPanels((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  return (
    <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: 12, padding: 24, width: "100%", maxWidth: 700, maxHeight: "90vh", overflow: "auto" }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 18, fontWeight: 600 }}>New Lab Order</h2>

        {error && (
          <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: 12, marginBottom: 16, color: "#dc2626", fontSize: 13 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Patient *</label>
              <select
                value={patientId || ""}
                onChange={(e) => setPatientId(Number(e.target.value) || null)}
                required
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              >
                <option value="">Select patient...</option>
                {patientsQ.data?.results.map((p: Patient) => (
                  <option key={p.id} value={p.id}>{p.first_name} {p.last_name} ({p.mrn})</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
              >
                {LAB_PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Ordering Physician *</label>
            <input
              type="text"
              value={physician}
              onChange={(e) => setPhysician(e.target.value)}
              required
              placeholder="Dr. Name"
              style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box" }}
            />
          </div>

          <div style={{ marginTop: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 4 }}>Clinical Notes</label>
            <textarea
              value={clinicalNotes}
              onChange={(e) => setClinicalNotes(e.target.value)}
              rows={2}
              placeholder="Reason for testing..."
              style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, boxSizing: "border-box", resize: "vertical" }}
            />
          </div>

          {/* Panels */}
          <div style={{ marginTop: 16 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 8 }}>Lab Panels</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {panelsQ.data?.results.map((panel: LabPanel) => (
                <button
                  key={panel.code}
                  type="button"
                  onClick={() => togglePanel(panel.code)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: selectedPanels.includes(panel.code) ? "2px solid #3b82f6" : "1px solid #ddd",
                    background: selectedPanels.includes(panel.code) ? "#eff6ff" : "white",
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  {panel.name} ({panel.tests.length} tests)
                </button>
              ))}
            </div>
          </div>

          {/* Individual Tests */}
          <div style={{ marginTop: 16 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, marginBottom: 8 }}>Individual Tests</label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search tests..."
              style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, marginBottom: 8, boxSizing: "border-box" }}
            />
            <div style={{ maxHeight: 200, overflow: "auto", border: "1px solid #eee", borderRadius: 6 }}>
              {testsQ.data?.results.map((test: LabTest) => (
                <label
                  key={test.code}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "8px 12px",
                    borderBottom: "1px solid #f3f4f6",
                    cursor: "pointer",
                    background: selectedTests.includes(test.code) ? "#eff6ff" : "white",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedTests.includes(test.code)}
                    onChange={() => toggleTest(test.code)}
                  />
                  <div>
                    <div style={{ fontSize: 13 }}>{test.name}</div>
                    <div style={{ fontSize: 11, color: "#666" }}>{test.code} - {test.category}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Selected summary */}
          {(selectedTests.length > 0 || selectedPanels.length > 0) && (
            <div style={{ marginTop: 12, padding: 12, background: "#f9fafb", borderRadius: 6, fontSize: 12 }}>
              <strong>Selected:</strong> {selectedPanels.length} panel(s), {selectedTests.length} individual test(s)
            </div>
          )}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 20 }}>
            <button type="button" onClick={onClose} style={{ padding: "8px 16px", border: "1px solid #ddd", borderRadius: 6, background: "white", cursor: "pointer" }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              style={{ padding: "8px 16px", border: "none", borderRadius: 6, background: createMutation.isPending ? "#9ca3af" : "#3b82f6", color: "white", cursor: createMutation.isPending ? "not-allowed" : "pointer" }}
            >
              {createMutation.isPending ? "Creating..." : "Create Order"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Order Detail Modal
function OrderDetailModal({
  orderId,
  onClose,
}: {
  orderId: number;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [resultValues, setResultValues] = useState<Record<number, { value: string; performedBy: string }>>({});

  const orderQ = useQuery({
    queryKey: ["lab-order", orderId],
    queryFn: () => fetchLabOrder(orderId),
  });

  const statusMutation = useMutation({
    mutationFn: ({ status }: { status: string }) => updateLabOrderStatus(orderId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-order", orderId] });
      queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
    },
  });

  const resultMutation = useMutation({
    mutationFn: (results: Array<{ order_test_id: number; value_numeric?: number; value_text?: string; performed_by?: string }>) =>
      enterLabResults(orderId, results),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-order", orderId] });
      queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
      setResultValues({});
    },
  });

  const handleSaveResults = () => {
    const results = Object.entries(resultValues)
      .filter(([, v]) => v.value)
      .map(([testId, v]) => ({
        order_test_id: Number(testId),
        value_numeric: !isNaN(Number(v.value)) ? Number(v.value) : undefined,
        value_text: isNaN(Number(v.value)) ? v.value : undefined,
        performed_by: v.performedBy,
      }));

    if (results.length > 0) {
      resultMutation.mutate(results);
    }
  };

  if (orderQ.isLoading) {
    return (
      <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
        <div style={{ background: "white", borderRadius: 12, padding: 40 }}>Loading...</div>
      </div>
    );
  }

  const order = orderQ.data;
  if (!order) return null;

  const statusInfo = LAB_ORDER_STATUSES.find((s) => s.value === order.status);
  const priorityInfo = LAB_PRIORITIES.find((p) => p.value === order.priority);

  return (
    <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: 12, padding: 24, width: "100%", maxWidth: 800, maxHeight: "90vh", overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 16 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Order {order.order_number}</h2>
            <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
              {order.patient_name} ({order.patient_mrn})
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 500, background: `${statusInfo?.color}20`, color: statusInfo?.color }}>
              {statusInfo?.label}
            </span>
            <span style={{ padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 500, background: `${priorityInfo?.color}20`, color: priorityInfo?.color }}>
              {priorityInfo?.label}
            </span>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16, fontSize: 13 }}>
          <div>
            <div style={{ color: "#666" }}>Ordered by</div>
            <div style={{ fontWeight: 500 }}>{order.ordering_physician}</div>
          </div>
          <div>
            <div style={{ color: "#666" }}>Ordered at</div>
            <div style={{ fontWeight: 500 }}>{new Date(order.ordered_at).toLocaleString()}</div>
          </div>
          {order.clinical_notes && (
            <div style={{ gridColumn: "1 / -1" }}>
              <div style={{ color: "#666" }}>Clinical Notes</div>
              <div>{order.clinical_notes}</div>
            </div>
          )}
        </div>

        {/* Status Actions */}
        {order.status !== "completed" && order.status !== "cancelled" && (
          <div style={{ marginBottom: 16, padding: 12, background: "#f9fafb", borderRadius: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8 }}>Update Status</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {order.status === "ordered" && (
                <button onClick={() => statusMutation.mutate({ status: "collected" })} style={{ padding: "6px 12px", border: "1px solid #ddd", borderRadius: 6, background: "white", cursor: "pointer", fontSize: 12 }}>
                  Mark Collected
                </button>
              )}
              {order.status === "collected" && (
                <button onClick={() => statusMutation.mutate({ status: "received" })} style={{ padding: "6px 12px", border: "1px solid #ddd", borderRadius: 6, background: "white", cursor: "pointer", fontSize: 12 }}>
                  Mark Received
                </button>
              )}
              {(order.status === "received" || order.status === "partial") && (
                <button onClick={() => statusMutation.mutate({ status: "processing" })} style={{ padding: "6px 12px", border: "1px solid #ddd", borderRadius: 6, background: "white", cursor: "pointer", fontSize: 12 }}>
                  Mark Processing
                </button>
              )}
            </div>
          </div>
        )}

        {/* Tests and Results */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Tests ({order.tests.length})</div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <th style={{ padding: 8, textAlign: "left" }}>Test</th>
                <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                <th style={{ padding: 8, textAlign: "left" }}>Result</th>
                <th style={{ padding: 8, textAlign: "left" }}>Reference</th>
                <th style={{ padding: 8, textAlign: "left" }}>Flag</th>
              </tr>
            </thead>
            <tbody>
              {order.tests.map((test) => {
                const hasResult = !!test.result;
                const flag = test.result?.flag || "N";
                const flagInfo = FLAG_LABELS[flag];

                return (
                  <tr key={test.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={{ padding: 8 }}>
                      <div style={{ fontWeight: 500 }}>{test.test_details.name}</div>
                      <div style={{ fontSize: 11, color: "#666" }}>{test.test_details.code}</div>
                    </td>
                    <td style={{ padding: 8 }}>
                      <span style={{
                        padding: "2px 8px",
                        borderRadius: 10,
                        fontSize: 11,
                        background: test.status === "completed" ? "#dcfce7" : "#fef3c7",
                        color: test.status === "completed" ? "#166534" : "#92400e",
                      }}>
                        {test.status}
                      </span>
                    </td>
                    <td style={{ padding: 8 }}>
                      {hasResult ? (
                        <span style={{ fontWeight: 500 }}>
                          {test.result?.value_numeric ?? test.result?.value_text} {test.result?.unit}
                        </span>
                      ) : order.status !== "cancelled" && order.status !== "ordered" ? (
                        <input
                          type="text"
                          value={resultValues[test.id]?.value || ""}
                          onChange={(e) => setResultValues({
                            ...resultValues,
                            [test.id]: { ...resultValues[test.id], value: e.target.value, performedBy: resultValues[test.id]?.performedBy || "" }
                          })}
                          placeholder="Enter value"
                          style={{ width: 80, padding: 4, border: "1px solid #ddd", borderRadius: 4, fontSize: 12 }}
                        />
                      ) : "-"}
                    </td>
                    <td style={{ padding: 8, fontSize: 11, color: "#666" }}>
                      {test.test_details.reference_range_low && test.test_details.reference_range_high
                        ? `${test.test_details.reference_range_low} - ${test.test_details.reference_range_high}`
                        : test.test_details.reference_range_text || "-"}
                    </td>
                    <td style={{ padding: 8 }}>
                      {hasResult && (
                        <span style={{
                          padding: "2px 8px",
                          borderRadius: 10,
                          fontSize: 11,
                          fontWeight: 500,
                          background: `${flagInfo.color}20`,
                          color: flagInfo.color,
                        }}>
                          {flagInfo.label}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {Object.keys(resultValues).some((k) => resultValues[Number(k)]?.value) && (
            <div style={{ marginTop: 12 }}>
              <button
                onClick={handleSaveResults}
                disabled={resultMutation.isPending}
                style={{ padding: "8px 16px", border: "none", borderRadius: 6, background: "#10b981", color: "white", cursor: "pointer", fontSize: 13 }}
              >
                {resultMutation.isPending ? "Saving..." : "Save Results"}
              </button>
            </div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "8px 16px", border: "1px solid #ddd", borderRadius: 6, background: "white", cursor: "pointer" }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Orders Tab
function OrdersTab() {
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);

  const ordersQ = useQuery({
    queryKey: ["lab-orders", statusFilter],
    queryFn: () => fetchLabOrders({ status: statusFilter || undefined, limit: 100 }),
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13 }}
          >
            <option value="">All statuses</option>
            {LAB_ORDER_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setShowForm(true)}
          style={{ padding: "8px 16px", background: "#3b82f6", color: "white", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
        >
          + New Order
        </button>
      </div>

      {ordersQ.isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading orders...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Order #</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Patient</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Tests</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Status</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Priority</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Ordered</th>
              <th style={{ padding: 12, textAlign: "right", fontWeight: 600 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {ordersQ.data?.results.map((order: LabOrderListItem) => {
              const statusInfo = LAB_ORDER_STATUSES.find((s) => s.value === order.status);
              const priorityInfo = LAB_PRIORITIES.find((p) => p.value === order.priority);

              return (
                <tr key={order.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 12, fontFamily: "monospace" }}>{order.order_number}</td>
                  <td style={{ padding: 12 }}>
                    <div style={{ fontWeight: 500 }}>{order.patient_name}</div>
                    <div style={{ fontSize: 11, color: "#666" }}>{order.patient_mrn}</div>
                  </td>
                  <td style={{ padding: 12 }}>
                    {order.completed_count}/{order.test_count} completed
                  </td>
                  <td style={{ padding: 12 }}>
                    <span style={{
                      padding: "2px 10px",
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 500,
                      background: `${statusInfo?.color}20`,
                      color: statusInfo?.color,
                    }}>
                      {statusInfo?.label}
                    </span>
                  </td>
                  <td style={{ padding: 12 }}>
                    <span style={{
                      padding: "2px 10px",
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 500,
                      background: `${priorityInfo?.color}20`,
                      color: priorityInfo?.color,
                    }}>
                      {priorityInfo?.label}
                    </span>
                  </td>
                  <td style={{ padding: 12, color: "#666" }}>
                    {new Date(order.ordered_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: 12, textAlign: "right" }}>
                    <button
                      onClick={() => setSelectedOrderId(order.id)}
                      style={{ padding: "4px 12px", border: "1px solid #ddd", borderRadius: 4, background: "white", cursor: "pointer", fontSize: 12 }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {showForm && (
        <OrderFormModal
          onClose={() => setShowForm(false)}
          onSuccess={() => setShowForm(false)}
        />
      )}

      {selectedOrderId && (
        <OrderDetailModal
          orderId={selectedOrderId}
          onClose={() => setSelectedOrderId(null)}
        />
      )}
    </div>
  );
}

// Catalog Tab
function CatalogTab() {
  const queryClient = useQueryClient();
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");

  const testsQ = useQuery({
    queryKey: ["lab-catalog", category, search],
    queryFn: () => fetchLabTests({ category: category || undefined, search: search || undefined, limit: 200 }),
  });

  const initMutation = useMutation({
    mutationFn: initializeLabCatalog,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab-catalog"] });
      queryClient.invalidateQueries({ queryKey: ["lab-panels"] });
    },
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tests..."
            style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13, width: 200 }}
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, fontSize: 13 }}
          >
            <option value="">All categories</option>
            {LAB_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => initMutation.mutate()}
          disabled={initMutation.isPending}
          style={{ padding: "8px 16px", background: "#10b981", color: "white", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
        >
          {initMutation.isPending ? "Initializing..." : "Initialize Catalog"}
        </button>
      </div>

      {testsQ.isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#666" }}>Loading catalog...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Code</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Name</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Category</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Specimen</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Reference Range</th>
              <th style={{ padding: 12, textAlign: "left", fontWeight: 600 }}>Unit</th>
            </tr>
          </thead>
          <tbody>
            {testsQ.data?.results.map((test: LabTest) => (
              <tr key={test.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: 12, fontFamily: "monospace" }}>{test.code}</td>
                <td style={{ padding: 12, fontWeight: 500 }}>{test.name}</td>
                <td style={{ padding: 12 }}>{LAB_CATEGORIES.find((c) => c.value === test.category)?.label}</td>
                <td style={{ padding: 12 }}>{test.specimen_type}</td>
                <td style={{ padding: 12, fontSize: 12 }}>
                  {test.reference_range_low !== null && test.reference_range_high !== null
                    ? `${test.reference_range_low} - ${test.reference_range_high}`
                    : test.reference_range_text || "-"}
                </td>
                <td style={{ padding: 12 }}>{test.unit || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// Stats Component
function StatsPanel() {
  const statsQ = useQuery({
    queryKey: ["lab-stats"],
    queryFn: fetchLabStats,
    refetchInterval: 30000,
  });

  if (!statsQ.data) return null;

  const stats = statsQ.data;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 16 }}>
      <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#3b82f6" }}>{stats.orders_today}</div>
        <div style={{ fontSize: 11, color: "#666" }}>Orders Today</div>
      </div>
      <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#f59e0b" }}>{stats.pending_orders}</div>
        <div style={{ fontSize: 11, color: "#666" }}>Pending</div>
      </div>
      <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#ef4444" }}>{stats.critical_results_today}</div>
        <div style={{ fontSize: 11, color: "#666" }}>Critical Today</div>
      </div>
      <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#10b981" }}>{stats.average_tat_hours || "-"}</div>
        <div style={{ fontSize: 11, color: "#666" }}>Avg TAT (hrs)</div>
      </div>
      <div style={{ background: "#f9fafb", borderRadius: 8, padding: 16, textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#8b5cf6" }}>{stats.total_tests_in_catalog}</div>
        <div style={{ fontSize: 11, color: "#666" }}>Tests in Catalog</div>
      </div>
    </div>
  );
}

export function LabsDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("orders");

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
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Lab Orders & Results</h2>
        <p style={{ margin: "4px 0 0", fontSize: 12, color: "#666" }}>
          Manage lab orders, enter results, and view test catalog
        </p>
      </div>

      <StatsPanel />

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button style={tabButtonStyle(activeTab === "orders")} onClick={() => setActiveTab("orders")}>
          All Orders
        </button>
        <button style={tabButtonStyle(activeTab === "pending")} onClick={() => setActiveTab("pending")}>
          Pending Results
        </button>
        <button style={tabButtonStyle(activeTab === "catalog")} onClick={() => setActiveTab("catalog")}>
          Test Catalog
        </button>
      </div>

      {activeTab === "orders" && <OrdersTab />}
      {activeTab === "pending" && <OrdersTab />}
      {activeTab === "catalog" && <CatalogTab />}
    </div>
  );
}
