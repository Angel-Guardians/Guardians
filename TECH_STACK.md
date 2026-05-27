# Guardian — Tech System Stack

Hardware target: **NVIDIA DGX Spark (GB10 Grace Blackwell Superchip)** — ARM64 + Blackwell GPU, fully on-device inference, no cloud APIs for any health-relevant path.

This document maps every block of the architecture diagram (and a few neighboring ones it implies) to concrete modules. For each layer we list **2–3 options** with a recommended pick and a one-line reason. Recommendations balance "ship in a hackathon weekend" against "won't be embarrassing in a real PHIPA deployment."

---

## Architecture at a Glance

```
                                                ┌──────────────┐
                                                │   Database   │
                                                └──────┬───────┘
                                                       │
┌──────┐   ┌──────────┐   ┌──────────────┐   ┌─────┐   ┌─▼─────────────────────┐   ┌─────┐   ┌──────┐
│Voice │──▶│ Backend  │──▶│ Wake / Voice │──▶│ STT │──▶│   Agent (LLM core)    │──▶│ TTS │──▶│  UI  │
│ Mic  │   │ (spine)  │   │ Recognition  │   │ASR  │   │  Tools + MCP servers  │   │     │   │ +Spkr│
└──────┘   └──────────┘   └──────────────┘   └─────┘   └───────────────────────┘   └─────┘   └──────┘
                ▲                                                  │
                │                                                  ▼
                │                                              External
                └──────────────── intents / events ───────────(911, family,
                                                              translation)
```

**Data-flow:** the mic feeds raw audio into the **Backend**, which is the spine of the system. Everything downstream — wake-word, STT, Agent, tools/MCP, TTS, UI, external comms — is orchestrated by the Backend. The Agent emits *intents*; the Backend turns those into side effects.

---

## 1. Audio Capture & Front-End

| Concern | Option A | Option B (recommended) | Option C |
|---|---|---|---|
| **Microphone hardware** | Built-in laptop mic | **ReSpeaker 6-Mic Array** | MATRIX Voice |
| **Audio I/O library** | `pyaudio` | **`sounddevice` (PortAudio)** | PipeWire native |
| **Noise suppression** | none | **`rnnoise`** (real-time NN denoise) | NVIDIA Maxine SDK |
| **Echo cancellation** | none | **WebRTC AEC3** (`speexdsp` bindings) | — |

**Recommendation:** ReSpeaker 6-Mic + `sounddevice` + `rnnoise`. The mic array matters for far-field pickup ("Guardian, I fell" from across the room). `rnnoise` keeps Whisper accurate when the TV is on.

---

## 2. Backend / API Server (the `Backend` block — the spine)

This is the central orchestrator. The mic hands raw audio to the Backend, and **everything downstream is invoked, sequenced, and persisted by it**: wake-word detection, STT, Agent reasoning, tool execution, MCP calls, TTS playback, UI events, external emergency comms. The Agent reasons; the Backend **persists, exposes, schedules, and routes**. Without this layer the UI can't show history, scheduled reminders can't fire when the LLM is idle, and the Agent ends up doing infrastructure work it shouldn't.

### Responsibilities

- **Audio ingress.** Open the mic, run the wake-word + VAD pipeline, hand voiced segments to STT.
- **Pipeline orchestration.** STT → Agent → TTS, with interruption handling (a Pipecat pipeline runs inside the Backend process).
- **Persistence.** Write incidents, conversations, medication logs, vitals snapshots into the Database layer.
- **API surface.** REST + WebSocket/SSE endpoints for the UI (history, live incident status, vitals stream).
- **Scheduler.** Medication and check-in reminders fire on time, independent of whether the LLM is awake.
- **Event multiplexing.** Wake word, audio event (fall sound), wearable anomaly, UI command, and scheduled reminder all become entries in a single `Event` stream the Agent subscribes to.
- **Side-effect broker.** Twilio call, Spotify play, TTS request — the Agent emits *intents*, the Backend dispatches them.
- **Authentication.** Household members + caregiver remote access.
- **Audit logging.** PHIPA-compliant append-only log of every action taken on patient data.

### Module recommendations

| Concern | Option A | Option B (recommended) | Option C |
|---|---|---|---|
| **Web framework** | Flask / Django | **FastAPI** | Litestar |
| **ASGI server** | Uvicorn (single-worker) | **Uvicorn + Gunicorn** (multi-worker) | Hypercorn |
| **Async task queue** | Celery + Redis | **Arq** (Redis-based, async-native, lightweight) | Dramatiq |
| **Scheduler** | cron | **APScheduler** (in-process) or Arq's scheduled jobs | Temporal (overkill for hackathon) |
| **Pub/sub event bus** | In-process `asyncio.Queue` (hackathon) | **NATS** (lightweight) | Redis Streams |
| **WebSockets / SSE** | `websockets` (lib) | **FastAPI's `WebSocket` + `sse-starlette`** | Socket.IO |
| **Validation** | Hand-rolled | **Pydantic v2** (shared with Agent tool schemas) | attrs + cattrs |
| **Auth** | Username/password | **Passkey-only** (WebAuthn) for household; **Tailscale identity** for caregivers | Authelia |
| **Migrations** | Hand-rolled SQL | **Alembic** (with SQLModel) | Liquibase |
| **Background workflows** | Plain async tasks | **Arq workflows** | Temporal / Prefect |

### Recommendation

**FastAPI + Uvicorn + SQLModel + Alembic + Arq + APScheduler**, with `sse-starlette` for live updates to the UI and Pipecat embedded inside the Backend process for the real-time audio pipeline. The Agent talks to the Backend over an in-process Python interface (they share the same Python runtime); the UI talks to it over HTTP + SSE.

### Why this shape

- **One service, clear seams.** The Agent imports backend services as a Python module (no extra network hop), but external clients (UI, caregiver phone) go through HTTP/SSE. You get separation-of-concerns without microservice overhead — important at hackathon scale.
- **Pydantic everywhere.** The same Pydantic models define DB rows (via SQLModel), API responses (via FastAPI), agent tool schemas (via LangGraph/PydanticAI), and event payloads. One source of truth.
- **Scheduler lives in the Backend, not the Agent.** Medication reminders must fire at 8:00 AM whether or not the Agent is mid-conversation. APScheduler in the Backend dispatches an event; the Agent reacts.

### Sketch of the directory layout

```
backend/
├── audio/              # mic capture, Pipecat pipeline wiring
├── api/                # FastAPI routers
│   ├── incidents.py
│   ├── medications.py
│   ├── vitals.py
│   └── events_sse.py
├── services/           # Business logic the Agent also calls
│   ├── patient_profile.py
│   ├── incident_recorder.py
│   ├── reminder_scheduler.py
│   └── emergency_dispatch.py
├── db/                 # SQLModel models + Alembic migrations
├── events/             # Event bus, pub/sub
├── workers/            # Arq workers (long-running jobs, retries)
└── main.py             # Uvicorn entrypoint
```

---

## 3. Wake Word Detection

Always-on, runs continuously inside the Backend's audio pipeline, must be cheap.

| Option | Notes |
|---|---|
| **openWakeWord** (recommended) | Open source, train custom wake words ("Hey Guardian"), ~50ms latency, runs on CPU so it doesn't compete with the LLM for GPU. |
| Picovoice Porcupine | Higher accuracy but commercial license for production. |
| Vosk + keyword spotting | Free but heavier. |

**Recommendation:** **openWakeWord** with a custom "Hey Guardian" model. Train on ~50 utterances per team member for the demo.

---

## 4. Voice Activity Detection (VAD)

Decides "is someone actually speaking right now" before we burn STT cycles.

| Option | Notes |
|---|---|
| **Silero VAD** (recommended) | 1MB ONNX model, 1ms latency, accurate, runs on CPU. The de-facto VAD for local voice agents. |
| WebRTC VAD | Faster but less accurate, more false triggers. |
| `pyannote.audio` VAD | Best accuracy, too heavy for always-on. |

**Recommendation:** **Silero VAD**.

---

## 5. Speech-to-Text (STT)

This is the block labeled "STT" in your diagram. On DGX Spark we should exploit the Blackwell GPU.

| Option | Notes |
|---|---|
| **NVIDIA Parakeet-TDT-1.1B** (recommended) | NVIDIA's own ASR via NeMo. Currently #1 on HF OpenASR leaderboard. Streaming-capable. Built for this exact hardware. |
| `faster-whisper` (large-v3-turbo) | CTranslate2-optimized Whisper. Best fallback if NeMo setup eats a day. |
| `whisper.cpp` | Lightweight, runs on CPU. Backup. |

**Recommendation:** **Parakeet-TDT via NVIDIA NeMo**, with `faster-whisper large-v3-turbo` as the hackathon fallback. Stream partial transcripts so the agent can react to "I fell" before the sentence finishes.

---

## 6. Speaker Recognition (Stretch Goal in diagram)

Identifies *which* household member is talking — important for multi-resident homes and for not triaging the visiting grandkid as the patient.

| Option | Notes |
|---|---|
| **`pyannote.audio` 3.x** (recommended) | Diarization + speaker embedding in one library. Stable API. |
| SpeechBrain ECAPA-TDNN | Lower-level, more control, more work. |
| Resemblyzer | Simple, older, less accurate. |

**Recommendation:** **`pyannote.audio`** with a 30-second enrollment per household member during onboarding.

---

## 7. Audio Event Detection (Not in diagram — recommended addition)

For passive mode: detecting falls, glass break, coughing fits, distress sounds without waiting for speech.

| Option | Notes |
|---|---|
| **CLAP (LAION/Microsoft)** (recommended) | Contrastive language-audio model. You can describe events in natural language ("body hitting floor", "person coughing repeatedly") without training a classifier per event. |
| YAMNet (TF Hub) | Pre-trained on 521 AudioSet events. Fast, less flexible. |
| PANNs | Strong baseline, similar to YAMNet. |

**Recommendation:** **CLAP** for flexibility + YAMNet as a fast first-pass filter. Run YAMNet always; only invoke CLAP when YAMNet flags something interesting.

---

## 8. LLM Inference Runtime

The brain of the Agent box.

| Option | Notes |
|---|---|
| **NVIDIA NIM + TensorRT-LLM** (recommended for production) | Most optimized path on Blackwell. ~2-4x throughput over vLLM on NVIDIA hardware. |
| **vLLM** (recommended for hackathon) | Easier setup, excellent throughput, OpenAI-compatible API out of the box. |
| Ollama | Simplest dev experience, fine for the demo if vLLM gives you grief on ARM. |
| llama.cpp | CPU/GPU, lightweight, good fallback. |

**Recommendation:** **vLLM** during the hackathon (you'll spend zero time on inference plumbing), migrate to **NIM/TensorRT-LLM** post-event if you continue.

---

## 9. LLM Models

You'll likely want **two** models: a fast generalist for conversation/agent loop, and a medical-grounded model for triage reasoning.

| Role | Model | Notes |
|---|---|---|
| **Generalist agent** (recommended) | **Llama 3.3 70B Instruct** (or Llama 3.1 8B for latency) | Strong tool use, good instruction following. 8B fits comfortably with room for everything else. |
| Generalist alt | Qwen 2.5 32B / Qwen 3 | Excellent multilingual — useful given your 911 interpretation scenario. |
| **Medical reasoning** | **Meditron-7B / Meditron-70B** (EPFL) | Llama-based, continued-pretrained on PubMed + clinical guidelines. Open source. |
| Medical alt | OpenBioLLM-Llama3-8B | Solid medical fine-tune. |
| **Triage scoring (CTAS)** | Small fine-tuned classifier on top of a 1B model | Wrap structured CTAS output in a schema, not free text. |

**Recommendation for hackathon:** Run **Llama 3.1 8B Instruct** as the agent and call **Meditron-7B** as a "consult" tool when the agent needs clinical reasoning. Don't try to fine-tune anything during the hackathon — use prompting + a medical RAG layer instead.

---

## 10. Agent Framework

Orchestrates the tool-using loop shown in your diagram.

| Option | Notes |
|---|---|
| **LangGraph** (recommended) | State-machine-style agents. Perfect for Guardian's escalation graph (check-in → family alert → 911). Built-in persistence, replay, human-in-the-loop. |
| **PydanticAI** | Type-safe, clean. Lighter than LangGraph but less mature for stateful agents. |
| CrewAI | Multi-agent specialization. Overkill for one Guardian. |
| Smolagents (Hugging Face) | Minimal, fast to learn. |

**Recommendation:** **LangGraph**. The escalation logic (passive watch → soft check-in → loud check-in → contact family → call 911) is *literally* a state graph. Don't fight that with prompt engineering.

---

## 11. Agent Tools (the `Tools: [...]` block)

Each tool is its own well-scoped module.

| Tool in diagram | Implementation |
|---|---|
| **`note_taking`** | LangGraph node that appends a structured `IncidentNote` (Pydantic model) to the conversation log. Auto-summarizes with the LLM when the incident closes. |
| **`send_reminders`** | APScheduler (Python) or a cron-driven worker. Pushes reminders via TTS + UI + optional SMS. |
| **`call_emergency`** | Twilio Voice API for the hackathon demo (mock 911). In production: regional CAD/911 integration. |
| **`bio_marker`** (smartwatch data) | See **§16 Wearable Integration**. |
| **`making_calm`** | Composite: TTS with calming voice + Spotify MCP for music + guided breathing script library (text → TTS). |

**Recommendation:** Define every tool as a Pydantic-typed function with a JSON schema so the LLM can never call it with garbage. Keep tools idempotent where possible.

---

## 12. MCP Servers (the `mcp: [...]` block)

Anthropic's Model Context Protocol — exactly the right abstraction here.

| MCP Server | What it does | Source |
|---|---|---|
| **Google Calendar MCP** | Read appointments (so Guardian knows the doctor's visit is tomorrow), create reminders. | Use the community `mcp-server-google-calendar` or build a thin one with the official MCP Python SDK. |
| **Spotify MCP** | Play relaxing music during anxiety/active mode. | Community `mcp-server-spotify` exists; needs OAuth setup. |
| **Twilio MCP** (recommended addition) | Send SMS / make calls for family alerts. | Build with the MCP Python SDK + Twilio REST API. |
| **Toronto Open Data MCP** (recommended addition) | Pull nearest ambulance station, average response time per neighborhood. | Build — it's just an HTTP wrapper around `open.toronto.ca`. |
| **Filesystem MCP** | Lets the agent read the local medical KB. | Official Anthropic MCP server. |

**Recommendation:** Wrap each external system as MCP — don't bake them as bespoke tools. This keeps the agent core portable and the external integrations swappable.

---

## 13. Translation (the Google Translate icon)

For multilingual 911 interpretation and for non-English-primary patients.

| Option | Notes |
|---|---|
| **Meta NLLB-200** (recommended for text) | 200 languages, fully local, multiple sizes (600M to 54B). |
| **Meta SeamlessM4T v2** (recommended for speech-to-speech) | Direct speech→speech translation in 100 languages. Game-changer for paramedic handoff with a non-English speaker. |
| Whisper (translation mode) | Whisper can transcribe-and-translate-to-English in one shot. Limited to "to-English." |

**Recommendation:** **SeamlessM4T v2** for the live-interpretation scenario, **NLLB-200** as a text-only fallback. Both run locally on DGX Spark.

---

## 14. Medical Knowledge Base (RAG)

So Guardian's medical reasoning is grounded in real guidelines, not hallucinated.

| Component | Recommendation | Notes |
|---|---|---|
| **Embedding model** | **NVIDIA NV-Embed-v2** or **MedCPT** | NV-Embed for general, MedCPT (NIH) for medical-specific retrieval. |
| **Vector DB** | **Qdrant** (recommended) or ChromaDB | Qdrant for production-grade filters and persistence, Chroma for dead-simple hackathon use. |
| **Re-ranker** | **bge-reranker-v2-m3** | Optional but improves precision a lot. |
| **Corpus** | First-aid manuals, CTAS guidelines, drug interaction databases (RxNav local snapshot) | Pre-ingest at build time. |

**Recommendation:** **Qdrant + NV-Embed-v2 + MedCPT** as a dual-index. General queries hit NV-Embed; explicitly clinical queries hit MedCPT.

---

## 15. Database Layer (the `Database` cylinder)

Three different data shapes; don't try to use one store for all of them.

| Data | Store | Why |
|---|---|---|
| **Patient profile, meds, contacts, conditions** | **SQLite with SQLCipher** (recommended) | Single-file, encrypted at rest, zero ops. Perfect for a single-home deployment. |
| Patient profile alt | PostgreSQL with `pgcrypto` | If you need multi-user or remote caregiver UI. |
| **Vitals time-series** | **InfluxDB 3** (recommended) or TimescaleDB | Built for this access pattern. |
| **Conversation embeddings / memory** | **Qdrant** | Same instance as the medical KB. |
| **Audio recordings & transcripts** | Encrypted local filesystem + manifest in SQLite | Don't put raw audio in a database. |
| **ORM** | **SQLModel** (Pydantic + SQLAlchemy) | Type-safe, plays nicely with FastAPI and Pydantic AI. |

**Recommendation:** **SQLite (SQLCipher) + InfluxDB + Qdrant**, accessed through SQLModel for the relational pieces.

---

## 16. Wearable / Vitals Integration (`bio_marker` tool)

Real-time pulse, HR, SpO₂ feeding the triage engine.

| Source | How to integrate locally |
|---|---|
| **Fitbit** (recommended) | Fitbit Web API requires OAuth + cloud — *for production* run a local proxy that fetches via OAuth on a schedule and immediately purges cloud copies. **For hackathon**, use the **Bluetooth GATT** path via `bleak` to read direct from the watch. |
| **Garmin** | Garmin Health API or BLE direct via `bleak`. |
| **Apple Watch** | HealthKit only — requires an iPhone in the loop. |
| **Generic BLE chest strap** (Polar H10) | Direct via `bleak`, sub-second HR. Best for live demo because it's cheap and the data is clean. |
| **Time-series storage** | **InfluxDB** or **TimescaleDB** | InfluxDB is faster to set up. |

**Recommendation:** **Polar H10 chest strap via `bleak` → InfluxDB** for the demo. Mention the Fitbit local-proxy design in the README for the privacy story.

---

## 17. Emergency Communication (`call_emergency` tool, family alerts)

| Action | Module |
|---|---|
| **SMS to family** (recommended) | **Twilio Programmable Messaging** |
| **Voice call to family** | **Twilio Programmable Voice** + TTS-generated message |
| **911 dispatch** (demo) | Twilio outbound voice with a pre-recorded incident summary |
| **911 dispatch** (real) | NENA i3 / regional CAD integration — out of scope for hackathon |
| **Push notifications to caregiver app** | **ntfy.sh** (self-hosted) or Firebase |

**Recommendation:** **Twilio** for the demo (all three channels). Mention `ntfy.sh` self-hosted as the privacy-preserving alternative.

---

## 18. Voice Agent Orchestration (gluing audio I/O ↔ STT ↔ Agent ↔ TTS together)

Rather than wiring every piece manually, use a real-time voice-agent framework. This runs **inside** the Backend process.

| Option | Notes |
|---|---|
| **Pipecat** (Daily) (recommended) | Open source, designed exactly for this: VAD → STT → LLM → TTS pipelines with interruption handling. Pluggable everywhere. |
| **LiveKit Agents** | Production-grade, real-time, more infra heavy. |
| **Vocode** | Similar to Pipecat, slightly less active. |
| Hand-rolled | Don't — interruption handling is the hard part. |

**Recommendation:** **Pipecat**, with LangGraph driving the conversational policy inside the LLM node.

---

## 19. Text-to-Speech (TTS)

The voice the patient actually hears. The Backend hands a text response (plus a "voice profile" — calm, urgent, whispered for night-time) to TTS, which streams audio back through the speaker.

| Option | Notes |
|---|---|
| **NVIDIA Riva** (recommended for production) | Native to DGX. Sub-100ms first-byte latency. Multiple voices. Streaming. |
| **Kokoro-82M** (recommended for hackathon) | 82M params, runs anywhere, *shockingly* natural quality for the size. Released 2024. |
| Piper | Fast, lightweight, slightly robotic. Good fallback. |
| XTTS-v2 (Coqui) | Voice cloning — could clone a family member's voice for comfort. Heavier. |
| F5-TTS | Zero-shot voice cloning, newer. |

**Recommendation:** **Kokoro** for the hackathon demo, **Riva** for production. Optionally use **XTTS-v2** in onboarding to clone the voice of a trusted family member — a familiar voice during an emergency genuinely helps.

**Integration note:** TTS is called by the Backend (via Pipecat's TTS service stage), not by the Agent directly. That way the Backend can log every utterance for the incident record, throttle if the LLM is rambling, and swap the voice profile based on context (calm vs. urgent).

---

## 20. UI Layer (the `UI` block — "user will see their history")

The patient and their family need a dashboard: medication intake, vitals, incident history.

| Component | Recommendation |
|---|---|
| **Web framework** | **Next.js 15 (App Router)** for production polish, or **Streamlit** for hackathon-speed prototype. |
| **State / real-time** | **Server-Sent Events** (one-way Backend → UI) — simpler than WebSockets and sufficient for live updates. WebSocket if you need duplex. |
| **Charts** | **Recharts** or **Apache ECharts** for vitals time-series. |
| **Voice in UI** | Web Audio API for the "talk to Guardian from your phone" path. |
| **Auth** | **Passkeys (WebAuthn)** — this is a household-scale app. |
| **Backend API client** | Auto-generated from FastAPI's OpenAPI schema (via `openapi-typescript`). |

**Recommendation:** **Next.js frontend → FastAPI backend over SSE + REST, with Recharts for vitals.** If time is tight, **Streamlit** gets you a usable history dashboard in two hours.

---

## 21. Wi-Fi Pose Detection (Stretch)

| Component | Notes |
|---|---|
| **CSI extraction firmware** | **Nexmon CSI** (Broadcom chips) or **ESP32-CSI-Tool** (cheap, $5 board). |
| **Pose / activity classification** | Custom model — start from **Wi-Pose** / **Person-in-WiFi** reference papers. No drop-in library exists yet. |

**Recommendation:** Use an **ESP32-CSI-Tool** for a *minimal* fall-vs-no-fall classifier. Skip full pose estimation for hackathon.

---

## 22. Synthetic Data & Demo Tooling

You'll need realistic patient histories and emergency scenarios for the demo.

| Need | Module |
|---|---|
| Synthetic patient records | **Synthea** (MITRE) — generates FHIR-compatible synthetic medical histories. |
| Synthetic voice scenarios | **XTTS-v2** to generate diverse patient voices saying scripted lines. |
| Audio incident library | **Freesound** + AudioSet samples (falls, glass break, coughing). |
| Scenario runner | Custom pytest harness that injects synthetic audio into the pipeline and asserts on agent actions. |

**Recommendation:** **Synthea + XTTS for voices + a pytest scenario harness** so you can replay any demo deterministically.

---

## 23. Observability & Ops

| Concern | Module |
|---|---|
| **Logs** | `loguru` (dev) → `structlog` + journald (prod) |
| **Metrics** | Prometheus + Grafana, all local |
| **LLM tracing** | **Langfuse** (self-hosted) or LangSmith |
| **Process manager** | systemd units, one per service |
| **Container runtime** | **Podman** (rootless) or Docker |

**Recommendation:** **Langfuse self-hosted** is huge for debugging the agent loop. Don't skip it.

---

## 24. Privacy, Security, Compliance (PHIPA)

| Layer | Module |
|---|---|
| **Disk encryption** | LUKS (the whole device) |
| **DB encryption** | SQLCipher (SQLite), `pgcrypto` (Postgres) |
| **Secrets** | `pass` + GPG, or HashiCorp Vault if multi-user |
| **Audit log** | Append-only `journald` + signed log chain |
| **Network** | Local-only by default. **Tailscale** for caregiver remote access — encrypted, ephemeral keys, no public exposure. |
| **Microphone kill switch** | Hardware switch on the mic array — non-negotiable for trust |

**Recommendation:** Lead the demo with the **hardware mic kill switch** + show the SQLCipher-encrypted DB. The privacy story is the differentiator; make it visible.

---

## Recommended Hackathon Build Order

1. **Day 1 AM** — Stand up the **Backend skeleton**: FastAPI + Uvicorn + SQLModel + Alembic, with a minimal `/health` and a stubbed `/events` SSE endpoint. Get vLLM + Llama 3.1 8B running on DGX. Wire up Pipecat (inside the Backend) with Silero VAD + Parakeet STT + Kokoro TTS. End-to-end "Hey Guardian, what time is it?" working.
2. **Day 1 PM** — LangGraph agent + SQLModel patient profile + Twilio mock 911 + APScheduler for reminders. The fall-scenario E2E happy path through the Backend.
3. **Day 2 AM** — Polar H10 → InfluxDB → `bio_marker` tool feeds vitals into agent context. Medical RAG with Qdrant + Meditron consult. Reminder events firing end-to-end via the scheduler.
4. **Day 2 PM** — Next.js history UI hitting Backend over SSE, demo polish, second scenario (slow-burn arm pain → revisit-on-incident), record the demo video.

Stretch (post-hackathon): Riva, Wi-Fi CSI, SeamlessM4T for the multilingual scenario, NIM/TensorRT-LLM migration.

---

## TL;DR Pick List (the version you put on a slide)

| Layer | Pick |
|---|---|
| Mic | ReSpeaker 6-Mic Array |
| **Backend** | **FastAPI + Uvicorn + SQLModel + Alembic + Arq + APScheduler + sse-starlette** |
| Wake word | openWakeWord |
| VAD | Silero VAD |
| STT | NVIDIA Parakeet-TDT (fallback: faster-whisper) |
| Speaker ID | pyannote.audio |
| Audio events | CLAP + YAMNet |
| LLM runtime | vLLM → NIM/TensorRT-LLM |
| LLM model | Llama 3.1 8B + Meditron-7B (consult) |
| Agent framework | LangGraph |
| Voice pipeline | Pipecat (inside Backend) |
| Translation | SeamlessM4T v2 |
| Vector DB | Qdrant |
| Embeddings | NV-Embed-v2 + MedCPT |
| Patient DB | SQLite + SQLCipher (via SQLModel) |
| Time-series | InfluxDB 3 |
| Wearable | Polar H10 via `bleak` |
| TTS | Kokoro (hackathon) → Riva (prod) |
| UI | Next.js + Recharts (or Streamlit for speed) |
| External MCPs | Google Calendar, Spotify, Twilio, Toronto Open Data |
| Emergency comms | Twilio |
| Observability | Langfuse + Prometheus + Grafana |
| Privacy | SQLCipher + LUKS + hardware mic switch + Tailscale |
