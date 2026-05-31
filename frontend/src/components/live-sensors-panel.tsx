"use client";

import {
  Activity,
  Droplets,
  Footprints,
  Gauge,
  PersonStanding,
} from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { useEventStream } from "@/hooks/useEventStream";
import { api } from "@/lib/api";
import type { FallEvent, VitalKind, VitalPoint } from "@/lib/types";
import { cn } from "@/lib/utils";

const POLL_MS = 5000;
// A fall only counts as "active" while it is recent — matches the backend
// FALL_WINDOW. Older events are history, not a current emergency, so the motion
// tile must not pin "Fall confirmed / impact detected" indefinitely.
const FALL_ACTIVE_MS = 30 * 60 * 1000;

interface SensorTile {
  id: string;
  label: string;
  unit: string;
  icon: ReactNode;
  kind?: VitalKind;
}

const TILES: SensorTile[] = [
  {
    id: "hr",
    kind: "hr",
    label: "Heart rate",
    unit: "bpm",
    icon: <Activity className="size-3.5" />,
  },
  {
    id: "spo2",
    kind: "spo2",
    label: "Blood oxygen",
    unit: "% SpO₂",
    icon: <Droplets className="size-3.5" />,
  },
  {
    id: "bp",
    kind: "bp",
    label: "Blood pressure",
    unit: "mmHg",
    icon: <Gauge className="size-3.5" />,
  },
  {
    id: "motion",
    label: "Motion / fall",
    unit: "",
    icon: <PersonStanding className="size-3.5" />,
  },
  {
    id: "steps",
    kind: "steps",
    label: "Steps",
    unit: "today",
    icon: <Footprints className="size-3.5" />,
  },
];

function fmtValue(points: VitalPoint[], kind: VitalKind): string | null {
  if (points.length === 0) return null;
  const latest = points[points.length - 1];
  if (kind === "bp" && latest.systolic != null && latest.diastolic != null) {
    return `${latest.systolic}/${latest.diastolic}`;
  }
  if (kind === "steps" || kind === "calories") {
    return Math.round(latest.value).toLocaleString();
  }
  return String(Math.round(latest.value * 10) / 10);
}

function fmtMotion(falls: FallEvent[]): { value: string; sub: string; hot: boolean } {
  const recent = falls[0];
  if (!recent) {
    return { value: "Resting", sub: "no impact detected", hot: false };
  }
  // A confirmed/suspected fall stays "hot" only while it is recent. Once it ages
  // out it becomes history — show the patient as resting, not perpetually fallen.
  const ageMs = Date.now() - new Date(recent.ts).getTime();
  const stale = Number.isNaN(ageMs) || ageMs > FALL_ACTIVE_MS;
  if (recent.kind === "fall_cancelled") {
    return { value: "Clear", sub: "all clear", hot: false };
  }
  if (stale) {
    return { value: "Resting", sub: "no impact detected", hot: false };
  }
  const hot =
    recent.kind === "fall_suspected" || recent.kind === "fall_confirmed";
  const value =
    recent.kind === "fall_confirmed"
      ? "Fall confirmed"
      : recent.kind === "fall_suspected"
        ? "Fall detected"
        : recent.kind.replace("_", " ");
  return { value, sub: hot ? "impact detected" : "all clear", hot };
}

function HrSparkline({
  points,
  hot,
}: {
  points: VitalPoint[];
  hot: boolean;
}) {
  if (points.length < 2) return null;
  const values = points.slice(-24).map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 120;
  const h = 22;
  const coords = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - 4 - ((v - min) / range) * (h - 8);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      className="mt-1 h-[22px] w-full"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        points={coords}
        fill="none"
        stroke={hot ? "var(--destructive)" : "var(--primary)"}
        strokeWidth="1.8"
      />
    </svg>
  );
}

function SensorTileCard({
  tile,
  value,
  sub,
  hot,
  loading,
  sparkPoints,
}: {
  tile: SensorTile;
  value: string | null;
  sub?: string;
  hot?: boolean;
  loading: boolean;
  sparkPoints?: VitalPoint[];
}) {
  return (
    <div
      className={cn(
        "rounded-[14px] border bg-card px-[15px] py-2.5 transition-colors",
        hot
          ? "border-destructive/50 shadow-[0_0_0_3px_oklch(0.7_0.2_27/0.1)]"
          : "border-border",
      )}
    >
      <div className="flex items-center gap-2 text-[11.5px] font-semibold text-muted-foreground">
        {tile.icon}
        {tile.label}
      </div>
      <p
        className={cn(
          "mt-1 flex items-baseline gap-1.5 text-[22px] font-extrabold tabular-nums leading-none",
          hot && "text-destructive",
        )}
      >
        {loading && value == null ? (
          <span className="text-sm font-normal text-muted-foreground">…</span>
        ) : value != null ? (
          <>
            <span>{value}</span>
            {tile.unit ? (
              <span className="text-[11px] font-semibold text-muted-foreground">
                {tile.unit}
              </span>
            ) : null}
          </>
        ) : (
          <span className="text-base font-normal text-muted-foreground">—</span>
        )}
      </p>
      {sub ? (
        <p className="mt-0.5 text-[11px] font-semibold text-muted-foreground">
          {sub}
        </p>
      ) : null}
      {tile.id === "hr" && sparkPoints && sparkPoints.length > 1 ? (
        <HrSparkline points={sparkPoints} hot={!!hot} />
      ) : null}
    </div>
  );
}

export function LiveSensorsPanel({ className }: { className?: string }) {
  const [values, setValues] = useState<Record<string, string | null>>({});
  const [hrPoints, setHrPoints] = useState<VitalPoint[]>([]);
  const [motion, setMotion] = useState({
    value: "Resting",
    sub: "no impact detected",
    hot: false,
  });
  const [subs, setSubs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const { events } = useEventStream(20);

  const load = useCallback(async () => {
    const vitalKinds = TILES.filter((t) => t.kind).map((t) => t.kind!);
    const results = await Promise.all([
      ...vitalKinds.map((k) => api.getVitals(k, "1h").catch(() => null)),
      api.getFalls("24h").catch(() => [] as FallEvent[]),
    ]);
    const fallResult = results[results.length - 1] as FallEvent[];
    const vitalResults = results.slice(0, vitalKinds.length) as (
      | { points: VitalPoint[] }
      | null
    )[];

    const next: Record<string, string | null> = {};
    const nextSubs: Record<string, string> = {};

    TILES.forEach((tile) => {
      if (!tile.kind) return;
      const idx = vitalKinds.indexOf(tile.kind);
      const series = vitalResults[idx];
      next[tile.id] = series ? fmtValue(series.points, tile.kind) : null;
      if (tile.kind === "spo2" && series?.points.length) {
        const v = series.points[series.points.length - 1].value;
        nextSubs.spo2 = v < 93 ? "low — monitoring" : "normal range";
      }
      if (tile.kind === "hr" && series?.points.length) {
        setHrPoints(series.points);
        nextSubs.hr = "live stream";
      }
    });

    setValues(next);
    setSubs(nextSubs);
    setMotion(fmtMotion(fallResult));
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    for (const ev of events) {
      if (ev.kind === "vital_sample" && ev.payload) {
        const kind = String(ev.payload.kind ?? "");
        const value = Number(ev.payload.value);
        if (!kind || Number.isNaN(value)) continue;
        const tile = TILES.find((t) => t.kind === kind);
        if (!tile) continue;
        setValues((prev) => ({
          ...prev,
          [tile.id]:
            kind === "steps"
              ? Math.round(value).toLocaleString()
              : String(Math.round(value * 10) / 10),
        }));
        if (kind === "spo2") {
          setSubs((prev) => ({
            ...prev,
            spo2: value < 93 ? "low — monitoring" : "normal range",
          }));
        }
      }
    }
  }, [events]);

  const hrNum = values.hr ? Number(values.hr) : null;
  const spo2Num = values.spo2 ? Number(values.spo2) : null;

  return (
    <aside
      aria-label="Live sensor readings"
      className={cn(
        "flex w-full flex-col gap-1.5 lg:w-[250px] lg:shrink-0",
        className,
      )}
    >
      {TILES.map((tile) => {
        if (tile.id === "motion") {
          return (
            <SensorTileCard
              key={tile.id}
              tile={tile}
              value={motion.value}
              sub={motion.sub}
              hot={motion.hot}
              loading={loading}
            />
          );
        }

        const hot =
          tile.id === "hr"
            ? hrNum != null && hrNum > 110
            : tile.id === "spo2"
              ? spo2Num != null && spo2Num < 93
              : false;

        return (
          <SensorTileCard
            key={tile.id}
            tile={tile}
            value={values[tile.id] ?? null}
            sub={subs[tile.id]}
            hot={hot}
            loading={loading}
            sparkPoints={tile.id === "hr" ? hrPoints : undefined}
          />
        );
      })}
    </aside>
  );
}
