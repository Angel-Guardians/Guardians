"use client";

import { AlertTriangle, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { FallEvent } from "@/lib/types";

const POLL_MS = 4000;
const RECENT_MS = 15 * 60 * 1000; // only banner falls from the last 15 minutes

function label(kind: string): string {
  switch (kind) {
    case "fall_confirmed":
      return "Fall confirmed — no response";
    case "fall_suspected":
      return "Possible fall detected";
    case "fall_cancelled":
      return "Fall alert — resident marked OK";
    default:
      return kind;
  }
}

function fmt(ts: string): string {
  const d = new Date(ts);
  return Number.isNaN(d.getTime())
    ? ts
    : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/**
 * Global watcher: polls the backend for fall events the watch has delivered,
 * fires a desktop (browser) notification on each new one, and shows a banner.
 * Mounted once in the root layout so it's live on every page.
 */
export function FallAlerts() {
  const [latest, setLatest] = useState<FallEvent | null>(null);
  const [dismissed, setDismissed] = useState<string | null>(null);
  const seenTs = useRef<string | null>(null);

  // Ask for notification permission once.
  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      void Notification.requestPermission().catch(() => {});
    }
  }, []);

  useEffect(() => {
    let active = true;

    const notify = (f: FallEvent) => {
      if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
      try {
        const n = new Notification(`⚠️ Guardian: ${label(f.kind)}`, {
          body: `From ${f.source} · ${fmt(f.ts)} · peak ${f.value.toFixed(1)} g`,
          tag: "guardian-fall",
          requireInteraction: f.kind !== "fall_cancelled",
        });
        n.onclick = () => window.focus();
      } catch {
        /* notifications unavailable */
      }
    };

    const tick = async () => {
      try {
        const falls = await api.getFalls("24h");
        if (!active || falls.length === 0) return;
        const newest = falls[0]; // backend returns newest-first
        if (seenTs.current !== null && newest.ts !== seenTs.current) {
          notify(newest);
          setDismissed(null);
        }
        seenTs.current = newest.ts;
        setLatest(newest);
      } catch {
        /* backend unreachable; retry next tick */
      }
    };

    void tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  if (!latest || dismissed === latest.ts) return null;
  if (Date.now() - new Date(latest.ts).getTime() >= RECENT_MS) return null;

  const urgent = latest.kind !== "fall_cancelled";
  return (
    <div
      role="alert"
      className={`flex items-center gap-3 px-6 py-3 text-sm text-white md:px-10 ${
        urgent ? "bg-red-600" : "bg-amber-500"
      }`}
    >
      <AlertTriangle className={`size-5 shrink-0 ${urgent ? "animate-pulse" : ""}`} />
      <div className="flex-1 leading-tight">
        <span className="font-semibold">{label(latest.kind)}</span>
        <span className="opacity-90">
          {" "}
          — {latest.source} · {fmt(latest.ts)} · peak {latest.value.toFixed(1)} g
        </span>
      </div>
      <button
        type="button"
        onClick={() => setDismissed(latest.ts)}
        aria-label="Dismiss alert"
        className="rounded p-1 transition-colors hover:bg-white/20"
      >
        <X className="size-4" />
      </button>
    </div>
  );
}
