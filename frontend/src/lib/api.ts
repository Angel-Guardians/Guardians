// Typed fetch client for the Guardian FastAPI backend.
//
// Endpoints: GET/PUT /patient/{id}/profile, GET /patient/, GET /patient/{id},
// GET /health, GET /events/sse. Vitals/medication schedule endpoints still TODO.

import type {
  AdminClearResult,
  AdminTablesResponse,
  FallEvent,
  LocationPoint,
  LabReport,
  LabReportDetail,
  LabUploadResult,
  Medication,
  Patient,
  PatientProfile,
  PatientProfileUpdate,
  VitalKind,
  VitalSeries,
} from "@/lib/types";
import { resolveActivePatientId } from "@/lib/profile-storage";

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

// Multipart POST. We deliberately do NOT set Content-Type — the browser adds it
// with the correct multipart boundary once the FormData body is attached.
async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { Accept: "application/json" },
    body: form,
  });
  if (!res.ok) {
    throw new ApiError(`POST ${path} -> ${res.status}`, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => getJson<{ status: string }>("/health"),
  ping: () => getJson<{ message: string }>("/ping"),

  getAdminTables: (limit = 50) =>
    getJson<AdminTablesResponse>(`/admin/tables?limit=${limit}`),

  clearAdminTable: (tableName: string) =>
    sendJson<AdminClearResult>(`/admin/tables/${encodeURIComponent(tableName)}`, {
      method: "DELETE",
    }),

  listPatients: () => getJson<Patient[]>("/patient/"),
  getPatient: (id: number) => getJson<Patient>(`/patient/${id}`),
  createPatient: (profile: PatientProfileUpdate) =>
    sendJson<PatientProfile>("/patient/", {
      method: "POST",
      body: JSON.stringify(profile),
    }),
  getPatientProfile: (id: number = resolveActivePatientId()) =>
    getJson<PatientProfile>(`/patient/${id}/profile`),
  updatePatientProfile: (id: number, profile: PatientProfileUpdate) =>
    sendJson<PatientProfile>(`/patient/${id}/profile`, {
      method: "PUT",
      body: JSON.stringify(profile),
    }),

  // Send one conversational turn to Guardian. The reply + routing + tool calls
  // are also streamed onto GET /events/sse, so the Live page updates in real time.
  turn: (text: string, patientId: number = resolveActivePatientId()) =>
    sendJson<{ route: string; reply: string; tool_calls: Record<string, unknown>[] }>(
      "/turn/",
      { method: "POST", body: JSON.stringify({ text, patient_id: patientId }) },
    ),

  // Implemented: GET /vitals?kind=&since= (served from the Vital table; watch feeds it).
  getVitals: (kind: VitalKind, since = "24h") =>
    getJson<VitalSeries>(`/vitals?kind=${kind}&since=${since}`),

  // Recent fall events from the watch (newest first).
  getFalls: (since = "24h") => getJson<FallEvent[]>(`/vitals/falls?since=${since}`),

  // GPS track from the wearable (newest first).
  getLocations: (since = "24h", patientId: number = resolveActivePatientId()) =>
    getJson<LocationPoint[]>(`/location?since=${since}&patient_id=${patientId}`),

  // Medical history: upload a results PDF; the backend parses it and stores the
  // document + extracted observation rows. Returns the parse summary.
  uploadLabRecord: (
    file: File,
    patientId: number = resolveActivePatientId(),
    source = "lifelabs_upload",
  ) => {
    const form = new FormData();
    form.append("patient_id", String(patientId));
    form.append("source", source);
    form.append("file", file);
    return postForm<LabUploadResult>("/lab-records/upload", form);
  },

  listLabRecords: (patientId: number = resolveActivePatientId()) =>
    getJson<LabReport[]>(`/lab-records?patient_id=${patientId}`),

  getLabRecord: (reportId: number) =>
    getJson<LabReportDetail>(`/lab-records/${reportId}`),

  deleteLabRecord: (reportId: number) =>
    sendJson<{ report_id: number; deleted: boolean }>(`/lab-records/${reportId}`, {
      method: "DELETE",
    }),

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
