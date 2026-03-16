import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchMedications,
  fetchPrescriptions,
  fetchAdministrations,
  fetchMedicationStats,
  seedMedicationCatalog,
  createPrescription,
  activatePrescription,
  holdPrescription,
  discontinuePrescription,
  administerMedication,
  recordNotGiven,
  type Prescription,
  type PrescriptionCreate,
} from "../lib/medicationsApi";
import { fetchPatients } from "../lib/patientApi";

type TabType = "prescriptions" | "mar" | "catalog" | "stats";

export function MedicationsDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>("prescriptions");

  const tabStyle = (active: boolean) => ({
    padding: "10px 20px",
    border: "none",
    borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
    background: "transparent",
    color: active ? "#2563eb" : "#666",
    cursor: "pointer",
    fontWeight: active ? 600 : 400,
    fontSize: 14,
  });

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: "#1f2937" }}>
          Medication Management
        </h2>
        <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>
          Prescriptions, Administration Records, and Drug Catalog
        </p>
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: "1px solid #e5e7eb", marginBottom: 16 }}>
        <button style={tabStyle(activeTab === "prescriptions")} onClick={() => setActiveTab("prescriptions")}>
          Prescriptions
        </button>
        <button style={tabStyle(activeTab === "mar")} onClick={() => setActiveTab("mar")}>
          MAR (Due Meds)
        </button>
        <button style={tabStyle(activeTab === "catalog")} onClick={() => setActiveTab("catalog")}>
          Drug Catalog
        </button>
        <button style={tabStyle(activeTab === "stats")} onClick={() => setActiveTab("stats")}>
          Statistics
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "prescriptions" && <PrescriptionsTab />}
      {activeTab === "mar" && <MARTab />}
      {activeTab === "catalog" && <CatalogTab />}
      {activeTab === "stats" && <StatsTab />}
    </div>
  );
}

function PrescriptionsTab() {
  const [showNewRx, setShowNewRx] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("active");
  const [selectedRx, setSelectedRx] = useState<Prescription | null>(null);
  const queryClient = useQueryClient();

  const prescriptionsQ = useQuery({
    queryKey: ["prescriptions", statusFilter],
    queryFn: () => fetchPrescriptions({ status: statusFilter || undefined }),
  });

  const activateMut = useMutation({
    mutationFn: (id: number) => activatePrescription(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
      setSelectedRx(null);
    },
  });

  const holdMut = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      holdPrescription(id, reason, "Current User"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
      setSelectedRx(null);
    },
  });

  const discontinueMut = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      discontinuePrescription(id, reason, "Current User"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
      setSelectedRx(null);
    },
  });

  const getStatusColor = (status: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      draft: { bg: "#f3f4f6", text: "#6b7280" },
      pending: { bg: "#fef3c7", text: "#92400e" },
      active: { bg: "#d1fae5", text: "#065f46" },
      on_hold: { bg: "#fecaca", text: "#991b1b" },
      completed: { bg: "#e5e7eb", text: "#374151" },
      discontinued: { bg: "#fecaca", text: "#991b1b" },
      cancelled: { bg: "#e5e7eb", text: "#6b7280" },
    };
    return colors[status] || colors.draft;
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      routine: { bg: "#e5e7eb", text: "#374151" },
      urgent: { bg: "#fed7aa", text: "#9a3412" },
      stat: { bg: "#fecaca", text: "#991b1b" },
      prn: { bg: "#dbeafe", text: "#1e40af" },
    };
    return colors[priority] || colors.routine;
  };

  return (
    <div>
      {/* Controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 13 }}
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending Review</option>
            <option value="active">Active</option>
            <option value="on_hold">On Hold</option>
            <option value="completed">Completed</option>
            <option value="discontinued">Discontinued</option>
          </select>
        </div>
        <button
          onClick={() => setShowNewRx(true)}
          style={{
            padding: "8px 16px",
            background: "#2563eb",
            color: "white",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          + New Prescription
        </button>
      </div>

      {/* Prescriptions List */}
      {prescriptionsQ.isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>Loading prescriptions...</div>
      ) : prescriptionsQ.data?.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>No prescriptions found</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {prescriptionsQ.data?.map((rx) => {
            const statusColor = getStatusColor(rx.status);
            const priorityColor = getPriorityColor(rx.priority);
            return (
              <div
                key={rx.id}
                onClick={() => setSelectedRx(rx)}
                style={{
                  padding: 16,
                  border: "1px solid #e5e7eb",
                  borderRadius: 8,
                  cursor: "pointer",
                  background: selectedRx?.id === rx.id ? "#f0f9ff" : "white",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 15 }}>{rx.medication_name}</span>
                      {rx.is_high_alert && (
                        <span
                          style={{
                            background: "#fecaca",
                            color: "#991b1b",
                            padding: "2px 6px",
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 600,
                          }}
                        >
                          HIGH ALERT
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>
                      {rx.dose_quantity} {rx.dose_unit} {rx.route} {rx.frequency}
                    </div>
                    <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>
                      {rx.patient_name} | {rx.prescription_number}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span
                      style={{
                        background: priorityColor.bg,
                        color: priorityColor.text,
                        padding: "4px 8px",
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 500,
                      }}
                    >
                      {rx.priority.toUpperCase()}
                    </span>
                    <span
                      style={{
                        background: statusColor.bg,
                        color: statusColor.text,
                        padding: "4px 8px",
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 500,
                      }}
                    >
                      {rx.status.replace("_", " ").toUpperCase()}
                    </span>
                  </div>
                </div>
                {rx.indication && (
                  <div style={{ fontSize: 12, color: "#6b7280", marginTop: 8, fontStyle: "italic" }}>
                    Indication: {rx.indication}
                  </div>
                )}
                {!rx.allergy_check_passed && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: 8,
                      background: "#fef2f2",
                      borderRadius: 4,
                      fontSize: 12,
                      color: "#dc2626",
                    }}
                  >
                    Allergy warning - requires review
                  </div>
                )}
                {rx.interaction_warnings && rx.interaction_warnings.length > 0 && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: 8,
                      background: "#fffbeb",
                      borderRadius: 4,
                      fontSize: 12,
                      color: "#b45309",
                    }}
                  >
                    {rx.interaction_warnings.length} drug interaction(s) detected
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Selected Prescription Actions */}
      {selectedRx && (
        <div
          style={{
            position: "fixed",
            bottom: 20,
            left: "50%",
            transform: "translateX(-50%)",
            background: "white",
            padding: 16,
            borderRadius: 8,
            boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
            display: "flex",
            gap: 12,
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 13, color: "#374151" }}>
            Selected: <strong>{selectedRx.medication_name}</strong>
          </span>
          {selectedRx.status === "pending" && (
            <button
              onClick={() => activateMut.mutate(selectedRx.id)}
              disabled={activateMut.isPending}
              style={{
                padding: "8px 16px",
                background: "#059669",
                color: "white",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              Activate
            </button>
          )}
          {selectedRx.status === "active" && (
            <>
              <button
                onClick={() => {
                  const reason = prompt("Reason for hold?");
                  if (reason) holdMut.mutate({ id: selectedRx.id, reason });
                }}
                style={{
                  padding: "8px 16px",
                  background: "#f59e0b",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                Hold
              </button>
              <button
                onClick={() => {
                  const reason = prompt("Reason for discontinuation?");
                  if (reason) discontinueMut.mutate({ id: selectedRx.id, reason });
                }}
                style={{
                  padding: "8px 16px",
                  background: "#dc2626",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                Discontinue
              </button>
            </>
          )}
          <button
            onClick={() => setSelectedRx(null)}
            style={{
              padding: "8px 16px",
              background: "#e5e7eb",
              color: "#374151",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Cancel
          </button>
        </div>
      )}

      {/* New Prescription Modal */}
      {showNewRx && <NewPrescriptionModal onClose={() => setShowNewRx(false)} />}
    </div>
  );
}

function NewPrescriptionModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<PrescriptionCreate>>({
    dose_quantity: 1,
    dose_unit: "mg",
    frequency: "Daily",
    start_date: new Date().toISOString().split("T")[0],
    priority: "routine",
    prescriber_name: "Dr. Smith",
  });

  const patientsQ = useQuery({
    queryKey: ["patients"],
    queryFn: () => fetchPatients(),
  });

  const medicationsQ = useQuery({
    queryKey: ["medications"],
    queryFn: () => fetchMedications({ is_active: true }),
  });

  const selectedMed = medicationsQ.data?.find((m) => m.id === formData.medication);

  const createMut = useMutation({
    mutationFn: (data: PrescriptionCreate) => createPrescription(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.patient || !formData.medication) {
      alert("Please select a patient and medication");
      return;
    }
    createMut.mutate(formData as PrescriptionCreate);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "white",
          borderRadius: 12,
          padding: 24,
          width: "100%",
          maxWidth: 600,
          maxHeight: "90vh",
          overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 16px", fontSize: 18, fontWeight: 600 }}>New Prescription</h3>

        <form onSubmit={handleSubmit}>
          {/* Patient Selection */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Patient *</label>
            <select
              value={formData.patient || ""}
              onChange={(e) => setFormData({ ...formData, patient: parseInt(e.target.value) })}
              required
              style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14 }}
            >
              <option value="">Select patient...</option>
              {patientsQ.data?.results?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name} - MRN: {p.mrn}
                </option>
              ))}
            </select>
          </div>

          {/* Medication Selection */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Medication *</label>
            <select
              value={formData.medication || ""}
              onChange={(e) => {
                const med = medicationsQ.data?.find((m) => m.id === parseInt(e.target.value));
                setFormData({
                  ...formData,
                  medication: parseInt(e.target.value),
                  dose_unit: med?.strength?.split(/\d+/)[1]?.trim() || "mg",
                  route: med?.route || "oral",
                });
              }}
              required
              style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14 }}
            >
              <option value="">Select medication...</option>
              {medicationsQ.data?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.generic_name} {m.strength} ({m.form})
                  {m.is_high_alert ? " [HIGH ALERT]" : ""}
                  {m.is_controlled ? " [CONTROLLED]" : ""}
                </option>
              ))}
            </select>
            {selectedMed && (
              <div style={{ marginTop: 8, padding: 8, background: "#f3f4f6", borderRadius: 6, fontSize: 12 }}>
                <div>
                  <strong>Category:</strong> {selectedMed.category}
                </div>
                <div>
                  <strong>Route:</strong> {selectedMed.route}
                </div>
                <div>
                  <strong>Form:</strong> {selectedMed.form}
                </div>
              </div>
            )}
          </div>

          {/* Dosing */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Dose *</label>
              <input
                type="number"
                step="0.01"
                value={formData.dose_quantity || ""}
                onChange={(e) => setFormData({ ...formData, dose_quantity: parseFloat(e.target.value) })}
                required
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Unit *</label>
              <input
                type="text"
                value={formData.dose_unit || ""}
                onChange={(e) => setFormData({ ...formData, dose_unit: e.target.value })}
                required
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Route *</label>
              <select
                value={formData.route || "oral"}
                onChange={(e) => setFormData({ ...formData, route: e.target.value })}
                required
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14 }}
              >
                <option value="oral">Oral</option>
                <option value="iv">IV</option>
                <option value="im">IM</option>
                <option value="subq">SubQ</option>
                <option value="topical">Topical</option>
                <option value="inhalation">Inhalation</option>
              </select>
            </div>
          </div>

          {/* Frequency */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Frequency *</label>
              <select
                value={formData.frequency || "Daily"}
                onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                required
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14 }}
              >
                <option value="Daily">Daily (QD)</option>
                <option value="BID">Twice Daily (BID)</option>
                <option value="TID">Three Times Daily (TID)</option>
                <option value="QID">Four Times Daily (QID)</option>
                <option value="Q4H">Every 4 Hours</option>
                <option value="Q6H">Every 6 Hours</option>
                <option value="Q8H">Every 8 Hours</option>
                <option value="Q12H">Every 12 Hours</option>
                <option value="Q4H PRN">Every 4 Hours PRN</option>
                <option value="Q6H PRN">Every 6 Hours PRN</option>
                <option value="QHS">At Bedtime</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Priority</label>
              <select
                value={formData.priority || "routine"}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14 }}
              >
                <option value="routine">Routine</option>
                <option value="urgent">Urgent</option>
                <option value="stat">STAT</option>
                <option value="prn">PRN</option>
              </select>
            </div>
          </div>

          {/* Dates */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Start Date *</label>
              <input
                type="date"
                value={formData.start_date || ""}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                required
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>End Date</label>
              <input
                type="date"
                value={formData.end_date || ""}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Duration (days)</label>
              <input
                type="number"
                value={formData.duration_days || ""}
                onChange={(e) => setFormData({ ...formData, duration_days: parseInt(e.target.value) })}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
              />
            </div>
          </div>

          {/* Prescriber */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Prescriber Name *</label>
            <input
              type="text"
              value={formData.prescriber_name || ""}
              onChange={(e) => setFormData({ ...formData, prescriber_name: e.target.value })}
              required
              style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, boxSizing: "border-box" }}
            />
          </div>

          {/* Indication */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Indication/Reason</label>
            <textarea
              value={formData.indication || ""}
              onChange={(e) => setFormData({ ...formData, indication: e.target.value })}
              rows={2}
              style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, resize: "vertical", boxSizing: "border-box" }}
            />
          </div>

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 24 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "10px 20px",
                background: "#e5e7eb",
                color: "#374151",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMut.isPending}
              style={{
                padding: "10px 20px",
                background: "#2563eb",
                color: "white",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 14,
                fontWeight: 500,
              }}
            >
              {createMut.isPending ? "Creating..." : "Create Prescription"}
            </button>
          </div>

          {createMut.isError && (
            <div style={{ marginTop: 12, padding: 12, background: "#fef2f2", borderRadius: 6, color: "#dc2626", fontSize: 13 }}>
              Error creating prescription. Please try again.
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

function MARTab() {
  const queryClient = useQueryClient();

  const administrationsQ = useQuery({
    queryKey: ["administrations", "due"],
    queryFn: () => fetchAdministrations({ due: true }),
    refetchInterval: 30000,
  });

  const administerMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { administered_by: string } }) =>
      administerMedication(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["administrations"] });
    },
  });

  const notGivenMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { reason: string; documented_by: string } }) =>
      recordNotGiven(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["administrations"] });
    },
  });

  const getTimeStatus = (scheduledTime: string) => {
    const now = new Date();
    const scheduled = new Date(scheduledTime);
    const diffMinutes = (now.getTime() - scheduled.getTime()) / (1000 * 60);

    if (diffMinutes < -30) return { label: "Upcoming", color: "#6b7280" };
    if (diffMinutes < 0) return { label: "Due Soon", color: "#f59e0b" };
    if (diffMinutes < 30) return { label: "Due Now", color: "#059669" };
    if (diffMinutes < 60) return { label: "Late", color: "#dc2626" };
    return { label: "Overdue", color: "#991b1b" };
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#1f2937" }}>
          Medication Administration Record - Due Medications
        </h3>
        <p style={{ margin: "4px 0 0", fontSize: 12, color: "#6b7280" }}>
          Medications due in the next hour
        </p>
      </div>

      {administrationsQ.isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>Loading due medications...</div>
      ) : administrationsQ.data?.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>
          No medications due at this time
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {administrationsQ.data?.map((admin) => {
            const timeStatus = getTimeStatus(admin.scheduled_time);
            return (
              <div
                key={admin.id}
                style={{
                  padding: 16,
                  border: "1px solid #e5e7eb",
                  borderRadius: 8,
                  background: "white",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 15 }}>{admin.medication_name}</span>
                      {admin.is_high_alert && (
                        <span
                          style={{
                            background: "#fecaca",
                            color: "#991b1b",
                            padding: "2px 6px",
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 600,
                          }}
                        >
                          HIGH ALERT
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: "#374151", marginTop: 4 }}>
                      Patient: <strong>{admin.patient_name}</strong>
                    </div>
                    <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
                      Scheduled: {new Date(admin.scheduled_time).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                    <span
                      style={{
                        color: timeStatus.color,
                        fontWeight: 600,
                        fontSize: 12,
                      }}
                    >
                      {timeStatus.label}
                    </span>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        onClick={() =>
                          administerMut.mutate({
                            id: admin.id,
                            data: { administered_by: "Current User" },
                          })
                        }
                        disabled={administerMut.isPending}
                        style={{
                          padding: "6px 12px",
                          background: "#059669",
                          color: "white",
                          border: "none",
                          borderRadius: 4,
                          cursor: "pointer",
                          fontSize: 12,
                        }}
                      >
                        Give
                      </button>
                      <button
                        onClick={() => {
                          const reason = prompt("Reason not given?", "patient_refused");
                          if (reason) {
                            notGivenMut.mutate({
                              id: admin.id,
                              data: { reason, documented_by: "Current User" },
                            });
                          }
                        }}
                        disabled={notGivenMut.isPending}
                        style={{
                          padding: "6px 12px",
                          background: "#e5e7eb",
                          color: "#374151",
                          border: "none",
                          borderRadius: 4,
                          cursor: "pointer",
                          fontSize: 12,
                        }}
                      >
                        Not Given
                      </button>
                    </div>
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

function CatalogTab() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const medicationsQ = useQuery({
    queryKey: ["medications", search, categoryFilter],
    queryFn: () =>
      fetchMedications({
        search: search || undefined,
        category: categoryFilter || undefined,
        is_active: true,
      }),
  });

  const seedMut = useMutation({
    mutationFn: seedMedicationCatalog,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medications"] });
    },
  });

  const categories = [
    "analgesic",
    "antibiotic",
    "antihypertensive",
    "antidiabetic",
    "anticoagulant",
    "cardiovascular",
    "respiratory",
    "gastrointestinal",
    "psychiatric",
    "vitamin",
    "antiinflammatory",
  ];

  return (
    <div>
      {/* Search and Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search medications..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1,
            minWidth: 200,
            padding: "10px 12px",
            border: "1px solid #d1d5db",
            borderRadius: 6,
            fontSize: 14,
          }}
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          style={{ padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14 }}
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </option>
          ))}
        </select>
        <button
          onClick={() => seedMut.mutate()}
          disabled={seedMut.isPending}
          style={{
            padding: "10px 16px",
            background: "#059669",
            color: "white",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          {seedMut.isPending ? "Seeding..." : "Seed Catalog"}
        </button>
      </div>

      {seedMut.isSuccess && (
        <div style={{ marginBottom: 16, padding: 12, background: "#d1fae5", borderRadius: 6, color: "#065f46", fontSize: 13 }}>
          Catalog seeded successfully!
        </div>
      )}

      {/* Medications Grid */}
      {medicationsQ.isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>Loading medications...</div>
      ) : medicationsQ.data?.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>
          No medications found. Click "Seed Catalog" to add common medications.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
          {medicationsQ.data?.map((med) => (
            <div
              key={med.id}
              style={{
                padding: 16,
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                background: "white",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{med.generic_name}</div>
                  <div style={{ fontSize: 12, color: "#6b7280" }}>{med.strength}</div>
                </div>
                <div style={{ display: "flex", gap: 4 }}>
                  {med.is_high_alert && (
                    <span
                      style={{
                        background: "#fecaca",
                        color: "#991b1b",
                        padding: "2px 6px",
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 600,
                      }}
                    >
                      HIGH ALERT
                    </span>
                  )}
                  {med.is_controlled && (
                    <span
                      style={{
                        background: "#dbeafe",
                        color: "#1e40af",
                        padding: "2px 6px",
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 600,
                      }}
                    >
                      CONTROLLED
                    </span>
                  )}
                </div>
              </div>
              {med.brand_names.length > 0 && (
                <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4 }}>
                  Brand: {med.brand_names.join(", ")}
                </div>
              )}
              <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                <span
                  style={{
                    background: "#f3f4f6",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 11,
                    color: "#374151",
                  }}
                >
                  {med.category}
                </span>
                <span
                  style={{
                    background: "#f3f4f6",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 11,
                    color: "#374151",
                  }}
                >
                  {med.form}
                </span>
                <span
                  style={{
                    background: "#f3f4f6",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 11,
                    color: "#374151",
                  }}
                >
                  {med.route}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "#6b7280", marginTop: 8 }}>
                RxNorm: {med.rxnorm_code}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatsTab() {
  const statsQ = useQuery({
    queryKey: ["medication-stats"],
    queryFn: fetchMedicationStats,
  });

  if (statsQ.isLoading) {
    return <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>Loading statistics...</div>;
  }

  const stats = statsQ.data;

  return (
    <div>
      {/* Overview Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 24 }}>
        <div style={{ padding: 20, background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", borderRadius: 12, color: "white" }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{stats?.prescriptions.active || 0}</div>
          <div style={{ fontSize: 13, opacity: 0.9 }}>Active Prescriptions</div>
        </div>
        <div style={{ padding: 20, background: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)", borderRadius: 12, color: "white" }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{stats?.prescriptions.pending_review || 0}</div>
          <div style={{ fontSize: 13, opacity: 0.9 }}>Pending Review</div>
        </div>
        <div style={{ padding: 20, background: "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)", borderRadius: 12, color: "white" }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{stats?.prescriptions.high_alert_active || 0}</div>
          <div style={{ fontSize: 13, opacity: 0.9 }}>High-Alert Active</div>
        </div>
        <div style={{ padding: 20, background: "linear-gradient(135deg, #059669 0%, #047857 100%)", borderRadius: 12, color: "white" }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{stats?.administrations_today.given || 0}</div>
          <div style={{ fontSize: 13, opacity: 0.9 }}>Given Today</div>
        </div>
      </div>

      {/* Today's Administration Summary */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={{ padding: 20, border: "1px solid #e5e7eb", borderRadius: 12 }}>
          <h4 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>Today's Administrations</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#6b7280" }}>Due Now</span>
              <span style={{ fontWeight: 600, color: "#f59e0b" }}>{stats?.administrations_today.due_now || 0}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#6b7280" }}>Given</span>
              <span style={{ fontWeight: 600, color: "#059669" }}>{stats?.administrations_today.given || 0}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#6b7280" }}>Missed/Not Given</span>
              <span style={{ fontWeight: 600, color: "#dc2626" }}>{stats?.administrations_today.missed || 0}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#6b7280" }}>Remaining Scheduled</span>
              <span style={{ fontWeight: 600 }}>{stats?.administrations_today.total_scheduled || 0}</span>
            </div>
          </div>
        </div>

        <div style={{ padding: 20, border: "1px solid #e5e7eb", borderRadius: 12 }}>
          <h4 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>Active by Category</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {stats?.category_breakdown.slice(0, 6).map((item) => (
              <div key={item.category} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#6b7280", fontSize: 13 }}>
                  {item.category?.charAt(0).toUpperCase() + item.category?.slice(1) || "Other"}
                </span>
                <span
                  style={{
                    background: "#e5e7eb",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  {item.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Catalog Summary */}
      <div style={{ marginTop: 16, padding: 16, background: "#f3f4f6", borderRadius: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#6b7280" }}>Total Medications in Catalog</span>
          <span style={{ fontWeight: 600, fontSize: 18 }}>{stats?.catalog_size || 0}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
          <span style={{ color: "#6b7280" }}>Controlled Substances Active</span>
          <span style={{ fontWeight: 600, color: "#1e40af" }}>{stats?.prescriptions.controlled_active || 0}</span>
        </div>
      </div>
    </div>
  );
}
