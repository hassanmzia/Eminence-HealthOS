/**
 * Eminence HealthOS — MCP Context Builder
 * Aggregates FHIR data from the backend into a unified MCP context for agents.
 */

import type {
  MCPContext,
  PatientContext,
  ClinicalConstraints,
  Condition,
  Medication,
  Vital,
  Allergy,
  RiskScore,
  EncounterNote,
  CareGap,
  PatientDemographics,
} from "./types";

// ── Configuration ───────────────────────────────────────────────────────────

const BACKEND_URL = process.env.HEALTHOS_BACKEND_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

// FHIR resource types to fetch in parallel
const FHIR_RESOURCES = [
  "Patient",
  "Condition",
  "MedicationRequest",
  "Observation",
  "AllergyIntolerance",
  "Encounter",
  "CarePlan",
  "DiagnosticReport",
  "Procedure",
] as const;

// ── Backend API Client ──────────────────────────────────────────────────────

async function fetchFromBackend<T>(
  path: string,
  tenantId: string,
  token: string
): Promise<T> {
  const url = `${BACKEND_URL}${API_PREFIX}${path}`;

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": tenantId,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Backend request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

// ── Context Assembly ────────────────────────────────────────────────────────

/**
 * Build a patient's full clinical context by fetching FHIR resources
 * in parallel and assembling them into the MCP format.
 */
export async function buildPatientContext(
  patientId: string,
  tenantId: string,
  token: string
): Promise<PatientContext> {
  // Fetch all resource types in parallel
  const [
    demographics,
    conditions,
    medications,
    vitals,
    allergies,
    riskScores,
    encounters,
    careGaps,
  ] = await Promise.all([
    fetchFromBackend<PatientDemographics>(
      `/patients/${patientId}`,
      tenantId,
      token
    ).catch(() => ({} as PatientDemographics)),

    fetchFromBackend<Condition[]>(
      `/fhir/Condition?patient=${patientId}`,
      tenantId,
      token
    ).catch(() => [] as Condition[]),

    fetchFromBackend<Medication[]>(
      `/fhir/MedicationRequest?patient=${patientId}`,
      tenantId,
      token
    ).catch(() => [] as Medication[]),

    fetchFromBackend<Vital[]>(
      `/observations?patient_id=${patientId}&limit=50`,
      tenantId,
      token
    ).catch(() => [] as Vital[]),

    fetchFromBackend<Allergy[]>(
      `/fhir/AllergyIntolerance?patient=${patientId}`,
      tenantId,
      token
    ).catch(() => [] as Allergy[]),

    fetchFromBackend<RiskScore[]>(
      `/patients/${patientId}/risk-scores`,
      tenantId,
      token
    ).catch(() => [] as RiskScore[]),

    fetchFromBackend<EncounterNote[]>(
      `/fhir/Encounter?patient=${patientId}&_count=10`,
      tenantId,
      token
    ).catch(() => [] as EncounterNote[]),

    fetchFromBackend<CareGap[]>(
      `/patients/${patientId}/care-gaps`,
      tenantId,
      token
    ).catch(() => [] as CareGap[]),
  ]);

  return {
    demographics,
    conditions,
    medications,
    vitals,
    allergies,
    riskScores,
    encounters,
    careGaps,
  };
}

/**
 * Fetch clinical constraints from vector similarity search across
 * knowledge bases (guidelines, drug interactions, protocols).
 */
export async function buildClinicalConstraints(
  conditions: Condition[],
  medications: Medication[],
  tenantId: string,
  token: string
): Promise<ClinicalConstraints> {
  const conditionCodes = conditions.map((c) => c.code);
  const medicationCodes = medications.map((m) => m.rxNormCode || m.code);

  const [guidelines, contraindications, protocols] = await Promise.all([
    fetchFromBackend<ClinicalConstraints["guidelines"]>(
      `/fhir/guidelines/search`,
      tenantId,
      token
    ).catch(() => []),

    fetchFromBackend<ClinicalConstraints["contraindications"]>(
      `/fhir/drug-interactions/check`,
      tenantId,
      token
    ).catch(() => []),

    fetchFromBackend<ClinicalConstraints["protocols"]>(
      `/fhir/protocols/search`,
      tenantId,
      token
    ).catch(() => []),
  ]);

  return { guidelines, contraindications, protocols };
}

/**
 * Build the full MCP context for a patient.
 */
export async function buildMCPContext(
  patientId: string,
  tenantId: string,
  token: string
): Promise<MCPContext> {
  const patient = await buildPatientContext(patientId, tenantId, token);
  const constraints = await buildClinicalConstraints(
    patient.conditions,
    patient.medications,
    tenantId,
    token
  );

  return {
    version: "1.0",
    timestamp: new Date().toISOString(),
    patient,
    constraints,
    metadata: {
      patientId,
      tenantId,
      buildDuration: 0, // filled in by caller
    },
  };
}
