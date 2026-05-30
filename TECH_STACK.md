# Guardian — Tech System Stack

Hardware target: **NVIDIA DGX Spark (GB10 Grace Blackwell Superchip)** — ARM64 + Blackwell GPU, fully on-device inference, no cloud APIs for any health-relevant path.

This document maps every block of the architecture diagram (and a few neighboring ones it implies) to concrete modules. For each layer we list **2–3 options** with a recommended pick and a one-line reason. Recommendations balance "ship in a hackathon weekend" against "won't be embarrassing in a real PHIPA deployment."

---

## Architecture at a Glance

Guardian is a **three-tier agent architecture** hosted inside a single Backend process. The Orchestrator routes signals to one of six specialist Sub-Agents; every Sub-Agent can call any tool on a shared four-bucket Tool Bus.

### Conceptual view (agent tiers)

```
                          ┌──────────────────────────────┐
                          │   Guardian Orchestrator      │
                          │  event router · escalation   │
                          │  policy · profile-aware      │
                          └───────────────┬──────────────┘
                                          │
   ┌─────────┬─────────┬──────────────────┼──────────────┬────────┬─────────┐
   ▼         ▼         ▼                  ▼              ▼        ▼
┌──────┐ ┌──────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐
│Safety│ │Health│ │ Reminder │ │ Companion  │ │ Behavior │ │Caregiver │
│Agent │ │Agent │ │  Agent   │ │   Agent    │ │  Agent   │ │  Liaison │
└──┬───┘ └──┬───┘ └────┬─────┘ └─────┬──────┘ └────┬─────┘ └────┬─────┘
   └────────┴──────────┴─────────────┴─────────────┴────────────┘
                                  │
                                  ▼
   ══════════════════════ SHARED TOOL BUS ════════════════════════════
   │  SENSING       │  MEMORY & REASONING   │  ACTION    │ INTEGRATIONS │
   │  ───────────   │  ───────────────────  │  ────────  │ ─────────────│
   │  Audio listener│  Event log            │  TTS dialog│ Fitbit/Apple │
   │  Wearable HR   │  Personal baseline    │  Notifs    │ Dexcom/Omron │
   │  Vision/motion │  Anomaly detector     │  Lights    │ Calendar     │
   │  BP/glucose    │  Pattern-absence det. │  911 caller│ Pharmacy     │
   │  Wake+VAD+STT  │  Risk classifier      │  Contacts  │ EHR/FHIR     │
   │  Geolocation   │  Conv. memory         │  UI render │ Twilio       │
   │  Env sensors   │  Regimen store        │  Confirm   │ Portals      │
   │  Manual input  │  Drug-interaction chk │            │              │
   │                │  LLM (small/large)    │            │              │
   │                │  Medical KB (RAG)     │            │              │
   ═════════════════════════════════════════════════════════════════════
```

### Physical view (deployment)

```
                                   ┌──────────────┐
                                   │   Database   │
                                   └──────┬───────┘
                                          │
┌──────┐   ┌──────────────────────────────▼─────────────────────────────┐
│ Mic  │──▶│  Backend  (FastAPI + Pipecat + LangGraph)                  │──▶ UI / TTS
└──────┘   │  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │     /911
           │  │ Sensing  │─▶│ Orchestrator │─▶│ 6 Sub-Agents       │    │
           │  │ pipeline │  │ (supervisor) │  │ (LangGraph subgrph)│    │
           │  └──────────┘  └──────────────┘  └─────────┬──────────┘    │
           │                                            │               │
           │                ┌──────── Shared Tool Bus ──┘               │
           │                │  (Sensing / Memory & Reasoning /          │
           │                │   Action / Integrations)                  │
           └────────────────────────────────────────────────────────────┘
```

**Tools are stateless capabilities. Sub-Agents own the policy. Orchestrator owns the user.**

---

## 1. Audio Capture & Front-End  *(Sensing)*

| Concern | Option A | Option B (recommended) | Option C |
|---|---|---|---|
| **Microphone hardware** | Built-in laptop mic | **ReSpeaker 6-Mic Array** | MATRIX Voice |
| **Audio I/O library** | `pyaudio` | **`sounddevice` (PortAudio)** | PipeWire native |
| **Noise suppression** | none | **`rnnoise`** (real-time NN denoise) | NVIDIA Maxine SDK |
| **Echo cancellation** | none | **WebRTC AEC3** (`speexdsp` bindings) | — |

**Recommendation:** ReSpeaker 6-Mic + `sounddevice` + `rnnoise`. The mic array matters for far-field pickup ("Guardian, I fell" from across the room).

---

## 2. Backend / API Server (the spine)

The central orchestrator's *host process*. Mic feeds raw audio in; the Backend runs the audio pipeline, hosts the **Orchestrator** and **Sub-Agents**, exposes the **Shared Tool Bus** as Python services, persists everything, and publishes events to the UI.

### Responsibilities

- **Audio ingress.** Open the mic, run wake-word + VAD, hand voiced segments to STT.
- **Pipeline orchestration.** STT → Orchestrator → Sub-Agent → Tools → TTS (Pipecat inside the process).
- **Agent hosting.** The Orchestrator and six Sub-Agents are LangGraph graphs running in this process.
- **Tool Bus exposure.** Every tool in the four buckets (§12) is a Pydantic-typed Python service the Sub-Agents call.
- **Persistence.** Incidents, conversations, medication logs, vitals snapshots written to the Database layer.
- **API surface.** REST + SSE endpoints for the UI; webhook intake for wearable / pharmacy / calendar integrations.
- **Scheduler.** APScheduler fires medication and check-in reminders independent of the LLM.
- **Event multiplexing.** Wake word, audio event, wearable anomaly, UI command, scheduled tick → all become entries in one `Event` stream the Orchestrator subscribes to.
- **Side-effect broker.** Sub-Agents emit *intents* (`call_911`, `play_calming_song`); the Backend dispatches them.
- **Audit logging.** PHIPA-compliant append-only log.

### Module recommendations

| Concern | Option A | Option B (recommended) | Option C |
|---|---|---|---|
| **Web framework** | Flask / Django | **FastAPI** | Litestar |
| **ASGI server** | Uvicorn (single-worker) | **Uvicorn + Gunicorn** | Hypercorn |
| **Async task queue** | Celery + Redis | **Arq** (Redis-based, async-native) | Dramatiq |
| **Scheduler** | cron | **APScheduler** (in-process) | Temporal |
| **Event bus** | In-process `asyncio.Queue` | **NATS** (lightweight) | Redis Streams |
| **WebSocket / SSE** | `websockets` | **FastAPI `WebSocket` + `sse-starlette`** | Socket.IO |
| **Validation** | Hand-rolled | **Pydantic v2** | attrs + cattrs |
| **Auth** | Username/password | **Passkeys (WebAuthn) + Tailscale identity** | Authelia |
| **Migrations** | Hand-rolled SQL | **Alembic** (with SQLModel) | Liquibase |

**Recommendation:** **FastAPI + Uvicorn + SQLModel + Alembic + Arq + APScheduler + sse-starlette**, with Pipecat embedded inside the same process.

### Directory layout

```
backend/
├── audio/              # mic capture, Pipecat pipeline wiring
├── orchestrator/       # top-tier LangGraph supervisor + routing rules
├── agents/             # one subgraph per sub-agent
│   ├── safety.py
│   ├── health.py
│   ├── reminder.py
│   ├── companion.py
│   ├── behavior.py
│   └── caregiver_liaison.py
├── tools/              # shared tool bus, 4 buckets
│   ├── sensing/
│   ├── memory_reasoning/
│   ├── action/
│   └── integrations/
├── api/                # FastAPI routers
├── services/           # business logic the agents call
├── db/                 # SQLModel models + Alembic migrations
├── events/             # event bus, pub/sub
├── workers/            # Arq workers
└── main.py             # Uvicorn entrypoint
```

---

## 3. Wake Word Detection  *(Sensing)*

| Option | Notes |
|---|---|
| **openWakeWord** (recommended) | Open source, custom wake words ("Hey Guardian"), ~50ms latency, CPU-only. |
| Picovoice Porcupine | Higher accuracy but commercial. |
| Vosk + keyword spotting | Free but heavier. |

---

## 4. Voice Activity Detection (VAD)  *(Sensing)*

| Option | Notes |
|---|---|
| **Silero VAD** (recommended) | 1MB ONNX, 1ms latency, accurate. De-facto for local voice agents. |
| WebRTC VAD | Faster but noisier. |
| `pyannote.audio` VAD | Best accuracy, too heavy for always-on. |

---

## 5. Speech-to-Text (STT)  *(Sensing)*

| Option | Notes |
|---|---|
| **NVIDIA Parakeet-TDT-1.1B** (recommended) | NVIDIA's own ASR via NeMo. Top of HF OpenASR leaderboard, streaming-capable, native to this hardware. |
| `faster-whisper` (large-v3-turbo) | CTranslate2 Whisper. Hackathon fallback. |
| `whisper.cpp` | CPU/GPU backup. |

Stream partial transcripts so the Orchestrator can react to "I fell" before the sentence finishes.

---

## 6. Speaker Recognition  *(Sensing, stretch goal)*

| Option | Notes |
|---|---|
| **`pyannote.audio` 3.x** (recommended) | Diarization + embeddings in one library. |
| SpeechBrain ECAPA-TDNN | Lower-level. |
| Resemblyzer | Simple, older. |

30-second enrollment per household member at onboarding.

---

## 7. Audio Event Detection  *(Sensing — recommended addition, not yet in diagram)*

For Safety Agent passive triggers: falls, glass break, coughing fits.

| Option | Notes |
|---|---|
| **CLAP (LAION/Microsoft)** (recommended) | Describe events in natural language ("body hitting floor"). No per-event training. |
| YAMNet | Pre-trained on 521 AudioSet events. Cheap first-pass filter. |
| PANNs | Strong baseline. |

**Recommendation:** YAMNet always-on; invoke CLAP only when YAMNet flags something interesting.

---

## 8. LLM Inference Runtime  *(Memory & Reasoning)*

| Option | Notes |
|---|---|
| **NVIDIA NIM + TensorRT-LLM** (recommended for production) | Best on Blackwell, 2–4x throughput over vLLM. |
| **vLLM** (recommended for hackathon) | Easy, OpenAI-compatible, excellent throughput. |
| Ollama | Simplest dev. |
| llama.cpp | Lightweight fallback. |

---

## 9. LLM Models  *(Memory & Reasoning)*

You need at least two: a fast generalist for the Orchestrator + chatty Sub-Agents (Companion, Reminder), and a clinical model the Health/Safety agents can consult.

| Role | Model | Notes |
|---|---|---|
| **Generalist / Orchestrator** (recommended) | **Llama 3.1 8B Instruct** | Fast, strong tool use, fits with room for everything else. Llama 3.3 70B for production. |
| Multilingual alt | **Qwen 2.5 32B / Qwen 3** | Useful for the 911-interpretation scenario. |
| **Clinical reasoning** | **Meditron-7B / Meditron-70B** (EPFL) | Llama-based, continued-pretrained on PubMed + clinical guidelines. |
| Clinical alt | OpenBioLLM-Llama3-8B | Solid medical fine-tune. |
| **Triage (CTAS) scoring** | Tiny model fine-tuned for structured output | Or constrain Llama 3.1 8B to a Pydantic schema. |
| **Tiny model for the Risk Classifier** | **Phi-3.5-mini** or **Gemma-2-2B** | Cheap, fast, runs alongside the big model for the always-on classifier tool. |

**Hackathon picks:** Llama 3.1 8B as the generalist, Meditron-7B as a `clinical_consult` tool, Phi-3.5-mini for the tiered Risk Classifier.

---

## 10. Orchestrator (Tier 1)

The top-tier agent that hears every signal and decides which Sub-Agent owns it. Implemented as a **LangGraph supervisor**.

### Responsibilities

- **Event intake.** Subscribe to the Backend's `Event` stream (voice utterance, wearable anomaly, schedule tick, audio event, UI command).
- **Routing.** Pick the Sub-Agent that owns the event based on signal type + patient profile + current mode (passive/active).
- **Severity assignment.** Tag every routed event with an initial severity (info / nudge / alert / emergency); the Sub-Agent can upgrade.
- **Cross-agent escalation.** If Health Agent flags an unexplained vitals anomaly, the Orchestrator can hand off to Safety Agent and put Companion Agent in calm-keeping mode in parallel.
- **Mode arbitration.** Only one Sub-Agent "holds the microphone" at a time, but several can run passive workflows concurrently.
- **Audit trail.** Every routing decision logged with a reason — important for PHIPA + debugging.

### Module recommendations

| Pattern | Option | Notes |
|---|---|---|
| **Supervisor pattern** | **LangGraph `Supervisor`** (recommended) | First-class supervisor pattern; subgraphs are first-class nodes; state persistence + replay built in. |
| | LangChain `AgentExecutor` | Older, less stateful. |
| | CrewAI | Multi-agent but assumes role-play; not the right shape. |
| | OpenAI Swarm | Lightweight but routing only, no persistence. |
| **Routing logic** | LLM-as-router | Generalist Llama 3.1 8B picks the sub-agent. |
| | Rule-based router | Deterministic + cheap for clear signals (e.g., audio event of category=`fall` → Safety Agent). |
| | **Hybrid** (recommended) | Rules for unambiguous signals, LLM for narrative ones. |
| **State store** | **LangGraph checkpointer → Postgres** | Lets you resume an in-flight incident across restarts. |

**Recommendation:** **LangGraph Supervisor** with a hybrid router (rules for clear signals, LLM for narrative), checkpointing to Postgres.

---

## 11. Sub-Agents (Tier 2)

Each Sub-Agent is its own **LangGraph subgraph** with: its own system prompt, its own allowed tool subset (a view onto the Shared Tool Bus), its own escalation policy, and its own personality for TTS.

| Sub-Agent | Allowed tools (subset of Tool Bus) | Key state | Escalation ceiling |
|---|---|---|---|
| **Safety Agent** | audio listener, CLAP, geolocation, contact-tree messenger, **911 caller**, lights/chimes, TTS (urgent voice) | Active incident object, location, last-known patient response | **911 + family contact** |
| **Health Agent** | wearable vitals, BP/glucose, anomaly detector, baseline model, drug-interaction check, medical KB (RAG), Meditron consult, TTS (calm voice) | Vitals time-series, condition list, medication list | Notify family / suggest doctor visit; escalate to Safety on red flags |
| **Reminder Agent** | regimen/schedule store, calendar integration, pharmacy/refill API, notification dispatcher, tap-to-confirm prompt, TTS (gentle voice) | Active reminders, intake log, refill timers | Caregiver Liaison after N missed doses |
| **Companion Agent** | conversation memory, event log, mood log, TTS (warm voice), ambient lights (calming), Spotify | Mood baseline, conversation history, weekly summary buffer | Hand off to Health/Safety on red flags |
| **Behavior Agent** | conversation memory, audio listener, risk classifier (tiered), counselor/officer portal, contact-tree, TTS (firm/de-escalating voice) | Behavior baseline, trigger history, consent flags | Counselor portal + (if court-ordered) probation officer |
| **Caregiver Liaison** | event log, conversation memory, EHR/FHIR share, contact-tree messenger, Twilio (SMS + voice), UI dashboard renderer | Recipient routing table, consent matrix, share log | Generates outbound reports; no in-home escalation |

### Module recommendations

| Concern | Pick |
|---|---|
| Subgraph framework | **LangGraph** (recommended) — each sub-agent is a `StateGraph` registered as a subgraph node of the Orchestrator |
| Per-agent prompts | Markdown templates in `agents/<name>/prompt.md`, hot-reloadable in dev |
| Tool-subset gating | A Pydantic schema per sub-agent listing allowed tool names; enforced in the tool dispatcher |
| Voice profile per agent | A `voice_profile` field on each sub-agent → passed to TTS; map to Kokoro voice IDs |
| Hand-off protocol | `HandoffEvent` Pydantic model emitted onto the event bus; supervisor re-routes |

---

## 12. Shared Tool Bus (Tier 3 — overview)

Every Sub-Agent calls into the same flat namespace of Pydantic-typed tool functions. Tools are **stateless** (any state belongs in `services/` or the Database). The four buckets are organizational; there is no enforcement at the bucket level — gating happens per-agent (§11).

### Bucket contents and where they live in this doc

| Bucket | Tools | Detailed in |
|---|---|---|
| **Sensing** | audio listener, wake+VAD+STT, vision/motion, wearable vitals, BP/glucose, env sensors, geolocation, manual input | §1, §3–§7, §17 |
| **Memory & Reasoning** | event log, personal baseline, conversation memory, regimen store, anomaly detector, pattern-absence detector, risk classifier, drug-interaction check, medical KB RAG, LLM inference | §8–§9, §13, §16, §18 |
| **Action** | TTS dialog, notification dispatcher, ambient lights/chimes, 911 caller, contact-tree messenger, UI renderer, tap-to-confirm | §19, §21, §22 |
| **Integrations** | Apple Health / Fitbit, Dexcom / Omron, Calendar, pharmacy / refill, EHR / FHIR, Twilio, counselor/officer portal | §14, §17, §19 |

### Cross-cutting design rules

- **Stateless interface.** Every tool is `def tool(args: ArgsModel) -> ResultModel`. No hidden globals.
- **Pydantic everywhere.** Tool schemas double as LLM tool descriptions, request/response validators, and DB row shapes.
- **Idempotency keys.** `call_911`, `send_sms`, `pharmacy_refill` all take an idempotency key — Sub-Agents are stateful, tools are not.
- **Audit on the tool side.** Every tool invocation writes to the audit log automatically via a decorator. The agent author can't forget.
- **Tiered output for Action tools.** All Action tools accept a `severity` enum (`whisper / nudge / alarm / call`) — the same `notify_family` tool whispers a text or makes a voice call depending on level.

---

## 13. Reasoning Modules  *(Memory & Reasoning — the non-LLM smarts)*

These are the dedicated modules shown in the SVG: **personal baseline model**, **anomaly detector**, **pattern-absence detector**, **tiered risk classifier**, **drug-interaction check**, **event log**.

| Module | Recommendation | Notes |
|---|---|---|
| **Personal baseline model** | Online statistics (rolling mean/variance + EWMA) per vital, per time-of-day, per activity context. **River** (Python online ML) for the maintained version. | "Unusual for *this* user" beats "unusual for the population." |
| **Anomaly detector** | **PyOD** with **IsolationForest** + **MAD** for univariate (HR, BP, glucose); **deep SVDD** for multivariate. | Run as a service the Health Agent and Behavior Agent both consult. |
| **Pattern-absence detector** | Custom: maintain a per-day rhythm fingerprint (audio activity per 15-min bucket, motion events, mic energy). Flag when current day deviates beyond N MAD from the rolling baseline. | The "silent morning" scenario. |
| **Tiered risk classifier** | Small fine-tuned classifier (Phi-3.5-mini or a sklearn gradient-boosted model on extracted features) emitting a 4-level severity. | Cheap so it can run on every event. The big LLM only gets called for ambiguous cases. |
| **Drug-interaction check** | Local snapshot of **RxNav / DrugBank** + a deterministic rules engine. | No API call at runtime — pure lookup on the patient's med list. |
| **Event log** | Append-only table in Postgres, with a content-hash chain for tamper-evidence. | Foundational for PHIPA audit + replay. |
| **Conversation memory** | Short-term in-process, long-term in Qdrant with episode-level summaries (LLM-generated nightly). | Companion Agent's memory recap feature relies on this. |

**Recommendation:** A `reasoning/` sub-package in the Backend with one file per module above, each exposed as a tool on the bus.

---

## 14. MCP Servers  *(Integrations layer)*

Anthropic's Model Context Protocol — the right abstraction for external systems each Sub-Agent might need.

| MCP Server | Used by | Source |
|---|---|---|
| **Google Calendar MCP** | Reminder Agent, Caregiver Liaison | Community `mcp-server-google-calendar` or build with MCP Python SDK |
| **Spotify MCP** | Companion Agent (relaxing music), Behavior Agent (de-escalation) | Community `mcp-server-spotify` |
| **Twilio MCP** | Safety Agent, Caregiver Liaison | Build with MCP Python SDK + Twilio REST |
| **Toronto Open Data MCP** | Safety Agent (nearest ambulance station) | Build — HTTP wrapper around `open.toronto.ca` |
| **Pharmacy / Refill MCP** | Reminder Agent | Custom; per-pharmacy backend |
| **EHR / FHIR MCP** | Caregiver Liaison | Build on **HAPI FHIR** client; outbound-only for the share scenario |
| **Filesystem MCP** | All agents (read medical KB) | Official Anthropic MCP server |

**Recommendation:** Wrap every external system as MCP — keeps each Sub-Agent's allowed-tool list portable and swappable.

---

## 15. Translation  *(Integrations)*

For the multilingual 911-interpretation scenario and non-English-primary patients.

| Option | Notes |
|---|---|
| **Meta SeamlessM4T v2** (recommended for speech→speech) | 100 languages, fully local. Game-changer for paramedic handoff with a non-English speaker. |
| **Meta NLLB-200** (recommended for text) | 200 languages, fully local. |
| Whisper (translate mode) | To-English only. |

---

## 16. Medical Knowledge Base (RAG)  *(Memory & Reasoning)*

Grounds clinical reasoning in real guidelines.

| Component | Recommendation | Notes |
|---|---|---|
| **Embedding model** | **NVIDIA NV-Embed-v2** (general) + **MedCPT** (medical) | Dual-index — general queries to NV-Embed, clinical to MedCPT. |
| **Vector DB** | **Qdrant** | Chroma is fine for hackathon; Qdrant for production filters & persistence. |
| **Re-ranker** | **bge-reranker-v2-m3** | Optional but improves precision. |
| **Corpus** | First-aid manuals, **CTAS guidelines**, RxNav local snapshot, condition-specific patient guides | Pre-ingest at build time. |

---

## 17. Wearable / Vitals Integration  *(Sensing + Integrations)*

Feeds the **Health Agent** and the **personal baseline model**.

| Source | How to integrate locally |
|---|---|
| **Polar H10 chest strap** (recommended for hackathon demo) | Direct BLE via `bleak`, sub-second HR. Cheap, clean data. |
| **Fitbit** | Production: local OAuth proxy + immediate cloud purge. Hackathon: BLE GATT via `bleak`. |
| **Dexcom CGM** | Dexcom Share / Follow API for real-time glucose. |
| **Omron BP cuff** | BLE via `bleak`, manufacturer GATT profile. |
| **Apple Watch** | HealthKit, requires iPhone in the loop. |
| **Time-series storage** | **InfluxDB 3** (recommended) or TimescaleDB. |

---

## 18. Database Layer

Three data shapes — don't try to use one store for all.

| Data | Store | Why |
|---|---|---|
| Patient profile, meds, contacts, conditions, regimens | **Postgres + pgcrypto/TLS** | Concurrent access, robust relational guarantees, encrypt-at-rest via pgcrypto |
| Vitals time-series | **InfluxDB 3** | Built for this access pattern |
| Conversation embeddings + medical KB | **Qdrant** | Same instance for both indices |
| Audio recordings + transcripts | Encrypted filesystem + Postgres manifest | Don't put raw audio in a DB |
| Event log (append-only) | Postgres with content-hash chain | Tamper-evident audit trail |
| ORM | **SQLModel** (Pydantic + SQLAlchemy) | Same Pydantic models everywhere |

---

## 19. Emergency Communication + Notification Dispatcher  *(Action + Integrations)*

The "tiered output" pipe: whisper → nudge → alarm → call.

| Severity | Channel | Module |
|---|---|---|
| Whisper | Soft TTS in the room | Kokoro / Riva |
| Nudge | UI toast + ambient light | SSE → Next.js, Hue/Matter via `python-matter-server` |
| Alarm | Loud TTS + bright light + caregiver SMS | + **Twilio Programmable Messaging** |
| Call | Voice call to family + 911 dispatch | **Twilio Programmable Voice** (demo); NENA i3 / regional CAD (production) |
| Push notif (out-of-home) | Caregiver phone | **ntfy.sh** (self-hosted) or Firebase |

The Sub-Agent picks the severity; the **notification dispatcher tool** picks the channel mix. One tool, four behaviors.

---

## 20. Voice Agent Orchestration  *(audio I/O ↔ STT ↔ LLM ↔ TTS glue)*

This runs **inside** the Backend.

| Option | Notes |
|---|---|
| **Pipecat** (recommended) | Designed for VAD → STT → LLM → TTS with interruption handling. Pluggable. |
| LiveKit Agents | Production-grade, heavier. |
| Vocode | Similar to Pipecat. |

**Recommendation:** Pipecat with LangGraph (the Orchestrator) as the LLM stage.

---

## 21. Text-to-Speech (TTS)  *(Action)*

The voice the patient hears — Sub-Agents pass a `voice_profile` so each agent can have its own tone.

| Option | Notes |
|---|---|
| **Kokoro-82M** (recommended hackathon) | 82M params, runs anywhere, shockingly natural. |
| **NVIDIA Riva** (recommended production) | DGX-native, sub-100ms first-byte. Multiple voices. |
| Piper | Light, robust fallback. |
| XTTS-v2 / F5-TTS | Voice cloning — optionally clone a trusted family member's voice. |

**Voice profiles per Sub-Agent:** urgent (Safety), calm (Health, Companion), gentle (Reminder), firm (Behavior), formal (Caregiver Liaison).

---

## 22. UI Layer  *(Action — dashboard renderer)*

What the patient and family see: medication intake, vitals, incident history, live status.

| Component | Recommendation |
|---|---|
| Web framework | **Next.js 15 (App Router)** for production; **Streamlit** for hackathon-speed prototype |
| State / real-time | **SSE** (Backend → UI) via `sse-starlette` |
| Charts | **Recharts** or Apache ECharts for vitals |
| Voice in UI | Web Audio API |
| Auth | Passkeys (WebAuthn) |
| API client | Auto-generated from FastAPI's OpenAPI |

---

## 23. Wi-Fi Pose Detection  *(Sensing, stretch)*

| Component | Notes |
|---|---|
| CSI extraction firmware | **ESP32-CSI-Tool** ($5) or **Nexmon CSI** (Broadcom) |
| Pose classification | Custom — start from Wi-Pose / Person-in-WiFi papers |

For hackathon: minimal fall-vs-no-fall classifier feeding the **Safety Agent**.

---

## 24. Synthetic Data & Demo Tooling

| Need | Module |
|---|---|
| Synthetic patient records | **Synthea** (MITRE), FHIR-compatible |
| Synthetic voices | **XTTS-v2** to read scripted patient lines |
| Audio incident library | **Freesound** + AudioSet samples |
| Scenario runner | Custom pytest harness; inject audio + vital events, assert on agent intents |

---

## 25. Observability & Ops

| Concern | Module |
|---|---|
| Logs | `loguru` (dev) → `structlog` + journald (prod) |
| Metrics | Prometheus + Grafana (local) |
| LLM + agent tracing | **Langfuse** (self-hosted) — *critical* for debugging the multi-agent loop |
| Process manager | systemd, one unit per service |
| Container runtime | **Podman** (rootless) or Docker |

---

## 26. Privacy, Security, Compliance (PHIPA)

| Layer | Module |
|---|---|
| Disk encryption | LUKS (whole device) |
| DB encryption | Postgres `pgcrypto` (column-level) + TLS in transit |
| Secrets | `pass` + GPG, or HashiCorp Vault |
| Audit log | Append-only Postgres event log + signed log chain |
| Network | Local-only by default; **Tailscale** for caregiver remote access |
| Microphone kill switch | Hardware switch on the mic array — non-negotiable for trust |

---

## Recommended Hackathon Build Order

1. **Day 1 AM** — Backend skeleton (FastAPI + SQLModel + Alembic). vLLM + Llama 3.1 8B up. Pipecat inside the Backend with Silero VAD + Parakeet STT + Kokoro TTS. "Hey Guardian" end-to-end.
2. **Day 1 PM** — LangGraph **Orchestrator** with hybrid router. **Safety Agent** + **Companion Agent** as the first two subgraphs. The fall-scenario E2E with mock Twilio 911.
3. **Day 2 AM** — Polar H10 → InfluxDB → personal baseline model + anomaly detector. **Health Agent** + **Reminder Agent**. APScheduler firing medication reminders. Qdrant + Meditron-7B for `clinical_consult`.
4. **Day 2 PM** — **Behavior Agent** + **Caregiver Liaison** scaffolds, even if shallow. Next.js history UI on SSE. Record demo: fall scenario + slow-burn arm-pain scenario + missed-meds scenario.

Stretch: Riva, SeamlessM4T multilingual, Wi-Fi CSI fall classifier, NIM/TensorRT-LLM migration.

---

## TL;DR Pick List (slide-ready)

| Layer | Pick |
|---|---|
| Mic | ReSpeaker 6-Mic Array |
| Backend | FastAPI + Uvicorn + SQLModel + Alembic + Arq + APScheduler + sse-starlette |
| Wake / VAD / STT | openWakeWord + Silero VAD + NVIDIA Parakeet-TDT |
| Speaker ID | pyannote.audio |
| Audio events | YAMNet + CLAP |
| LLM runtime | vLLM → NIM/TensorRT-LLM |
| LLM models | Llama 3.1 8B (generalist) + Meditron-7B (clinical) + Phi-3.5-mini (risk classifier) |
| **Orchestrator** | **LangGraph Supervisor + hybrid (rule + LLM) router + Postgres checkpointing** |
| **Sub-Agents** | **6 LangGraph subgraphs (Safety / Health / Reminder / Companion / Behavior / Caregiver Liaison)** |
| **Shared Tool Bus** | **Stateless Pydantic-typed Python tools in 4 buckets, gated per-agent** |
| Reasoning modules | River (baselines) + PyOD (anomalies) + Phi-3.5-mini risk classifier + local RxNav (interactions) |
| Medical RAG | Qdrant + NV-Embed-v2 + MedCPT |
| Voice pipeline | Pipecat (inside Backend) |
| Translation | SeamlessM4T v2 |
| Wearable | Polar H10 via `bleak` → InfluxDB |
| Patient DB | Postgres + pgcrypto/TLS (via SQLModel) |
| Time-series | InfluxDB 3 |
| TTS | Kokoro (hackathon) → Riva (prod); per-agent voice profiles |
| UI | Next.js + Recharts over SSE |
| Notification dispatcher | Tiered (whisper / nudge / alarm / call) over TTS + UI + Hue/Matter + Twilio |
| External MCPs | Calendar, Spotify, Twilio, Toronto Open Data, Pharmacy, FHIR, Filesystem |
| Observability | Langfuse + Prometheus + Grafana |
| Privacy | pgcrypto + TLS + LUKS + hardware mic switch + Tailscale + signed audit log |
