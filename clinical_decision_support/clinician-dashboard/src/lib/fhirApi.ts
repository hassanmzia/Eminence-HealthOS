import { fhir } from "./http";
import type { FhirBundle, Observation } from "./fhirTypes";

export async function fetchObservations(params: {
  patientRef?: string;        // e.g. "Patient/123" or just "123"
  count?: number;             // default 100
  category?: string;          // "vital-signs"
}) {
  const count = params.count ?? 200;
  const q: Record<string, string> = {
    _count: String(count),
    _sort: "-date",
  };

  if (params.category) q["category"] = params.category;
  if (params.patientRef) {
    // Support both "Patient/123" format and just "123"
    // For FHIR search, we can use either:
    // - subject=Patient/123 (full reference)
    // - subject:Patient=123 (typed search using modifier)
    // Using the typed search format to avoid URL encoding issues with '/'
    const id = params.patientRef.includes("/")
      ? params.patientRef.split("/")[1]
      : params.patientRef;
    q["subject:Patient"] = id;
  }

  const res = await fhir.get<FhirBundle<Observation>>("/Observation", { params: q });
  return res.data;
}

export function normalizeVitals(bundle: FhirBundle<Observation>) {
  const entries = bundle.entry?.map(e => e.resource).filter(Boolean) ?? [];

  // Extract key vitals + BP components into a common row structure for charts
  const rows = entries.map(o => {
    const code = o.code?.coding?.[0]?.code ?? "";
    const display = o.code?.coding?.[0]?.display ?? "Observation";
    const t = o.effectiveDateTime ?? o.issued ?? "";

    // BP special handling (component systolic/diastolic)
    const sys = o.component?.find(c => c.code?.coding?.[0]?.code === "8480-6")?.valueQuantity?.value;
    const dia = o.component?.find(c => c.code?.coding?.[0]?.code === "8462-4")?.valueQuantity?.value;

    // ECG special handling (LOINC 8601-7) - has valueCodeableConcept and components
    let ecg_data = null;
    if (code === "8601-7") {
      const rhythm = o.component?.find(c => c.code?.coding?.[0]?.code === "8884-9")?.valueString
        || o.valueCodeableConcept?.coding?.[0]?.display
        || "";
      const interpretation = o.valueCodeableConcept?.text || "";
      const findings: string[] = [];
      // Extract ECG findings from components
      o.component?.forEach(c => {
        if (c.code?.coding?.[0]?.code === "18844-1" && c.valueString) {
          findings.push(c.valueString);
        }
      });
      ecg_data = { rhythm, rate: "", interpretation, findings };
    }

    return {
      id: o.id ?? "",
      time: t,
      loinc: code,
      name: display,
      value: o.valueQuantity?.value ?? null,
      unit: o.valueQuantity?.unit ?? "",
      bp_sys: sys ?? null,
      bp_dia: dia ?? null,
      ecg_data,
    };
  });

  // Sort ascending by time for charts
  rows.sort((a, b) => (a.time || "").localeCompare(b.time || ""));
  return rows;
}

