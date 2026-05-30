// Typed fetch client for the Guardian FastAPI backend.
//
// Endpoints that already exist server-side: GET /health, GET /patient/,
// GET /patient/{id}, GET /events/sse (consumed via useEventStream, not here).
// Endpoints still TODO server-side (vitals, medications) are typed here so the
// UI is ready; callers handle failures gracefully until the backend lands them.

import type { Medication, Patient, VitalKind, VitalSeries } from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    throw new ApiError(`${init?.method ?? "GET"} ${path} -> ${res.status}`, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => getJson<{ status: string }>("/health"),
  ping: () => getJson<{ message: string }>("/ping"),

  listPatients: () => getJson<Patient[]>("/patient/"),
  getPatient: (id: number) => getJson<Patient>(`/patient/${id}`),

  // TODO(backend): GET /vitals?kind=&since= not implemented yet.
  getVitals: (kind: VitalKind, since = "24h") =>
    getJson<VitalSeries>(`/vitals?kind=${kind}&since=${since}`),

  // TODO(backend): GET /medications?patient_id= not implemented yet.
  listMedications: (patientId: number) =>
    getJson<Medication[]>(`/medications?patient_id=${patientId}`),

  // TODO(backend): POST /events to confirm intake (TapConfirmedEvent).
  confirmIntake: (medicationId: number) =>
    getJson<{ ok: boolean }>("/events", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ kind: "tap_confirmed", medication_id: medicationId }),
    }),
};
