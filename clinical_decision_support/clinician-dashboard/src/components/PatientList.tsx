import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPatients, deletePatient, resyncPatientToFhir, type Patient } from "../lib/patientApi";

interface PatientListProps {
  onSelectPatient: (patient: Patient) => void;
  onCreateNew: () => void;
  onImport: () => void;
}

export function PatientList({ onSelectPatient, onCreateNew, onImport }: PatientListProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("active");
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["patients", search, statusFilter],
    queryFn: () => fetchPatients({ search: search || undefined, status: statusFilter || undefined, limit: 100 }),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePatient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });

  const [syncingPatientId, setSyncingPatientId] = useState<number | null>(null);

  const resyncMutation = useMutation({
    mutationFn: resyncPatientToFhir,
    onSuccess: (result) => {
      setSyncingPatientId(null);
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ["patients"] });
      } else {
        alert(`Sync failed: ${result.error || "Unknown error"}`);
      }
    },
    onError: (error) => {
      setSyncingPatientId(null);
      alert(`Sync failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    },
  });

  const handleResync = (patient: Patient) => {
    setSyncingPatientId(patient.id);
    resyncMutation.mutate(patient.id);
  };

  const handleDelete = (patient: Patient) => {
    if (confirm(`Are you sure you want to deactivate patient ${patient.full_name || patient.first_name}?`)) {
      deleteMutation.mutate(patient.id);
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, { bg: string; fg: string }> = {
      active: { bg: "#e9f7ef", fg: "#1f7a3a" },
      inactive: { bg: "#f5f5f5", fg: "#666" },
      deceased: { bg: "#ffe5e5", fg: "#9b1c1c" },
    };
    const c = colors[status] || colors.inactive;
    return (
      <span style={{ padding: "2px 8px", borderRadius: 999, background: c.bg, color: c.fg, fontSize: 11, fontWeight: 600 }}>
        {status.toUpperCase()}
      </span>
    );
  };

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Patient Management</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onImport}
            style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #ddd", background: "#f5f5f5", cursor: "pointer" }}
          >
            Import JSON
          </button>
          <button
            onClick={onCreateNew}
            style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: "pointer" }}
          >
            + New Patient
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <input
          type="text"
          placeholder="Search by name or MRN..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd" }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd" }}
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="deceased">Deceased</option>
        </select>
      </div>

      {isLoading && <div style={{ padding: 20, textAlign: "center", color: "#666" }}>Loading patients...</div>}

      {error && (
        <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c" }}>
          Failed to load patients. Please try again.
        </div>
      )}

      {data && (
        <>
          <div style={{ marginBottom: 12, fontSize: 13, color: "#666" }}>
            Showing {data.results.length} of {data.total} patients
          </div>

          <div className="table-responsive" style={{ border: "1px solid #eee", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#f9f9f9" }}>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>MRN</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>FHIR ID</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Name</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>DOB / Age</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Gender</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Contact</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Status</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((patient) => (
                  <tr key={patient.id} style={{ cursor: "pointer" }} onClick={() => onSelectPatient(patient)}>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", fontFamily: "monospace" }}>{patient.mrn}</td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                      {patient.fhir_id ? (
                        <span
                          style={{ fontFamily: "monospace", background: "#e0f2fe", padding: "2px 6px", borderRadius: 4, cursor: "pointer" }}
                          title="Click to copy Patient/{fhir_id}"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigator.clipboard.writeText(`Patient/${patient.fhir_id}`);
                            alert(`Copied: Patient/${patient.fhir_id}`);
                          }}
                        >
                          {patient.fhir_id}
                        </span>
                      ) : (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResync(patient);
                          }}
                          disabled={syncingPatientId === patient.id}
                          style={{
                            padding: "4px 10px",
                            borderRadius: 4,
                            border: "none",
                            background: syncingPatientId === patient.id ? "#e5e7eb" : "#3b82f6",
                            color: "white",
                            cursor: syncingPatientId === patient.id ? "not-allowed" : "pointer",
                            fontSize: 11,
                            fontWeight: 500,
                          }}
                        >
                          {syncingPatientId === patient.id ? "Syncing..." : "Sync to FHIR"}
                        </button>
                      )}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", fontWeight: 500 }}>
                      {patient.full_name || `${patient.first_name} ${patient.last_name}`}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                      {patient.date_of_birth}
                      <span style={{ color: "#666", marginLeft: 8 }}>({patient.age} yrs)</span>
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", textTransform: "capitalize" }}>{patient.gender}</td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", fontSize: 13 }}>
                      {patient.phone && <div>{patient.phone}</div>}
                      {patient.email && <div style={{ color: "#666" }}>{patient.email}</div>}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>{statusBadge(patient.status)}</td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectPatient(patient);
                          }}
                          style={{
                            padding: "6px 12px",
                            borderRadius: 6,
                            border: "1px solid #3b82f6",
                            background: "white",
                            color: "#3b82f6",
                            cursor: "pointer",
                            fontSize: 12,
                            fontWeight: 500,
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(patient);
                          }}
                          style={{
                            padding: "6px 12px",
                            borderRadius: 6,
                            border: "1px solid #ef4444",
                            background: "white",
                            color: "#ef4444",
                            cursor: "pointer",
                            fontSize: 12,
                            fontWeight: 500,
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ padding: 40, textAlign: "center", color: "#666" }}>
                      No patients found. Create a new patient or import from JSON.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
