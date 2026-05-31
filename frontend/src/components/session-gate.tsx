"use client";

import { useSyncExternalStore } from "react";

import { AppHeader } from "@/components/app-header";
import { FallAlerts } from "@/components/fall-alerts";
import { ProfileGate } from "@/components/profile-gate";
import {
  ACTIVE_PATIENT_CHANGED_EVENT,
  getActivePatientId,
} from "@/lib/profile-storage";

type Session = number | null;

function subscribe(onChange: () => void) {
  window.addEventListener(ACTIVE_PATIENT_CHANGED_EVENT, onChange);
  window.addEventListener("storage", onChange); // keep tabs in sync
  return () => {
    window.removeEventListener(ACTIVE_PATIENT_CHANGED_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/**
 * Profile session boundary. With no active profile (logged out) it shows the
 * full-screen ProfileGate; otherwise it renders the normal app shell. The active
 * profile is read from localStorage via useSyncExternalStore so server render,
 * hydration, and cross-tab changes all stay consistent without flashing.
 */
export function SessionGate({ children }: { children: React.ReactNode }) {
  // `undefined` on the server and during hydration (we haven't read storage
  // yet) → neutral splash; then a patient id (logged in) or null (logged out).
  const session = useSyncExternalStore<Session | undefined>(
    subscribe,
    () => getActivePatientId(),
    () => undefined,
  );

  if (session === undefined) {
    return <div className="min-h-screen bg-background" aria-hidden />;
  }

  if (session === null) {
    return <ProfileGate />;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <FallAlerts />
      <main className="flex-1 overflow-x-hidden px-6 py-8 md:px-10 md:py-10">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
