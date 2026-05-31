"use client";

import { useMemo } from "react";

import type { PipelineStep } from "@/lib/agent-graph";
import {
  applyStep,
  initialPipelineState,
  type PipelineState,
} from "@/lib/pipeline-state";
import type { GuardianEvent } from "@/lib/types";

function eventToStep(ev: GuardianEvent): PipelineStep | null {
  const payload = ev.payload ?? {};
  switch (ev.kind) {
    case "transcript":
      return {
        kind: "transcript",
        text: String(payload.text ?? ev.summary ?? ""),
      };
    case "routing_decision":
      return {
        kind: "routing_decision",
        routed_to: String(payload.routed_to ?? ""),
      };
    case "tool_invocation":
      return {
        kind: "tool_invocation",
        tool: String(payload.tool ?? ""),
      };
    case "agent_reply":
      return {
        kind: "agent_reply",
        agent: String(payload.agent ?? ""),
      };
    default:
      return null;
  }
}

/**
 * Derives pipeline graph state from SSE events (newest-first buffer).
 * Resets on each new transcript (new turn).
 */
export function usePipelineFromEvents(
  events: GuardianEvent[],
  enabled: boolean,
): PipelineState {
  return useMemo(() => {
    if (!enabled) return initialPipelineState();

    const ordered = [...events].reverse();
    let state = initialPipelineState();
    const seen = new Set<string>();
    const steps: PipelineStep[] = [];

    for (const ev of ordered) {
      const step = eventToStep(ev);
      if (!step) continue;
      if (seen.has(ev.id)) continue;
      seen.add(ev.id);
      steps.push(step);
    }

    steps.forEach((step, i) => {
      state = applyStep(state, step, i + 1, steps.length);
    });

    return state;
  }, [events, enabled]);
}
