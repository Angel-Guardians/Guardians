"use client";

import { Activity } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useEventStream } from "@/hooks/useEventStream";
import { api } from "@/lib/api";
import type { VitalKind, VitalPoint } from "@/lib/types";
import { cn } from "@/lib/utils";

const POLL_MS = 5000;

interface SensorMetric {
  kind: VitalKind;
  label: string;
  unit: string;
}

const SENSORS: SensorMetric[] = [
  { kind: "hr", label: "Heart rate", unit: "bpm" },
  { kind: "spo2", label: "SpO₂", unit: "%" },
  { kind: "bp", label: "Blood pressure", unit: "mmHg" },
  { kind: "steps", label: "Steps", unit: "" },
  { kind: "calories", label: "Calories", unit: "kcal" },
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

export function LiveSensorsPanel({ className }: { className?: string }) {
  const [values, setValues] = useState<Record<VitalKind, string | null>>({
    hr: null,
    spo2: null,
    bp: null,
    steps: null,
    calories: null,
  });
  const [loading, setLoading] = useState(true);
  const { events } = useEventStream(20);

  const load = useCallback(async () => {
    const results = await Promise.all(
      SENSORS.map((s) => api.getVitals(s.kind, "1h").catch(() => null)),
    );
    setValues(() => {
      const next: Record<VitalKind, string | null> = {
        hr: null,
        spo2: null,
        bp: null,
        steps: null,
        calories: null,
      };
      SENSORS.forEach((s, i) => {
        const series = results[i];
        next[s.kind] = series ? fmtValue(series.points, s.kind) : null;
      });
      return next;
    });
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    const vitalEvents = events.filter((e) => e.kind === "vital_sample");
    if (vitalEvents.length === 0) return;

    setValues((prev) => {
      const next = { ...prev };
      for (const ev of vitalEvents) {
        const kind = String(ev.payload?.kind ?? "");
        const value = Number(ev.payload?.value);
        if (!kind || Number.isNaN(value)) continue;
        const mapped = kind as VitalKind;
        if (mapped in next) {
          next[mapped] =
            mapped === "steps" || mapped === "calories"
              ? Math.round(value).toLocaleString()
              : String(Math.round(value * 10) / 10);
        }
      }
      return next;
    });
  }, [events]);

  return (
    <aside
      aria-label="Live sensor readings"
      className={cn(
        "flex shrink-0 flex-col rounded-xl border border-border/80 bg-muted/20",
        className,
      )}
    >
      <div className="flex items-center gap-2 border-b border-border/60 px-3 py-2.5">
        <Activity className="size-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Sensors
        </span>
      </div>

      <ul className="flex flex-col divide-y divide-border/50">
        {SENSORS.map((sensor) => {
          const value = values[sensor.kind];
          return (
            <li key={sensor.kind} className="px-3 py-2.5">
              <p className="text-[11px] font-medium text-muted-foreground">
                {sensor.label}
              </p>
              <p className="mt-0.5 text-lg font-semibold tabular-nums leading-tight">
                {loading && value == null ? (
                  <span className="text-sm font-normal text-muted-foreground">…</span>
                ) : value != null ? (
                  <>
                    {value}
                    {sensor.unit ? (
                      <span className="ml-1 text-xs font-normal text-muted-foreground">
                        {sensor.unit}
                      </span>
                    ) : null}
                  </>
                ) : (
                  <span className="text-sm font-normal text-muted-foreground">—</span>
                )}
              </p>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
