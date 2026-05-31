"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useEventStream, type StreamStatus } from "@/hooks/useEventStream";

const STATUS_LABEL: Record<StreamStatus, string> = {
  connecting: "Connecting...",
  open: "Live",
  closed: "Disconnected",
};

function StatusBadge({ status }: { status: StreamStatus }) {
  return (
    <Badge variant={status === "open" ? "default" : "secondary"}>
      {STATUS_LABEL[status]}
    </Badge>
  );
}

function fmtTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString();
}

export default function LivePage() {
  const { events, status, clearEvents } = useEventStream();
  const [resetting, setResetting] = useState(false);

  async function handleReset() {
    setResetting(true);
    try {
      await api.resetContext();
      clearEvents();
    } catch {
      // Backend unreachable; leave the log as-is.
    } finally {
      setResetting(false);
    }
  }

  // Transcript = the running text of transcript-kind events, oldest first.
  const transcript = useMemo(
    () =>
      [...events]
        .reverse()
        .filter((e) => e.kind === "transcript")
        .map((e) => e.summary ?? "")
        .join(" "),
    [events],
  );

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Live</h1>
          <p className="text-muted-foreground">Event stream + active transcript</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="destructive"
            size="sm"
            onClick={handleReset}
            disabled={resetting}
          >
            {resetting ? "Resetting..." : "Reset context"}
          </Button>
          <StatusBadge status={status} />
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Event Log</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Waiting for events from the backend ({STATUS_LABEL[status].toLowerCase()}).
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-28">Time</TableHead>
                    <TableHead className="w-32">Kind</TableHead>
                    <TableHead>Summary</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((e) => (
                    <TableRow key={e.id}>
                      <TableCell className="font-mono text-xs">{fmtTime(e.ts)}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{e.kind}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">{e.summary ?? "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Transcript</CardTitle>
          </CardHeader>
          <CardContent>
            {transcript ? (
              <p className="text-sm leading-relaxed">{transcript}</p>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No speech transcribed yet.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
