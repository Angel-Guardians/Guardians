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
 * The "logged-in" patient — the active profile session. Persisted in
 * localStorage so it survives reloads and is shared across tabs. Returns `null`
 * when no profile is selected (logged out) or on the server, which is how the
 * SessionGate decides whether to show the app or the profile-selection screen.
 */
export function getActivePatientId(): number | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ACTIVE_PATIENT_KEY);
  const id = raw === null ? NaN : Number(raw);
  return Number.isFinite(id) && id > 0 ? id : null;
}

/**
 * The active patient id for data fetching, falling back to DEFAULT_PATIENT_ID.
 * Use this for API calls (which only fire once a profile is active); use
 * getActivePatientId() for session/auth-style logic that must see "logged out".
 */
export function resolveActivePatientId(): number {
  return getActivePatientId() ?? DEFAULT_PATIENT_ID;
}

/** Select the active patient (log in) and notify listeners. */
export function setActivePatientId(id: number): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACTIVE_PATIENT_KEY, String(id));
  window.dispatchEvent(
    new CustomEvent(ACTIVE_PATIENT_CHANGED_EVENT, { detail: id }),
  );
}

/** Clear the active patient (log out) and notify listeners. */
export function clearActivePatientId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACTIVE_PATIENT_KEY);
  window.dispatchEvent(
    new CustomEvent(ACTIVE_PATIENT_CHANGED_EVENT, { detail: null }),
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
