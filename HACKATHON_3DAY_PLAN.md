# Guardian — 3-Day Hackathon Plan: MVP to Production-Demo

> 72 hours from `git clone` to judges seeing a production-quality demo.

All workloads live on **the DGX Spark** — no separate edge hardware. Always-on services (wake word, VAD, STT, audio event classification, sensor poll, scheduler) run in **CPU-pinned background processes** on the Grace ARM cores. The Llama 3.1 8B agent + Kokoro TTS bind to the **Blackwell GPU** on demand.

**"Production-quality" here = polished, defensible, repeatable in front of judges.** Real PHIPA hardening (SQLCipher, signed audit chain, mic kill switch, Tailscale, FHIR auth) is post-hackathon Phase 7 in [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md). The demo proves the concept and the architecture; deployment is a separate sprint.

---

## What we are shipping by hour 72

Five scenarios, judge-ready, on a live UI:

1. **Fall scenario** — *"Hey Guardian, I fell"* → Safety + Companion run in parallel → mock 911 dispatch with personalized handoff → calm reassurance.
2. **Vitamin reminder** — APScheduler fires at scheduled time → UI nudge + TTS → tap-to-confirm intake logged.
3. **Memory recall** — *"Hey Guardian, did I take my pill?"* → Companion answers from the Event Log.
4. **Vitals anomaly** — Polar H10 chest strap detects HR spike → Health Agent triggers a gentle in-room check-in.
5. **Caregiver SMS** — Real Twilio SMS lands on a real test phone with an incident summary, plus a structured FHIR `Communication` resource pushed to a HAPI test server.

Live UI shows: streaming event log, real-time vitals chart, reminders dashboard with intake checklist.

---

## Pre-day-0 setup (the night before)

Done before Day 1 starts. If not, do it during Day 1 morning and slip everything by a few hours.

- [ ] DGX environment: CUDA 12.x, Python 3.11, Docker, Git
- [ ] Ollama installed; `ollama pull llama3.1:8b-instruct-q4_K_M` (≈5GB)
- [ ] Verify Ollama: `ollama run llama3.1:8b "hello"` returns reasonable text
- [ ] Mic working: `arecord -l` lists the ReSpeaker, test capture
- [ ] Polar H10 paired and discoverable via `bluetoothctl scan on`
- [ ] Twilio account with $5 credit, test number provisioned, one team phone numbers verified
- [ ] Git repo cloned by all team members; `uv` or `poetry` initialized
- [ ] Smoke test: `streamlit hello`, `uvicorn --help`, `kokoro` import works, `faster_whisper` import works
- [ ] HAPI FHIR test server reachable: `curl http://hapi.fhir.org/baseR4/Patient?_count=1`
- [ ] CPU core pinning verified: identify which Grace cores you'll pin always-on services to (recommend cores 0–5 for always-on, 6+ for everything else)

---

# Day 1 — MVP: Single-agent fall demo works (12h)

**Goal at end of day:** You can say *"Hey Guardian, I fell"* and get a personalized response with a mock 911 call, with Safety and Companion running in parallel and writing to an Event Log.

## 09:00–10:00 — Repo scaffold

**Owner:** tech lead.

- Create the package layout from [`ARCHITECTURE.md`](ARCHITECTURE.md) §2 Backend sketch:
  ```
  backend/
  ├── always_on/          # CPU-pinned: mic, VAD, wake, STT-lite, audio events
  ├── orchestrator/       # supervisor + router + risk classifier
  ├── agents/             # safety.py, companion.py, ... (one per sub-agent)
  ├── tools/{sensing,memory_reasoning,action,integrations}/
  ├── api/                # FastAPI routers
  ├── services/           # business logic shared with agents
  ├── db/                 # SQLModel + Alembic
  ├── events/             # event bus
  ├── workers/            # Arq workers (slow-time)
  └── main.py
  frontend/               # Streamlit app
  ```
- `pyproject.toml` deps: fastapi, uvicorn, sqlmodel, alembic, langgraph, langchain-ollama, pydantic, sounddevice, faster-whisper, kokoro, openwakeword, apscheduler, bleak, influxdb-client, sse-starlette, plotly
- Initial Pydantic models in `backend/db/models.py`: `Patient`, `Incident`, `EventLogEntry`
- First commit: `chore: scaffold backend package layout`

## 10:00–11:00 — Audio I/O round-trip

**Owner:** audio person.

- `always_on/capture.py`: `sounddevice` → 16 kHz mono numpy buffer
- `always_on/transcribe.py`: `faster_whisper` int8 wrapper (`small.en` for speed)
- `tools/action/tts.py`: Kokoro TTS → audio playback
- Test script: press Enter → capture 5s → transcribe → echo via TTS
- Acceptance: round-trip latency < 4s, output intelligible at normal volume

## 11:00–12:00 — LLM call

**Owner:** agent person.

- `agents/llm.py`: Ollama wrapper bound to `llama3.1:8b-instruct-q4_K_M`
- Hard-coded Guardian system prompt
- Tie audio to LLM: voice in → text → LLM → text → voice out
- Acceptance: *"What time is it?"* → reasonable spoken response

## 12:00–13:00 — Lunch / model checkpoint

If Llama 3.1 8B isn't pulled yet, do it now. Verify free VRAM ≥ 6GB with `nvidia-smi`.

## 13:00–14:00 — Backend skeleton + patient profile

**Owner:** backend person.

- FastAPI app on `localhost:8000`
- SQLite + SQLModel; `alembic init backend/db/migrations`
- `Patient` model: name, age, conditions, meds, allergies, emergency contacts
- Seed `Eleanor, 70, cardiac history, lives alone` + daughter Maria as primary contact
- `GET /patient/{id}` returns the profile
- Acceptance: `curl localhost:8000/patient/1` returns Eleanor's record

## 14:00–15:00 — Single LangGraph agent with 2 tools

**Owner:** agent person.

- `agents/guardian.py`: one LangGraph `StateGraph`
- Tool 1: `get_patient_profile()` → reads from SQLite
- Tool 2: `call_911_mock(summary: str)` → prints to console + writes `Incident` row
- System prompt teaches the agent to use both tools when emergency keywords appear
- Acceptance: feeding "I fell" produces a structured emergency response that names Eleanor and her cardiac history

## 15:00–16:00 — Wake word

**Owner:** audio person.

- `always_on/wake.py`: openWakeWord with a custom *"Hey Guardian"* model
- Train on ~50 utterances per team member (you can use the openWakeWord training notebook)
- **Fallback:** if accuracy is poor, ship with a push-to-talk hotkey (`F9`) and tell the demo audience
- Acceptance: 5 minutes of normal conversation triggers zero false fires; saying "Hey Guardian" from 6 feet works 5/5 times

## 16:00–17:00 — Fall demo end-to-end

**Owner:** full team.

- Wire the pieces: wake word → STT → single agent → tool calls → TTS response
- Demo line: *"Hey Guardian, I fell and I can't get up"*
- Expected output: TTS says something like *"Eleanor, I'm calling 911. They know about your cardiac history. Help is on the way. Stay still and try not to move."* Console prints the mock 911 summary with profile fields.
- Acceptance: works 5 times in a row from ~6 feet

## 17:00–19:00 — Three-tier refactor (Phase 2 starts)

**Owner:** agent person + tech lead.

- Split `agents/guardian.py` into:
  - `orchestrator/supervisor.py` — LangGraph supervisor with hybrid router (rules for `event.type == "emergency_keyword"`, fall through to LLM otherwise)
  - `agents/safety.py` — owns 911 + contact tree, urgent voice profile
  - `agents/companion.py` — owns calm-keeping dialogue, calm voice profile
- Both sub-agents share the Llama 3.1 8B model (different system prompts, different allowed tools)
- Voice profiles: pick two distinct Kokoro voice IDs
- Acceptance: the fall demo still passes, but logs show both sub-agents acting in parallel, and the user hears two distinct voices

## 19:00–20:00 — Event Log

**Owner:** backend person.

- Append-only `EventLog` table with `(ts, source, event_type, payload, reason)`
- `@audit_log` decorator on every tool call writes a row
- Orchestrator logs every routing decision with a reason field
- Acceptance: after a fall demo, the Event Log is a complete ordered timeline of both sub-agents' activity

## 20:00–21:00 — Day 1 wrap

- Smoke test: run the fall demo 3 times back-to-back, verify nothing has regressed
- `git commit -m "feat: day-1 mvp three-tier fall demo working"`
- Write down rough edges for tomorrow

### Day 1 exit criteria

- [ ] Wake word triggers reliably (or push-to-talk works)
- [ ] *"Hey Guardian, I fell"* triggers Safety + Companion in parallel
- [ ] 911 summary references Eleanor's cardiac history (personalization works)
- [ ] Companion delivers calming response in a *distinct* voice
- [ ] Event Log shows the full ordered timeline
- [ ] Demo works 5 times in a row reliably

---

# Day 2 — Multi-scenario + vitals + reminders + UI (12h)

**Goal at end of day:** Four scenarios run reliably + a judge can SEE what the system is doing on a live UI.

## 09:00–10:00 — Tool Bus formalization

**Owner:** tech lead.

- `tools/` package structured into the 4 buckets: `sensing/`, `memory_reasoning/`, `action/`, `integrations/`
- Every tool is a Pydantic-typed function with a Pydantic `ArgsModel` and `ResultModel`
- `@audit_log` decorator (already from Day 1)
- `@idempotent(key_fn=...)` decorator for outbound side-effect tools (911, SMS, FHIR)
- Per-agent allowed-tool sets defined in `agents/<name>/allowed_tools.py`
- Acceptance: Companion calling `call_911_mock` raises a `ToolNotAllowed` exception

## 10:00–11:00 — Risk Classifier (rules v0)

**Owner:** agent person.

- `tools/memory_reasoning/risk_classifier.py`
- Rule table: keyword + duration + signal-source → Tier 1/2/3/4
- Orchestrator runs this on every event **before** routing — severity is a routing input
- Acceptance: *"I fell"* → Tier 4; *"I'm tired"* → Tier 1; *"where am I"* → Tier 2

## 11:00–12:00 — Reminder Agent + APScheduler

**Owner:** backend person.

- `agents/reminder.py` LangGraph subgraph
- APScheduler embedded in the Backend; one job per medication time
- Tool: `schedule_reminder(med_name, time)` and `dispatch_reminder(med_name)`
- Scheduler fires → emits `ReminderEvent` onto the bus → Orchestrator routes to Reminder Agent → dispatches notification
- Acceptance: a med scheduled for "now + 60s" fires; TTS says *"Eleanor, time for your blood pressure pill."*

## 12:00–13:00 — Lunch

## 13:00–15:00 — Wearable vitals integration

**Owner:** integrations person.

- `always_on/wearable.py`: `bleak` BLE client reads Polar H10 HR characteristic
- Streams to InfluxDB (or just a `Vital(ts, type, value, source)` SQLite table for speed)
- `tools/sensing/bio_marker.py`: returns latest HR for a window
- Acceptance: putting on the chest strap surfaces HR in the system within 2 seconds; HR is queryable via the tool

## 15:00–16:00 — Notification dispatcher with severity tiers

**Owner:** agent person.

- `tools/action/notification_dispatcher.py`
- Tiered behavior:
  - Tier 1 → soft TTS only
  - Tier 2 → TTS + UI toast
  - Tier 3 → loud TTS + ambient-light stub (console print for now) + caregiver SMS
  - Tier 4 → 911 mock + family voice call mock
- Acceptance: med reminder fires at Tier 2 (TTS + toast); fall demo fires at Tier 4 (full chain)

## 16:00–17:00 — Memory recall demo

**Owner:** agent person.

- Companion Agent tool: `query_event_log(start_time, end_time, event_type)`
- Demo: *"Hey Guardian, did I take my pill?"* → Companion queries Event Log → answers with timestamp
- Acceptance: works correctly after a tap-to-confirm intake earlier in the session

## 17:00–19:00 — Streamlit UI: Live + Vitals

**Owner:** UI person.

- `frontend/app.py` with three pages: **Live**, **Vitals**, **Reminders**
- Backend exposes `GET /events/sse` using `sse-starlette`
- **Live page:** SSE-driven Event Log table + current transcript pane
- **Vitals page:** Plotly chart of HR over last 1h
- Acceptance: doing a fall demo, the Live page updates within 1 second of each step

## 19:00–20:00 — Streamlit UI: Reminders + tap-to-confirm

**Owner:** UI person.

- **Reminders page:** today's schedule + intake checklist with tap-to-confirm buttons
- Tap-to-confirm emits a `TapConfirmedEvent` onto the bus
- Reminder Agent logs confirmation to the Event Log
- Acceptance: vitamin reminder can be confirmed by tap, and "did I take my pill?" then answers correctly

## 20:00–21:00 — Day 2 smoke test

- All four scenarios E2E: Fall, Vitamin Reminder, Memory Recall, Vitals stream visible
- `git commit -m "feat: day-2 multi-scenario + ui + vitals"`

### Day 2 exit criteria

- [ ] Three-tier architecture fully live (Orchestrator + Safety + Companion + Reminder)
- [ ] Polar H10 HR appears in system + UI within 2s
- [ ] Med reminder fires + can be tap-confirmed
- [ ] *"Did I take my pill?"* returns the right answer
- [ ] Live UI shows the architecture working in real time

---

# Day 3 — Polish + Health Agent + Caregiver Liaison + Demo (12h)

**Goal at end of day:** Production-quality demo ready, video recorded as fallback, pitch rehearsed, slide deck done.

## 09:00–10:00 — Health Agent

**Owner:** agent person.

- `agents/health.py` LangGraph subgraph
- Allowed tools: `bio_marker`, `personal_baseline`, `anomaly_detector`, `clinical_consult` (stubbed — could wrap a Meditron prompt against Ollama if there's time)
- Voice profile: calm
- Orchestrator routes vitals-anomaly events to Health Agent

## 10:00–11:00 — Personal Baseline + Anomaly Detector

**Owner:** agent person.

- `tools/memory_reasoning/personal_baseline.py`: rolling mean and stddev per vital per time-of-day, stored in SQLite, updated nightly via an Arq worker stub
- `tools/memory_reasoning/anomaly_detector.py`: simple z-score threshold (PyOD IsolationForest is nicer but takes longer to wire)
- Acceptance: a manually-injected HR of 130 (when baseline is 60) classifies as a Tier 2 anomaly

## 11:00–12:00 — Sleep HR anomaly scenario

**Owner:** agent person + audio person.

- Demo path: simulate an HR excursion (via a debug endpoint that injects a fake vital) → Health Agent does ambient soft TTS check-in: *"I noticed your heart rate changed. Are you okay?"* → tap-to-confirm dismisses; no response after 60s escalates to caregiver SMS
- Acceptance: full flow works end-to-end with both branches (confirm and no-response)

## 12:00–13:00 — Lunch

## 13:00–14:00 — Caregiver Liaison + real Twilio SMS

**Owner:** integrations person.

- `agents/caregiver_liaison.py` LangGraph subgraph
- `tools/integrations/twilio_sms.py`: real Twilio SMS via the REST API
- Configure Twilio creds via env vars (NOT in git)
- Acceptance: a fall demo triggers a real SMS landing on a team phone within 5 seconds, with Eleanor's name + the incident type

## 14:00–15:00 — Mock FHIR push

**Owner:** integrations person.

- `tools/integrations/fhir_push.py`: push a `Communication` resource to `http://hapi.fhir.org/baseR4` with the incident summary
- Caregiver Liaison invokes this after a Tier 3+ incident
- Acceptance: after a fall demo, the resource is queryable on HAPI by its returned ID

## 15:00–16:00 — UI polish

**Owner:** UI person.

- Hero header with Guardian branding (logo, tagline)
- Typography, spacing, dark-mode-friendly colors
- Hide debug noise; surface only what judges need to see
- Demo-state reset button (clears today's events, re-seeds reminders for "demo time + 2 min")
- Acceptance: a non-technical person can look at the screen and understand what's happening

## 16:00–17:00 — Demo script + dry run #1

**Owner:** full team.

3-minute demo outline:

| Time | Beat |
|---|---|
| 0:00–0:20 | Problem statement: 350k+ Toronto paramedic calls, gap between event and response. Guardian's value. |
| 0:20–1:00 | **Live fall scenario.** Show the multi-agent response, the personalized 911 summary, the calming voice. |
| 1:00–1:30 | Switch to UI: Event Log shows what just happened, live transcript, vitals chart. |
| 1:30–2:00 | **Vitamin reminder** fires + tap-to-confirm. *"Did I take my pill?"* answered. |
| 2:00–2:30 | **Vitals anomaly** + soft check-in + caregiver SMS arrives on actual phone (hold it up). |
| 2:30–3:00 | Privacy posture: local-only, PHIPA-aligned. Architecture diagram. Roadmap. Thanks. |

Run through it cold. Identify weak spots.

## 17:00–18:00 — Dry run #2 + fix weak spots

Specific things to lock down:

- The fall demo speech-to-911-summary path is reliable
- The vitamin demo doesn't surprise the speaker (time the dispatch right)
- The UI is showing the *right* things at the *right* time (transcript pane visible during voice; vitals pane visible during anomaly)
- Twilio SMS arrives within 5s — if there's carrier delay, show the UI's "SMS sent" toast instead

## 18:00–20:00 — Record demo video as fallback

**Owner:** full team.

- Screen + mic recording via OBS or equivalent
- Aim for a 3-minute final cut
- Multiple takes — pick the best
- This is your safety net if the live demo hardware flakes (Polar H10 won't pair, network drops, etc.)
- Upload to a shared drive; have the file ready on every team member's laptop

## 20:00–21:00 — Slide deck for judge Q&A

5–8 slides:

1. **Problem + tagline** (the README's first two paragraphs, condensed)
2. **Two modes** (passive + active)
3. **Three-tier architecture** ([ARCHITECTURE.md](ARCHITECTURE.md) §4 diagram)
4. **Scenario coverage** (showed 5, have 27 playbooks ready — see [guardian_scenarios.md](guardian_scenarios.md))
5. **Privacy posture** (consent matrix, local-only inference, PHIPA-aligned)
6. **Tech stack one-pager** (TL;DR pick list from [TECH_STACK.md](TECH_STACK.md))
7. **Roadmap** (Phases 4–9 from [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) — what's coming after the hackathon)
8. **Team + acknowledgements**

### Day 3 exit criteria

- [ ] All five demo scenarios work reliably (Fall, Vitamin, Recall, Vitals anomaly, Caregiver SMS)
- [ ] Real SMS lands on a real phone during the demo
- [ ] FHIR resource pushed and visible on HAPI
- [ ] Live UI is judge-comprehensible
- [ ] Demo video recorded as fallback (under 3 min)
- [ ] Live demo dry-run done at least twice
- [ ] Architecture slide deck ready
- [ ] Repo is clean, `git status` shows no surprises

---

## Stretch goals (only if ahead of schedule)

In rough order of impact-per-hour:

| Stretch | Effort | Adds |
|---|---|---|
| **Spotify MCP** for calming music | 2h | Companion plays calming track during a Tier-1 reassurance — shows MCP working |
| **YAMNet audio event detection** | 3h | Pre-recorded fall sound (no patient voice) triggers Safety — the "passive mode" headline |
| **Wandering scenario** | 4h | Front-door sensor mock at simulated 3 AM → Companion does gentle redirection — shows behavioral range |
| **Cloned voice via XTTS-v2** | 3h | One team member's family voice cloned for a Companion utterance — demos S17/S22/S26 capability |
| **Calendar MCP** | 2h | Reminder Agent pulls a doctor appointment — shows external integrations |

Pick at most two. Do not pick a stretch that risks the core five demos.

---

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Polar H10 doesn't pair during demo | Medium | Pre-pair morning of, lock the device, add a "simulated vitals stream" toggle in the UI as fallback |
| openWakeWord misfires or misses | High | Ship with push-to-talk fallback (F9 hotkey); train on more samples if time |
| Llama 3.1 8B mis-routes a narrative scenario | Medium | Use the **hybrid router** — rules for the demo keywords; LLM only for ambiguous |
| Twilio SMS doesn't arrive in time | Low | Show a "sent" status in the UI; the demo doesn't wait |
| Streamlit struggles with live updates | Medium | Use `st.empty()` polling pattern, not stateful widgets; fallback to static-with-F5 |
| Demo machine OOMs | Low | Quantize Llama to q4_K_M (≈5GB); monitor `nvidia-smi` during dev |
| Network drops during demo | Medium | Twilio + FHIR will fail. Have screenshots of prior successful sends as backup. |
| Team member is sick / drops out | Medium | Every scenario is scripted; demo video is the ultimate fallback |
| LLM hallucinates patient data | Medium | Constrain the agent's outputs with Pydantic schemas, not free text, for emergency summaries |
| Two voices talk over each other | Medium | Enforce the conversational floor lock in code; only Companion holds the TTS lock during active dialog |

---

## Team roles (3–4 people optimal)

| Role | Owns |
|---|---|
| **Tech lead / backend** | Repo scaffold, FastAPI, SQLModel, event bus, Alembic, integration glue, demo-day deployment |
| **Agent / LLM** | LangGraph orchestrator, sub-agents, tool definitions, routing rules, system prompts |
| **Audio / integrations** | STT, TTS, wake word, Polar H10 BLE, Twilio, FHIR push, audio-pipeline reliability |
| **UI / demo** | Streamlit pages, design, demo script, video, slide deck, judge-facing polish |

With 3 people: merge UI into the tech-lead role or split UI between agent and audio.

---

## What "production" means — and does NOT mean — in 72 hours

After 72 hours you have a **defensible, demo-ready, judge-pitchable Guardian**. You do **not yet** have a PHIPA-deployable product. Be honest about the gap — judges respect this.

What's NOT in scope for the hackathon (each is mapped to a later Phase in [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md)):

| Capability | Why it's deferred | Phase |
|---|---|---|
| SQLCipher (DB encryption) | Phase 1 SQLite is plaintext for dev speed | Phase 7 |
| LUKS disk encryption | Requires re-imaging the DGX | Phase 7 |
| Tamper-evident audit chain | Append-only log is there; hash chain is not | Phase 7 |
| Hardware mic kill switch | Requires hardware mod to the ReSpeaker | Phase 7 |
| Production-grade wake-word accuracy | openWakeWord with 50 samples per person is "demo-good," not "real-deployment-good" | Phase 6+ |
| NVIDIA Riva TTS | Kokoro is faster to set up and Good Enough for the demo | Phase 7 |
| TensorRT-LLM / NIM | Ollama is faster to set up and Good Enough for the demo | Phase 7 |
| Pipecat audio pipeline with interruption-handling | Ad-hoc audio loop is enough for scripted demos | Phase 6 |
| Consent matrix UI | Consent is hard-coded in dev to "everything allowed" | Phase 5 |
| Next.js UI | Streamlit is faster to ship | Phase 7 |
| Health Agent medical RAG (Meditron + Qdrant) | Health Agent is stubbed; clinical consult is mocked | Phase 4 |
| Real 911 dispatch | Real 911 requires NENA i3 / CAD integration | Post-Phase-9 |

When a judge asks "is this PHIPA-ready?" — answer honestly: *"The architecture is PHIPA-shaped from the ground up — consent matrix, audit log, local-only inference, encryption-friendly storage layout. Hardening (SQLCipher, signed audit chain, hardware kill switch, Tailscale, hardware-rooted attestation) is the next eight-week sprint after this hackathon. The phased plan in DEVELOPMENT_PLAN.md spells it out."*

---

## Phase mapping back to DEVELOPMENT_PLAN.md

This 3-day plan is a fast-forward through **Phases 0 → 4 (partial)** of the long-term plan:

- **Day 1 09:00–17:00** = Phase 0 (walking skeleton) + Phase 1 (MVP fall demo)
- **Day 1 17:00–21:00** = Phase 2 start (three-tier refactor + Event Log)
- **Day 2 09:00–17:00** = Phase 2 finish + Phase 3 start (Reminder Agent, vitals, tool bus, dispatcher, memory recall)
- **Day 2 17:00–21:00** = Phase 3 finish (Streamlit UI on SSE)
- **Day 3 09:00–15:00** = Phase 4 partial (Health Agent + simple baseline + anomaly) + Phase 5 partial (Caregiver Liaison + real Twilio + FHIR)
- **Day 3 15:00–21:00** = Demo polish, video, slide deck

After the hackathon, the long-term plan picks up at Phase 4 proper (medical RAG, full PyOD anomaly suite, pattern-absence detector) and Phase 5 proper (Behavior Agent, consent matrix, court/counselor portal).

---

## One-page summary (slide-ready)

```
DAY 1  →  MVP single-agent fall demo, then three-tier refactor + Event Log
DAY 2  →  Tool Bus + Risk Classifier + Reminder Agent + vitals + Streamlit UI
DAY 3  →  Health Agent + Caregiver Liaison + real Twilio + FHIR + polish + video

EXIT: 5 demos working live + recorded fallback + slide deck + judge Q&A prep
```
