import type { PatientProfile } from "@/lib/types";

export const PROFILE_UPDATED_EVENT = "guardian:profile-updated";

export const DEFAULT_PATIENT_ID = Number(
  process.env.NEXT_PUBLIC_PATIENT_ID ?? "1",
);

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
