"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Medication } from "@/lib/types";

const PATIENT_ID = 1;

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; meds: Medication[] };

function fmtTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function RemindersPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [confirming, setConfirming] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    api
      .listMedications(PATIENT_ID)
      .then((meds) => active && setState({ status: "ready", meds }))
      .catch((err: unknown) =>
        active &&
        setState({
          status: "error",
          message: err instanceof Error ? err.message : "Failed to load",
        }),
      );
    return () => {
      active = false;
    };
  }, []);

  async function confirm(med: Medication) {
    setConfirming(med.id);
    try {
      await api.confirmIntake(med.id);
      setState((prev) =>
        prev.status === "ready"
          ? {
              status: "ready",
              meds: prev.meds.map((m) => (m.id === med.id ? { ...m, taken: true } : m)),
            }
          : prev,
      );
    } catch {
      // Leave unchecked; backend POST /events is still a stub.
    } finally {
      setConfirming(null);
    }
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Reminders</h1>
        <p className="text-muted-foreground">Today&apos;s medications and check-ins</p>
      </header>

      <Card className="mx-auto max-w-2xl">
        <CardHeader>
          <CardTitle>Today&apos;s Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          {state.status === "ready" && state.meds.length > 0 ? (
            <ul className="divide-y divide-border">
              {state.meds.map((med) => (
                <li key={med.id} className="flex items-center justify-between gap-4 py-3">
                  <div className="space-y-0.5">
                    <p className="font-medium">
                      {med.name} <span className="text-muted-foreground">{med.dose}</span>
                    </p>
                    <p className="text-xs text-muted-foreground">{fmtTime(med.scheduledFor)}</p>
                  </div>
                  {med.taken ? (
                    <Badge>Confirmed</Badge>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={confirming === med.id}
                      onClick={() => confirm(med)}
                    >
                      {confirming === med.id ? "..." : "Confirm"}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Today&apos;s reminders will appear here once the schedule is configured.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
