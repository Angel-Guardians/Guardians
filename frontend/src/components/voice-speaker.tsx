"use client";

import { Mic, Volume2, VolumeX } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useVoiceListen } from "@/hooks/useVoiceListen";

/**
 * Live speaker for the watch microphone. Plays the raw PCM stream the watch is
 * sending to the backend (`/voice/listen`) so the dashboard can monitor the
 * wearer's voice in real time, with the live transcript and the agent's reply.
 */
export function VoiceSpeaker() {
  const { status, listening, speaking, level, transcript, reply, toggleListening } =
    useVoiceListen();

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
        {/* Live level meter — fills while the wearer speaks. */}
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
