"use client";

import { Loader2, Plus, Shield } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { CreateProfileDialog } from "@/components/create-profile-dialog";
import { api } from "@/lib/api";
import { profileInitials, setActivePatientId } from "@/lib/profile-storage";
import type { Patient, PatientProfile } from "@/lib/types";

/**
 * Logged-out screen shown by SessionGate when no profile is active. Lists the
 * existing patients to "log in" as, and offers a quick-create. Selecting (or
 * creating) a profile stores it as the active session and reloads so every page
 * mounts against the chosen patient.
 */
export function ProfileGate() {
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .listPatients()
      .then((list) => active && setPatients(list))
      .catch(() => active && setError("Couldn't reach the backend. Is it running?"));
    return () => {
      active = false;
    };
  }, []);

  const choose = useCallback((id: number) => {
    setActivePatientId(id);
    window.location.reload();
  }, []);

  const onCreated = useCallback((profile: PatientProfile) => {
    setActivePatientId(profile.id);
    window.location.reload();
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-2xl">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
            <Shield className="size-7" strokeWidth={2.25} />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Who&apos;s using Guardian?</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Choose a profile to continue, or create a new one.
          </p>
        </div>

        {error && (
          <p className="mb-6 text-center text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        {patients === null && !error ? (
          <div className="flex justify-center py-10 text-muted-foreground">
            <Loader2 className="size-6 animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {(patients ?? []).map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => choose(p.id)}
                className="group flex flex-col items-center gap-3 rounded-2xl border border-border/80 bg-card p-5 text-center shadow-sm transition-all hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-md focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <span className="flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-slate-700 to-slate-950 text-lg font-semibold text-white shadow-inner">
                  {profileInitials(p.name)}
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-medium text-foreground">{p.name}</span>
                  {typeof p.age === "number" && (
                    <span className="block text-xs text-muted-foreground">{p.age} years old</span>
                  )}
                </span>
              </button>
            ))}

            <button
              type="button"
              onClick={() => setCreating(true)}
              className="group flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-transparent p-5 text-center text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <span className="flex size-16 items-center justify-center rounded-full border border-dashed border-current">
                <Plus className="size-6" />
              </span>
              <span className="font-medium">New profile</span>
            </button>
          </div>
        )}
      </div>

      <CreateProfileDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={onCreated}
      />
    </div>
  );
}
