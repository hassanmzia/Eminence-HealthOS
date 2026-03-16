import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
  timeout: 15000,
});

export const fhir = axios.create({
  baseURL: import.meta.env.VITE_FHIR_BASE,
  timeout: 20000,
  headers: { Accept: "application/fhir+json" },
});

