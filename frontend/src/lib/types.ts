// Shared types mirroring the FastAPI backend (backend/api/*).

export interface EmergencyContact {
  id?: number;
  name: string;
  relationship: string;
  phone: string;
  priority: number;
}

export interface ProfileMedication {
  id?: number;
  name: string;
  dose: string;
  schedule_cron: string;
  with_food: boolean;
  notes?: string | null;
}

export interface PatientProfile {
  id: number;
  name: string;
  age: number;
  conditions: string[];
  allergies: string[];
  primary_language: string;
  location?: string | null;
  bio?: string | null;
  notes?: string | null;
  emergency_contacts: EmergencyContact[];
  medications: ProfileMedication[];
}

export type PatientProfileUpdate = Omit<PatientProfile, "id">;

export interface Patient {
  id: number;
  name: string;
  age?: number;
  conditions?: string[];
  allergies?: string[];
  primary_language?: string;
  notes?: string | null;
}

/** One step in a conversational turn — mirrors backend/api/turn.py publish order. */
export type PipelineStep =
  | { kind: "transcript"; text: string }
  | { kind: "routing_decision"; routed_to: string }
  | { kind: "tool_invocation"; tool: string }
  | { kind: "agent_reply"; agent: string };

// Events streamed from GET /events/sse. The backend serializes domain events
// (fall detected, transcript chunk, vitals reading, nudge, etc.) as JSON.
export interface GuardianEvent {
  id: string;
  kind: string;
  ts: string; // ISO timestamp
  summary?: string;
  payload?: Record<string, unknown>;
}

export type VitalKind = "hr" | "spo2" | "bp" | "steps" | "calories";

export interface VitalPoint {
  ts: string; // ISO timestamp
  value: number;
  // For blood pressure we carry both numbers.
  systolic?: number;
  diastolic?: number;
}

export interface VitalSeries {
  kind: VitalKind;
  points: VitalPoint[];
}

// A fall event from the watch: fall_suspected (detected / demo) then
// fall_confirmed (no response) or fall_cancelled ("I'm OK").
export interface FallEvent {
  kind: string;
  value: number; // peak impact (g)
  ts: string; // ISO timestamp (UTC)
  source: string;
}

export interface RiskFactor {
  name: string;
  score: number;
  weight: number;
  detail: string;
}

export interface RiskSnapshot {
  score: number;
  level: "low" | "moderate" | "high" | "critical";
  severity_tier: string;
  factors: RiskFactor[];
  updated_at: string;
}

export interface LocationPoint {
  lat: number;
  lng: number;
  accuracy?: number | null;
  ts: string; // ISO timestamp (UTC)
}

export interface Medication {
  id: number;
  name: string;
  dose: string;
  scheduledFor: string; // ISO timestamp
  taken: boolean;
}

// ---------------------------------------------------------------------------
// Lab / medical-history records — uploaded PDF documents + parsed rows.
// Mirrors backend/api/schemas.py (LabReportRead / LabReportDetail / ...).
// ---------------------------------------------------------------------------

export interface LabObservation {
  id: number;
  test_name: string;
  value_text?: string | null;
  value_num?: number | null;
  unit?: string | null;
  reference_range?: string | null;
  flag?: string | null;
  category?: string | null;
  observed_at?: string | null;
}

export interface LabReport {
  id: number;
  patient_id: number;
  source: string;
  lab_name?: string | null;
  ordering_provider?: string | null;
  collected_at?: string | null;
  reported_at?: string | null;
  document_filename?: string | null;
  status: string; // "parsed" | "raw_only" | "needs_review"
  created_at: string;
  observation_count: number;
}

export interface LabReportDetail extends LabReport {
  raw_text?: string | null;
  observations: LabObservation[];
}

// Summary of profile fields the LLM extracted from an uploaded document and
// merged into the patient profile. Only fields present in the document are filled.
export interface MedicalHistoryExtraction {
  applied: boolean;
  name?: string | null;
  age?: number | null;
  conditions_added: string[];
  allergies_added: string[];
  medications_added: string[];
  notes_added: boolean;
  error?: string | null;
}

export interface LabUploadResult {
  report_id: number;
  observations: number;
  duplicate: boolean;
  status: string;
  profile?: MedicalHistoryExtraction | null;
}

export interface AdminTable {
  name: string;
  count: number;
  rows: Record<string, unknown>[];
  clearable: boolean;
}

export interface AdminTablesResponse {
  tables: AdminTable[];
}

export interface AdminClearResult {
  table: string;
  deleted: number;
}
