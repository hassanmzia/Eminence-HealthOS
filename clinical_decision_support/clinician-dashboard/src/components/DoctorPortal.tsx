import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPatients, type Patient } from "../lib/patientApi";
import {
  fetchPatientClinicalSummary,
  fetchEncounters,
  fetchNotes,
  createEncounter,
  createNote,
  signNote,
  type PatientClinicalSummary,
  type Encounter,
  type ClinicalNote,
  ENCOUNTER_TYPES,
  NOTE_TYPES,
} from "../lib/clinicalApi";
import { fetchRecommendations } from "../lib/api";
import { fetchObservations, normalizeVitals } from "../lib/fhirApi";
import { RecommendationsPanel } from "./RecommendationsPanel";
import { ClinicalAssessmentPanel } from "./ClinicalAssessmentPanel";

export function DoctorPortal() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [showNewEncounter, setShowNewEncounter] = useState(false);
  const [showNewNote, setShowNewNote] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "notes" | "encounters" | "recommendations" | "assessment">("overview");

  // Fetch patients for search
  const patientsQuery = useQuery({
    queryKey: ["doctor-patients", search],
    queryFn: () => fetchPatients({ search: search || undefined, status: "active", limit: 20 }),
    enabled: search.length >= 2,
  });

  // Fetch clinical summary for selected patient
  const summaryQuery = useQuery({
    queryKey: ["clinical-summary", selectedPatient?.id],
    queryFn: () => fetchPatientClinicalSummary(selectedPatient!.id),
    enabled: !!selectedPatient,
  });

  // Fetch all notes for patient
  const notesQuery = useQuery({
    queryKey: ["patient-notes", selectedPatient?.id],
    queryFn: () => fetchNotes({ patient: selectedPatient!.id, limit: 50 }),
    enabled: !!selectedPatient && activeTab === "notes",
  });

  // Fetch all encounters for patient
  const encountersQuery = useQuery({
    queryKey: ["patient-encounters", selectedPatient?.id],
    queryFn: () => fetchEncounters({ patient: selectedPatient!.id, limit: 50 }),
    enabled: !!selectedPatient && activeTab === "encounters",
  });

  // Fetch AI recommendations for patient
  // Note: recommendations are stored with just the FHIR ID (e.g., "1201"), not "Patient/1201"
  const recommendationsQuery = useQuery({
    queryKey: ["patient-recommendations", selectedPatient?.fhir_id],
    queryFn: () => fetchRecommendations(selectedPatient?.fhir_id || undefined),
    enabled: !!selectedPatient && activeTab === "recommendations",
    refetchInterval: 30000,
  });

  // Fetch FHIR vitals for patient
  const fhirVitalsQuery = useQuery({
    queryKey: ["patient-fhir-vitals", selectedPatient?.fhir_id],
    queryFn: () => fetchObservations({
      patientRef: `Patient/${selectedPatient!.fhir_id}`,
      count: 200,
    }),
    enabled: !!selectedPatient?.fhir_id && activeTab === "overview",
    refetchInterval: 30000,
  });

  // Normalize FHIR vitals to get latest values
  const latestFhirVitals = useMemo(() => {
    if (!fhirVitalsQuery.data) return null;
    const rows = normalizeVitals(fhirVitalsQuery.data);
    if (rows.length === 0) return null;

    // Get the most recent value for each vital type
    const latestByType: Record<string, typeof rows[0]> = {};
    for (const row of rows) {
      if (!latestByType[row.loinc] || row.time > latestByType[row.loinc].time) {
        latestByType[row.loinc] = row;
      }
    }

    // Map LOINC codes to vital names
    const hr = latestByType["8867-4"]; // Heart Rate
    const spo2 = latestByType["59408-5"]; // SpO2
    const temp = latestByType["8310-5"]; // Temperature
    const rr = latestByType["9279-1"]; // Respiratory Rate
    const bp = latestByType["85354-9"]; // Blood Pressure
    const gluc = latestByType["2339-0"]; // Glucose
    const ecg = latestByType["8601-7"]; // ECG

    const mostRecent = rows[rows.length - 1];

    return {
      heart_rate: hr?.value ?? undefined,
      oxygen_saturation: spo2?.value ?? undefined,
      temperature: temp?.value ?? undefined,
      respiratory_rate: rr?.value ?? undefined,
      blood_pressure: bp ? `${bp.bp_sys}/${bp.bp_dia}` : undefined,
      glucose: gluc?.value ?? undefined,
      ecg_rhythm: ecg?.ecg_data?.rhythm ?? undefined,
      ecg_interpretation: ecg?.ecg_data?.interpretation ?? undefined,
      ecg_findings: ecg?.ecg_data?.findings ?? undefined,
      recorded_at: mostRecent?.time,
    };
  }, [fhirVitalsQuery.data]);

  const cardStyle = { border: "1px solid #eee", borderRadius: 12, padding: 16, marginBottom: 16 };
  const tabStyle = (active: boolean) => ({
    padding: "8px 16px",
    border: "none",
    borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
    background: "transparent",
    color: active ? "#2563eb" : "#666",
    cursor: "pointer",
    fontWeight: active ? 600 : 400,
  });

  return (
    <div className="doctor-portal-grid" style={{ padding: 16, display: "grid", gridTemplateColumns: "300px 1fr", gap: 16, minHeight: "calc(100vh - 150px)" }}>
      {/* Left Panel - Patient Search */}
      <div style={{ ...cardStyle, height: "fit-content", position: "sticky", top: 16 }}>
        <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Patient Search</h3>
        <input
          type="text"
          placeholder="Search by name, MRN..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", marginBottom: 12 }}
        />

        <div style={{ maxHeight: 400, overflow: "auto" }}>
          {patientsQuery.isLoading && <div style={{ color: "#666", fontSize: 13 }}>Searching...</div>}

          {patientsQuery.data?.results.map((patient) => (
            <div
              key={patient.id}
              onClick={() => {
                setSelectedPatient(patient);
                setActiveTab("overview");
              }}
              style={{
                padding: 10,
                borderRadius: 8,
                marginBottom: 6,
                cursor: "pointer",
                background: selectedPatient?.id === patient.id ? "#eff6ff" : "#f9fafb",
                border: selectedPatient?.id === patient.id ? "1px solid #2563eb" : "1px solid transparent",
              }}
            >
              <div style={{ fontWeight: 500 }}>{patient.first_name} {patient.last_name}</div>
              <div style={{ fontSize: 12, color: "#666" }}>MRN: {patient.mrn} | DOB: {patient.date_of_birth}</div>
            </div>
          ))}

          {search.length >= 2 && patientsQuery.data?.results.length === 0 && (
            <div style={{ color: "#666", fontSize: 13, textAlign: "center", padding: 20 }}>No patients found</div>
          )}

          {search.length < 2 && (
            <div style={{ color: "#999", fontSize: 13, textAlign: "center", padding: 20 }}>
              Type at least 2 characters to search
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Patient Details */}
      <div>
        {!selectedPatient ? (
          <div style={{ ...cardStyle, textAlign: "center", padding: 60 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🩺</div>
            <h3 style={{ margin: 0, color: "#333" }}>Doctor Portal</h3>
            <p style={{ color: "#666", marginTop: 8 }}>Search and select a patient to view their clinical information</p>
          </div>
        ) : (
          <>
            {/* Patient Header */}
            <div style={{ ...cardStyle, background: "#f8fafc" }}>
              <div className="patient-header-layout" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h2 style={{ margin: 0 }}>{selectedPatient.first_name} {selectedPatient.last_name}</h2>
                  <div className="patient-meta-row" style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 14, color: "#666" }}>
                    <span>MRN: <strong>{selectedPatient.mrn}</strong></span>
                    <span>DOB: <strong>{selectedPatient.date_of_birth}</strong></span>
                    <span>Age: <strong>{summaryQuery.data?.age || "—"}</strong></span>
                    <span>Gender: <strong>{selectedPatient.gender}</strong></span>
                  </div>
                </div>
                <div className="patient-header-actions" style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() => setShowNewEncounter(true)}
                    style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#059669", color: "white", cursor: "pointer" }}
                  >
                    + New Encounter
                  </button>
                  <button
                    onClick={() => setShowNewNote(true)}
                    style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: "pointer" }}
                  >
                    + New Note
                  </button>
                </div>
              </div>

              {/* Allergies & Medications Banner */}
              {(summaryQuery.data?.allergies?.length || summaryQuery.data?.medications?.length) && (
                <div className="allergies-meds-row" style={{ display: "flex", gap: 16, marginTop: 12 }}>
                  {summaryQuery.data?.allergies?.length ? (
                    <div style={{ padding: "6px 12px", background: "#fee2e2", borderRadius: 6, fontSize: 13 }}>
                      <strong style={{ color: "#dc2626" }}>Allergies:</strong>{" "}
                      <span style={{ color: "#7f1d1d" }}>{summaryQuery.data.allergies.join(", ")}</span>
                    </div>
                  ) : null}
                  {summaryQuery.data?.medications?.length ? (
                    <div style={{ padding: "6px 12px", background: "#dbeafe", borderRadius: 6, fontSize: 13 }}>
                      <strong style={{ color: "#1d4ed8" }}>Medications:</strong>{" "}
                      <span style={{ color: "#1e3a8a" }}>{summaryQuery.data.medications.join(", ")}</span>
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            {/* Tabs */}
            <div className="tabs-container" style={{ borderBottom: "1px solid #eee", marginBottom: 16 }}>
              <button style={tabStyle(activeTab === "overview")} onClick={() => setActiveTab("overview")}>Overview</button>
              <button style={tabStyle(activeTab === "notes")} onClick={() => setActiveTab("notes")}>Clinical Notes</button>
              <button style={tabStyle(activeTab === "encounters")} onClick={() => setActiveTab("encounters")}>Encounters</button>
              <button style={tabStyle(activeTab === "recommendations")} onClick={() => setActiveTab("recommendations")}>AI Recommendations</button>
              <button style={{ ...tabStyle(activeTab === "assessment"), background: activeTab === "assessment" ? "#eff6ff" : "transparent" }} onClick={() => setActiveTab("assessment")}>AI Assessment</button>
            </div>

            {/* Tab Content */}
            {activeTab === "overview" && summaryQuery.data && (
              <PatientOverview summary={summaryQuery.data} fhirVitals={latestFhirVitals} />
            )}

            {activeTab === "notes" && (
              <NotesTab
                notes={notesQuery.data?.results || []}
                isLoading={notesQuery.isLoading}
                onSign={(noteId) => {
                  signNote(noteId).then(() => {
                    queryClient.invalidateQueries({ queryKey: ["patient-notes"] });
                    queryClient.invalidateQueries({ queryKey: ["clinical-summary"] });
                  });
                }}
              />
            )}

            {activeTab === "encounters" && (
              <EncountersTab
                encounters={encountersQuery.data?.results || []}
                isLoading={encountersQuery.isLoading}
              />
            )}

            {activeTab === "recommendations" && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <div style={{ fontSize: 13, color: "#666" }}>
                    {selectedPatient?.fhir_id
                      ? `Recommendations for Patient/${selectedPatient.fhir_id}`
                      : "Patient not synced to FHIR - recommendations may be limited"}
                  </div>
                  <button
                    onClick={() => recommendationsQuery.refetch()}
                    disabled={recommendationsQuery.isFetching}
                    style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #ddd", background: "#fafafa", cursor: "pointer", fontSize: 12 }}
                  >
                    {recommendationsQuery.isFetching ? "Refreshing..." : "Refresh"}
                  </button>
                </div>
                <RecommendationsPanel items={recommendationsQuery.data ?? []} />
              </div>
            )}

            {activeTab === "assessment" && (
              <ClinicalAssessmentPanel
                patientId={String(selectedPatient.id)}
                fhirId={selectedPatient.fhir_id}
              />
            )}

            {/* New Encounter Modal */}
            {showNewEncounter && (
              <NewEncounterModal
                patientId={selectedPatient.id}
                onClose={() => setShowNewEncounter(false)}
                onSuccess={() => {
                  setShowNewEncounter(false);
                  queryClient.invalidateQueries({ queryKey: ["patient-encounters"] });
                  queryClient.invalidateQueries({ queryKey: ["clinical-summary"] });
                }}
              />
            )}

            {/* New Note Modal */}
            {showNewNote && (
              <NewNoteModal
                patientId={selectedPatient.id}
                encounters={summaryQuery.data?.active_encounters || []}
                onClose={() => setShowNewNote(false)}
                onSuccess={() => {
                  setShowNewNote(false);
                  queryClient.invalidateQueries({ queryKey: ["patient-notes"] });
                  queryClient.invalidateQueries({ queryKey: ["clinical-summary"] });
                }}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// FHIR Vitals type
type FhirVitals = {
  heart_rate?: number;
  oxygen_saturation?: number;
  temperature?: number;
  respiratory_rate?: number;
  blood_pressure?: string;
  glucose?: number;
  ecg_rhythm?: string;
  ecg_interpretation?: string;
  ecg_findings?: string[];
  recorded_at?: string;
} | null;

// Patient Overview Component
function PatientOverview({ summary, fhirVitals }: { summary: PatientClinicalSummary; fhirVitals?: FhirVitals }) {
  const cardStyle = { border: "1px solid #eee", borderRadius: 12, padding: 16, marginBottom: 16 };

  // Prefer FHIR vitals over backend vitals
  const vitals = fhirVitals || summary.latest_vitals;
  const hasVitals = vitals && (vitals.heart_rate || vitals.blood_pressure || vitals.oxygen_saturation || vitals.temperature || vitals.respiratory_rate || vitals.glucose || vitals.ecg_rhythm);

  return (
    <div className="patient-overview-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      {/* Latest Vitals */}
      <div style={cardStyle}>
        <h4 style={{ marginTop: 0, marginBottom: 12 }}>
          Latest Vitals
          {fhirVitals && <span style={{ fontSize: 11, color: "#2563eb", marginLeft: 8 }}>(from FHIR)</span>}
        </h4>
        {hasVitals ? (
          <div className="vitals-inner-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {vitals.heart_rate && (
              <VitalItem label="Heart Rate" value={`${vitals.heart_rate} bpm`} />
            )}
            {vitals.blood_pressure && (
              <VitalItem label="Blood Pressure" value={`${vitals.blood_pressure} mmHg`} />
            )}
            {vitals.oxygen_saturation && (
              <VitalItem label="SpO2" value={`${vitals.oxygen_saturation}%`} />
            )}
            {vitals.temperature && (
              <VitalItem label="Temperature" value={`${vitals.temperature}°C`} />
            )}
            {vitals.respiratory_rate && (
              <VitalItem label="Resp. Rate" value={`${vitals.respiratory_rate} /min`} />
            )}
            {vitals.glucose && (
              <VitalItem label="Blood Sugar" value={`${vitals.glucose} mg/dL`} />
            )}
            {vitals.ecg_rhythm && (
              <div style={{ gridColumn: "1 / -1", padding: 8, background: vitals.ecg_findings?.length ? "#fef3c7" : "#f0fdf4", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "#666" }}>ECG</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#333" }}>{vitals.ecg_rhythm}</div>
                {vitals.ecg_interpretation && (
                  <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>{vitals.ecg_interpretation}</div>
                )}
                {vitals.ecg_findings && vitals.ecg_findings.length > 0 && (
                  <div style={{ fontSize: 11, color: "#d97706", marginTop: 4 }}>
                    Findings: {vitals.ecg_findings.join(", ")}
                  </div>
                )}
              </div>
            )}
            {vitals.recorded_at && (
              <div style={{ gridColumn: "1 / -1", fontSize: 11, color: "#999", marginTop: 8 }}>
                Recorded: {new Date(vitals.recorded_at).toLocaleString()}
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: "#999", fontSize: 13 }}>No vitals recorded. Start the IoT simulator to generate vitals.</div>
        )}
      </div>

      {/* Active Diagnoses */}
      <div style={cardStyle}>
        <h4 style={{ marginTop: 0, marginBottom: 12 }}>Active Diagnoses</h4>
        {summary.active_diagnoses.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {summary.active_diagnoses.map((dx) => (
              <div key={dx.id} style={{ padding: 8, background: "#f9fafb", borderRadius: 6 }}>
                <div style={{ fontWeight: 500, fontSize: 13 }}>
                  {dx.is_primary && <span style={{ color: "#dc2626" }}>● </span>}
                  {dx.icd10_code}: {dx.description}
                </div>
                {dx.severity && <div style={{ fontSize: 11, color: "#666" }}>Severity: {dx.severity}</div>}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: "#999", fontSize: 13 }}>No active diagnoses</div>
        )}
      </div>

      {/* Active Encounters */}
      <div style={cardStyle}>
        <h4 style={{ marginTop: 0, marginBottom: 12 }}>Active Encounters</h4>
        {summary.active_encounters.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {summary.active_encounters.map((enc) => (
              <div key={enc.id} style={{ padding: 8, background: "#f9fafb", borderRadius: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 500, fontSize: 13 }}>
                    {ENCOUNTER_TYPES.find(t => t.value === enc.encounter_type)?.label || enc.encounter_type}
                  </span>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 999,
                    background: enc.status === "in_progress" ? "#dcfce7" : "#f3f4f6",
                    color: enc.status === "in_progress" ? "#166534" : "#666",
                    fontSize: 11,
                    fontWeight: 600,
                  }}>
                    {enc.status.toUpperCase().replace("_", " ")}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
                  {new Date(enc.start_time).toLocaleDateString()} • {enc.attending_physician || "No physician assigned"}
                </div>
                {enc.chief_complaint && (
                  <div style={{ fontSize: 12, color: "#333", marginTop: 4 }}>CC: {enc.chief_complaint}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: "#999", fontSize: 13 }}>No active encounters</div>
        )}
      </div>

      {/* Recent Notes */}
      <div style={cardStyle}>
        <h4 style={{ marginTop: 0, marginBottom: 12 }}>Recent Notes</h4>
        {summary.recent_notes.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {summary.recent_notes.slice(0, 5).map((note) => (
              <div key={note.id} style={{ padding: 8, background: "#f9fafb", borderRadius: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{note.title}</span>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 999,
                    background: note.status === "final" ? "#dcfce7" : "#fef3c7",
                    color: note.status === "final" ? "#166534" : "#92400e",
                    fontSize: 11,
                    fontWeight: 600,
                  }}>
                    {note.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
                  {NOTE_TYPES.find(t => t.value === note.note_type)?.label} • {note.author} • {new Date(note.note_datetime).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: "#999", fontSize: 13 }}>No clinical notes</div>
        )}
      </div>

      {/* Active Care Plans */}
      <div style={{ ...cardStyle, gridColumn: "1 / -1" }}>
        <h4 style={{ marginTop: 0, marginBottom: 12 }}>Active Care Plans</h4>
        {summary.active_care_plans.length > 0 ? (
          <div className="care-plans-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {summary.active_care_plans.map((plan) => (
              <div key={plan.id} style={{ padding: 12, background: "#f0fdf4", borderRadius: 8, border: "1px solid #bbf7d0" }}>
                <div style={{ fontWeight: 500 }}>{plan.title}</div>
                <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
                  {plan.category} • Created by {plan.created_by}
                </div>
                <div style={{ fontSize: 12, color: "#333", marginTop: 4 }}>
                  {plan.start_date} {plan.end_date ? `to ${plan.end_date}` : "- Ongoing"}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: "#999", fontSize: 13 }}>No active care plans</div>
        )}
      </div>
    </div>
  );
}

function VitalItem({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: 8, background: "#f9fafb", borderRadius: 6, textAlign: "center" }}>
      <div style={{ fontSize: 11, color: "#666" }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: "#333" }}>{value}</div>
    </div>
  );
}

// Notes Tab Component
function NotesTab({ notes, isLoading, onSign }: { notes: ClinicalNote[]; isLoading: boolean; onSign: (id: number) => void }) {
  const [expandedNote, setExpandedNote] = useState<number | null>(null);

  if (isLoading) return <div style={{ padding: 20, textAlign: "center", color: "#666" }}>Loading notes...</div>;

  if (notes.length === 0) {
    return <div style={{ padding: 40, textAlign: "center", color: "#666" }}>No clinical notes found</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {notes.map((note) => (
        <div
          key={note.id}
          style={{ border: "1px solid #eee", borderRadius: 12, overflow: "hidden" }}
        >
          <div
            onClick={() => setExpandedNote(expandedNote === note.id ? null : note.id)}
            style={{
              padding: 16,
              background: "#f9fafb",
              cursor: "pointer",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontWeight: 500 }}>{note.title}</div>
              <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
                {NOTE_TYPES.find(t => t.value === note.note_type)?.label} • {note.author} ({note.author_role || "—"}) • {new Date(note.note_datetime).toLocaleString()}
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{
                padding: "4px 12px",
                borderRadius: 999,
                background: note.status === "final" ? "#dcfce7" : "#fef3c7",
                color: note.status === "final" ? "#166534" : "#92400e",
                fontSize: 12,
                fontWeight: 600,
              }}>
                {note.status.toUpperCase()}
              </span>
              <span style={{ fontSize: 18 }}>{expandedNote === note.id ? "▼" : "▶"}</span>
            </div>
          </div>

          {expandedNote === note.id && (
            <div style={{ padding: 16 }}>
              {note.note_type === "soap" ? (
                <div style={{ display: "grid", gap: 12 }}>
                  {note.subjective && <SOAPSection title="Subjective" content={note.subjective} />}
                  {note.objective && <SOAPSection title="Objective" content={note.objective} />}
                  {note.assessment && <SOAPSection title="Assessment" content={note.assessment} />}
                  {note.plan && <SOAPSection title="Plan" content={note.plan} />}
                </div>
              ) : (
                <div style={{ whiteSpace: "pre-wrap" }}>{note.content || "No content"}</div>
              )}

              {note.status === "draft" && (
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #eee" }}>
                  <button
                    onClick={(e) => { e.stopPropagation(); onSign(note.id); }}
                    style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#059669", color: "white", cursor: "pointer" }}
                  >
                    Sign Note
                  </button>
                </div>
              )}

              {note.signed_datetime && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#666" }}>
                  Signed: {new Date(note.signed_datetime).toLocaleString()}
                  {note.co_signer && ` (Co-signed by: ${note.co_signer})`}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function SOAPSection({ title, content }: { title: string; content: string }) {
  return (
    <div>
      <div style={{ fontWeight: 600, fontSize: 13, color: "#2563eb", marginBottom: 4 }}>{title}</div>
      <div style={{ whiteSpace: "pre-wrap", fontSize: 14 }}>{content}</div>
    </div>
  );
}

// Encounters Tab Component
function EncountersTab({ encounters, isLoading }: { encounters: Encounter[]; isLoading: boolean }) {
  if (isLoading) return <div style={{ padding: 20, textAlign: "center", color: "#666" }}>Loading encounters...</div>;

  if (encounters.length === 0) {
    return <div style={{ padding: 40, textAlign: "center", color: "#666" }}>No encounters found</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {encounters.map((enc) => (
        <div key={enc.id} style={{ border: "1px solid #eee", borderRadius: 12, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ fontWeight: 500, fontSize: 15 }}>
                {ENCOUNTER_TYPES.find(t => t.value === enc.encounter_type)?.label || enc.encounter_type}
              </div>
              <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
                {new Date(enc.start_time).toLocaleString()}
                {enc.end_time && ` - ${new Date(enc.end_time).toLocaleString()}`}
              </div>
            </div>
            <span style={{
              padding: "4px 12px",
              borderRadius: 999,
              background: enc.status === "completed" ? "#dcfce7" :
                         enc.status === "in_progress" ? "#dbeafe" :
                         enc.status === "cancelled" ? "#fee2e2" : "#f3f4f6",
              color: enc.status === "completed" ? "#166534" :
                     enc.status === "in_progress" ? "#1d4ed8" :
                     enc.status === "cancelled" ? "#dc2626" : "#666",
              fontSize: 12,
              fontWeight: 600,
            }}>
              {enc.status.toUpperCase().replace("_", " ")}
            </span>
          </div>

          {enc.chief_complaint && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: "#666" }}>Chief Complaint</div>
              <div style={{ fontSize: 14 }}>{enc.chief_complaint}</div>
            </div>
          )}

          <div className="encounter-details-row" style={{ display: "flex", gap: 16, marginTop: 12, fontSize: 13, color: "#666" }}>
            {enc.attending_physician && <span>Physician: {enc.attending_physician}</span>}
            {enc.facility && <span>Facility: {enc.facility}</span>}
            {enc.department && <span>Department: {enc.department}</span>}
            {enc.room && <span>Room: {enc.room}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// New Encounter Modal
function NewEncounterModal({ patientId, onClose, onSuccess }: { patientId: number; onClose: () => void; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    encounter_type: "ambulatory",
    priority: "routine",
    facility: "",
    department: "",
    attending_physician: "",
    chief_complaint: "",
  });

  const mutation = useMutation({
    mutationFn: () => createEncounter({
      patient: patientId,
      ...formData,
      start_time: new Date().toISOString(),
      status: "in_progress",
    }),
    onSuccess,
  });

  const inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", fontSize: 14 };

  return (
    <div className="modal-overlay" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
      <div className="modal-content" style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 500, padding: 24 }}>
        <h3 style={{ marginTop: 0 }}>Start New Encounter</h3>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="form-grid-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Type</label>
              <select value={formData.encounter_type} onChange={(e) => setFormData({ ...formData, encounter_type: e.target.value })} style={inputStyle}>
                {ENCOUNTER_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Priority</label>
              <select value={formData.priority} onChange={(e) => setFormData({ ...formData, priority: e.target.value })} style={inputStyle}>
                <option value="routine">Routine</option>
                <option value="urgent">Urgent</option>
                <option value="emergency">Emergency</option>
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Attending Physician</label>
            <input value={formData.attending_physician} onChange={(e) => setFormData({ ...formData, attending_physician: e.target.value })} placeholder="Dr. Smith" style={inputStyle} />
          </div>

          <div className="form-grid-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Facility</label>
              <input value={formData.facility} onChange={(e) => setFormData({ ...formData, facility: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Department</label>
              <input value={formData.department} onChange={(e) => setFormData({ ...formData, department: e.target.value })} style={inputStyle} />
            </div>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Chief Complaint</label>
            <textarea
              value={formData.chief_complaint}
              onChange={(e) => setFormData({ ...formData, chief_complaint: e.target.value })}
              rows={3}
              placeholder="Primary reason for visit..."
              style={{ ...inputStyle, resize: "vertical" }}
            />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 24 }}>
          <button onClick={onClose} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}>Cancel</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#059669", color: "white", cursor: "pointer" }}
          >
            {mutation.isPending ? "Creating..." : "Start Encounter"}
          </button>
        </div>
      </div>
    </div>
  );
}

// New Note Modal
function NewNoteModal({ patientId, encounters, onClose, onSuccess }: { patientId: number; encounters: Encounter[]; onClose: () => void; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    note_type: "soap",
    title: "",
    encounter: "",
    author: "",
    author_role: "MD",
    subjective: "",
    objective: "",
    assessment: "",
    plan: "",
    content: "",
  });

  const mutation = useMutation({
    mutationFn: () => createNote({
      patient: patientId,
      encounter: formData.encounter ? parseInt(formData.encounter) : undefined,
      note_type: formData.note_type,
      title: formData.title || `${NOTE_TYPES.find(t => t.value === formData.note_type)?.label} - ${new Date().toLocaleDateString()}`,
      author: formData.author,
      author_role: formData.author_role,
      subjective: formData.subjective,
      objective: formData.objective,
      assessment: formData.assessment,
      plan: formData.plan,
      content: formData.content,
      note_datetime: new Date().toISOString(),
      status: "draft",
    }),
    onSuccess,
  });

  const inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", fontSize: 14 };
  const isSOAP = formData.note_type === "soap";

  return (
    <div className="modal-overlay" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "flex-start", padding: 40, overflow: "auto", zIndex: 1000 }}>
      <div className="modal-content" style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 700, padding: 24 }}>
        <h3 style={{ marginTop: 0 }}>Create Clinical Note</h3>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="form-grid-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Note Type</label>
              <select value={formData.note_type} onChange={(e) => setFormData({ ...formData, note_type: e.target.value })} style={inputStyle}>
                {NOTE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Encounter (optional)</label>
              <select value={formData.encounter} onChange={(e) => setFormData({ ...formData, encounter: e.target.value })} style={inputStyle}>
                <option value="">No encounter</option>
                {encounters.map(enc => (
                  <option key={enc.id} value={enc.id}>
                    {enc.encounter_type} - {new Date(enc.start_time).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Title</label>
            <input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} placeholder="Note title..." style={inputStyle} />
          </div>

          <div className="form-grid-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Author *</label>
              <input value={formData.author} onChange={(e) => setFormData({ ...formData, author: e.target.value })} placeholder="Dr. Smith" required style={inputStyle} />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Role</label>
              <select value={formData.author_role} onChange={(e) => setFormData({ ...formData, author_role: e.target.value })} style={inputStyle}>
                <option value="MD">MD</option>
                <option value="DO">DO</option>
                <option value="NP">NP</option>
                <option value="PA">PA</option>
                <option value="RN">RN</option>
              </select>
            </div>
          </div>

          {isSOAP ? (
            <>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#2563eb" }}>Subjective</label>
                <textarea value={formData.subjective} onChange={(e) => setFormData({ ...formData, subjective: e.target.value })} rows={3} placeholder="Patient's symptoms and complaints..." style={{ ...inputStyle, resize: "vertical" }} />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#2563eb" }}>Objective</label>
                <textarea value={formData.objective} onChange={(e) => setFormData({ ...formData, objective: e.target.value })} rows={3} placeholder="Physical exam and test results..." style={{ ...inputStyle, resize: "vertical" }} />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#2563eb" }}>Assessment</label>
                <textarea value={formData.assessment} onChange={(e) => setFormData({ ...formData, assessment: e.target.value })} rows={3} placeholder="Diagnoses and clinical impressions..." style={{ ...inputStyle, resize: "vertical" }} />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#2563eb" }}>Plan</label>
                <textarea value={formData.plan} onChange={(e) => setFormData({ ...formData, plan: e.target.value })} rows={3} placeholder="Treatment plan and next steps..." style={{ ...inputStyle, resize: "vertical" }} />
              </div>
            </>
          ) : (
            <div>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Note Content</label>
              <textarea value={formData.content} onChange={(e) => setFormData({ ...formData, content: e.target.value })} rows={10} placeholder="Enter note content..." style={{ ...inputStyle, resize: "vertical" }} />
            </div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 24 }}>
          <button onClick={onClose} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}>Cancel</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !formData.author}
            style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: "pointer", opacity: !formData.author ? 0.5 : 1 }}
          >
            {mutation.isPending ? "Saving..." : "Save as Draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
