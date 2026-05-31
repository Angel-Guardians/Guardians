"use client";

import { Mic, Volume2, VolumeX } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useVoiceListen } from "@/hooks/useVoiceListen";
import { cn } from "@/lib/utils";

function EqBars({ active }: { active: boolean }) {
  return (
    <span className="flex h-3 items-end gap-0.5">
      {[0, 1, 2, 3, 4].map((i) => (
        <i
          key={i}
          className={cn(
            "block w-[3px] rounded-sm bg-muted-foreground",
            active && "animate-[eq_0.9s_ease-in-out_infinite] bg-primary",
          )}
          style={active ? { animationDelay: `${i * 0.15}s`, height: 4 } : { height: 4 }}
        />
      ))}
    </span>
  );
}

interface VoiceSpeakerProps {
  variant?: "card" | "bar";
  /** Fallback text when nothing is streaming (e.g. agent reply from pipeline). */
  fallbackText?: string;
}

/**
 * Live speaker for the watch microphone. Plays the raw PCM stream the watch is
 * sending to the backend (`/voice/listen`) so the dashboard can monitor the
 * wearer's voice in real time, with the live transcript and the agent's reply.
 */
export function VoiceSpeaker({
  variant = "card",
  fallbackText,
}: VoiceSpeakerProps) {
  const { status, listening, speaking, level, transcript, reply, toggleListening } =
    useVoiceListen();

  const displayText =
    reply || transcript || fallbackText || (listening ? "— listening" : "— idle");
  const active = speaking || !!reply;

  if (variant === "bar") {
    return (
      <div
        className={cn(
          "flex items-center gap-3 rounded-xl border bg-card px-3.5 py-2.5 transition-all",
          active
            ? "border-primary/40 bg-primary/5 opacity-100"
            : "opacity-60",
        )}
      >
        <span
          className={cn(
            "flex size-[30px] shrink-0 items-center justify-center rounded-[9px] bg-muted",
            active && "bg-primary/10",
          )}
        >
          {active ? (
            <Volume2 className="size-4 text-primary" />
          ) : (
            <Mic className="size-4 text-muted-foreground" />
          )}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-[10.5px] font-bold uppercase tracking-wider text-muted-foreground">
            Speaking
            <EqBars active={active} />
            {speaking && (
              <Badge variant="outline" className="ml-1 h-4 px-1.5 text-[9px]">
                live
              </Badge>
            )}
          </div>
          <p
            className={cn(
              "mt-0.5 line-clamp-2 text-[13px] leading-snug",
              active ? "text-foreground" : "text-muted-foreground",
            )}
          >
            {displayText}
          </p>
        </div>

        <div className="hidden w-16 shrink-0 sm:block">
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-75"
              style={{ width: `${Math.round(level * 100)}%` }}
            />
          </div>
        </div>

        <Button
          variant={listening ? "default" : "outline"}
          size="sm"
          className="shrink-0"
          onClick={toggleListening}
          disabled={status !== "open"}
        >
          {listening ? <Volume2 className="size-3.5" /> : <VolumeX className="size-3.5" />}
          <span className="sr-only">{listening ? "Listening" : "Listen"}</span>
        </Button>
      </div>
    );
  }

  return (
    <Card className="rounded-2xl shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2">
        <div className="flex items-center gap-2">
          <CardTitle>Watch microphone</CardTitle>
          {speaking && (
            <Badge variant="default" className="gap-1">
              <Mic className="size-3 animate-pulse" />
              Speaking
            </Badge>
          )}
        </div>
        <Button
          variant={listening ? "default" : "outline"}
          size="sm"
          onClick={toggleListening}
          disabled={status !== "open"}
        >
          {listening ? <Volume2 /> : <VolumeX />}
          {listening ? "Listening" : "Listen"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-75"
            style={{ width: `${Math.round(level * 100)}%` }}
          />
        </div>

        {transcript ? (
          <div>
            <p className="text-xs font-medium text-muted-foreground">Heard</p>
            <p className="text-sm leading-relaxed">{transcript}</p>
          </div>
        ) : null}

        {reply ? (
          <div>
            <p className="text-xs font-medium text-muted-foreground">Guardian replied</p>
            <p className="text-sm leading-relaxed">{reply}</p>
          </div>
        ) : null}

        {!transcript && !reply ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            {status === "open"
              ? listening
                ? "Listening for the watch… hold the watch's talk button to stream."
                : "Click Listen to hear the watch's microphone live."
              : "Connecting to the voice stream…"}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
