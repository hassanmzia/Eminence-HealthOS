export type FhirBundle<T = any> = {
  resourceType: "Bundle";
  total?: number;
  entry?: Array<{ resource: T }>;
};

export type Observation = {
  resourceType: "Observation";
  id?: string;
  status?: string;
  category?: Array<{ coding?: Array<{ system?: string; code?: string; display?: string }> }>;
  code?: { coding?: Array<{ system?: string; code?: string; display?: string }> };
  subject?: { reference?: string };
  effectiveDateTime?: string;
  issued?: string;
  valueQuantity?: { value?: number; unit?: string };
  valueCodeableConcept?: {
    coding?: Array<{ system?: string; code?: string; display?: string }>;
    text?: string;
  };
  component?: Array<{
    code?: { coding?: Array<{ system?: string; code?: string; display?: string }> };
    valueQuantity?: { value?: number; unit?: string };
    valueString?: string;
  }>;
};

