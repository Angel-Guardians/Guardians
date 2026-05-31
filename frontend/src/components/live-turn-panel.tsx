"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { stepLabel, type PipelineState } from "@/lib/pipeline-state";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface LiveTurnPanelProps {
  pipeline: PipelineState;
  className?: string;
}

export function LiveTurnPanel({ pipeline, className }: LiveTurnPanelProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleReset = () => {
    setError(null);
    setNotice(null);
    setInput("");
  };

  // Forget the LLM's previous turns so the next answers aren't anchored to the
  // earlier conversation (the patient profile/persona stays loaded).
  const handleClearContext = async () => {
    setError(null);
    setNotice(null);
    setClearing(true);
    try {
      await api.clearContext();
      setNotice("Conversation context cleared — answers start fresh.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Clear context failed");
    } finally {
      setClearing(false);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setSending(true);
    setError(null);
    try {
      await api.turn(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Turn failed");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={cn("space-y-3 rounded-[14px] border bg-card p-3.5", className)}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm font-medium">Turn</span>
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
            if (e.key === "Enter") void handleSend();
          }}
          className="flex-1 rounded-[10px] bg-background"
        />
        <div className="flex shrink-0 gap-2">
          <Button
            className="rounded-[9px]"
            onClick={() => void handleSend()}
            disabled={sending || !input.trim()}
          >
            {sending ? "Sending…" : "Send"}
          </Button>
          <Button variant="outline" className="rounded-[9px]" onClick={handleReset}>
            Reset
          </Button>
          <Button
            variant="outline"
            className="rounded-[9px]"
            onClick={() => void handleClearContext()}
            disabled={clearing}
            title="Forget the LLM's previous conversation so answers start fresh"
          >
            {clearing ? "Clearing…" : "Clear context"}
          </Button>
        </div>
      </div>

      {error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : null}
      {notice ? (
        <p className="text-xs text-muted-foreground">{notice}</p>
      ) : null}
    </div>
  );
}
