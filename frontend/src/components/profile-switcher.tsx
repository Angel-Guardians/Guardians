"use client";

import { Check, ChevronsUpDown, LogOut, Plus, UserRound } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { CreateProfileDialog } from "@/components/create-profile-dialog";
import { api } from "@/lib/api";
import {
  clearActivePatientId,
  getActivePatientId,
  profileInitials,
  setActivePatientId,
} from "@/lib/profile-storage";
import type { Patient, PatientProfile } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Header dropdown for the active profile session: switch to another patient,
 * create a new one, or log out. The choice is stored in localStorage (see
 * profile-storage) and every data call defaults to it, so a switch retargets the
 * whole UI — and the agent, via /turn's patient_id. We reload after switching or
 * creating so each page refetches against the new patient; logging out clears the
 * session and SessionGate shows the profile picker.
 */
export function ProfileSwitcher() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  // Constant for the component's life — switching triggers a full reload — so a
  // lazy initializer is all we need (and avoids setState-in-effect churn).
  const [activeId] = useState<number | null>(() =>
    typeof window === "undefined" ? null : getActivePatientId(),
  );
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .listPatients()
      .then(setPatients)
      .catch(() => setPatients([]));
  }, []);

  // Close the menu on outside click or Escape.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const select = useCallback(
    (id: number) => {
      setOpen(false);
      if (id === activeId) return;
      setActivePatientId(id);
      // Reload so every page/component refetches for the newly active patient.
      window.location.reload();
    },
    [activeId],
  );

  const onCreated = useCallback((profile: PatientProfile) => {
    setActivePatientId(profile.id);
    window.location.reload();
  }, []);

  const logout = useCallback(() => {
    setOpen(false);
    // SessionGate listens for this and swaps in the profile picker — no reload.
    clearActivePatientId();
  }, []);

  const active = patients.find((p) => p.id === activeId);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          "flex items-center gap-2 rounded-full border border-border/80 bg-card py-1.5 pr-2.5 pl-2 text-sm shadow-sm transition-all hover:border-foreground/20 hover:shadow-md focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
          open && "border-primary/30 bg-primary/5",
        )}
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-gradient-to-br from-slate-700 to-slate-950 text-xs font-semibold text-white">
          {active ? profileInitials(active.name) : <UserRound className="size-4" />}
        </span>
        <span className="hidden max-w-28 truncate font-medium text-foreground sm:block">
          {active?.name ?? "Patient"}
        </span>
        <ChevronsUpDown className="size-4 text-muted-foreground" strokeWidth={2} />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-xl border border-border/80 bg-popover p-1 shadow-lg"
        >
          <p className="px-2.5 py-1.5 text-xs font-medium text-muted-foreground">
            Switch profile
          </p>
          {patients.map((p) => {
            const isActive = p.id === activeId;
            return (
              <button
                key={p.id}
                type="button"
                role="option"
                aria-selected={isActive}
                onClick={() => select(p.id)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors hover:bg-muted",
                  isActive && "bg-primary/5",
                )}
              >
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-slate-700 to-slate-950 text-xs font-semibold text-white">
                  {profileInitials(p.name)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium text-foreground">
                    {p.name}
                  </span>
                  {typeof p.age === "number" && (
                    <span className="block text-xs text-muted-foreground">
                      {p.age} years old
                    </span>
                  )}
                </span>
                {isActive && <Check className="size-4 shrink-0 text-primary" strokeWidth={2.5} />}
              </button>
            );
          })}

          <div className="my-1 h-px bg-border/70" />

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              setCreating(true);
            }}
            className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm font-medium transition-colors hover:bg-muted"
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-dashed border-border text-muted-foreground">
              <Plus className="size-4" />
            </span>
            Create new profile
          </button>

          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full">
              <LogOut className="size-4" />
            </span>
            Log out
          </button>
        </div>
      )}

      {creating && (
        <CreateProfileDialog onClose={() => setCreating(false)} onCreated={onCreated} />
      )}
    </div>
  );
}
