import { api } from "./http";

// Lab Test Catalog Types
export interface LabTest {
  id: number;
  code: string;
  name: string;
  description?: string;
  category: string;
  specimen_type: string;
  unit: string;
  reference_range_low?: number;
  reference_range_high?: number;
  reference_range_text?: string;
  critical_low?: number;
  critical_high?: number;
  typical_tat_hours: number;
  is_active: boolean;
  requires_fasting: boolean;
  special_instructions?: string;
  created_at: string;
  updated_at: string;
}

export interface LabPanel {
  id: number;
  code: string;
  name: string;
  description?: string;
  tests: LabTest[];
  is_active: boolean;
  created_at: string;
}

// Lab Order Types
export interface LabOrderTest {
  id: number;
  order: number;
  test: number;
  test_details: LabTest;
  status: "pending" | "processing" | "completed" | "cancelled";
  notes?: string;
  result?: LabResult;
  created_at: string;
}

export interface LabOrder {
  id: number;
  order_number: string;
  fhir_id?: string;
  patient: number;
  patient_name: string;
  patient_mrn?: string;
  encounter_id?: number;
  status: "ordered" | "collected" | "received" | "processing" | "partial" | "completed" | "cancelled";
  priority: "routine" | "urgent" | "stat";
  ordering_physician: string;
  ordering_physician_id?: string;
  clinical_notes?: string;
  diagnosis_codes?: string[];
  specimen_collected_at?: string;
  specimen_collector?: string;
  specimen_id?: string;
  received_at?: string;
  completed_at?: string;
  ordered_at: string;
  updated_at: string;
  cancelled_at?: string;
  cancelled_by?: string;
  cancellation_reason?: string;
  tests: LabOrderTest[];
}

export interface LabOrderListItem {
  id: number;
  order_number: string;
  patient: number;
  patient_name: string;
  patient_mrn?: string;
  status: string;
  priority: string;
  ordering_physician: string;
  test_count: number;
  completed_count: number;
  ordered_at: string;
  completed_at?: string;
}

// Lab Result Types
export interface LabResult {
  id: number;
  order_test: number;
  fhir_id?: string;
  test_name: string;
  test_code: string;
  test_unit: string;
  value_numeric?: number;
  value_text?: string;
  unit: string;
  reference_range_low?: number;
  reference_range_high?: number;
  reference_range_text?: string;
  flag: "N" | "L" | "H" | "LL" | "HH" | "A" | "U";
  is_critical: boolean;
  interpretation?: string;
  performed_by?: string;
  verified_by?: string;
  performed_at?: string;
  verified_at?: string;
  comments?: string;
  method?: string;
  created_at: string;
  updated_at: string;
}

// List Responses
export interface LabTestListResponse {
  total: number;
  limit: number;
  offset: number;
  results: LabTest[];
}

export interface LabOrderListResponse {
  total: number;
  limit: number;
  offset: number;
  results: LabOrderListItem[];
}

// Lab Stats
export interface LabStats {
  orders_by_status: Record<string, number>;
  orders_today: number;
  pending_orders: number;
  critical_results_today: number;
  average_tat_hours?: number;
  top_ordered_tests: Array<{
    test__name: string;
    test__code: string;
    count: number;
  }>;
  total_tests_in_catalog: number;
  total_panels: number;
}

// Patient Lab History
export interface PatientLabHistory {
  patient_id: number;
  tests: Array<{
    test_code: string;
    test_name: string;
    unit: string;
    category: string;
    reference_range_low?: number;
    reference_range_high?: number;
    results: Array<{
      result_id: number;
      order_number: string;
      value_numeric?: number;
      value_text?: string;
      unit: string;
      flag: string;
      is_critical: boolean;
      performed_at?: string;
      reference_range_low?: number;
      reference_range_high?: number;
    }>;
  }>;
}

// Constants
export const LAB_CATEGORIES = [
  { value: "chemistry", label: "Chemistry" },
  { value: "hematology", label: "Hematology" },
  { value: "urinalysis", label: "Urinalysis" },
  { value: "microbiology", label: "Microbiology" },
  { value: "immunology", label: "Immunology" },
  { value: "coagulation", label: "Coagulation" },
  { value: "endocrine", label: "Endocrine" },
  { value: "cardiac", label: "Cardiac Markers" },
  { value: "toxicology", label: "Toxicology" },
  { value: "genetic", label: "Genetic Testing" },
  { value: "other", label: "Other" },
];

export const LAB_ORDER_STATUSES = [
  { value: "ordered", label: "Ordered", color: "#3b82f6" },
  { value: "collected", label: "Specimen Collected", color: "#8b5cf6" },
  { value: "received", label: "Received by Lab", color: "#6366f1" },
  { value: "processing", label: "Processing", color: "#f59e0b" },
  { value: "partial", label: "Partial Results", color: "#d97706" },
  { value: "completed", label: "Completed", color: "#10b981" },
  { value: "cancelled", label: "Cancelled", color: "#ef4444" },
];

export const LAB_PRIORITIES = [
  { value: "routine", label: "Routine", color: "#6b7280" },
  { value: "urgent", label: "Urgent", color: "#f59e0b" },
  { value: "stat", label: "STAT", color: "#ef4444" },
];

export const FLAG_LABELS: Record<string, { label: string; color: string }> = {
  N: { label: "Normal", color: "#10b981" },
  L: { label: "Low", color: "#3b82f6" },
  H: { label: "High", color: "#f59e0b" },
  LL: { label: "Critical Low", color: "#dc2626" },
  HH: { label: "Critical High", color: "#dc2626" },
  A: { label: "Abnormal", color: "#f59e0b" },
  U: { label: "Undetermined", color: "#6b7280" },
};

// API Functions

// Lab Test Catalog
export async function fetchLabTests(params?: {
  category?: string;
  search?: string;
  active_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<LabTestListResponse> {
  const res = await api.get<LabTestListResponse>("/api/v1/labs/catalog/", { params });
  return res.data;
}

export async function createLabTest(data: Partial<LabTest>): Promise<LabTest> {
  const res = await api.post<LabTest>("/api/v1/labs/catalog/", data);
  return res.data;
}

export async function updateLabTest(testId: number, data: Partial<LabTest>): Promise<LabTest> {
  const res = await api.put<LabTest>(`/api/v1/labs/catalog/${testId}/`, data);
  return res.data;
}

export async function initializeLabCatalog(): Promise<{
  message: string;
  tests_created: number;
  panels_created: number;
  total_tests: number;
  total_panels: number;
}> {
  const res = await api.post("/api/v1/labs/catalog/initialize/");
  return res.data;
}

// Lab Panels
export async function fetchLabPanels(): Promise<{ total: number; results: LabPanel[] }> {
  const res = await api.get("/api/v1/labs/panels/");
  return res.data;
}

// Lab Orders
export async function fetchLabOrders(params?: {
  patient_id?: number;
  status?: string;
  priority?: string;
  physician?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}): Promise<LabOrderListResponse> {
  const res = await api.get<LabOrderListResponse>("/api/v1/labs/orders/", { params });
  return res.data;
}

export async function fetchLabOrder(orderId: number): Promise<LabOrder> {
  const res = await api.get<LabOrder>(`/api/v1/labs/orders/${orderId}/`);
  return res.data;
}

export async function createLabOrder(data: {
  patient: number;
  priority?: string;
  ordering_physician: string;
  ordering_physician_id?: string;
  clinical_notes?: string;
  diagnosis_codes?: string[];
  test_codes?: string[];
  panel_codes?: string[];
}): Promise<LabOrder> {
  const res = await api.post<LabOrder>("/api/v1/labs/orders/", data);
  return res.data;
}

export async function updateLabOrderStatus(
  orderId: number,
  data: {
    status: string;
    specimen_collected_at?: string;
    specimen_collector?: string;
    specimen_id?: string;
    received_at?: string;
    completed_at?: string;
  }
): Promise<LabOrder> {
  const res = await api.post<LabOrder>(`/api/v1/labs/orders/${orderId}/status/`, data);
  return res.data;
}

export async function cancelLabOrder(
  orderId: number,
  reason: string,
  cancelledBy: string
): Promise<LabOrder> {
  const res = await api.post<LabOrder>(`/api/v1/labs/orders/${orderId}/cancel/`, {
    reason,
    cancelled_by: cancelledBy,
  });
  return res.data;
}

export async function addTestsToOrder(
  orderId: number,
  testCodes: string[],
  panelCodes?: string[]
): Promise<{ added_tests: string[]; order: LabOrder }> {
  const res = await api.post(`/api/v1/labs/orders/${orderId}/add-tests/`, {
    test_codes: testCodes,
    panel_codes: panelCodes,
  });
  return res.data;
}

// Lab Results
export async function enterLabResults(
  orderId: number,
  results: Array<{
    order_test_id: number;
    value_numeric?: number;
    value_text?: string;
    performed_by?: string;
    comments?: string;
    method?: string;
  }>
): Promise<{
  entered: Array<{ order_test_id: number; test_name: string; flag: string; is_critical: boolean }>;
  errors: unknown[];
  order_status: string;
  critical_results: unknown[];
}> {
  const res = await api.post(`/api/v1/labs/orders/${orderId}/results/`, { results });
  return res.data;
}

export async function verifyLabResult(
  resultId: number,
  verifiedBy: string
): Promise<LabResult> {
  const res = await api.post<LabResult>(`/api/v1/labs/results/${resultId}/verify/`, {
    verified_by: verifiedBy,
  });
  return res.data;
}

// Patient History
export async function fetchPatientLabHistory(
  patientId: number,
  testCode?: string,
  days?: number
): Promise<PatientLabHistory> {
  const res = await api.get<PatientLabHistory>(`/api/v1/labs/patient/${patientId}/history/`, {
    params: { test_code: testCode, days },
  });
  return res.data;
}

// Statistics
export async function fetchLabStats(): Promise<LabStats> {
  const res = await api.get<LabStats>("/api/v1/labs/stats/");
  return res.data;
}
