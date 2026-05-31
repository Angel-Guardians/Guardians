"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  DEMO_SCENARIOS,
  type DemoScenario,
} from "@/lib/agent-graph";
import {
  applyStep,
  initialPipelineState,
  type PipelineState,
} from "@/lib/pipeline-state";

const STEP_MS = 850;

export function useDemoPipeline(
  onPipelineChange: (state: PipelineState) => void,
  onModeChange?: (mode: "demo") => void,
) {
  const [scenario, setScenario] = useState<DemoScenario | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => () => clearTimer(), [clearTimer]);

  const reset = useCallback(() => {
    clearTimer();
    setScenario(null);
    setIsPlaying(false);
    onPipelineChange(initialPipelineState());
  }, [clearTimer, onPipelineChange]);

  const runScenario = useCallback(
    (preset: DemoScenario) => {
      clearTimer();
      onModeChange?.("demo");
      setScenario(preset);
      setIsPlaying(true);

      let state = initialPipelineState();
      let index = 0;

      const tick = () => {
        if (index >= preset.steps.length) {
          setIsPlaying(false);
          return;
        }
        const step = preset.steps[index];
        state = applyStep(state, step, index + 1, preset.steps.length);
        onPipelineChange(state);
        index += 1;
        if (index < preset.steps.length) {
          timerRef.current = setTimeout(tick, STEP_MS);
        } else {
          setIsPlaying(false);
        }
      };

      tick();
      return preset.inputText;
    },
    [clearTimer, onModeChange, onPipelineChange],
  );

  const advanceStep = useCallback(
    (pipeline: PipelineState) => {
      if (!scenario) return;
      clearTimer();
      setIsPlaying(false);
      onModeChange?.("demo");
      const nextIndex = pipeline.stepIndex;
      if (nextIndex >= scenario.steps.length) return;
      const step = scenario.steps[nextIndex];
      const base =
        nextIndex === 0 && !pipeline.currentStep
          ? initialPipelineState()
          : pipeline;
      onPipelineChange(
        applyStep(base, step, nextIndex + 1, scenario.steps.length),
      );
    },
    [scenario, clearTimer, onModeChange, onPipelineChange],
  );

  return {
    scenario,
    isPlaying,
    runScenario,
    advanceStep,
    reset,
    clearTimer,
  };
}

export { DEMO_SCENARIOS };
