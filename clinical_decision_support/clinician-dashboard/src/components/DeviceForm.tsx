import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createDevice, updateDevice, DEVICE_TYPES, type Device } from "../lib/deviceApi";

interface DeviceFormProps {
  device?: Device | null;
  onClose: () => void;
  onSuccess: (device: Device) => void;
}

export function DeviceForm({ device, onClose, onSuccess }: DeviceFormProps) {
  const queryClient = useQueryClient();
  const isEditing = !!device;

  const [formData, setFormData] = useState<Partial<Device>>({
    device_id: "",
    serial_number: "",
    name: "",
    device_type: "vital_monitor",
    manufacturer: "",
    model_number: "",
    firmware_version: "",
    facility: "",
    department: "",
    room: "",
    bed: "",
    capabilities: [],
    reading_interval_seconds: 60,
    status: "active",
    battery_level: undefined,
    notes: "",
  });

  const [capabilitiesText, setCapabilitiesText] = useState("");

  useEffect(() => {
    if (device) {
      setFormData(device);
      setCapabilitiesText((device.capabilities || []).join(", "));
    }
  }, [device]);

  const createMutation = useMutation({
    mutationFn: createDevice,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      onSuccess(data);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Device> }) => updateDevice(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      onSuccess(data);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const data = {
      ...formData,
      capabilities: capabilitiesText.split(",").map((s) => s.trim()).filter(Boolean),
    };

    if (isEditing && device) {
      updateMutation.mutate({ id: device.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "number" ? (value === "" ? undefined : Number(value)) : value,
    }));
  };

  const inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", fontSize: 14 };
  const labelStyle = { display: "block", marginBottom: 4, fontSize: 13, fontWeight: 500, color: "#333" } as const;
  const sectionStyle = { marginBottom: 24 };
  const gridStyle = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 };

  const isLoading = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "flex-start", padding: 40, overflow: "auto", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: 12, width: "100%", maxWidth: 700, maxHeight: "90vh", overflow: "auto" }}>
        <div style={{ padding: 20, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>{isEditing ? "Edit Device" : "Register New Device"}</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer" }}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: 20 }}>
          {error && (
            <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c", marginBottom: 20 }}>
              Failed to save device. Please check the form and try again.
            </div>
          )}

          {/* Device Identification */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Device Identification</h3>
            <div style={gridStyle}>
              <div>
                <label style={labelStyle}>Device ID *</label>
                <input name="device_id" value={formData.device_id || ""} onChange={handleChange} required placeholder="DEV-001" style={inputStyle} disabled={isEditing} />
                {isEditing && <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>Device ID cannot be changed</div>}
              </div>
              <div>
                <label style={labelStyle}>Serial Number</label>
                <input name="serial_number" value={formData.serial_number || ""} onChange={handleChange} placeholder="SN-XXXX-XXXX" style={inputStyle} />
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Device Name *</label>
                <input name="name" value={formData.name || ""} onChange={handleChange} required placeholder="ICU Vital Signs Monitor #1" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Device Type *</label>
                <select name="device_type" value={formData.device_type || "vital_monitor"} onChange={handleChange} required style={inputStyle}>
                  {DEVICE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Status</label>
                <select name="status" value={formData.status || "active"} onChange={handleChange} style={inputStyle}>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="maintenance">Under Maintenance</option>
                  <option value="retired">Retired</option>
                </select>
              </div>
            </div>
          </div>

          {/* Manufacturer Info */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Manufacturer Information</h3>
            <div style={gridStyle}>
              <div>
                <label style={labelStyle}>Manufacturer</label>
                <input name="manufacturer" value={formData.manufacturer || ""} onChange={handleChange} placeholder="Philips, GE Healthcare, etc." style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Model Number</label>
                <input name="model_number" value={formData.model_number || ""} onChange={handleChange} placeholder="Model XYZ-123" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Firmware Version</label>
                <input name="firmware_version" value={formData.firmware_version || ""} onChange={handleChange} placeholder="v1.2.3" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Battery Level (%)</label>
                <input name="battery_level" type="number" min={0} max={100} value={formData.battery_level ?? ""} onChange={handleChange} placeholder="0-100" style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Location */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Location</h3>
            <div style={gridStyle}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Facility</label>
                <input name="facility" value={formData.facility || ""} onChange={handleChange} placeholder="General Hospital" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Department</label>
                <input name="department" value={formData.department || ""} onChange={handleChange} placeholder="ICU, Emergency, Cardiology" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Room</label>
                <input name="room" value={formData.room || ""} onChange={handleChange} placeholder="101" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Bed</label>
                <input name="bed" value={formData.bed || ""} onChange={handleChange} placeholder="A" style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Capabilities & Config */}
          <div style={sectionStyle}>
            <h3 style={{ marginTop: 0, marginBottom: 16, color: "#333" }}>Capabilities & Configuration</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={labelStyle}>Capabilities (comma-separated)</label>
                <input
                  value={capabilitiesText}
                  onChange={(e) => setCapabilitiesText(e.target.value)}
                  placeholder="heart_rate, blood_pressure, spo2, temperature, respiratory_rate"
                  style={inputStyle}
                />
                <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
                  List the vital signs this device can measure
                </div>
              </div>
              <div>
                <label style={labelStyle}>Reading Interval (seconds)</label>
                <input
                  name="reading_interval_seconds"
                  type="number"
                  min={1}
                  value={formData.reading_interval_seconds ?? 60}
                  onChange={handleChange}
                  style={{ ...inputStyle, maxWidth: 200 }}
                />
                <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
                  How often the device sends vitals data
                </div>
              </div>
              <div>
                <label style={labelStyle}>Notes</label>
                <textarea
                  name="notes"
                  value={formData.notes || ""}
                  onChange={handleChange}
                  rows={3}
                  placeholder="Additional notes about this device..."
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
            <button type="submit" disabled={isLoading} style={{ padding: "10px 20px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: isLoading ? "not-allowed" : "pointer", opacity: isLoading ? 0.7 : 1 }}>
              {isLoading ? "Saving..." : isEditing ? "Update Device" : "Register Device"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
