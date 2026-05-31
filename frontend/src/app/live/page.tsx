"use client";

import {
  MessageCircle,
  Pill,
  Play,
  RotateCcw,
  Shield,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { AgentPipelineGraph } from "@/components/agent-pipeline-graph";
import { LiveSensorsPanel } from "@/components/live-sensors-panel";
import { LiveTurnPanel } from "@/components/live-turn-panel";
import { RiskMonitor } from "@/components/risk-monitor";
import { PageHeader } from "@/components/page-header";
import { VoiceSpeaker } from "@/components/voice-speaker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DEMO_SCENARIOS, useDemoPipeline } from "@/hooks/useDemoPipeline";
import { useEventStream, type StreamStatus } from "@/hooks/useEventStream";
import { usePipelineFromEvents } from "@/hooks/usePipelineFromEvents";
import type { PipelineStep } from "@/lib/agent-graph";
import { initialPipelineState, type PipelineState } from "@/lib/pipeline-state";
import type { GuardianEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_LABEL: Record<StreamStatus, string> = {
  connecting: "Connecting...",
  open: "Live",
  closed: "Disconnected",
};

// Wall-clock spacing between demo steps — mirrors STEP_MS in useDemoPipeline so
// the synthetic event-log timestamps line up with the graph animation.
const DEMO_STEP_MS = 850;

function LiveStatusPill({ status }: { status: StreamStatus }) {
  const live = status === "open";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-bold",
        live
          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
          : "bg-muted text-muted-foreground",
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          live ? "animate-pulse bg-emerald-500" : "bg-muted-foreground/50",
        )}
      />
      {STATUS_LABEL[status]}
    </span>
  );
}

function fmtTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString();
}

function eventKindClass(kind: string): string {
  if (kind.includes("fall") || kind.includes("risk") || kind === "call_request") {
    return "bg-red-500/15 text-destructive";
  }
  if (kind === "tool_invocation") {
    return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400";
  }
  if (kind === "routing_decision" || kind.includes("warn")) {
    return "bg-amber-500/15 text-amber-700 dark:text-amber-400";
  }
  return "bg-muted text-muted-foreground";
}

const PIPELINE_EVENT_KINDS = new Set([
  "transcript",
  "routing_decision",
  "tool_invocation",
  "agent_reply",
]);

/** One-line summary for a demo step, shown in the synthetic event log. */
function demoStepSummary(step: PipelineStep): string {
  switch (step.kind) {
    case "transcript":
      return `Patient: “${step.text}”`;
    case "routing_decision":
      return `Routed to ${step.routed_to}`;
    case "tool_invocation":
      return `${step.tool}() invoked`;
    case "agent_reply":
      return `${step.agent} replied`;
  }
}

export default function LivePage() {
  const { events, status } = useEventStream();

  // "live" reflects the real backend SSE stream; "demo" plays a scripted
  // scenario that animates the pipeline graph and fills a synthetic event log.
  const [mode, setMode] = useState<"live" | "demo">("live");
  const [demoPipeline, setDemoPipeline] = useState<PipelineState>(
    initialPipelineState,
  );
  const [demoStartedAt, setDemoStartedAt] = useState(0);

  const demo = useDemoPipeline(setDemoPipeline, () => setMode("demo"));

  const ssePipeline = usePipelineFromEvents(events, mode === "live");
  const pipeline = mode === "demo" ? demoPipeline : ssePipeline;

  const transcript = useMemo(
    () =>
      [...events]
        .reverse()
        .filter((e) => e.kind === "transcript")
        .map((e) => e.summary ?? "")
        .join(" "),
    [events],
  );

  const displayTranscript = pipeline.transcript || transcript;
  const agentReply = useMemo(
    () => events.find((e) => e.kind === "agent_reply")?.summary,
    [events],
  );

  // While a demo plays, derive event-log rows from the steps applied so far
  // (newest first) so the log animates in step with the graph.
  const demoLog = useMemo<GuardianEvent[]>(() => {
    if (mode !== "demo" || !demo.scenario) return [];
    const applied = demo.scenario.steps.slice(0, demoPipeline.stepIndex);
    return applied
      .map((step, i) => ({
        id: `demo-${demo.scenario!.id}-${i}`,
        kind: step.kind,
        ts: new Date(demoStartedAt + i * DEMO_STEP_MS).toISOString(),
        summary: demoStepSummary(step),
      }))
      .reverse();
  }, [mode, demo.scenario, demoPipeline.stepIndex, demoStartedAt]);

  const displayEvents = mode === "demo" ? demoLog : events;

  const handleRunDemo = useCallback(
    (preset: (typeof DEMO_SCENARIOS)[number]) => {
      setDemoStartedAt(Date.now());
      setMode("demo");
      demo.runScenario(preset);
    },
    [demo],
  );

  const handleResetDemo = useCallback(() => {
    demo.reset();
    setMode("live");
  }, [demo]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Live"
        description="Routing pipeline, agent activity, and event stream."
        action={<LiveStatusPill status={status} />}
      />

      <RiskMonitor variant="tier" />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        <LiveSensorsPanel />

        <div className="flex min-w-0 flex-1 flex-col gap-3.5">
          <AgentPipelineGraph pipeline={pipeline} />

          <VoiceSpeaker
            variant="bar"
            fallbackText={agentReply || displayTranscript || undefined}
          />

          <LiveTurnPanel pipeline={pipeline} />
        </div>
      </div>

      <Card className="rounded-[14px] shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-bold">
            Event stream
            {mode === "demo" ? (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10.5px] font-bold text-amber-700 dark:text-amber-400">
                Demo
              </span>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {displayEvents.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              {mode === "demo"
                ? "Run a demo below to populate the event log."
                : `Waiting for events from the backend (${STATUS_LABEL[status].toLowerCase()}).`}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[110px] text-[11px] uppercase tracking-wider">
                    Time
                  </TableHead>
                  <TableHead className="w-[120px] text-[11px] uppercase tracking-wider">
                    Kind
                  </TableHead>
                  <TableHead className="text-[11px] uppercase tracking-wider">
                    Summary
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayEvents.map((e) => (
                  <TableRow
                    key={e.id}
                    className={
                      mode === "demo" || PIPELINE_EVENT_KINDS.has(e.kind)
                        ? "bg-primary/5"
                        : undefined
                    }
                  >
                    <TableCell className="font-mono text-[11.5px] text-muted-foreground">
                      {fmtTime(e.ts)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "inline-flex rounded-full px-2 py-0.5 text-[10.5px] font-bold",
                          eventKindClass(e.kind),
                        )}
                      >
                        {e.kind}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">{e.summary ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Demo controls — kept at the far bottom. Each button plays a scripted
          scenario that animates the pipeline graph and event log above. */}
      <Card className="rounded-[14px] border-dashed shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold">Demo flows</CardTitle>
          <p className="text-xs text-muted-foreground">
            Preview the routing pipeline without the watch — animates the graph
            and event log above.
          </p>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-wrap items-center gap-2">
            {DEMO_SCENARIOS.map((preset) => {
              const Icon =
                preset.id === "fall"
                  ? Shield
                  : preset.id === "medication"
                    ? Pill
                    : MessageCircle;
              const isActive =
                mode === "demo" && demo.scenario?.id === preset.id;
              return (
                <Button
                  key={preset.id}
                  type="button"
                  variant={isActive ? "default" : "outline"}
                  size="sm"
                  disabled={demo.isPlaying && !isActive}
                  className={cn(
                    "gap-1.5 shadow-sm",
                    isActive && "ring-2 ring-primary/30",
                  )}
                  onClick={() => handleRunDemo(preset)}
                  title={preset.description}
                >
                  <Icon className="size-3.5" />
                  {preset.label}
                </Button>
              );
            })}

            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="gap-1.5 text-muted-foreground"
              disabled={demo.isPlaying || mode !== "demo"}
              onClick={handleResetDemo}
            >
              <RotateCcw className="size-3.5" />
              Reset to live
            </Button>

            <div className="ml-auto flex items-center gap-2">
              {mode === "demo" && pipeline.totalSteps > 0 ? (
                <span className="font-mono text-xs text-muted-foreground">
                  {pipeline.stepIndex}/{pipeline.totalSteps}
                </span>
              ) : null}
              <Button
                type="button"
                size="sm"
                className="gap-1.5"
                disabled={demo.isPlaying}
                onClick={() => {
                  const fall = DEMO_SCENARIOS[0];
                  if (fall) handleRunDemo(fall);
                }}
              >
                <Play className="size-3.5 fill-current" />
                Play demo
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
