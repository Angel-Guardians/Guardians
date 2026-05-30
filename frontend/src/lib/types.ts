// Shared types mirroring the FastAPI backend (backend/api/*).

export interface Patient {
  id: number;
  name: string;
  // Backend model is still a stub; extend as backend/db/models grows.
  [key: string]: unknown;
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

export type VitalKind = "hr" | "spo2" | "bp";

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
