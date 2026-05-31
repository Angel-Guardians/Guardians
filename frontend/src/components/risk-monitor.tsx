"use client";

import { ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { useEventStream } from "@/hooks/useEventStream";
import { api } from "@/lib/api";
import { resolveActivePatientId } from "@/lib/profile-storage";
import type { RiskSnapshot } from "@/lib/types";
import { cn } from "@/lib/utils";

const POLL_MS = 5000;
const PATIENT_ID = resolveActivePatientId();

const LEVEL_STYLE: Record<
  RiskSnapshot["level"],
  { badge: string; bar: string; label: string; tier: string }
> = {
  low: {
    badge: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
    bar: "bg-emerald-500",
    label: "Low",
    tier: "Tier 1",
  },
  moderate: {
    badge: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
    bar: "bg-amber-500",
    label: "Moderate",
    tier: "Tier 2",
  },
  high: {
    badge: "bg-orange-500/15 text-orange-700 dark:text-orange-400",
    bar: "bg-orange-500",
    label: "High",
    tier: "Tier 3",
  },
  critical: {
    badge: "bg-red-600/15 text-red-700 dark:text-red-400",
    bar: "bg-red-600",
    label: "Critical",
    tier: "Tier 4",
  },
};

const TIER_BOX: Record<
  RiskSnapshot["level"],
  { box: string; title: string }
> = {
  low: {
    box: "border-sky-200/80 bg-sky-50/80 dark:border-sky-900 dark:bg-sky-950/40",
    title: "text-primary",
  },
  moderate: {
    box: "border-amber-200/80 bg-amber-50/80 dark:border-amber-900 dark:bg-amber-950/40",
    title: "text-amber-700 dark:text-amber-400",
  },
  high: {
    box: "border-orange-200/80 bg-orange-50/80 dark:border-orange-900 dark:bg-orange-950/40",
    title: "text-orange-700 dark:text-orange-400",
  },
  critical: {
    box: "border-red-300/80 bg-red-50/80 dark:border-red-900 dark:bg-red-950/40",
    title: "text-destructive",
  },
};

function tierSubtitle(snapshot: RiskSnapshot): string {
  if (snapshot.factors.length > 0) {
    return snapshot.factors.map((f) => f.detail).join(" · ");
  }
  if (snapshot.level === "low") {
    return "All channels within baseline. Passive watch — no agent engaged.";
  }
  if (snapshot.level === "moderate") {
    return "Elevated signals detected. Guardian is monitoring closely.";
  }
  return "Critical threshold reached. Agent may be engaged.";
}

function fmtTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime())
    ? ts
    : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

interface RiskMonitorProps {
  variant?: "full" | "bar" | "tier";
}

export function RiskMonitor({ variant = "full" }: RiskMonitorProps) {
  const [snapshot, setSnapshot] = useState<RiskSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { events } = useEventStream(30);

  const load = useCallback(async () => {
    try {
      const data = await api.getRiskScore(PATIENT_ID);
      setSnapshot(data);
      setError(null);
    } catch {
      setError("Unable to load risk score");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    const latest = events.find((e) => e.kind === "risk_score_updated");
    if (!latest?.payload) return;
    const p = latest.payload;
    setSnapshot({
      score: Number(p.score ?? 0),
      level: (p.level as RiskSnapshot["level"]) ?? "low",
      severity_tier: String(p.severity_tier ?? p.severity ?? ""),
      factors: Array.isArray(p.factors)
        ? (p.factors as RiskSnapshot["factors"])
        : [],
      updated_at: String(p.updated_at ?? latest.ts),
    });
  }, [events]);

  const isBar = variant === "bar";
  const isTier = variant === "tier";

  if (loading && !snapshot) {
    return (
      <div
        className={cn(
          "border border-border/80 bg-card shadow-sm",
          isBar || isTier
            ? "rounded-[14px] px-[18px] py-[14px]"
            : "rounded-2xl p-5",
        )}
      >
        <p className="text-sm text-muted-foreground">Loading risk score…</p>
      </div>
    );
  }

  if (error && !snapshot) {
    return (
      <div
        className={cn(
          "border border-dashed border-border/80 bg-muted/20",
          isBar || isTier
            ? "rounded-[14px] px-[18px] py-[14px]"
            : "rounded-2xl p-5",
        )}
      >
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (!snapshot) return null;

  const style = LEVEL_STYLE[snapshot.level];
  const tierBox = TIER_BOX[snapshot.level];
  const urgent = snapshot.level === "high" || snapshot.level === "critical";

  if (isTier) {
    return (
      <section
        role="status"
        aria-label={`Risk level ${style.label}, score ${snapshot.score}`}
        className={cn(
          "rounded-[14px] border px-[18px] py-[14px] transition-colors",
          tierBox.box,
        )}
      >
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          Risk classifier · severity tier
        </p>
        <p className={cn("mt-0.5 flex items-center gap-2.5 text-xl font-extrabold", tierBox.title)}>
          <span>{style.tier}</span>
          <span className="font-mono text-[11px] font-bold rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
            {snapshot.score.toFixed(0)} / 100
          </span>
        </p>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          {tierSubtitle(snapshot)}
        </p>
      </section>
    );
  }

  if (isBar) {
    return (
      <section
        role="status"
        aria-label={`Risk level ${style.label}, score ${snapshot.score}`}
        className={cn(
          "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card px-4 py-3 shadow-sm transition-colors",
          urgent ? "border-red-500/40" : "border-border/80",
          snapshot.level === "critical" && "ring-1 ring-red-500/30",
        )}
      >
        <div className="flex items-center gap-2">
          <ShieldAlert
            className={cn(
              "size-4 shrink-0",
              urgent ? "text-red-600 dark:text-red-400" : "text-primary",
              snapshot.level === "critical" && "animate-pulse",
            )}
          />
          <span className="text-sm font-medium">Risk</span>
        </div>

        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-semibold tabular-nums leading-none">
            {snapshot.score.toFixed(0)}
          </span>
          <span className="text-xs text-muted-foreground">/ 100</span>
        </div>

        <div className="h-2 min-w-[100px] flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full transition-all duration-500", style.bar)}
            style={{ width: `${Math.min(100, Math.max(0, snapshot.score))}%` }}
          />
        </div>

        <Badge className={cn("font-semibold capitalize", style.badge)}>
          {style.label}
        </Badge>

        <span className="text-xs text-muted-foreground">
          Updated {fmtTime(snapshot.updated_at)}
        </span>
      </section>
    );
  }

  return (
    <section
      role="status"
      aria-label={`Risk level ${style.label}, score ${snapshot.score}`}
      className={cn(
        "rounded-2xl border bg-card p-5 shadow-sm transition-colors",
        urgent ? "border-red-500/40" : "border-border/80",
        snapshot.level === "critical" && "ring-1 ring-red-500/30",
      )}
    >
      <div className="flex flex-wrap items-start gap-4">
        <div
          className={cn(
            "flex size-12 shrink-0 items-center justify-center rounded-xl",
            urgent ? "bg-red-500/10" : "bg-primary/10",
          )}
        >
          <ShieldAlert
            className={cn(
              "size-6",
              urgent ? "text-red-600 dark:text-red-400" : "text-primary",
              snapshot.level === "critical" && "animate-pulse",
            )}
          />
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold tracking-tight">Risk monitor</h2>
            <Badge className={cn("font-semibold capitalize", style.badge)}>
              {style.label}
            </Badge>
            <span className="ml-auto text-xs text-muted-foreground">
              Updated {fmtTime(snapshot.updated_at)}
            </span>
          </div>

          <div className="flex items-end gap-3">
            <p className="text-4xl font-semibold tabular-nums leading-none">
              {snapshot.score.toFixed(0)}
            </p>
            <p className="pb-0.5 text-sm text-muted-foreground">/ 100</p>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full transition-all duration-500", style.bar)}
              style={{ width: `${Math.min(100, Math.max(0, snapshot.score))}%` }}
            />
          </div>

          {snapshot.factors.length > 0 ? (
            <ul className="space-y-1.5 pt-1">
              {snapshot.factors.map((f) => (
                <li
                  key={f.name}
                  className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm"
                >
                  <span className="font-medium">{f.name}</span>
                  <span className="text-muted-foreground">{f.detail}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No contributing factors — vitals look stable.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
