"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { VitalKind, VitalPoint } from "@/lib/types";

interface MetricConfig {
  kind: VitalKind;
  title: string;
  unit: string;
  color: string;
}

const METRICS: MetricConfig[] = [
  { kind: "hr", title: "Heart Rate", unit: "bpm", color: "var(--chart-1)" },
  { kind: "spo2", title: "SpO2", unit: "%", color: "var(--chart-2)" },
  { kind: "bp", title: "Blood Pressure", unit: "mmHg", color: "var(--chart-3)" },
  { kind: "steps", title: "Steps", unit: "count", color: "var(--chart-4)" },
  { kind: "calories", title: "Calories", unit: "kcal", color: "var(--chart-5)" },
];

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; points: VitalPoint[] };

function fmtTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function VitalCard({ metric }: { metric: MetricConfig }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    api
      .getVitals(metric.kind)
      .then((series) => active && setState({ status: "ready", points: series.points }))
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
  }, [metric.kind]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-baseline justify-between">
          <span>{metric.title}</span>
          <span className="text-xs font-normal text-muted-foreground">{metric.unit}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="h-56">
        {state.status === "ready" && state.points.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={state.points} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="ts"
                tickFormatter={fmtTime}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              />
              <Tooltip labelFormatter={(l) => fmtTime(String(l))} />
              <Line
                type="monotone"
                dataKey={metric.kind === "bp" ? "systolic" : "value"}
                stroke={metric.color}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              {metric.kind === "bp" && (
                <Line
                  type="monotone"
                  dataKey="diastolic"
                  stroke="var(--chart-4)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-center text-sm text-muted-foreground">
              {state.status === "loading"
                ? "Loading..."
                : `${metric.title} will appear here once the wearable is streaming.`}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function VitalsPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Vitals</h1>
        <p className="text-muted-foreground">
          Heart rate, SpO2, blood pressure - last 24 hours
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        {METRICS.map((metric) => (
          <VitalCard key={metric.kind} metric={metric} />
        ))}
      </div>
    </div>
  );
}
