"use client";

import {
  Activity,
  ArrowRight,
  BellRing,
  FileText,
  HeartPulse,
  MapPin,
  Radio,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { PingButton } from "@/components/ping-button";
import { useEventStream, type StreamStatus } from "@/hooks/useEventStream";
import { api } from "@/lib/api";
import {
  getActivePatientId,
  profileInitials,
} from "@/lib/profile-storage";
import type { LocationPoint, Medication, PatientProfile, VitalPoint } from "@/lib/types";
import { cn } from "@/lib/utils";

const PATIENT_ID = getActivePatientId();

interface SectionCardProps {
  href: string;
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

function SectionCard({
  href,
  icon,
  iconBg,
  title,
  description,
  children,
  footer,
}: SectionCardProps) {
  return (
    <article className="flex h-full flex-col rounded-2xl border border-border/80 bg-card shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-md">
      <Link href={href} className="group flex flex-1 flex-col p-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl", iconBg)}>
            {icon}
          </div>
          <ArrowRight className="size-4 text-muted-foreground/50 transition-all group-hover:translate-x-0.5 group-hover:text-primary" />
        </div>
        <div className="mb-3 space-y-0.5">
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <div className="flex-1 space-y-2">{children}</div>
      </Link>
      {footer ? (
        <div className="border-t border-border/60 px-5 pb-5 pt-3">{footer}</div>
      ) : null}
    </article>
  );
}

function StatusDot({ status }: { status: StreamStatus }) {
  const color =
    status === "open"
      ? "bg-emerald-500"
      : status === "connecting"
        ? "bg-amber-400 animate-pulse"
        : "bg-muted-foreground/40";
  return <span className={cn("inline-block size-2 rounded-full", color)} />;
}

function fmtTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function latestVital(points: VitalPoint[], kind: "value" | "bp" = "value") {
  if (points.length === 0) return null;
  const latest = points[points.length - 1];
  if (kind === "bp" && latest.systolic != null && latest.diastolic != null) {
    return `${latest.systolic}/${latest.diastolic}`;
  }
  return String(latest.value);
}

function ProfileSummary() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .getPatientProfile(PATIENT_ID)
      .then((p) => active && setProfile(p))
      .catch(() => active && setProfile(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading profile…</p>;
  }

  if (!profile?.name) {
    return (
      <p className="text-sm text-muted-foreground">
        No patient profile yet. Set up name, contacts, and medications.
      </p>
    );
  }

  const primaryContact =
    profile.emergency_contacts.find((c) => c.priority === 1) ??
    profile.emergency_contacts[0];

  return (
    <>
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
          {profileInitials(profile.name) || "?"}
        </div>
        <div>
          <p className="font-medium">{profile.name}</p>
          <p className="text-sm text-muted-foreground">Age {profile.age || "—"}</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 pt-1">
        {profile.conditions.length > 0 ? (
          <Badge variant="secondary">{profile.conditions.length} conditions</Badge>
        ) : null}
        {profile.allergies.length > 0 ? (
          <Badge variant="destructive">{profile.allergies.length} allergies</Badge>
        ) : null}
        {profile.medications.length > 0 ? (
          <Badge variant="outline">{profile.medications.length} medications</Badge>
        ) : null}
      </div>
      {primaryContact ? (
        <p className="text-xs text-muted-foreground">
          Primary contact: {primaryContact.name} ({primaryContact.relationship.replace("_", " ")})
        </p>
      ) : null}
    </>
  );
}

function LiveSummary() {
  const { events, status } = useEventStream(50);

  const transcript = useMemo(
    () =>
      [...events]
        .reverse()
        .filter((e) => e.kind === "transcript")
        .map((e) => e.summary ?? "")
        .join(" "),
    [events],
  );

  const lastEvent = events[0];

  return (
    <>
      <div className="flex items-center gap-2">
        <StatusDot status={status} />
        <span className="text-sm font-medium capitalize">
          {status === "open" ? "Connected" : status === "connecting" ? "Connecting…" : "Disconnected"}
        </span>
        {events.length > 0 ? (
          <Badge variant="outline" className="ml-auto">
            {events.length} events
          </Badge>
        ) : null}
      </div>
      {lastEvent ? (
        <div className="rounded-lg bg-muted/50 px-3 py-2">
          <p className="text-xs text-muted-foreground">
            Latest · {fmtTime(lastEvent.ts)} · {lastEvent.kind}
          </p>
          <p className="mt-0.5 line-clamp-2 text-sm">{lastEvent.summary ?? "—"}</p>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Waiting for activity from Guardian…</p>
      )}
      {transcript ? (
        <p className="line-clamp-2 text-xs italic text-muted-foreground">
          &ldquo;{transcript.slice(-120)}&rdquo;
        </p>
      ) : null}
    </>
  );
}

function VitalsSummary() {
  const [hr, setHr] = useState<string | null>(null);
  const [spo2, setSpo2] = useState<string | null>(null);
  const [bp, setBp] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getVitals("hr").catch(() => null),
      api.getVitals("spo2").catch(() => null),
      api.getVitals("bp").catch(() => null),
    ])
      .then(([hrSeries, spo2Series, bpSeries]) => {
        if (!active) return;
        if (hrSeries) setHr(latestVital(hrSeries.points));
        if (spo2Series) setSpo2(latestVital(spo2Series.points));
        if (bpSeries) setBp(latestVital(bpSeries.points, "bp"));
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading vitals…</p>;
  }

  const hasData = hr || spo2 || bp;

  if (!hasData) {
    return (
      <p className="text-sm text-muted-foreground">
        No vitals yet. Readings appear once the wearable is streaming.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-3">
      {[
        { label: "Heart rate", value: hr, unit: "bpm" },
        { label: "SpO₂", value: spo2, unit: "%" },
        { label: "Blood pressure", value: bp, unit: "mmHg" },
      ].map((item) => (
        <div key={item.label} className="rounded-lg bg-muted/50 px-3 py-2 text-center">
          <p className="text-xs text-muted-foreground">{item.label}</p>
          <p className="mt-0.5 text-lg font-semibold tabular-nums">
            {item.value ?? "—"}
            {item.value ? (
              <span className="ml-0.5 text-xs font-normal text-muted-foreground">
                {item.unit}
              </span>
            ) : null}
          </p>
        </div>
      ))}
    </div>
  );
}

function RemindersSummary() {
  const [meds, setMeds] = useState<Medication[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .listMedications(PATIENT_ID)
      .then((m) => active && setMeds(m))
      .catch(() => active && setMeds([]))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading schedule…</p>;
  }

  if (!meds || meds.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No medications scheduled for today.
      </p>
    );
  }

  const taken = meds.filter((m) => m.taken).length;
  const pending = meds.length - taken;
  const next = meds.find((m) => !m.taken);

  return (
    <>
      <div className="flex items-baseline gap-3">
        <p className="text-3xl font-semibold tabular-nums">{pending}</p>
        <p className="text-sm text-muted-foreground">
          {pending === 1 ? "dose remaining" : "doses remaining"} today
        </p>
      </div>
      <div className="flex gap-2">
        <Badge variant="secondary">{taken} confirmed</Badge>
        {pending > 0 ? <Badge variant="outline">{pending} pending</Badge> : null}
      </div>
      {next ? (
        <p className="text-sm text-muted-foreground">
          Next: {next.name} {next.dose} at {fmtTime(next.scheduledFor)}
        </p>
      ) : (
        <p className="text-sm text-emerald-600 dark:text-emerald-500">All doses confirmed today.</p>
      )}
    </>
  );
}

function LocationSummary() {
  const [latest, setLatest] = useState<LocationPoint | null>(null);
  const [pointCount, setPointCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .getLocations()
      .then((points) => {
        if (!active) return;
        setLatest(points[0] ?? null);
        setPointCount(points.length);
      })
      .catch(() => active && setLatest(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading location…</p>;
  }

  if (!latest) {
    return (
      <p className="text-sm text-muted-foreground">
        No GPS fix yet. Positions appear once the watch is monitoring outdoors or
        near a window.
      </p>
    );
  }

  return (
    <>
      <p className="font-mono text-lg font-semibold tabular-nums">
        {latest.lat.toFixed(5)}, {latest.lng.toFixed(5)}
      </p>
      <div className="flex flex-wrap gap-2">
        {latest.accuracy != null ? (
          <Badge variant="outline">±{Math.round(latest.accuracy)} m</Badge>
        ) : null}
        {pointCount > 0 ? (
          <Badge variant="secondary">{pointCount} points (24h)</Badge>
        ) : null}
      </div>
      <p className="text-xs text-muted-foreground">Updated {fmtTime(latest.ts)}</p>
    </>
  );
}

export function Dashboard() {
  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
        <p className="max-w-2xl text-muted-foreground">
          Your at-a-glance view of Guardian. Tap any section for full details.
        </p>
      </header>

      <div className="grid gap-5 sm:grid-cols-2">
        <SectionCard
          href="/profile"
          icon={<UserRound className="size-5 text-teal-700 dark:text-teal-300" />}
          iconBg="bg-teal-500/10"
          title="Profile"
          description="Patient info, emergency contacts, and medications"
        >
          <ProfileSummary />
        </SectionCard>

        <SectionCard
          href="/live"
          icon={<Radio className="size-5 text-sky-700 dark:text-sky-300" />}
          iconBg="bg-sky-500/10"
          title="Live"
          description="What Guardian is hearing and doing right now"
        >
          <LiveSummary />
        </SectionCard>

        <SectionCard
          href="/vitals"
          icon={<Activity className="size-5 text-rose-700 dark:text-rose-300" />}
          iconBg="bg-rose-500/10"
          title="Vitals"
          description="Heart rate, SpO₂, and blood pressure trends"
        >
          <VitalsSummary />
        </SectionCard>

        <SectionCard
          href="/reminders"
          icon={<BellRing className="size-5 text-amber-700 dark:text-amber-300" />}
          iconBg="bg-amber-500/10"
          title="Reminders"
          description="Today's medications and check-ins"
        >
          <RemindersSummary />
        </SectionCard>

        <SectionCard
          href="/location"
          icon={<MapPin className="size-5 text-emerald-700 dark:text-emerald-300" />}
          iconBg="bg-emerald-500/10"
          title="Location"
          description="GPS track from the wearable — last 24 hours"
          footer={
            <Link
              href="/location-map.html"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            >
              <MapPin className="size-3.5" />
              View live map
            </Link>
          }
        >
          <LocationSummary />
        </SectionCard>

        <SectionCard
          href="/medical-history"
          icon={<FileText className="size-5 text-violet-700 dark:text-violet-300" />}
          iconBg="bg-violet-500/10"
          title="Medical history"
          description="Upload lab PDFs — Guardian extracts the results"
        >
          <p className="text-sm text-muted-foreground">
            Drop in a lab results PDF and we&apos;ll pull out the test values
            automatically.
          </p>
        </SectionCard>
      </div>

      <div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-dashed border-border/80 bg-muted/20 px-5 py-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <HeartPulse className="size-5 text-muted-foreground" />
          <div>
            <p className="text-sm font-medium">Backend connection</p>
            <p className="text-xs text-muted-foreground">
              Verify the local Guardian API is reachable
            </p>
          </div>
        </div>
        <div className="w-full sm:w-auto">
          <PingButton />
        </div>
      </div>
    </div>
  );
}
