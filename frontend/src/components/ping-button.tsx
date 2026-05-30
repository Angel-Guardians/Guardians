"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type PingState = "idle" | "pinging" | "up" | "down";

const LABEL: Record<PingState, string> = {
  idle: "Ping backend",
  pinging: "Pinging...",
  up: "pong - backend up",
  down: "No response",
};

export function PingButton() {
  const [state, setState] = useState<PingState>("idle");

  async function ping() {
    setState("pinging");
    try {
      const res = await api.ping();
      setState(res.message === "pong" ? "up" : "down");
    } catch {
      setState("down");
    }
  }

  return (
    <div className="space-y-2">
      <Button
        variant="outline"
        size="sm"
        className="min-w-[10rem]"
        disabled={state === "pinging"}
        onClick={ping}
      >
        {state === "pinging" ? "Pinging..." : "Ping backend"}
      </Button>
      {state !== "idle" && state !== "pinging" && (
        <p
          className={
            state === "up"
              ? "text-center text-xs text-green-600 dark:text-green-500"
              : "text-center text-xs text-destructive"
          }
        >
          {LABEL[state]}
        </p>
      )}
    </div>
  );
}
