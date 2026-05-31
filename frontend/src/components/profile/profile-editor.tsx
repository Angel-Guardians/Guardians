"use client";

import {
  AlertTriangle,
  HeartPulse,
  Pill,
  Plus,
  RotateCcw,
  Save,
  Trash2,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import {
  EMPTY_PATIENT_PROFILE,
  notifyProfileUpdated,
  profileInitials,
} from "@/lib/profile-storage";
import type {
  EmergencyContact,
  PatientProfile,
  ProfileMedication,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "zh", label: "Chinese (Mandarin)" },
  { value: "ar", label: "Arabic" },
  { value: "pt", label: "Portuguese" },
] as const;

const RELATIONSHIPS = [
  "daughter",
  "son",
  "spouse",
  "neighbour",
  "family_doctor",
  "caregiver",
  "other",
] as const;

function emptyContact(): EmergencyContact {
  return { name: "", relationship: "daughter", phone: "", priority: 1 };
}

function emptyMedication(): ProfileMedication {
  return {
    name: "",
    dose: "",
    schedule_cron: "0 8 * * *",
    with_food: false,
    notes: "",
  };
}

function profileEquals(a: PatientProfile, b: PatientProfile) {
  return JSON.stringify(a) === JSON.stringify(b);
}

interface TagInputProps {
  id: string;
  label: string;
  description?: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  variant?: "default" | "destructive";
}

function TagInput({
  id,
  label,
  description,
  values,
  onChange,
  placeholder = "Type and press Enter",
  variant = "default",
}: TagInputProps) {
  const [draft, setDraft] = useState("");

  function addTag(raw: string) {
    const tag = raw.trim();
    if (!tag || values.some((v) => v.toLowerCase() === tag.toLowerCase())) return;
    onChange([...values, tag]);
    setDraft("");
  }

  function removeTag(index: number) {
    onChange(values.filter((_, i) => i !== index));
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {description ? (
        <p className="text-xs text-muted-foreground">{description}</p>
      ) : null}
      <div
        className={cn(
          "flex min-h-9 flex-wrap items-center gap-1.5 rounded-lg border border-input bg-background px-2 py-1.5 shadow-xs focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 dark:bg-input/30",
          variant === "destructive" && "border-destructive/30",
        )}
      >
        {values.map((tag, i) => (
          <Badge
            key={`${tag}-${i}`}
            variant={variant === "destructive" ? "destructive" : "secondary"}
            className="gap-1 pr-1"
          >
            {tag}
            <button
              type="button"
              aria-label={`Remove ${tag}`}
              className="rounded-full p-0.5 hover:bg-foreground/10"
              onClick={() => removeTag(i)}
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        <input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              addTag(draft);
            } else if (e.key === "Backspace" && !draft && values.length > 0) {
              removeTag(values.length - 1);
            }
          }}
          onBlur={() => addTag(draft)}
          placeholder={values.length === 0 ? placeholder : ""}
          className="min-w-[8rem] flex-1 bg-transparent px-1 py-0.5 text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>
    </div>
  );
}

export function ProfileEditor() {
  const [profile, setProfile] = useState<PatientProfile>(EMPTY_PATIENT_PROFILE);
  const [savedProfile, setSavedProfile] = useState<PatientProfile>(EMPTY_PATIENT_PROFILE);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);

  const loadProfile = useCallback(async () => {
    setLoadState("loading");
    setLoadError(null);
    try {
      const loaded = await api.getPatientProfile();
      setProfile(loaded);
      setSavedProfile(loaded);
      setLoadState("ready");
    } catch (err: unknown) {
      setLoadState("error");
      setLoadError(err instanceof Error ? err.message : "Failed to load profile");
    }
  }, []);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  const isDirty = useMemo(
    () => !profileEquals(profile, savedProfile),
    [profile, savedProfile],
  );

  const update = useCallback(
    <K extends keyof PatientProfile>(key: K, value: PatientProfile[K]) => {
      setProfile((prev) => ({ ...prev, [key]: value }));
      setSaveNotice(null);
    },
    [],
  );

  async function handleSave() {
    setSaving(true);
    setSaveNotice(null);
    try {
      const { id, ...body } = profile;
      const saved = await api.updatePatientProfile(id, body);
      setProfile(saved);
      setSavedProfile(saved);
      notifyProfileUpdated(saved);
      setSaveNotice("Profile saved to database.");
    } catch (err: unknown) {
      setSaveNotice(
        err instanceof Error ? err.message : "Failed to save profile",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleReload() {
    await loadProfile();
    setSaveNotice("Reloaded from database.");
  }

  if (loadState === "loading") {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading profile…</p>
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-12 text-center">
        <p className="text-sm text-destructive">{loadError}</p>
        <p className="text-sm text-muted-foreground">
          Make sure Postgres is running and you have seeded a patient (
          <code className="rounded bg-muted px-1">make db-up seed</code>).
        </p>
        <Button type="button" variant="outline" onClick={() => void loadProfile()}>
          <RotateCcw />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-20">
      {/* Hero header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary text-lg font-semibold text-primary-foreground">
            {profileInitials(profile.name) || "?"}
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Patient Profile</h1>
            <p className="max-w-xl text-muted-foreground">
              Medical history, emergency contacts, and medications Guardian uses during
              incidents and daily check-ins.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => void handleReload()}>
            <RotateCcw />
            Reload
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!isDirty || saving}
            onClick={() => void handleSave()}
          >
            <Save />
            {saving ? "Saving…" : "Save profile"}
          </Button>
        </div>
      </div>

      {saveNotice ? (
        <p className="rounded-lg border border-border bg-muted/50 px-4 py-2.5 text-sm text-muted-foreground">
          {saveNotice}
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Basic info */}
        <Card className="lg:col-span-2">
          <CardHeader className="border-b">
            <div className="flex items-center gap-2">
              <UserRound className="size-4 text-muted-foreground" />
              <CardTitle>Basic information</CardTitle>
            </div>
            <CardDescription>Name, age, and language preferences</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 pt-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="name">Full name</Label>
              <Input
                id="name"
                value={profile.name}
                onChange={(e) => update("name", e.target.value)}
                placeholder="Eleanor"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="age">Age</Label>
              <Input
                id="age"
                type="number"
                min={0}
                max={130}
                value={profile.age || ""}
                onChange={(e) =>
                  update("age", e.target.value === "" ? 0 : Number(e.target.value))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="language">Primary language</Label>
              <select
                id="language"
                value={profile.primary_language}
                onChange={(e) => update("primary_language", e.target.value)}
                className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.value} value={lang.value}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2 sm:col-span-2 lg:col-span-4">
              <Label htmlFor="notes">Care notes</Label>
              <Textarea
                id="notes"
                value={profile.notes ?? ""}
                onChange={(e) => update("notes", e.target.value || null)}
                placeholder="Living situation, mobility aids, communication preferences…"
              />
            </div>
          </CardContent>
        </Card>

        {/* Medical */}
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center gap-2">
              <HeartPulse className="size-4 text-muted-foreground" />
              <CardTitle>Medical history</CardTitle>
            </div>
            <CardDescription>
              Conditions and allergies included in 911 summaries
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 pt-4">
            <TagInput
              id="conditions"
              label="Conditions"
              description="e.g. cardiac history, diabetes, mobility limitations"
              values={profile.conditions}
              onChange={(conditions) => update("conditions", conditions)}
              placeholder="Add condition"
            />
            <TagInput
              id="allergies"
              label="Allergies"
              description="Drug and food allergies — highlighted in emergencies"
              values={profile.allergies}
              onChange={(allergies) => update("allergies", allergies)}
              placeholder="Add allergy"
              variant="destructive"
            />
          </CardContent>
        </Card>

        {/* Emergency contacts */}
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center justify-between gap-2">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Users className="size-4 text-muted-foreground" />
                  <CardTitle>Emergency contacts</CardTitle>
                </div>
                <CardDescription>Call order — priority 1 is contacted first</CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  update("emergency_contacts", [
                    ...profile.emergency_contacts,
                    emptyContact(),
                  ])
                }
              >
                <Plus />
                Add
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {profile.emergency_contacts.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No contacts yet. Add at least one person Guardian can reach during an
                incident.
              </p>
            ) : (
              profile.emergency_contacts.map((contact, index) => (
                <div
                  key={index}
                  className="space-y-3 rounded-lg border border-border/80 bg-muted/20 p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline">Priority {contact.priority}</Badge>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Remove contact"
                      onClick={() =>
                        update(
                          "emergency_contacts",
                          profile.emergency_contacts.filter((_, i) => i !== index),
                        )
                      }
                    >
                      <Trash2 className="text-muted-foreground" />
                    </Button>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor={`contact-name-${index}`}>Name</Label>
                      <Input
                        id={`contact-name-${index}`}
                        value={contact.name}
                        onChange={(e) => {
                          const next = [...profile.emergency_contacts];
                          next[index] = { ...contact, name: e.target.value };
                          update("emergency_contacts", next);
                        }}
                        placeholder="Maria"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`contact-rel-${index}`}>Relationship</Label>
                      <select
                        id={`contact-rel-${index}`}
                        value={contact.relationship}
                        onChange={(e) => {
                          const next = [...profile.emergency_contacts];
                          next[index] = { ...contact, relationship: e.target.value };
                          update("emergency_contacts", next);
                        }}
                        className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
                      >
                        {RELATIONSHIPS.map((rel) => (
                          <option key={rel} value={rel}>
                            {rel.replace("_", " ")}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`contact-phone-${index}`}>Phone</Label>
                      <Input
                        id={`contact-phone-${index}`}
                        type="tel"
                        value={contact.phone}
                        onChange={(e) => {
                          const next = [...profile.emergency_contacts];
                          next[index] = { ...contact, phone: e.target.value };
                          update("emergency_contacts", next);
                        }}
                        placeholder="+1 (555) 555-0111"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`contact-priority-${index}`}>Priority</Label>
                      <Input
                        id={`contact-priority-${index}`}
                        type="number"
                        min={1}
                        max={9}
                        value={contact.priority}
                        onChange={(e) => {
                          const next = [...profile.emergency_contacts];
                          next[index] = {
                            ...contact,
                            priority: Number(e.target.value) || 1,
                          };
                          update("emergency_contacts", next);
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Medications */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex items-center justify-between gap-2">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Pill className="size-4 text-muted-foreground" />
                <CardTitle>Medications</CardTitle>
              </div>
              <CardDescription>
                Doses and schedules for reminders and drug-interaction checks
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                update("medications", [...profile.medications, emptyMedication()])
              }
            >
              <Plus />
              Add medication
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {profile.medications.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No medications configured. Add entries to power reminder nudges.
            </p>
          ) : (
            <div className="space-y-4">
              {profile.medications.map((med, index) => (
                <div key={index}>
                  {index > 0 ? <Separator className="mb-4" /> : null}
                  <div className="grid gap-3 lg:grid-cols-12 lg:items-end">
                    <div className="space-y-2 lg:col-span-3">
                      <Label htmlFor={`med-name-${index}`}>Name</Label>
                      <Input
                        id={`med-name-${index}`}
                        value={med.name}
                        onChange={(e) => {
                          const next = [...profile.medications];
                          next[index] = { ...med, name: e.target.value };
                          update("medications", next);
                        }}
                        placeholder="Lisinopril"
                      />
                    </div>
                    <div className="space-y-2 lg:col-span-2">
                      <Label htmlFor={`med-dose-${index}`}>Dose</Label>
                      <Input
                        id={`med-dose-${index}`}
                        value={med.dose}
                        onChange={(e) => {
                          const next = [...profile.medications];
                          next[index] = { ...med, dose: e.target.value };
                          update("medications", next);
                        }}
                        placeholder="10 mg"
                      />
                    </div>
                    <div className="space-y-2 lg:col-span-3">
                      <Label htmlFor={`med-cron-${index}`}>Schedule (cron)</Label>
                      <Input
                        id={`med-cron-${index}`}
                        value={med.schedule_cron}
                        onChange={(e) => {
                          const next = [...profile.medications];
                          next[index] = { ...med, schedule_cron: e.target.value };
                          update("medications", next);
                        }}
                        placeholder="0 8 * * *"
                        className="font-mono text-xs"
                      />
                    </div>
                    <div className="space-y-2 lg:col-span-3">
                      <Label htmlFor={`med-notes-${index}`}>Notes</Label>
                      <Input
                        id={`med-notes-${index}`}
                        value={med.notes ?? ""}
                        onChange={(e) => {
                          const next = [...profile.medications];
                          next[index] = { ...med, notes: e.target.value || null };
                          update("medications", next);
                        }}
                        placeholder="With breakfast"
                      />
                    </div>
                    <div className="flex items-center gap-3 lg:col-span-1">
                      <label className="flex cursor-pointer items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={med.with_food}
                          onChange={(e) => {
                            const next = [...profile.medications];
                            next[index] = { ...med, with_food: e.target.checked };
                            update("medications", next);
                          }}
                          className="size-4 rounded border-input accent-primary"
                        />
                        With food
                      </label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Remove medication"
                        onClick={() =>
                          update(
                            "medications",
                            profile.medications.filter((_, i) => i !== index),
                          )
                        }
                      >
                        <Trash2 className="text-muted-foreground" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="mt-4 text-xs text-muted-foreground">
            Cron examples: <code className="rounded bg-muted px-1">0 8 * * *</code> daily at
            8:00 AM · <code className="rounded bg-muted px-1">0 8,20 * * *</code> at 8 AM
            and 8 PM
          </p>
        </CardContent>
      </Card>

      {/* Summary preview */}
      <Card className="border-dashed">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-4 text-amber-600 dark:text-amber-500" />
            <CardTitle>Emergency summary preview</CardTitle>
          </div>
          <CardDescription>
            What Guardian would include in a mock 911 call today
          </CardDescription>
        </CardHeader>
        <CardContent>
          <blockquote className="rounded-lg bg-muted/40 px-4 py-3 text-sm leading-relaxed text-muted-foreground">
            Patient{" "}
            <span className="font-medium text-foreground">
              {profile.name || "Unknown"}, age {profile.age || "—"}
            </span>
            {profile.conditions.length > 0 ? (
              <>
                {" "}
                with{" "}
                <span className="font-medium text-foreground">
                  {profile.conditions.join(", ")}
                </span>
              </>
            ) : null}
            .{" "}
            {profile.allergies.length > 0 ? (
              <>
                Allergies:{" "}
                <span className="font-medium text-destructive">
                  {profile.allergies.join(", ")}
                </span>
                .{" "}
              </>
            ) : null}
            Primary contact:{" "}
            <span className="font-medium text-foreground">
              {profile.emergency_contacts.find((c) => c.priority === 1)?.name ||
                profile.emergency_contacts[0]?.name ||
                "not set"}
            </span>
            .
          </blockquote>
        </CardContent>
      </Card>

      {/* Sticky save bar */}
      {isDirty ? (
        <div className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-background/95 px-6 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">You have unsaved changes</p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setProfile(savedProfile);
                  setSaveNotice(null);
                }}
              >
                Discard
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={saving}
                onClick={() => void handleSave()}
              >
                <Save />
                {saving ? "Saving…" : "Save profile"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
