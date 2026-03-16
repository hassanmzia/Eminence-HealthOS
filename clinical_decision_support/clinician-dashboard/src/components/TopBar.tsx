export function TopBar() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px", borderBottom: "1px solid #eee" }}>
      <div>
        <div style={{ fontWeight: 700, fontSize: 18 }}>Clinician Dashboard</div>
        <div style={{ color: "#666", fontSize: 12 }}>Vitals + AI Recommendations (FHIR-backed)</div>
      </div>
      <div style={{ display: "flex", gap: 10, fontSize: 12, color: "#444" }}>
        <span>FHIR: {import.meta.env.VITE_FHIR_BASE}</span>
      </div>
    </div>
  );
}

