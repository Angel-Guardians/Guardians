#!/usr/bin/env python3
"""Guardian — scripted live demo: Scenario 1 (Matthew, night fall -> 911 + caregiver).

Run this and step away from the keyboard. It drives the *real* backend over HTTP so
the Live dashboard lights up on its own, and speaks Guardian's replies out loud from
this PC. Nothing here is mocked inside the backend — we only synthesise the watch's
sensor stream and the patient's spoken answers; the routing, the safety agent, the
tool calls and the replies are all produced by the running system.

Timeline (mirrors demo/SCENARIO_WALKTHROUGHS.md, Scenario 1):

    t+0s    armed -> 10 second countdown
    t+10s   1. Baseline      ingest HR 57 (asleep, sinus)          -> green
    t+~16s  2. Rhythm flare  ingest HR 142 (AFib w/ rapid rate)    -> amber, risk rises
    t+~23s  3-5. The fall    ingest fall_confirmed 2.8g + HR 135 + SpO2 91
                             -> backend AUTO-runs the Safety agent (recall -> 911 ->
                                notify caregiver). Replies are spoken from this PC.
    t+~31s  7. Confirm win.  ~8s for Matthew to cancel a false alarm (he doesn't)
    t+~39s  person input 1   feed a known faint reply -> real escalation, spoken
    t+~47s  person input 2   feed "call my daughter" -> caregiver notify, spoken
    t+~55s  12. Wind down    recovery vitals, incident logged

How it works:
  * A background thread subscribes to the same SSE stream the dashboard uses
    (GET /events/sse) and speaks every `agent_reply` and `call_request` through the
    Windows speech engine, so you hear exactly what the dashboard shows.
  * The main thread plays the timeline by POSTing vitals and turns to the backend.

Usage (from the repo root, with the backend already running on :8000):

    C:/Python313/python.exe demo/run_fall_scenario.py
    C:/Python313/python.exe demo/run_fall_scenario.py --setup     # first run: load Matthew
    C:/Python313/python.exe demo/run_fall_scenario.py --no-voice  # silent (just the UI)
    C:/Python313/python.exe demo/run_fall_scenario.py --base http://localhost:8000

Only the Python standard library is used, so any interpreter works.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Load the backend's .env so we can reuse TWILIO_911_NUMBER (the verified demo
# phone) for the scripted caregiver calls. Best-effort: no-op without python-dotenv.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except Exception:  # noqa: BLE001
    pass

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

    def turn(self, text: str, speak: bool = True) -> dict:
        # speak=True makes the backend render the reply with Kokoro and stream it
        # to the Live page speaker, so Guardian is heard in the real voice stack.
        return self._post(
            "/turn/", {"text": text, "patient_id": self.patient_id, "speak": speak}
        )

    def put_profile(self, profile: dict) -> dict:
        return self._put(f"/patient/{self.patient_id}/profile", profile)


# --------------------------------------------------------------------------- #
# Optional PC voice via the Windows speech engine (no deps). This is a *fallback*:
# by default Guardian is voiced with the real Kokoro stack on the Live dashboard
# (the backend renders each reply and streams it to /voice/listen). Enable this
# only with --pc-voice if you'd rather hear it from the PC's own speakers.
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
# + speak the agent's replies and outbound calls as they happen.
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
            print(f"{_C['red']}    [PHONE] dialling {_C['bold']}{who}{_C['reset']}"
                  f"{_C['red']} ({payload.get('phone', '')}){_C['reset']}")
            if msg:
                self.voice.say(msg)
        elif kind == "risk_score_updated":
            lvl = payload.get("level", "?")
            score = payload.get("score", "?")
            col = {"low": "green", "moderate": "amber",
                   "high": "red", "critical": "red"}.get(str(lvl), "cyan")
            print(f"{_C[col]}    [RISK] {lvl} ({score}){_C['reset']}")


# --------------------------------------------------------------------------- #
# Optional setup: load the Matthew cardiac persona so the safety agent's recall
# and grounding match the scripted scenario.
# --------------------------------------------------------------------------- #
MATTHEW_PROFILE = {
    "name": "Matthew Brennan",
    "age": 78,
    "conditions": [
        "paroxysmal atrial fibrillation",
        "coronary artery disease (prior MI, stents)",
        "mild heart failure",
        "orthostatic hypotension",
    ],
    "allergies": [],
    "primary_language": "en",
    "location": "200 Wellesley St E, Apt 1407, Toronto, ON M4X 1G7",
    "bio": "78, lives alone since his wife Eleanor passed in 2023. Daughter Claire "
           "is in Ottawa. Wears the Guardian watch (the only sensor).",
    "notes": "Anticoagulated (apixaban). Cardiac history means a nighttime fall can "
             "signal arrhythmic syncope. Highest-risk fall window is the 2-3am "
             "bathroom trip. Preferred hospital: St. Michael's.",
    "emergency_contacts": [
        {"name": "Sophie Tran, RN", "relationship": "caregiver (RN, same building)",
         "phone": "(416) 555-0188", "priority": 1},
        {"name": "Claire Brennan", "relationship": "daughter",
         "phone": "(613) 555-0173", "priority": 2},
    ],
    "medications": [
        {"name": "Apixaban", "dose": "5mg", "schedule_cron": "0 8,20 * * *",
         "with_food": False, "notes": "blood thinner (anticoagulant)"},
        {"name": "Metoprolol", "dose": "50mg", "schedule_cron": "0 8 * * *",
         "with_food": True, "notes": "rate control for AFib"},
    ],
}


def _demo_profile() -> dict:
    """Matthew's profile, with contact numbers pointed at the verified demo phone.

    On a Twilio trial account only *verified* numbers can be dialled. ``call_911``
    already uses ``TWILIO_911_NUMBER`` (the safe stand-in the team verified), so we
    route the caregiver/daughter calls to that same number — every "call" in the
    demo rings the one safe phone, exactly as the walkthrough intends. Without it,
    the calls degrade gracefully to a "failed" status (the turn still completes).
    """
    import copy

    profile = copy.deepcopy(MATTHEW_PROFILE)
    demo_phone = os.getenv("TWILIO_911_NUMBER", "").strip()
    if demo_phone:
        for contact in profile["emergency_contacts"]:
            contact["phone"] = demo_phone
    return profile


def do_setup(be: Backend) -> None:
    narrate("Setup: loading the Matthew cardiac persona…", "mag")

    # 1) Write data/personas/matthew.md (concatenate the demo persona docs) so
    #    recall_history has cardiac context to surface.
    src_dir = REPO_ROOT / "demo" / "personas" / "matthew"
    out_dir = REPO_ROOT / "data" / "personas"
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    for md in sorted(src_dir.glob("*.md")):
        parts.append(md.read_text(encoding="utf-8"))
    (out_dir / "matthew.md").write_text("\n\n---\n\n".join(parts), encoding="utf-8")
    detail(f"wrote {out_dir / 'matthew.md'}")

    # 2) Point patient #<id> at Matthew so the agent grounds on his cardiac profile.
    try:
        profile = _demo_profile()
        be.put_profile(profile)
        demo_phone = os.getenv("TWILIO_911_NUMBER", "").strip()
        detail(f"patient #{be.patient_id} profile -> Matthew Brennan (cardiac)")
        if demo_phone:
            detail(f"caregiver/daughter calls routed to verified demo phone {demo_phone}")
        else:
            detail("TWILIO_911_NUMBER unset — caregiver calls will log as 'failed' (ok for demo)")
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

    print()
    narrate("SCENARIO 1 — Matthew, 78. 2:14am. Asleep. Watch streaming.", "green")
    countdown(int(10 * speed), "fall scenario triggers in")

    # 1. Baseline — asleep, sinus rhythm, everything nominal.
    narrate("1. Baseline — all quiet.", "green")
    detail("watch -> HR 57, SpO2 97 (normal sinus)")
    be.ingest([{"kind": "hr", "value": 57}, {"kind": "spo2", "value": 97}])
    pause(5)

    # 2. The precursor — AFib with rapid ventricular rate as he sits up.
    narrate("2. Rhythm flares — irregular, rapid heartbeat (the near-faint precursor).", "amber")
    detail("watch -> HR 142, ECG flag: irregularly irregular")
    be.ingest([{"kind": "hr", "value": 142}])
    pause(6)

    # 3-5. The fall + corroboration. fall_confirmed makes the backend AUTO-run the
    #      Safety agent: recall -> 911 -> notify caregiver. We just watch + listen.
    narrate("3. THE FALL — accelerometer logs impact + orientation flip.", "red")
    detail("watch -> fall_confirmed (peak 2.8g), HR 135 (still irregular), SpO2 91, no recovery motion")
    be.ingest([
        {"kind": "fall_confirmed", "value": 2.8},
        {"kind": "hr", "value": 135},
        {"kind": "spo2", "value": 91},
    ])
    narrate("   -> classifier: hard fall + non-response + abnormal rhythm = TOP TIER (cardiac).", "red")
    narrate("   -> routing to SAFETY. The agent is now acting on its own…", "red")

    # 7. Confirm window — the safety agent holds the floor and gives Matthew time
    #    to cancel a false alarm. He's unresponsive.
    pause(2)
    narrate("7. Safety holds the floor — Matthew has 8s to cancel a false alarm.", "amber")
    countdown(int(8 * speed), "listening for 'I'm okay'")
    narrate("   …no response. Matthew is unresponsive.", "red")

    # Person input #1 (faked, fed to the real backend to get a real reply).
    pause(1)
    answer1 = "I can't get up... my chest hurts and my heart is racing."
    narrate("(simulated) Matthew answers faintly:", "mag")
    detail(f'"{answer1}"')
    try:
        be.turn(answer1)
    except Exception as exc:  # noqa: BLE001
        detail(f"turn failed: {exc}")
    pause(7)

    # Person input #2 — ask for the daughter; drives the caregiver-notify beat.
    answer2 = "Please call my daughter Claire and tell her what's happening."
    narrate("(simulated) Matthew adds:", "mag")
    detail(f'"{answer2}"')
    try:
        be.turn(answer2)
    except Exception as exc:  # noqa: BLE001
        detail(f"turn failed: {exc}")
    pause(7)

    # 12. Wind down — vitals stabilising as help arrives; incident logged.
    narrate("12. Help is on the way. Vitals stabilising; incident logged.", "amber")
    detail("watch -> HR 96, SpO2 95 (recovering)")
    be.ingest([{"kind": "hr", "value": 96}, {"kind": "spo2", "value": 95}])
    pause(2)
    narrate("Scenario complete. Risk de-escalates Red -> Amber.", "green")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Guardian scripted fall demo (Scenario 1).")
    ap.add_argument("--base", default="http://localhost:8000", help="backend base URL")
    ap.add_argument("--patient-id", type=int, default=1, help="target patient id")
    ap.add_argument("--setup", action="store_true",
                    help="load the Matthew cardiac persona into this patient first")
    ap.add_argument("--pc-voice", action="store_true",
                    help="ALSO speak replies via Windows TTS on this PC "
                         "(Kokoro already plays on the Live dashboard)")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="time multiplier for all delays (e.g. 0.5 = twice as fast)")
    args = ap.parse_args()

    be = Backend(args.base, args.patient_id)

    print(f"{_C['bold']}{_C['cyan']}")
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║   GUARDIAN — live demo: night fall -> 911 + caregiver         ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print(_C["reset"])
    narrate(f"backend: {be.base}   patient: #{be.patient_id}", "dim")

    if not be.health():
        narrate(f"Backend not reachable at {be.base}. Start it first:", "red")
        detail("C:/Python313/python.exe -m uvicorn backend.main:app --port 8000")
        return 1
    narrate("Backend is up.", "green")
    narrate("Open the Live dashboard now: http://localhost:3000/live", "cyan")
    narrate("On the Live page, click the speaker 'Listen' button ONCE so the browser "
            "allows audio — Guardian's real (Kokoro) voice plays there.", "amber")

    if args.setup:
        do_setup(be)

    # Voice is produced by the backend's Kokoro stack and played on the dashboard.
    # The PC speech engine is only an optional extra (--pc-voice).
    voice = Voice(enabled=args.pc_voice)
    if voice.enabled:
        narrate("PC voice ON — replies also spoken from this PC's speakers.", "green")
    else:
        narrate("Voice: real Kokoro stack, played on the Live dashboard.", "green")

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
