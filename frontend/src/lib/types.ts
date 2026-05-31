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

export interface Medication {
  id: number;
  name: string;
  dose: string;
  scheduledFor: string; // ISO timestamp
  taken: boolean;
}

export interface AdminTable {
  name: string;
  count: number;
  rows: Record<string, unknown>[];
}

export interface AdminTablesResponse {
  tables: AdminTable[];
}
