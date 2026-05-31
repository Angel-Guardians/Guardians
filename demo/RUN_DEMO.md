# Running the live demos

Two scripts drive the **real** backend so the Live dashboard lights up on its own
and Guardian's replies are **spoken from this PC**. They script the two scenarios
from [SCENARIO_WALKTHROUGHS.md](SCENARIO_WALKTHROUGHS.md):

- **`run_fall_scenario.py`** — Scenario 1: Matthew, 78, night fall → 911 + caregiver.
- **`run_companion_scenario.py`** — Scenario 2: Sarah, 35, wheelchair user → proactive
  companion engagement (meds, an accessible painting class, Wheel-Trans, calendar).

The rest of this file describes the fall demo; the companion demo runs the same way
(see [Scenario 2](#scenario-2--companion-engagement) at the bottom).

## Scenario 1 — the fall demo

`run_fall_scenario.py` drives the **real** backend so the Live dashboard lights up
on its own and Guardian's replies are **spoken from this PC**. It scripts Scenario 1
from [SCENARIO_WALKTHROUGHS.md](SCENARIO_WALKTHROUGHS.md): Matthew, 78, night fall →
911 + caregiver.

## What it does
1. Waits **10 seconds** after you start it (a countdown).
2. Streams a mock watch timeline into `POST /vitals/ingest`: baseline HR → an AFib
   rhythm flare → a `fall_confirmed` impact.
3. The `fall_confirmed` reading makes the backend **automatically run the Safety
   agent** — recall the patient's cardiac history, call 911, notify the caregiver.
   Nothing is faked inside the backend; routing, tools and replies are all real.
4. Holds an **8-second confirm window** (Matthew doesn't cancel), then feeds two
   **known patient answers** into `POST /turn/` and plays back the real replies.
5. Winds down with recovering vitals.

Guardian's replies are voiced with the **real Kokoro stack** (the same TTS the watch
turns use): the backend renders each reply and streams it to the Live page speaker.
A background thread in the script also narrates the event stream in your terminal.

> **Click "Listen" once.** On the Live page, click the speaker **Listen** button a
> single time before/just after you start the script — browsers only allow audio
> after a user gesture. From then on Guardian's voice plays automatically.

## The Live monitor reflects the backend
The Live page no longer has an in-UI "Play demo" animation or a Demo/Live toggle — it
now **always mirrors the real backend** over SSE. As the script runs you'll see the
**pipeline flow map** light up (Input → Router → Safety → tools), the **event stream**
table fill in, the **risk gauge** climb, and the **speaker** voice the replies.

## Prerequisites
- **Backend running** on :8000 (from the repo root):
  ```powershell
  C:/Python313/python.exe -m uvicorn backend.main:app --port 8000
  ```
- **Frontend running** on :3000 — open **http://localhost:3000/live** before you start.
- An LLM configured in `.env` (the `/health` check must say `"guardian":"ready"`).
- Kokoro (or an OpenAI key) configured for TTS, and sound on. Click **Listen** on the
  Live page once so the browser allows audio.

## Run it (from the repo root)
```powershell
# First time: load the Matthew cardiac persona into patient #1, then play it
C:/Python313/python.exe demo/run_fall_scenario.py --setup

# Subsequent runs (persona already loaded)
C:/Python313/python.exe demo/run_fall_scenario.py
```

`--setup` writes `data/personas/matthew.md` (so `recall_history` surfaces his cardiac
history) and points patient **#1**'s profile at Matthew Brennan with Sophie (RN) and
Claire as contacts. Out of the box patient #1 is the seeded **Eleanor**, so run
`--setup` once to make the cardiac narrative land.

## Options
| Flag | Effect |
|---|---|
| `--setup` | Load the Matthew cardiac persona into the patient first. |
| `--pc-voice` | *Also* speak replies via Windows TTS on this PC (Kokoro already plays on the dashboard). |
| `--speed 0.5` | Time multiplier for every delay (`0.5` = twice as fast). |
| `--base URL` | Backend base URL (default `http://localhost:8000`). |
| `--patient-id N` | Target patient id (default `1`). |

## Notes
- A real fall response only fires once per **60 s** per patient (a debounce in
  `backend/services/fall_response.py`). Wait a minute between full runs.
- The heart-rate sparkline on the Live page updates from a **5 s poll** of `/vitals`,
  so the spike appears a few seconds after it's ingested; the risk gauge, pipeline
  graph, transcript and replies update **instantly** over SSE.
- The demo never dials a real phone — `call_request` events carry the announcement
  text/audio for a connected phone app; here we just speak and log them.

## Scenario 2 — companion engagement

`run_companion_scenario.py` is the calm counterpart. It scripts Scenario 2 from
[SCENARIO_WALKTHROUGHS.md](SCENARIO_WALKTHROUGHS.md): Sarah, 35, a wheelchair user
who's been home and low for about a week. There is **no alarm** — Guardian acts as a
proactive companion that does things on her behalf.

### What it does
1. Waits **10 seconds** (a countdown), then streams calm low-activity vitals and
   narrates the 6-days-home isolation signal.
2. Feeds Sarah's spoken side of the conversation into `POST /turn/` and plays back
   the **real** companion replies: a warm morning check-in that leads with her
   Sertraline, logging the dose, noticing the isolation, suggesting a beginner
   watercolour class, booking it + accessible Wheel-Trans transport + her calendar,
   then a low-key heads-up to her sister Amara.
3. Winds down with the plan confirmed and a gentle follow-up.

Everything that lands in the dashboard — routing to the **companion**, the tool
calls and the replies — is produced by the running system; the script only
synthesises the watch stream and Sarah's answers.

### Run it (from the repo root)
```powershell
# First time: load the Sarah companion persona into patient #2, then play it
C:/Python313/python.exe demo/run_companion_scenario.py --setup

# Subsequent runs (persona already loaded)
C:/Python313/python.exe demo/run_companion_scenario.py
```

`--setup` writes `data/personas/sarah.md` (so `recall_history` surfaces her interests,
mood and supports) and points patient **#2** at Sarah Okafor with **Amara** (sister)
as her primary support. The same flags as Scenario 1 apply (`--pc-voice`, `--speed`,
`--base`, `--patient-id`; here `--patient-id` defaults to **2** so Scenario 1's
Matthew on #1 and Sarah on #2 can coexist).
