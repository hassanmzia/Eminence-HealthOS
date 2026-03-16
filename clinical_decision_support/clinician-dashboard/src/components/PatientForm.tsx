import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createPatient, updatePatient, type Patient } from "../lib/patientApi";

interface PatientFormProps {
  patient?: Patient | null;
  onClose: () => void;
  onSuccess: (patient: Patient) => void;
}

export function PatientForm({ patient, onClose, onSuccess }: PatientFormProps) {
  const queryClient = useQueryClient();
  const isEditing = !!patient;

  const [formData, setFormData] = useState<Partial<Patient>>({
    first_name: "",
    last_name: "",
    middle_name: "",
    prefix: "",
    suffix: "",
    date_of_birth: "",
    gender: "unknown",
    blood_type: "unknown",
    ssn: "",
    phone: "",
    phone_secondary: "",
    email: "",
    address_line1: "",
    address_line2: "",
    city: "",
    state: "",
    postal_code: "",
    country: "USA",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relationship: "",
    insurance_provider: "",
    insurance_policy_number: "",
    insurance_group_number: "",
    allergies: [],
    medications: [],
    medical_conditions: [],
    medical_history: "",
    primary_care_physician: "",
    status: "active",
  });

  const [allergiesText, setAllergiesText] = useState("");
  const [medicationsText, setMedicationsText] = useState("");
  const [conditionsText, setConditionsText] = useState("");

  useEffect(() => {
    if (patient) {
      setFormData(patient);
      setAllergiesText((patient.allergies || []).join(", "));
      setMedicationsText((patient.medications || []).join(", "));
      setConditionsText((patient.medical_conditions || []).join(", "));
    }
  }, [patient]);

  const createMutation = useMutation({
    mutationFn: createPatient,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      onSuccess(data);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Patient> }) => updatePatient(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      onSuccess(data);
    },
  });

  const [validationError, setValidationError] = useState<string | null>(null);

  const validateForm = (): string | null => {
    // Validate date of birth format (YYYY-MM-DD)
    const dob = formData.date_of_birth || "";
    if (!dob) {
      return "Date of birth is required.";
    }

    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(dob)) {
      return "Date of birth must be in YYYY-MM-DD format.";
    }

    const [yearStr, monthStr, dayStr] = dob.split("-");
    const year = parseInt(yearStr, 10);
    const month = parseInt(monthStr, 10);
    const day = parseInt(dayStr, 10);

    // Validate year is reasonable (between 1900 and current year)
    const currentYear = new Date().getFullYear();
    if (year < 1900 || year > currentYear) {
      return `Year must be between 1900 and ${currentYear}.`;
    }

    // Validate month and day
    if (month < 1 || month > 12) {
      return "Invalid month in date of birth.";
    }
    if (day < 1 || day > 31) {
      return "Invalid day in date of birth.";
    }

    // Check if the date is valid
    const dateObj = new Date(year, month - 1, day);
    if (dateObj.getFullYear() !== year || dateObj.getMonth() !== month - 1 || dateObj.getDate() !== day) {
      return "Invalid date of birth.";
    }

    // Validate required fields
    if (!formData.first_name?.trim()) {
      return "First name is required.";
    }
    if (!formData.last_name?.trim()) {
      return "Last name is required.";
    }

    return null;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    // Validate form before submitting
    const error = validateForm();
    if (error) {
      setValidationError(error);
      return;
    }

    const rawData = {
      ...formData,
      allergies: allergiesText.split(",").map((s) => s.trim()).filter(Boolean),
      medications: medicationsText.split(",").map((s) => s.trim()).filter(Boolean),
      medical_conditions: conditionsText.split(",").map((s) => s.trim()).filter(Boolean),
    };

    // Filter out empty strings to avoid validation errors
    // Keep required fields and non-empty values
    const requiredFields = ['first_name', 'last_name', 'date_of_birth'];
    const data: Partial<Patient> = {};
    for (const [key, value] of Object.entries(rawData)) {
      if (requiredFields.includes(key) || (value !== '' && value !== null && value !== undefined)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (data as any)[key] = value;
      }
    }

    if (isEditing && patient) {
      updateMutation.mutate({ id: patient.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", fontSize: 14 };
  const labelStyle = { display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#333" };
  const sectionStyle = { marginBottom: 24 };
  const gridStyle = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 };

  const isLoading = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "flex-start", padding: 40, overflow: "auto", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 800, maxHeight: "90vh", overflow: "auto" }}>
        <div style={{ padding: 20, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>{isEditing ? "Edit Patient" : "New Patient"}</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer" }}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: 20 }}>
          {(error || validationError) && (
            <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c", marginBottom: 20 }}>
              {validationError || `Failed to save patient: ${(error as Error).message || "Please check the form and try again."}`}
            </div>
          )}

          {/* Basic Information */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Basic Information</h3>
            <div style={gridStyle}>
              <div>
                <label style={labelStyle}>Prefix</label>
                <input name="prefix" value={formData.prefix || ""} onChange={handleChange} placeholder="Mr., Mrs., Dr." style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Suffix</label>
                <input name="suffix" value={formData.suffix || ""} onChange={handleChange} placeholder="Jr., Sr., III" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>First Name *</label>
                <input name="first_name" value={formData.first_name || ""} onChange={handleChange} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Middle Name</label>
                <input name="middle_name" value={formData.middle_name || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Last Name *</label>
                <input name="last_name" value={formData.last_name || ""} onChange={handleChange} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Date of Birth *</label>
                <input name="date_of_birth" type="date" value={formData.date_of_birth || ""} onChange={handleChange} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Gender</label>
                <select name="gender" value={formData.gender || "unknown"} onChange={handleChange} style={inputStyle}>
                  <option value="unknown">Unknown</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Blood Type</label>
                <select name="blood_type" value={formData.blood_type || "unknown"} onChange={handleChange} style={inputStyle}>
                  <option value="unknown">Unknown</option>
                  <option value="A+">A+</option>
                  <option value="A-">A-</option>
                  <option value="B+">B+</option>
                  <option value="B-">B-</option>
                  <option value="AB+">AB+</option>
                  <option value="AB-">AB-</option>
                  <option value="O+">O+</option>
                  <option value="O-">O-</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>SSN</label>
                <input name="ssn" value={formData.ssn || ""} onChange={handleChange} placeholder="XXX-XX-XXXX" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Status</label>
                <select name="status" value={formData.status || "active"} onChange={handleChange} style={inputStyle}>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="deceased">Deceased</option>
                </select>
              </div>
            </div>
          </div>

          {/* Contact Information */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Contact Information</h3>
            <div style={gridStyle}>
              <div>
                <label style={labelStyle}>Phone</label>
                <input name="phone" type="tel" value={formData.phone || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Secondary Phone</label>
                <input name="phone_secondary" type="tel" value={formData.phone_secondary || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Email</label>
                <input name="email" type="email" value={formData.email || ""} onChange={handleChange} style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Address */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Address</h3>
            <div style={gridStyle}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Address Line 1</label>
                <input name="address_line1" value={formData.address_line1 || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Address Line 2</label>
                <input name="address_line2" value={formData.address_line2 || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>City</label>
                <input name="city" value={formData.city || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>State</label>
                <input name="state" value={formData.state || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Postal Code</label>
                <input name="postal_code" value={formData.postal_code || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Country</label>
                <input name="country" value={formData.country || "USA"} onChange={handleChange} style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Emergency Contact */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Emergency Contact</h3>
            <div style={gridStyle}>
              <div>
                <label style={labelStyle}>Contact Name</label>
                <input name="emergency_contact_name" value={formData.emergency_contact_name || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Relationship</label>
                <input name="emergency_contact_relationship" value={formData.emergency_contact_relationship || ""} onChange={handleChange} placeholder="Spouse, Parent, etc." style={inputStyle} />
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Contact Phone</label>
                <input name="emergency_contact_phone" type="tel" value={formData.emergency_contact_phone || ""} onChange={handleChange} style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Insurance */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Insurance Information</h3>
            <div style={gridStyle}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Insurance Provider</label>
                <input name="insurance_provider" value={formData.insurance_provider || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Policy Number</label>
                <input name="insurance_policy_number" value={formData.insurance_policy_number || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Group Number</label>
                <input name="insurance_group_number" value={formData.insurance_group_number || ""} onChange={handleChange} style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Medical Information */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Medical Information</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={labelStyle}>Primary Care Physician</label>
                <input name="primary_care_physician" value={formData.primary_care_physician || ""} onChange={handleChange} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Allergies (comma-separated)</label>
                <input value={allergiesText} onChange={(e) => setAllergiesText(e.target.value)} placeholder="Penicillin, Peanuts, Latex" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Current Medications (comma-separated)</label>
                <input value={medicationsText} onChange={(e) => setMedicationsText(e.target.value)} placeholder="Aspirin 81mg, Lisinopril 10mg" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Medical Conditions (comma-separated)</label>
                <input value={conditionsText} onChange={(e) => setConditionsText(e.target.value)} placeholder="Hypertension, Diabetes Type 2" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Medical History Notes</label>
                <textarea name="medical_history" value={formData.medical_history || ""} onChange={handleChange} rows={4} style={{ ...inputStyle, resize: "vertical" }} />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, paddingTop: 16, borderTop: "1px solid #eee" }}>
            <button type="button" onClick={onClose} style={{ padding: "10px 20px", borderRadius: 8, border: "1px solid #ddd", background: "white", cursor: "pointer" }}>
              Cancel
            </button>
            <button type="submit" disabled={isLoading} style={{ padding: "10px 20px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: isLoading ? "not-allowed" : "pointer", opacity: isLoading ? 0.7 : 1 }}>
              {isLoading ? "Saving..." : isEditing ? "Update Patient" : "Create Patient"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
