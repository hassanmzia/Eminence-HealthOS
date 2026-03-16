import { useState } from "react";

export function PatientPicker(props: {
  patientRef: string;
  onChange: (v: string) => void;
}) {
  const [draft, setDraft] = useState(props.patientRef);

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
      <label style={{ fontSize: 12, color: "#555" }}>Patient ref (FHIR)</label>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder='e.g. 1201 or Patient/1201 (blank for all)'
        style={{ padding: "8px 10px", border: "1px solid #ddd", borderRadius: 8, width: 260 }}
      />
      <button
        onClick={() => props.onChange(draft.trim())}
        style={{ padding: "8px 12px", borderRadius: 10, border: "1px solid #ddd", background: "#fafafa", cursor: "pointer" }}
      >
        Load
      </button>
    </div>
  );
}

