import axios from "axios";

const SIMULATOR_URL = import.meta.env.VITE_SIMULATOR_URL || "http://localhost:8004";

const simulatorApi = axios.create({
  baseURL: SIMULATOR_URL,
});

export interface SimulatorStatus {
  running: boolean;
  interval: number;
  last_run: string | null;
  devices_count: number;
  observations_sent: number;
  errors_count: number;
}

export interface SimulatorConfig {
  interval: number;
  enabled: boolean;
}

export interface PatientCondition {
  patient_id: string;
  condition: string;
}

export interface AssignedDevice {
  device_id: string;
  name: string;
  patient_id: number;
  patient_name: string;
  capabilities: string[];
}

export async function getSimulatorStatus(): Promise<SimulatorStatus> {
  const res = await simulatorApi.get<SimulatorStatus>("/status");
  return res.data;
}

export async function startSimulator(interval?: number): Promise<void> {
  await simulatorApi.post("/start", interval ? { interval, enabled: true } : undefined);
}

export async function stopSimulator(): Promise<void> {
  await simulatorApi.post("/stop");
}

export async function configureSimulator(config: SimulatorConfig): Promise<void> {
  await simulatorApi.post("/configure", config);
}

export async function triggerSimulator(): Promise<{ devices_count: number; observations_sent: number }> {
  const res = await simulatorApi.post("/trigger");
  return res.data;
}

export async function setPatientCondition(data: PatientCondition): Promise<void> {
  await simulatorApi.post("/patient-condition", data);
}

export async function getPatientProfiles(): Promise<Record<string, { age: number; condition: string }>> {
  const res = await simulatorApi.get("/patient-profiles");
  return res.data;
}

export async function getAssignedDevices(): Promise<{ count: number; devices: AssignedDevice[] }> {
  const res = await simulatorApi.get("/devices");
  return res.data;
}

export async function resetStats(): Promise<void> {
  await simulatorApi.post("/reset-stats");
}

export const PATIENT_CONDITIONS = [
  { value: "normal", label: "Normal", description: "Healthy baseline vitals" },
  { value: "hypertensive", label: "Hypertensive", description: "Elevated blood pressure with LVH pattern on ECG" },
  { value: "hypotensive", label: "Hypotensive", description: "Low blood pressure with compensatory tachycardia" },
  { value: "fever", label: "Fever", description: "Elevated temperature with increased heart rate" },
  { value: "tachycardic", label: "Tachycardic", description: "Elevated heart rate with sinus tachycardia on ECG" },
  { value: "bradycardic", label: "Bradycardic", description: "Low heart rate with sinus bradycardia on ECG" },
  { value: "hypoxic", label: "Hypoxic", description: "Low oxygen saturation with respiratory distress" },
  { value: "diabetic", label: "Diabetic", description: "Slightly elevated blood glucose (100-140 mg/dL)" },
  { value: "diabetic_hyper", label: "Diabetic Hyperglycemic", description: "Severe hyperglycemia (180-350 mg/dL)" },
  { value: "afib", label: "Atrial Fibrillation", description: "Irregular heart rhythm with absent P waves on ECG" },
  { value: "mi_risk", label: "MI Risk", description: "ST changes on ECG suggesting ischemia or infarction" },
];
