import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assignDevice, type Device } from "../lib/deviceApi";
import { fetchPatients, type Patient } from "../lib/patientApi";

interface DeviceAssignmentProps {
  device: Device;
  onClose: () => void;
  onSuccess: () => void;
}

export function DeviceAssignment({ device, onClose, onSuccess }: DeviceAssignmentProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [assignedBy, setAssignedBy] = useState("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");

  const patientsQuery = useQuery({
    queryKey: ["patients", search],
    queryFn: () => fetchPatients({ search: search || undefined, status: "active", limit: 50 }),
  });

  const assignMutation = useMutation({
    mutationFn: () => assignDevice(device.id, {
      patient_id: selectedPatient!.id,
      assigned_by: assignedBy || undefined,
      reason: reason || undefined,
      notes: notes || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      onSuccess();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient) return;
    assignMutation.mutate();
  };

  const inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", fontSize: 14 };
  const labelStyle = { display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#333" } as const;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "flex-start", padding: 40, overflow: "auto", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 600, maxHeight: "90vh", overflow: "auto" }}>
        <div style={{ padding: 20, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0 }}>Assign Device to Patient</h2>
            <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
              {device.name} ({device.device_id})
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer" }}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: 20 }}>
          {assignMutation.error && (
            <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c", marginBottom: 20 }}>
              Failed to assign device. Please try again.
            </div>
          )}

          {/* Patient Search */}
          <div style={{ marginBottom: 24 }}>
            <label style={labelStyle}>Search Patient *</label>
            <input
              type="text"
              placeholder="Search by name, MRN, or DOB..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={inputStyle}
            />

            {/* Patient List */}
            <div style={{ marginTop: 12, border: "1px solid #eee", borderRadius: 8, maxHeight: 250, overflow: "auto" }}>
              {patientsQuery.isLoading && (
                <div style={{ padding: 20, textAlign: "center", color: "#666" }}>Loading patients...</div>
              )}

              {patientsQuery.data?.results.map((patient) => (
                <div
                  key={patient.id}
                  onClick={() => setSelectedPatient(patient)}
                  style={{
                    padding: 12,
                    borderBottom: "1px solid #eee",
                    cursor: "pointer",
                    background: selectedPatient?.id === patient.id ? "#e0f2fe" : "white",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500 }}>
                      {patient.first_name} {patient.last_name}
                    </div>
                    <div style={{ fontSize: 12, color: "#666" }}>
                      MRN: {patient.mrn} | DOB: {patient.date_of_birth}
                    </div>
                  </div>
                  {selectedPatient?.id === patient.id && (
                    <span style={{ color: "#2563eb", fontSize: 18 }}>✓</span>
                  )}
                </div>
              ))}

              {patientsQuery.data?.results.length === 0 && (
                <div style={{ padding: 20, textAlign: "center", color: "#666" }}>
                  No patients found. Try a different search.
                </div>
              )}
            </div>
          </div>

          {/* Selected Patient Display */}
          {selectedPatient && (
            <div style={{ marginBottom: 24, padding: 16, background: "#f0fdf4", borderRadius: 8, border: "1px solid #bbf7d0" }}>
              <div style={{ fontWeight: 600, color: "#166534", marginBottom: 4 }}>Selected Patient</div>
              <div style={{ fontSize: 15, fontWeight: 500 }}>
                {selectedPatient.first_name} {selectedPatient.last_name}
              </div>
              <div style={{ fontSize: 13, color: "#666" }}>
                MRN: {selectedPatient.mrn} | DOB: {selectedPatient.date_of_birth} | {selectedPatient.gender}
              </div>
            </div>
          )}

          {/* Assignment Details */}
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333", fontSize: 15 }}>Assignment Details</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={labelStyle}>Assigned By</label>
                <input
                  type="text"
                  value={assignedBy}
                  onChange={(e) => setAssignedBy(e.target.value)}
                  placeholder="Your name or staff ID"
                  style={inputStyle}
                />
              </div>
              <div>
                <label style={labelStyle}>Reason for Assignment</label>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g., Continuous vitals monitoring"
                  style={inputStyle}
                />
              </div>
              <div>
                <label style={labelStyle}>Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Additional notes..."
                  style={{ ...inputStyle, resize: "vertical" }}
                />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, paddingTop: 16, borderTop: "1px solid #eee" }}>
            <button type="button" onClick={onClose} style={{ padding: "10px 20px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedPatient || assignMutation.isPending}
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border: "none",
                background: selectedPatient ? "#2563eb" : "#ccc",
                color: "white",
                cursor: !selectedPatient || assignMutation.isPending ? "not-allowed" : "pointer",
                opacity: assignMutation.isPending ? 0.7 : 1,
              }}
            >
              {assignMutation.isPending ? "Assigning..." : "Assign Device"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
