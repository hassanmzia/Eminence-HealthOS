import { api } from "./http";

export interface Device {
  id: number;
  device_id: string;
  fhir_id?: string;
  serial_number?: string;
  name: string;
  device_type: string;
  manufacturer?: string;
  model_number?: string;
  firmware_version?: string;
  facility?: string;
  department?: string;
  room?: string;
  bed?: string;
  capabilities?: string[];
  reading_interval_seconds?: number;
  config?: Record<string, unknown>;
  status: "active" | "inactive" | "maintenance" | "retired";
  last_seen?: string;
  battery_level?: number;
  notes?: string;
  created_at: string;
  updated_at?: string;
  assigned_patient_name?: string;
  assigned_patient_id?: number;
  current_assignment?: DeviceAssignment;
  assignments?: DeviceAssignment[];
}

export interface DeviceAssignment {
  id: number;
  device: number;
  patient: number;
  patient_name?: string;
  patient_mrn?: string;
  assigned_at: string;
  unassigned_at?: string;
  is_active: boolean;
  assigned_by?: string;
  reason?: string;
  notes?: string;
}

export interface DeviceListResponse {
  total: number;
  limit: number;
  offset: number;
  results: Device[];
}

export const DEVICE_TYPES = [
  { value: "vital_monitor", label: "Vital Signs Monitor" },
  { value: "pulse_oximeter", label: "Pulse Oximeter" },
  { value: "bp_monitor", label: "Blood Pressure Monitor" },
  { value: "thermometer", label: "Thermometer" },
  { value: "ecg_monitor", label: "ECG Monitor" },
  { value: "glucose_monitor", label: "Glucose Monitor" },
  { value: "weight_scale", label: "Weight Scale" },
  { value: "multi_parameter", label: "Multi-Parameter Monitor" },
  { value: "wearable", label: "Wearable Device" },
  { value: "other", label: "Other" },
];

// Fetch all devices with optional filtering
export async function fetchDevices(params?: {
  search?: string;
  status?: string;
  type?: string;
  assigned?: string;
  facility?: string;
  limit?: number;
  offset?: number;
}): Promise<DeviceListResponse> {
  const res = await api.get<DeviceListResponse>("/api/v1/devices/", { params });
  return res.data;
}

// Fetch a single device by ID
export async function fetchDevice(deviceId: number): Promise<Device> {
  const res = await api.get<Device>(`/api/v1/devices/${deviceId}/`);
  return res.data;
}

// Create a new device
export async function createDevice(device: Partial<Device>): Promise<Device> {
  const res = await api.post<Device>("/api/v1/devices/", device);
  return res.data;
}

// Update a device
export async function updateDevice(deviceId: number, device: Partial<Device>): Promise<Device> {
  const res = await api.put<Device>(`/api/v1/devices/${deviceId}/`, device);
  return res.data;
}

// Delete a device (soft delete - sets to retired)
export async function deleteDevice(deviceId: number): Promise<void> {
  await api.delete(`/api/v1/devices/${deviceId}/`);
}

// Assign device to patient
export async function assignDevice(
  deviceId: number,
  data: { patient_id: number; assigned_by?: string; reason?: string; notes?: string }
): Promise<DeviceAssignment> {
  const res = await api.post<DeviceAssignment>(`/api/v1/devices/${deviceId}/assign/`, data);
  return res.data;
}

// Unassign device from patient
export async function unassignDevice(
  deviceId: number,
  data?: { notes?: string }
): Promise<DeviceAssignment> {
  const res = await api.post<DeviceAssignment>(`/api/v1/devices/${deviceId}/unassign/`, data || {});
  return res.data;
}

// Get assignment history for a device
export async function fetchDeviceAssignments(deviceId: number): Promise<DeviceAssignment[]> {
  const res = await api.get<DeviceAssignment[]>(`/api/v1/devices/${deviceId}/assignments/`);
  return res.data;
}

// Get devices assigned to a patient
export async function fetchPatientDevices(
  patientId: number,
  activeOnly: boolean = true
): Promise<DeviceAssignment[]> {
  const res = await api.get<DeviceAssignment[]>(`/api/v1/devices/patient/${patientId}/`, {
    params: { active: activeOnly }
  });
  return res.data;
}
