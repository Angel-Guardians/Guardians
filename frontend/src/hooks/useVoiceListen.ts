"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";

export type ListenStatus = "connecting" | "open" | "closed";

export interface VoiceListenState {
  status: ListenStatus;
  /** Whether the browser is actively playing the incoming mic audio. */
  listening: boolean;
  /** True between mic_begin and mic_end — the wearer is currently speaking. */
  speaking: boolean;
  /** 0..1 RMS level of the most recent audio frame (for a VU meter). */
  level: number;
  transcript: string;
  reply: string;
  toggleListening: () => void;
}

function toWsUrl(base: string): string {
  const u = base.trim().replace(/\/$/, "");
  if (u.startsWith("https://")) return `wss://${u.slice("https://".length)}/voice/listen`;
  if (u.startsWith("http://")) return `ws://${u.slice("http://".length)}/voice/listen`;
  return `ws://${u}/voice/listen`;
}

/**
 * Subscribes to the backend's live mic fan-out (`/voice/listen`) and plays the
 * raw PCM stream coming from the watch through Web Audio.
 *
 * The socket is always connected (so we can show a "speaking" indicator), but
 * audio only plays once the user clicks Listen — browsers require a user gesture
 * before an AudioContext can produce sound.
 */
export function useVoiceListen(): VoiceListenState {
  const [status, setStatus] = useState<ListenStatus>("connecting");
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [level, setLevel] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [reply, setReply] = useState("");

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const gainRef = useRef<GainNode | null>(null);
  const nextStartRef = useRef(0);
  const sampleRateRef = useRef(16000);
  const listeningRef = useRef(false);

  // Keep a ref in sync so the WS message handler (bound once) reads live state.
  useEffect(() => {
    listeningRef.current = listening;
  }, [listening]);

  const playPcm = useCallback((buffer: ArrayBuffer) => {
    const ctx = audioCtxRef.current;
    const gain = gainRef.current;
    if (!ctx || !gain || !listeningRef.current) return;

    const int16 = new Int16Array(buffer);
    const float32 = new Float32Array(int16.length);
    let sumSq = 0;
    for (let i = 0; i < int16.length; i++) {
      const s = int16[i] / 32768;
      float32[i] = s;
      sumSq += s * s;
    }
    if (int16.length === 0) return;
    setLevel(Math.min(1, Math.sqrt(sumSq / int16.length) * 4));

    const audioBuffer = ctx.createBuffer(1, float32.length, sampleRateRef.current);
    audioBuffer.copyToChannel(float32, 0);
    const src = ctx.createBufferSource();
    src.buffer = audioBuffer;
    src.connect(gain);

    // Schedule gaplessly; if we've fallen behind, resync with a little latency.
    const now = ctx.currentTime;
    const start = Math.max(nextStartRef.current, now + 0.05);
    src.start(start);
    nextStartRef.current = start + audioBuffer.duration;
  }, []);

  useEffect(() => {
    const ws = new WebSocket(toWsUrl(API_BASE_URL));
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => setStatus("open");
    ws.onclose = () => setStatus("closed");
    ws.onerror = () => setStatus("closed");
    ws.onmessage = (e) => {
      if (typeof e.data !== "string") {
        playPcm(e.data as ArrayBuffer);
        return;
      }
      let msg: { type?: string; sample_rate?: number; text?: string };
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }
      switch (msg.type) {
        case "mic_begin":
          sampleRateRef.current = msg.sample_rate ?? 16000;
          nextStartRef.current = 0;
          setSpeaking(true);
          setTranscript("");
          setReply("");
          break;
        case "mic_end":
          setSpeaking(false);
          setLevel(0);
          break;
        case "transcript":
          setTranscript(msg.text ?? "");
          break;
        case "reply":
          setReply(msg.text ?? "");
          break;
      }
    };

    return () => {
      ws.close();
      audioCtxRef.current?.close();
      audioCtxRef.current = null;
    };
  }, [playPcm]);

  const toggleListening = useCallback(() => {
    setListening((on) => {
      const next = !on;
      if (next) {
        // Create/resume the AudioContext inside the user gesture.
        const Ctx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext })
            .webkitAudioContext;
        const ctx = audioCtxRef.current ?? new Ctx();
        const gain = gainRef.current ?? ctx.createGain();
        gain.connect(ctx.destination);
        audioCtxRef.current = ctx;
        gainRef.current = gain;
        nextStartRef.current = 0;
        void ctx.resume();
      } else {
        void audioCtxRef.current?.suspend();
        setLevel(0);
      }
      return next;
    });
  }, []);

  return { status, listening, speaking, level, transcript, reply, toggleListening };
}
