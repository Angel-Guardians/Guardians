"use client";

import { ExternalLink, MapPin, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import type { LocationPoint } from "@/lib/types";
import { cn } from "@/lib/utils";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; points: LocationPoint[] };

function fmtTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString();
}

function googleMapsUrl(lat: number, lng: number) {
  return `https://www.google.com/maps?q=${lat},${lng}`;
}

export default function LocationPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [clearing, setClearing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadLocations = useCallback(async () => {
    setState({ status: "loading" });
    setActionError(null);
    try {
      const points = await api.getLocations();
      setState({ status: "ready", points });
    } catch (err: unknown) {
      setState({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to load",
      });
    }
  }, []);

  useEffect(() => {
    void loadLocations();
  }, [loadLocations]);

  async function clearHistory() {
    if (state.status !== "ready" || state.points.length === 0) return;
    const ok = window.confirm(
      `Clear all ${state.points.length} stored GPS point(s)? This cannot be undone.`,
    );
    if (!ok) return;

    setClearing(true);
    setActionError(null);
    try {
      await api.clearAdminTable("location");
      setState({ status: "ready", points: [] });
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to clear history");
    } finally {
      setClearing(false);
    }
  }

  const latest = state.status === "ready" ? state.points[0] : null;
  const hasPoints = state.status === "ready" && state.points.length > 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Location"
        description="GPS track from the wearable — last 24 hours."
        action={
          <div className="flex flex-wrap items-center gap-2">
            {hasPoints ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                disabled={clearing}
                onClick={() => void clearHistory()}
              >
                <Trash2 />
                {clearing ? "Clearing…" : "Clear history"}
              </Button>
            ) : null}
            <Link
              href="/location-map.html"
              className={cn(buttonVariants({ variant: "default", size: "sm" }))}
            >
              <MapPin />
              View on map
            </Link>
          </div>
        }
      />

      {state.status === "error" ? (
        <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {state.message}
        </p>
      ) : null}

      {actionError ? (
        <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {actionError}
        </p>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle>Latest position</CardTitle>
        </CardHeader>
        <CardContent>
          {state.status === "loading" ? (
            <p className="text-sm text-muted-foreground">Loading location…</p>
          ) : latest ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-baseline gap-3">
                <p className="font-mono text-lg font-semibold tabular-nums">
                  {latest.lat.toFixed(5)}, {latest.lng.toFixed(5)}
                </p>
                {latest.accuracy != null ? (
                  <Badge variant="outline">±{Math.round(latest.accuracy)} m</Badge>
                ) : null}
              </div>
              <p className="text-sm text-muted-foreground">{fmtTime(latest.ts)}</p>
              <a
                href={googleMapsUrl(latest.lat, latest.lng)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-primary underline-offset-4 hover:underline"
              >
                Open in Google Maps
                <ExternalLink className="size-3.5 opacity-70" />
              </a>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No positions yet — turn Monitoring on and give the watch a GPS fix
              (near a window or outdoors).
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-3">
            <span>Track history</span>
            {state.status === "ready" && state.points.length > 0 ? (
              <Badge variant="secondary">{state.points.length} points</Badge>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {state.status === "ready" && state.points.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Latitude</TableHead>
                  <TableHead>Longitude</TableHead>
                  <TableHead>Accuracy</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.points.map((point) => (
                  <TableRow key={point.ts}>
                    <TableCell className="text-sm">{fmtTime(point.ts)}</TableCell>
                    <TableCell className="font-mono text-xs tabular-nums">
                      {point.lat.toFixed(5)}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums">
                      {point.lng.toFixed(5)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {point.accuracy != null ? `±${Math.round(point.accuracy)} m` : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : state.status !== "loading" ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Track points will appear here once the watch starts reporting GPS.
            </p>
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
