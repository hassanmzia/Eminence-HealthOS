import type { Recommendation } from "../lib/api";

function badge(sev?: string) {
  const s = sev ?? "info";
  const bg = s === "critical" ? "#ffe5e5" : s === "warning" ? "#fff3d6" : "#e9f7ef";
  const fg = s === "critical" ? "#9b1c1c" : s === "warning" ? "#8a5a00" : "#1f7a3a";
  return { bg, fg, label: s.toUpperCase() };
}

export function RecommendationsPanel({ items }: { items: Recommendation[] }) {
  return (
    <div style={{ border: "1px solid #eee", borderRadius: 14, padding: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>AI Recommendations</div>

      {items.length === 0 ? (
        <div style={{ color: "#666", fontSize: 13 }}>No recommendations yet. Post vitals events and refresh.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {items.map((r) => {
            const b = badge(r.severity);
            return (
              <div key={r.id} style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div style={{ fontWeight: 700 }}>{r.title}</div>
                  <div style={{ padding: "2px 8px", borderRadius: 999, background: b.bg, color: b.fg, fontSize: 11, fontWeight: 700 }}>
                    {b.label}
                  </div>
                </div>
                <div style={{ color: "#555", marginTop: 6, fontSize: 13 }}>{r.summary}</div>

                {r.rationale ? (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ cursor: "pointer", fontSize: 12, color: "#444" }}>Why</summary>
                    <div style={{ marginTop: 6, fontSize: 12, color: "#333", whiteSpace: "pre-wrap" }}>{r.rationale}</div>
                  </details>
                ) : null}

                {r.evidence?.length ? (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ cursor: "pointer", fontSize: 12, color: "#444" }}>Evidence</summary>
                    <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
                      {r.evidence.map((e, idx) => (
                        <div key={idx} style={{ fontSize: 12 }}>
                          <div style={{ fontWeight: 700 }}>{e.source}</div>
                          <div style={{ color: "#333" }}>{e.snippet}</div>
                        </div>
                      ))}
                    </div>
                  </details>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

