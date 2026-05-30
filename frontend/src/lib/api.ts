// Typed fetch client for the Guardian FastAPI backend.
//
// Endpoints: GET/PUT /patient/{id}/profile, GET /patient/, GET /patient/{id},
// GET /health, GET /events/sse. Vitals/medication schedule endpoints still TODO.

import type {
  Medication,
  Patient,
  PatientProfile,
  PatientProfileUpdate,
  VitalKind,
  VitalSeries,
} from "@/lib/types";
import { DEFAULT_PATIENT_ID } from "@/lib/profile-storage";

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

async function sendJson<T>(
  path: string,
  init: RequestInit & { method: string },
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    throw new ApiError(`${init.method} ${path} -> ${res.status}`, res.status);
  }
  return (await res.json()) as T;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  return sendJson<T>(path, { method: "GET", ...init });
}

export const api = {
  health: () => getJson<{ status: string }>("/health"),
  ping: () => getJson<{ message: string }>("/ping"),

  listPatients: () => getJson<Patient[]>("/patient/"),
  getPatient: (id: number) => getJson<Patient>(`/patient/${id}`),
  getPatientProfile: (id: number = DEFAULT_PATIENT_ID) =>
    getJson<PatientProfile>(`/patient/${id}/profile`),
  updatePatientProfile: (id: number, profile: PatientProfileUpdate) =>
    sendJson<PatientProfile>(`/patient/${id}/profile`, {
      method: "PUT",
      body: JSON.stringify(profile),
    }),

  // Send one conversational turn to Guardian. The reply + routing + tool calls
  // are also streamed onto GET /events/sse, so the Live page updates in real time.
  turn: (text: string, patientId: number = DEFAULT_PATIENT_ID) =>
    sendJson<{ route: string; reply: string; tool_calls: Record<string, unknown>[] }>(
      "/turn/",
      { method: "POST", body: JSON.stringify({ text, patient_id: patientId }) },
    ),

  // Implemented: GET /vitals?kind=&since= (served from the Vital table; watch feeds it).
  getVitals: (kind: VitalKind, since = "24h") =>
    getJson<VitalSeries>(`/vitals?kind=${kind}&since=${since}`),

  // TODO(backend): GET /medications?patient_id= not implemented yet.
  listMedications: (patientId: number) =>
    getJson<Medication[]>(`/medications?patient_id=${patientId}`),

  // TODO(backend): POST /events to confirm intake (TapConfirmedEvent).
  confirmIntake: (medicationId: number) =>
    sendJson<{ ok: boolean }>("/events", {
      method: "POST",
      body: JSON.stringify({ kind: "tap_confirmed", medication_id: medicationId }),
    }),
};
