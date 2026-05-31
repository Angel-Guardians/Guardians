"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { getActivePatientId } from "@/lib/profile-storage";
import type { Medication } from "@/lib/types";

const PATIENT_ID = getActivePatientId();

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

  const takenCount =
    state.status === "ready" ? state.meds.filter((m) => m.taken).length : 0;
  const totalCount = state.status === "ready" ? state.meds.length : 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reminders"
        description="Today's medication schedule. Confirm each dose when taken."
        action={
          state.status === "ready" && totalCount > 0 ? (
            <Badge variant="secondary">
              {takenCount}/{totalCount} confirmed
            </Badge>
          ) : null
        }
      />

      <Card className="mx-auto max-w-2xl rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle>Today&apos;s schedule</CardTitle>
        </CardHeader>
        <CardContent>
          {state.status === "ready" && state.meds.length > 0 ? (
            <ul className="divide-y divide-border">
              {state.meds.map((med) => (
                <li key={med.id} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
                  <div className="space-y-0.5">
                    <p className="font-medium">
                      {med.name}{" "}
                      <span className="font-normal text-muted-foreground">{med.dose}</span>
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
            <p className="py-12 text-center text-sm text-muted-foreground">
              Today&apos;s reminders will appear here once the schedule is configured.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
