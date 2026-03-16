import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { importPatients, type ImportResult } from "../lib/patientApi";

interface PatientImportProps {
  onClose: () => void;
  onSuccess: () => void;
}

const SAMPLE_JSON = `{
  "patients": [
    {
      "first_name": "John",
      "last_name": "Doe",
      "date_of_birth": "1985-03-15",
      "gender": "male",
      "phone": "+15551234567",
      "email": "john.doe@example.com",
      "address_line1": "123 Main St",
      "city": "Springfield",
      "state": "IL",
      "postal_code": "62701",
      "allergies": ["Penicillin"],
      "medications": ["Lisinopril 10mg"],
      "medical_conditions": ["Hypertension"]
    },
    {
      "first_name": "Jane",
      "last_name": "Smith",
      "date_of_birth": "1990-07-22",
      "gender": "female",
      "phone": "+15559876543",
      "email": "jane.smith@example.com"
    }
  ]
}`;

export function PatientImport({ onClose, onSuccess }: PatientImportProps) {
  const [jsonText, setJsonText] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const importMutation = useMutation({
    mutationFn: importPatients,
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      if (data.imported > 0 && data.failed === 0) {
        setTimeout(() => onSuccess(), 2000);
      }
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setJsonText(event.target?.result as string);
        setParseError(null);
        setResult(null);
      };
      reader.readAsText(file);
    }
  };

  const handleImport = () => {
    setParseError(null);
    setResult(null);

    try {
      const data = JSON.parse(jsonText);
      if (!data.patients || !Array.isArray(data.patients)) {
        setParseError("JSON must have a 'patients' array");
        return;
      }
      importMutation.mutate(data.patients);
    } catch {
      setParseError("Invalid JSON format. Please check your input.");
    }
  };

  const loadSample = () => {
    setJsonText(SAMPLE_JSON);
    setParseError(null);
    setResult(null);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "flex-start", padding: 40, overflow: "auto", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 800, maxHeight: "90vh", overflow: "auto" }}>
        <div style={{ padding: 20, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>Import Patients from JSON</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer" }}>&times;</button>
        </div>

        <div style={{ padding: 20 }}>
          {/* File Upload */}
          <div style={{ marginBottom: 20 }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileSelect}
              style={{ display: "none" }}
            />
            <div style={{ display: "flex", gap: 12 }}>
              <button
                onClick={() => fileInputRef.current?.click()}
                style={{ padding: "10px 20px", borderRadius: 8, border: "1px solid #ddd", background: "#f5f5f5", cursor: "pointer" }}
              >
                Upload JSON File
              </button>
              <button
                onClick={loadSample}
                style={{ padding: "10px 20px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}
              >
                Load Sample Data
              </button>
            </div>
          </div>

          {/* JSON Editor */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", marginBottom: 8, fontSize: 14, fontWeight: 500 }}>
              JSON Data
            </label>
            <textarea
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                setParseError(null);
                setResult(null);
              }}
              placeholder='{"patients": [...]}'
              style={{
                width: "100%",
                height: 300,
                padding: 12,
                borderRadius: 8,
                border: "1px solid #ddd",
                fontFamily: "monospace",
                fontSize: 13,
                resize: "vertical",
              }}
            />
          </div>

          {/* Error Display */}
          {parseError && (
            <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c", marginBottom: 20 }}>
              {parseError}
            </div>
          )}

          {importMutation.error && (
            <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c", marginBottom: 20 }}>
              Import failed. Please check your data and try again.
            </div>
          )}

          {/* Results Display */}
          {result && (
            <div style={{ marginBottom: 20 }}>
              <div style={{
                padding: 16,
                borderRadius: 8,
                background: result.failed === 0 ? "#e9f7ef" : result.imported === 0 ? "#ffe5e5" : "#fff3d6",
                marginBottom: 12
              }}>
                <div style={{ fontWeight: 600, marginBottom: 8 }}>
                  Import Complete
                </div>
                <div style={{ display: "flex", gap: 20 }}>
                  <div>
                    <span style={{ color: "#1f7a3a", fontWeight: 600 }}>{result.imported}</span> imported successfully
                  </div>
                  <div>
                    <span style={{ color: "#9b1c1c", fontWeight: 600 }}>{result.failed}</span> failed
                  </div>
                </div>
              </div>

              {result.created.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>Created Patients:</div>
                  <div style={{ maxHeight: 150, overflow: "auto", border: "1px solid #eee", borderRadius: 8 }}>
                    {result.created.map((p, i) => (
                      <div key={i} style={{ padding: "8px 12px", borderBottom: "1px solid #eee", fontSize: 13 }}>
                        <strong>{p.mrn}</strong> - {p.name}
                        {p.fhir_id && <span style={{ color: "#666", marginLeft: 8 }}>(FHIR: {p.fhir_id})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.errors.length > 0 && (
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8, color: "#9b1c1c" }}>Errors:</div>
                  <div style={{ maxHeight: 150, overflow: "auto", border: "1px solid #ffe5e5", borderRadius: 8, background: "#fff9f9" }}>
                    {result.errors.map((err, i) => (
                      <div key={i} style={{ padding: "8px 12px", borderBottom: "1px solid #ffe5e5", fontSize: 13 }}>
                        <strong>Row {err.index + 1}:</strong> {err.error || JSON.stringify(err.errors)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Format Help */}
          <details style={{ marginBottom: 20 }}>
            <summary style={{ cursor: "pointer", fontSize: 14, color: "#666" }}>JSON Format Help</summary>
            <div style={{ marginTop: 12, padding: 12, background: "#f9f9f9", borderRadius: 8, fontSize: 13 }}>
              <p style={{ margin: "0 0 8px 0" }}><strong>Required fields:</strong> first_name, last_name, date_of_birth</p>
              <p style={{ margin: "0 0 8px 0" }}><strong>Date format:</strong> YYYY-MM-DD</p>
              <p style={{ margin: "0 0 8px 0" }}><strong>Gender options:</strong> male, female, other, unknown</p>
              <p style={{ margin: 0 }}><strong>Array fields:</strong> allergies, medications, medical_conditions (comma-separated values)</p>
            </div>
          </details>

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, paddingTop: 16, borderTop: "1px solid #eee" }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: "10px 20px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}
            >
              {result && result.imported > 0 ? "Done" : "Cancel"}
            </button>
            <button
              onClick={handleImport}
              disabled={!jsonText || importMutation.isPending}
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border: "none",
                background: "#2563eb",
                color: "white",
                cursor: !jsonText || importMutation.isPending ? "not-allowed" : "pointer",
                opacity: !jsonText || importMutation.isPending ? 0.7 : 1,
              }}
            >
              {importMutation.isPending ? "Importing..." : "Import Patients"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
