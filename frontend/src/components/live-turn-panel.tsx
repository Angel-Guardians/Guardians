"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DEMO_SCENARIOS } from "@/lib/agent-graph";
import { stepLabel, type PipelineState } from "@/lib/pipeline-state";
import { api } from "@/lib/api";
import type { useDemoPipeline } from "@/hooks/useDemoPipeline";
import { cn } from "@/lib/utils";

export type LiveMode = "demo" | "live";

type DemoControls = ReturnType<typeof useDemoPipeline>;

interface LiveTurnPanelProps {
  pipeline: PipelineState;
  mode: LiveMode;
  onModeChange: (mode: LiveMode) => void;
  demo: DemoControls;
  className?: string;
}

export function LiveTurnPanel({
  pipeline,
  mode,
  onModeChange,
  demo,
  className,
}: LiveTurnPanelProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePreset = (preset: (typeof DEMO_SCENARIOS)[number]) => {
    setError(null);
    onModeChange("demo");
    setInput(demo.runScenario(preset));
  };

  const handleAdvance = () => {
    onModeChange("demo");
    demo.advanceStep(pipeline);
    if (demo.scenario) setInput(demo.scenario.inputText);
  };

  const handleReset = () => {
    setError(null);
    setInput("");
    demo.reset();
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setSending(true);
    setError(null);
    onModeChange("live");
    demo.clearTimer();
    try {
      await api.turn(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Turn failed");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={cn("space-y-4 rounded-2xl border bg-card p-4 shadow-sm", className)}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Turn</span>
          <div className="flex rounded-lg border p-0.5">
            <button
              type="button"
              className={cn(
                "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                mode === "demo"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={() => onModeChange("demo")}
            >
              Demo
            </button>
            <button
              type="button"
              className={cn(
                "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                mode === "live"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={() => onModeChange("live")}
            >
              Live
            </button>
          </div>
        </div>
        <Badge variant="outline" className="font-mono text-xs">
          {stepLabel(pipeline.currentStep)}
        </Badge>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          placeholder="Type a message to Guardian…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && mode === "live") void handleSend();
          }}
          className="flex-1"
        />
        <div className="flex shrink-0 gap-2">
          <Button
            onClick={() => void handleSend()}
            disabled={sending || !input.trim()}
          >
            {sending ? "Sending…" : "Send"}
          </Button>
          <Button variant="outline" onClick={handleReset}>
            Reset
          </Button>
        </div>
      </div>

      {error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {DEMO_SCENARIOS.map((preset) => (
          <Button
            key={preset.id}
            variant="secondary"
            size="sm"
            disabled={demo.isPlaying}
            onClick={() => handlePreset(preset)}
          >
            {preset.label}
          </Button>
        ))}
        {mode === "demo" && demo.scenario ? (
          <Button
            variant="outline"
            size="sm"
            disabled={demo.isPlaying}
            onClick={handleAdvance}
          >
            Advance step
          </Button>
        ) : null}
      </div>

      {mode === "demo" && pipeline.totalSteps > 0 ? (
        <p className="text-xs text-muted-foreground">
          Step {pipeline.stepIndex} of {pipeline.totalSteps}
          {demo.scenario ? ` — ${demo.scenario.description}` : ""}
        </p>
      ) : null}
    </div>
  );
}
