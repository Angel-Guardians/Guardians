"use client";

import { useCallback, useMemo, useState } from "react";

import { AgentPipelineGraph } from "@/components/agent-pipeline-graph";
import { LiveTurnPanel, type LiveMode } from "@/components/live-turn-panel";
import { PageHeader } from "@/components/page-header";
import { VoiceSpeaker } from "@/components/voice-speaker";
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
import { useDemoPipeline } from "@/hooks/useDemoPipeline";
import { useEventStream, type StreamStatus } from "@/hooks/useEventStream";
import { usePipelineFromEvents } from "@/hooks/usePipelineFromEvents";
import { initialPipelineState, type PipelineState } from "@/lib/pipeline-state";

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

const PIPELINE_EVENT_KINDS = new Set([
  "transcript",
  "routing_decision",
  "tool_invocation",
  "agent_reply",
]);

export default function LivePage() {
  const { events, status, clearEvents } = useEventStream();
  const [mode, setMode] = useState<LiveMode>("demo");
  const [resetting, setResetting] = useState(false);
  const [demoPipeline, setDemoPipeline] = useState<PipelineState>(
    initialPipelineState,
  );

  // Wipe the agent's conversation memory (and the visible event log) so a test
  // or demo run starts from a clean slate. Calls POST /turn/reset.
  const handleReset = useCallback(async () => {
    setResetting(true);
    try {
      await api.resetContext();
      clearEvents();
    } finally {
      setResetting(false);
    }
  }, [clearEvents]);

  const demo = useDemoPipeline(setDemoPipeline, () => setMode("demo"));

  const ssePipeline = usePipelineFromEvents(events, mode === "live");

  const pipeline = mode === "live" ? ssePipeline : demoPipeline;

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

  const handleGraphDemo = useCallback(
    (preset: Parameters<typeof demo.runScenario>[0]) => {
      setMode("demo");
      demo.runScenario(preset);
    },
    [demo],
  );

  return (
    <div className="space-y-8">
      <PageHeader
        title="Live"
        description="Agent pipeline, real-time events, and active transcript from Guardian."
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={resetting}
            >
              {resetting ? "Resetting..." : "Reset context"}
            </Button>
            <StatusBadge status={status} />
          </div>
        }
      />

      <Card className="overflow-hidden rounded-2xl shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle>Agent pipeline</CardTitle>
          <p className="text-sm text-muted-foreground">
            Left to right: input → router → specialist → tools. Use the demo bar
            below the graph to preview the flow.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <AgentPipelineGraph
            pipeline={pipeline}
            onRunDemo={handleGraphDemo}
            onReset={demo.reset}
            isPlaying={demo.isPlaying}
            activeScenarioId={demo.scenario?.id ?? null}
          />
          <LiveTurnPanel
            pipeline={pipeline}
            mode={mode}
            onModeChange={setMode}
            demo={demo}
          />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Event log</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Waiting for events from the backend (
                {STATUS_LABEL[status].toLowerCase()}).
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
                    <TableRow
                      key={e.id}
                      className={
                        mode === "live" && PIPELINE_EVENT_KINDS.has(e.kind)
                          ? "bg-primary/5"
                          : undefined
                      }
                    >
                      <TableCell className="font-mono text-xs">
                        {fmtTime(e.ts)}
                      </TableCell>
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

        <div className="space-y-6">
          <VoiceSpeaker />

          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle>Active transcript</CardTitle>
            </CardHeader>
            <CardContent>
              {displayTranscript ? (
                <p className="text-sm leading-relaxed">{displayTranscript}</p>
              ) : (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  No speech transcribed yet.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
