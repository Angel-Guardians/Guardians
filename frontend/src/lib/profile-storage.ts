import type { PatientProfile } from "@/lib/types";

const STORAGE_KEY = "guardian:patient-profile";

export const PROFILE_UPDATED_EVENT = "guardian:profile-updated";

export function profileInitials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Demo default — Eleanor from Scenario 1 (Midnight fall). */
export const DEFAULT_PATIENT_PROFILE: PatientProfile = {
  id: 1,
  name: "Eleanor",
  age: 70,
  conditions: ["cardiac history", "lives alone"],
  allergies: ["penicillin"],
  primary_language: "en",
  notes: "Post-hip-fracture recovery. Prefers calm reassurance during emergencies.",
  emergency_contacts: [
    {
      name: "Maria",
      relationship: "daughter",
      phone: "+1 (555) 555-0111",
      priority: 1,
    },
    {
      name: "Dr. Adeyemi",
      relationship: "family_doctor",
      phone: "+1 (555) 555-0122",
      priority: 2,
    },
  ],
  medications: [
    {
      name: "Lisinopril",
      dose: "10 mg",
      schedule_cron: "0 8 * * *",
      with_food: false,
      notes: "Blood pressure — morning",
    },
    {
      name: "Metoprolol",
      dose: "25 mg",
      schedule_cron: "0 8,20 * * *",
      with_food: true,
      notes: "Twice daily with meals",
    },
  ],
};

export function loadPatientProfile(): PatientProfile {
  if (typeof window === "undefined") return DEFAULT_PATIENT_PROFILE;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PATIENT_PROFILE;
    const parsed = JSON.parse(raw) as PatientProfile;
    return { ...DEFAULT_PATIENT_PROFILE, ...parsed, id: 1 };
  } catch {
    return DEFAULT_PATIENT_PROFILE;
  }
}

export function savePatientProfile(profile: PatientProfile): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(PROFILE_UPDATED_EVENT, { detail: profile }));
  }
}

export function resetPatientProfile(): PatientProfile {
  localStorage.removeItem(STORAGE_KEY);
  return DEFAULT_PATIENT_PROFILE;
}
