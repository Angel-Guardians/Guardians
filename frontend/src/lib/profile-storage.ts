import type { PatientProfile } from "@/lib/types";

export const PROFILE_UPDATED_EVENT = "guardian:profile-updated";

/** Dispatched (with the new id as `detail`) when the active patient changes. */
export const ACTIVE_PATIENT_CHANGED_EVENT = "guardian:active-patient-changed";

const ACTIVE_PATIENT_KEY = "guardian:active-patient-id";

/** Build-time fallback used on the server and before the user picks a profile. */
export const DEFAULT_PATIENT_ID = Number(
  process.env.NEXT_PUBLIC_PATIENT_ID ?? "1",
);

/**
 * The patient the UI is currently viewing. Persisted in localStorage so the
 * choice survives reloads and is shared across tabs. Falls back to
 * DEFAULT_PATIENT_ID on the server (no window) or when nothing is stored yet.
 */
export function getActivePatientId(): number {
  if (typeof window === "undefined") return DEFAULT_PATIENT_ID;
  const raw = window.localStorage.getItem(ACTIVE_PATIENT_KEY);
  const id = raw === null ? NaN : Number(raw);
  return Number.isFinite(id) && id > 0 ? id : DEFAULT_PATIENT_ID;
}

/** Switch the active patient and notify listeners (see ACTIVE_PATIENT_CHANGED_EVENT). */
export function setActivePatientId(id: number): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACTIVE_PATIENT_KEY, String(id));
  window.dispatchEvent(
    new CustomEvent(ACTIVE_PATIENT_CHANGED_EVENT, { detail: id }),
  );
}

export function profileInitials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Fallback while loading or when the API is unreachable. */
export const EMPTY_PATIENT_PROFILE: PatientProfile = {
  id: DEFAULT_PATIENT_ID,
  name: "",
  age: 0,
  conditions: [],
  allergies: [],
  primary_language: "en",
  notes: null,
  emergency_contacts: [],
  medications: [],
};

export function notifyProfileUpdated(profile: PatientProfile): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(PROFILE_UPDATED_EVENT, { detail: profile }));
}
