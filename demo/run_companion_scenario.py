#!/usr/bin/env python3
"""Guardian — scripted live demo: Scenario 2 (Sarah, proactive companion engagement).

The calm counterpart to the fall demo. Run this and step away from the keyboard:
it drives the *real* backend over HTTP so the Live dashboard lights up on its own,
and speaks Guardian's replies out loud from this PC. Nothing here is mocked inside
the backend — we only synthesise the watch's sensor stream and Sarah's spoken
answers; the routing, the companion agent, the tool calls and the replies are all
produced by the running system.

Timeline (mirrors demo/SCENARIO_WALKTHROUGHS.md, Scenario 2):

    t+0s    armed -> 10 second countdown
    t+10s   1. Context     ingest low-activity vitals (HR 64, SpO2 98) +
                           narrate the 6-days-home isolation signal       -> calm
    t+~16s  2-3. Check-in  Sarah says "good morning" -> companion greets,
                           leads with her morning Sertraline               -> warm
    t+~26s  4. Med taken   Sarah confirms -> companion logs it
    t+~36s  5-6. Isolation Sarah admits she's been low/home a week ->
                           companion recalls her interests, suggests a class
    t+~46s  7. Find class  Sarah agrees -> companion finds an accessible
                           painting class nearby
    t+~56s  8-10. Book it  Sarah says yes -> book class + Wheel-Trans + calendar
    t+~66s  12. Supporter  Sarah asks to tell her sister -> low-key heads-up
    t+~74s  Wind down      plan read back, follow-up scheduled

How it works:
  * A background thread subscribes to the same SSE stream the dashboard uses
    (GET /events/sse) and speaks every `agent_reply` and `call_request` through the
    Windows speech engine, so you hear exactly what the dashboard shows.
  * The main thread plays the timeline by POSTing vitals and turns to the backend.

Usage (from the repo root, with the backend already running on :8000):

    C:/Python313/python.exe demo/run_companion_scenario.py
    C:/Python313/python.exe demo/run_companion_scenario.py --setup     # first run: load Sarah
    C:/Python313/python.exe demo/run_companion_scenario.py --no-voice  # silent (just the UI)
    C:/Python313/python.exe demo/run_companion_scenario.py --base http://localhost:8000

Only the Python standard library is used, so any interpreter works.
"""
from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- #
# Tiny ANSI console helpers (degrade gracefully if the terminal ignores them)
# --------------------------------------------------------------------------- #
_C = {
    "reset": "\033[0m", "dim": "\033[2m", "bold": "\033[1m",
    "green": "\033[32m", "amber": "\033[33m", "red": "\033[31m",
    "blue": "\033[34m", "cyan": "\033[36m", "mag": "\033[35m",
}


def _t() -> str:
    return time.strftime("%H:%M:%S")


def narrate(msg: str, color: str = "cyan") -> None:
    print(f"{_C.get(color, '')}{_C['bold']}[{_t()}] {msg}{_C['reset']}")


def detail(msg: str) -> None:
    print(f"{_C['dim']}            {msg}{_C['reset']}")


# --------------------------------------------------------------------------- #
# HTTP (stdlib only)
# --------------------------------------------------------------------------- #
class Backend:
    def __init__(self, base: str, patient_id: int) -> None:
        self.base = base.rstrip("/")
        self.patient_id = patient_id

    def _post(self, path: str, body: dict) -> dict:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.base + path, data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")

    def _put(self, path: str, body: dict) -> dict:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.base + path, data=data,
            headers={"Content-Type": "application/json"}, method="PUT",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(self.base + "/health", timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def ingest(self, readings: list[dict], device: str = "guardian_watch") -> None:
        self._post(
            "/vitals/ingest",
            {"patient_id": self.patient_id, "device": device, "readings": readings},
        )

    def turn(self, text: str) -> dict:
        return self._post("/turn/", {"text": text, "patient_id": self.patient_id})

    def put_profile(self, profile: dict) -> dict:
        return self._put(f"/patient/{self.patient_id}/profile", profile)


# --------------------------------------------------------------------------- #
# Voice: speak text from this PC via the Windows speech engine (no deps).
# A single worker thread serialises utterances so they never talk over each other.
# --------------------------------------------------------------------------- #
_PS_SPEAK = (
    "Add-Type -AssemblyName System.Speech;"
    "$t=[Console]::In.ReadToEnd();"
    "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "$s.Rate=-1;"
    "try{$s.SelectVoiceByHints('Female')}catch{};"
    "$s.Speak($t)"
)


class Voice:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled and sys.platform == "win32"
        self._q: queue.Queue[str | None] = queue.Queue()
        if self.enabled:
            self._worker = threading.Thread(target=self._run, daemon=True)
            self._worker.start()

    def say(self, text: str) -> None:
        if self.enabled and text.strip():
            self._q.put(text)

    def _run(self) -> None:
        while True:
            text = self._q.get()
            if text is None:
                return
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_SPEAK],
                    input=text, text=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=60,
                )
            except Exception:
                pass  # never let a TTS hiccup break the demo

    def drain(self, timeout: float = 30.0) -> None:
        """Block until queued speech has finished (best effort)."""
        if not self.enabled:
            return
        deadline = time.time() + timeout
        while not self._q.empty() and time.time() < deadline:
            time.sleep(0.2)
        time.sleep(2.0)  # let the final utterance play out


# --------------------------------------------------------------------------- #
# SSE listener: subscribe to /events/sse (same feed as the dashboard) and narrate
# + speak the agent's replies as they happen.
# --------------------------------------------------------------------------- #
class EventListener(threading.Thread):
    def __init__(self, base: str, voice: Voice) -> None:
        super().__init__(daemon=True)
        self.base = base.rstrip("/")
        self.voice = voice
        self._seen: set[str] = set()
        self.connected = threading.Event()
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        url = self.base + "/events/sse"
        while not self._stop.is_set():
            try:
                req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    self.connected.set()
                    for raw in resp:
                        if self._stop.is_set():
                            return
                        line = raw.decode("utf-8", "replace").rstrip("\n").rstrip("\r")
                        if line.startswith("data:"):
                            self._handle(line[5:].strip())
            except Exception:
                if self._stop.is_set():
                    return
                time.sleep(1.0)  # reconnect

    def _handle(self, data: str) -> None:
        try:
            ev = json.loads(data)
        except Exception:
            return
        eid = str(ev.get("id", ""))
        if eid and eid in self._seen:
            return
        if eid:
            self._seen.add(eid)
        kind = ev.get("kind", "")
        payload = ev.get("payload") or {}
        summary = ev.get("summary") or ""

        if kind == "routing_decision":
            print(f"{_C['mag']}    -> router: routed to "
                  f"{_C['bold']}{payload.get('routed_to', '?')}{_C['reset']}"
                  f"{_C['mag']}{_C['reset']}")
        elif kind == "tool_invocation":
            print(f"{_C['blue']}    -> tool: {_C['bold']}{payload.get('tool', '?')}()"
                  f"{_C['reset']} {_C['dim']}{summary[:90]}{_C['reset']}")
        elif kind == "agent_reply":
            agent = payload.get("agent", "guardian")
            text = payload.get("text", "")
            print(f"{_C['green']}    >> {agent}: {_C['bold']}{text}{_C['reset']}")
            self.voice.say(text)
        elif kind == "call_request":
            who = payload.get("contact_name") or payload.get("phone") or "someone"
            msg = payload.get("message", "")
            print(f"{_C['blue']}    [NOTIFY] {_C['bold']}{who}{_C['reset']}"
                  f"{_C['blue']} ({payload.get('phone', '')}){_C['reset']}")
            if msg:
                self.voice.say(msg)
        elif kind == "risk_score_updated":
            lvl = payload.get("level", "?")
            score = payload.get("score", "?")
            col = {"low": "green", "moderate": "amber",
                   "high": "red", "critical": "red"}.get(str(lvl), "cyan")
            print(f"{_C[col]}    [RISK] {lvl} ({score}){_C['reset']}")


# --------------------------------------------------------------------------- #
# Optional setup: load the Sarah persona so the companion's recall and grounding
# match the scripted scenario.
# --------------------------------------------------------------------------- #
SARAH_PROFILE = {
    "name": "Sarah Okafor",
    "age": 35,
    "conditions": [
        "T10 paraplegia (wheelchair user, 2019 spinal cord injury)",
        "major depressive disorder (PHQ-9 14, moderate)",
        "spasticity below injury level",
        "neuropathic pain",
    ],
    "allergies": [],
    "primary_language": "en",
    "location": "200 Sackville St, Apt 612, Toronto, ON M5A 0B9 (Regent Park)",
    "bio": "35, former graphic designer, now freelance illustrator. Lives alone in a "
           "wheelchair-accessible apartment. Manual-chair independent. Enjoys "
           "watercolour painting, knitting and audiobooks. Wears the Guardian watch "
           "(the only sensor).",
    "notes": "Managing depression; some weeks she does not leave home. Highest-risk "
             "window is several consecutive days at home with low activity and low "
             "mood. Prefers gentle, non-urgent, optional outreach — never an alarm "
             "for simply staying home. Accessibility (step-free access + accessible "
             "transport) is a hard requirement for any activity. Primary support is "
             "her sister Amara.",
    "emergency_contacts": [
        {"name": "Amara Okafor", "relationship": "sister (primary support)",
         "phone": "(416) 555-0144", "priority": 1},
        {"name": "Priya Shah, PSW", "relationship": "personal support worker",
         "phone": "(416) 555-0156", "priority": 2},
    ],
    "medications": [
        {"name": "Sertraline", "dose": "50mg", "schedule_cron": "0 8 * * *",
         "with_food": True, "notes": "antidepressant (SSRI) — taken with breakfast"},
        {"name": "Baclofen", "dose": "10mg", "schedule_cron": "0 8,14,20 * * *",
         "with_food": False, "notes": "muscle relaxant for spasticity"},
        {"name": "Gabapentin", "dose": "300mg", "schedule_cron": "0 8,14,20 * * *",
         "with_food": False, "notes": "neuropathic pain (can cause drowsiness)"},
    ],
}


def do_setup(be: Backend) -> None:
    narrate("Setup: loading the Sarah companion persona…", "mag")

    # 1) Write data/personas/sarah.md (concatenate the demo persona docs) so
    #    recall_history has her interests / mood / supports to surface.
    src_dir = REPO_ROOT / "demo" / "personas" / "sarah"
    out_dir = REPO_ROOT / "data" / "personas"
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    for md in sorted(src_dir.glob("*.md")):
        parts.append(md.read_text(encoding="utf-8"))
    (out_dir / "sarah.md").write_text("\n\n---\n\n".join(parts), encoding="utf-8")
    detail(f"wrote {out_dir / 'sarah.md'}")

    # 2) Point patient #<id> at Sarah so the companion grounds on her profile.
    try:
        be.put_profile(SARAH_PROFILE)
        detail(f"patient #{be.patient_id} profile -> Sarah Okafor (companion)")
    except urllib.error.HTTPError as exc:
        detail(f"profile update skipped (HTTP {exc.code}); continuing with existing patient")
    except Exception as exc:  # noqa: BLE001
        detail(f"profile update skipped ({exc}); continuing with existing patient")


# --------------------------------------------------------------------------- #
# The scripted timeline
# --------------------------------------------------------------------------- #
def countdown(secs: int, label: str) -> None:
    for i in range(secs, 0, -1):
        sys.stdout.write(f"\r{_C['dim']}            {label}: {i:>2}s {_C['reset']}")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


def run_scenario(be: Backend, speed: float) -> None:
    def pause(s: float) -> None:
        time.sleep(s * speed)

    def say_as_sarah(label: str, text: str, wait: float = 8.0) -> None:
        narrate(f"(simulated) Sarah {label}:", "mag")
        detail(f'"{text}"')
        try:
            be.turn(text)
        except Exception as exc:  # noqa: BLE001
            detail(f"turn failed: {exc}")
        pause(wait)

    print()
    narrate("SCENARIO 2 — Sarah, 35. 8:00am. Wheelchair user. Watch streaming.", "green")
    countdown(int(10 * speed), "morning check-in begins in")

    # 1. Context builds — low activity, normal vitals; the 6-days-home isolation
    #    signal has been logged quietly over the prior days (no interruption).
    narrate("1. Context — calm. Low activity; she's been home ~6 days.", "green")
    detail("watch -> HR 64, SpO2 98 (resting, low activity)")
    be.ingest([{"kind": "hr", "value": 64}, {"kind": "spo2", "value": 98}])
    detail("background: PatternAbsence(expected='leaves_home', ~6 days) -> soft isolation flag")
    pause(5)

    # 2-3. Morning check-in — companion greets and leads with her medication.
    narrate("2. Morning check-in — companion takes the floor gently.", "cyan")
    say_as_sarah(
        "wakes and says",
        "Good morning. I'm up — slow start today.",
        wait=9,
    )

    # 4. She confirms the med — companion logs it.
    narrate("4. She takes her morning Sertraline.", "cyan")
    say_as_sarah(
        "confirms",
        "Okay, I just took my sertraline with breakfast.",
        wait=8,
    )

    # 5-6. Notice the isolation — companion recalls her interests, suggests a class.
    narrate("5. Sarah opens up — the companion recalls who she is, with care.", "amber")
    say_as_sarah(
        "admits",
        "Honestly, I haven't been out in almost a week. I've been feeling pretty low.",
        wait=10,
    )

    # 7. Find an accessible class.
    narrate("7. She's open to it — companion searches for an accessible class.", "cyan")
    say_as_sarah(
        "agrees",
        "Yeah… I do miss painting. Could you find a beginner watercolour class "
        "nearby that I can actually get to in my chair?",
        wait=10,
    )

    # 8-10. Book the class + accessible transport + calendar.
    narrate("8. She says yes — companion books the class, Wheel-Trans and calendar.", "cyan")
    say_as_sarah(
        "decides",
        "Yes, please book it for me — and sort out the accessible ride so I get "
        "there on time. Put it on my calendar too.",
        wait=11,
    )

    # 12. Optional supporter loop — low-key heads-up to her sister.
    narrate("12. Supporter loop — a low-key note to her sister (consent-approved).", "cyan")
    say_as_sarah(
        "adds",
        "Could you let my sister Amara know I'm heading out today?",
        wait=9,
    )

    # Wind down — plan read back, follow-up scheduled.
    narrate("Wind down — plan confirmed; gentle follow-up scheduled.", "green")
    detail("watch -> HR 71, SpO2 98 (a little more active)")
    be.ingest([{"kind": "hr", "value": 71}, {"kind": "spo2", "value": 98}])
    pause(2)
    narrate("Scenario complete. No alarm — proactive companion engagement.", "green")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Guardian scripted companion demo (Scenario 2).")
    ap.add_argument("--base", default="http://localhost:8000", help="backend base URL")
    ap.add_argument("--patient-id", type=int, default=2, help="target patient id")
    ap.add_argument("--setup", action="store_true",
                    help="load the Sarah companion persona into this patient first")
    ap.add_argument("--no-voice", action="store_true", help="don't speak from this PC")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="time multiplier for all delays (e.g. 0.5 = twice as fast)")
    args = ap.parse_args()

    be = Backend(args.base, args.patient_id)

    print(f"{_C['bold']}{_C['cyan']}")
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║   GUARDIAN — live demo: proactive companion engagement        ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print(_C["reset"])
    narrate(f"backend: {be.base}   patient: #{be.patient_id}", "dim")

    if not be.health():
        narrate(f"Backend not reachable at {be.base}. Start it first:", "red")
        detail("C:/Python313/python.exe -m uvicorn backend.main:app --port 8000")
        return 1
    narrate("Backend is up.", "green")
    narrate("Open the Live dashboard now: http://localhost:3000/live", "cyan")

    if args.setup:
        do_setup(be)

    voice = Voice(enabled=not args.no_voice)
    if voice.enabled:
        narrate("Voice ON — Guardian's replies will be spoken from this PC.", "green")
    else:
        narrate("Voice OFF.", "dim")

    listener = EventListener(be.base, voice)
    listener.start()
    if listener.connected.wait(timeout=5):
        narrate("Subscribed to the live event stream (same feed as the dashboard).", "green")
    else:
        narrate("Could not confirm SSE stream; continuing anyway.", "amber")

    try:
        run_scenario(be, speed=args.speed)
    except KeyboardInterrupt:
        narrate("Interrupted.", "amber")
    finally:
        narrate("Letting final speech play out…", "dim")
        voice.drain()
        listener.stop()

    narrate("Done.", "green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
