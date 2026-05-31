"use client";

import { Loader2, UserPlus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import type { PatientProfile, PatientProfileUpdate } from "@/lib/types";

interface CreateProfileDialogProps {
  onClose: () => void;
  /** Called with the freshly created profile after a successful save. */
  onCreated: (profile: PatientProfile) => void;
}

/**
 * Quick-create modal: captures just the essentials (name, age, optional home
 * location) and creates the patient. The rest of the profile — conditions,
 * medications, emergency contacts — is filled in afterward on the /profile page.
 *
 * Mounted only while open (by the parent), so its state is always fresh.
 */
export function CreateProfileDialog({ onClose, onCreated }: CreateProfileDialogProps) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  // Autofocus the first field and close on Escape (no state writes here).
  useEffect(() => {
    const id = window.setTimeout(() => nameRef.current?.focus(), 50);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const ageNum = Number(age);
  const canSubmit =
    name.trim().length > 0 && Number.isFinite(ageNum) && ageNum > 0 && ageNum < 130;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || saving) return;
    setSaving(true);
    setError(null);
    const body: PatientProfileUpdate = {
      name: name.trim(),
      age: ageNum,
      conditions: [],
      allergies: [],
      primary_language: "en",
      location: location.trim() || null,
      bio: null,
      notes: null,
      emergency_contacts: [],
      medications: [],
    };
    try {
      const created = await api.createPatient(body);
      onCreated(created);
    } catch (err: unknown) {
      setSaving(false);
      setError(
        err instanceof ApiError
          ? `Couldn't create profile (${err.status}).`
          : "Couldn't create profile. Is the backend running?",
      );
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Create new profile"
    >
      <button
        type="button"
        aria-label="Close"
        className="absolute inset-0 bg-background/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-md rounded-2xl border border-border/80 bg-card p-6 shadow-xl"
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute top-4 right-4 flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="size-4" />
        </button>

        <div className="mb-5 flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <UserPlus className="size-5" strokeWidth={2} />
          </div>
          <div>
            <h2 className="text-base font-semibold leading-tight">New profile</h2>
            <p className="text-xs text-muted-foreground">
              You can add medical details later.
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="np-name">Name</Label>
            <Input
              id="np-name"
              ref={nameRef}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Eleanor"
              autoComplete="off"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="np-age">Age</Label>
            <Input
              id="np-age"
              type="number"
              min={1}
              max={129}
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="e.g. 70"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="np-location">
              Home address <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Input
              id="np-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. 42 Maple Street, Toronto"
              autoComplete="off"
            />
          </div>
        </div>

        {error && (
          <p className="mt-4 text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button type="button" variant="ghost" size="lg" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" size="lg" disabled={!canSubmit || saving}>
            {saving && <Loader2 className="animate-spin" />}
            Create &amp; switch
          </Button>
        </div>
      </form>
    </div>
  );
}
