"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DEMO_SCENARIOS, type DemoScenario } from "@/lib/agent-graph";
import {
  applyStep,
  initialPipelineState,
  stepLabel,
  type PipelineState,
} from "@/lib/pipeline-state";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export type LiveMode = "demo" | "live";

interface LiveTurnPanelProps {
  pipeline: PipelineState;
  mode: LiveMode;
  onModeChange: (mode: LiveMode) => void;
  onPipelineChange: (state: PipelineState) => void;
  onReset: () => void;
}

export function LiveTurnPanel({
  pipeline,
  mode,
  onModeChange,
  onPipelineChange,
  onReset,
}: LiveTurnPanelProps) {
  const [input, setInput] = useState("");
  const [scenario, setScenario] = useState<DemoScenario | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => () => clearTimer(), [clearTimer]);

  const runDemoSteps = useCallback(
    (steps: DemoScenario["steps"], startText: string) => {
      clearTimer();
      onModeChange("demo");
      let state = initialPipelineState();
      let index = 0;

      const tick = () => {
        if (index >= steps.length) return;
        const step = steps[index];
        state = applyStep(state, step, index + 1, steps.length);
        onPipelineChange(state);
        index += 1;
        if (index < steps.length) {
          timerRef.current = setTimeout(tick, 700);
        }
      };

      tick();
      setInput(startText);
    },
    [clearTimer, onModeChange, onPipelineChange],
  );

  const handlePreset = (preset: DemoScenario) => {
    setScenario(preset);
    setError(null);
    runDemoSteps(preset.steps, preset.inputText);
  };

  const handleAdvance = () => {
    if (!scenario) return;
    clearTimer();
    onModeChange("demo");
    const nextIndex = pipeline.stepIndex;
    if (nextIndex >= scenario.steps.length) return;
    const step = scenario.steps[nextIndex];
    const base =
      nextIndex === 0 && !pipeline.currentStep
        ? initialPipelineState()
        : pipeline;
    const state = applyStep(base, step, nextIndex + 1, scenario.steps.length);
    onPipelineChange(state);
    if (nextIndex === 0) setInput(scenario.inputText);
  };

  const handleReset = () => {
    clearTimer();
    setScenario(null);
    setError(null);
    setInput("");
    onReset();
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setSending(true);
    setError(null);
    onModeChange("live");
    clearTimer();
    try {
      await api.turn(text);
      // Pipeline updates via SSE in parent
    } catch (e) {
      setError(e instanceof Error ? e.message : "Turn failed");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-4 rounded-2xl border bg-card p-4 shadow-sm">
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
            onClick={() => handlePreset(preset)}
          >
            {preset.label}
          </Button>
        ))}
        {mode === "demo" && scenario ? (
          <Button variant="outline" size="sm" onClick={handleAdvance}>
            Advance step
          </Button>
        ) : null}
      </div>

      {mode === "demo" && pipeline.totalSteps > 0 ? (
        <p className="text-xs text-muted-foreground">
          Step {pipeline.stepIndex} of {pipeline.totalSteps}
          {scenario ? ` — ${scenario.description}` : ""}
        </p>
      ) : null}
    </div>
  );
}
