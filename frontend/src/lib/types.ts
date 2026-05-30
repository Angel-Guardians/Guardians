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

export interface Medication {
  id: number;
  name: string;
  dose: string;
  scheduledFor: string; // ISO timestamp
  taken: boolean;
}
