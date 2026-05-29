# Guardian — Recommended Architecture

> The architecture decisions that hold up under all 27 scenarios, on real hardware, with real users, with PHI in play.

This document is the result of a re-read across [`README.md`](README.md), [`TECH_STACK.md`](TECH_STACK.md), [`guardian_scenarios.md`](guardian_scenarios.md), and [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md). It is the **definitive recommendation** for how Guardian should be built — the architectural shape that survives the demands of every scenario in the playbook, the constraints of the DGX Spark, and the legal weight of PHIPA.

If anything in the other documents disagrees with this one, **this document wins**. Update the others to match.

---

## 1. What we are building

A single-home, on-premise, multi-agent AI system that:

- Listens passively to a home, 24/7, without sending audio off-device.
- Responds actively when addressed by name.
- Detects medical, behavioral, and environmental emergencies via voice + vitals + sensors.
- Triages, escalates, and dispatches help — with the right severity for the right severity.
- Handles routine care (meds, vitamins, mood, vitals trends, calendar).
- Generates structured clinical handoffs to receiving professionals.
- Never sends PHI off-device without explicit, per-recipient, per-data-category consent.

The user-facing experience is **a calm voice in the home**. The system underneath is a six-sub-agent multi-agent system on a four-bucket shared tool bus, hosted by a FastAPI process on DGX Spark, with always-on detection offloaded to a low-power edge node.

---

## 2. What the 27 scenarios actually demand

The architecture has to absorb all of these without scenario-specific special cases.

| Demand | From scenarios | Implication |
|---|---|---|
| **Sub-5-second emergency response** | 1, 12, 14, 20, 21, 24 | Always-on detection has to be cheap and continuous |
| **Conversational interruption-handling** | 4, 5, 6, 17, 23, 25, 27 | Real-time audio pipeline with barge-in |
| **Multi-agent parallel** | 1, 9, 12, 14, 16 | Two or three sub-agents talking, listening, acting concurrently |
| **Explicit Companion suppression** | 20, 24 | The Orchestrator must know *when not to talk* |
| **Long-horizon pattern detection** | 7, 18, 19, 26 | A slow-time path running daily / weekly / monthly |
| **Scheduled events to-the-minute** | 3, 4 | A scheduler that fires independently of the LLM |
| **Different demographic, same architecture** | 17 (veteran), 22 (dementia), 23 (young adult), 25 (elderly), 27 (toddler) | Voice profile + tool subset is *per sub-agent*, not per scenario |
| **Outbound to humans** | 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 27 | A consent-gated integrations layer with idempotency |
| **Multilingual** | 15 | Translation as a tool, not a special architecture |
| **Differential diagnosis** | 25 | The Health Agent does structured reasoning, not just severity scoring |
| **Caregiver-as-asker** | 19, 27 | The patient on file ≠ the person speaking |
| **Cloned-voice therapeutic value** | 17, 22, 26 | Voice profile per sub-agent must be *patient-specific*, not global |
| **Recurring expected events** | 26 (sundowning) | Preemptive intervention based on learned daily patterns |
| **Restricted-environment handling** | 20 (no speech), 21 (wet/closed), 24 (smoke/O₂) | Tools work when fewer than the usual modalities are available |

A single fact emerges: this is a **broad-demand system**, not a deep-stack one. The right architecture absorbs breadth.

---

## 3. The ten architectural principles

These are the non-negotiable rules that shape every other decision.

### 3.1 Always-on / On-demand process separation

Everything runs on the **DGX Spark** — no separate edge hardware. Always-on sensing (wake word, VAD, audio event classification, wearable BLE ingest, environmental sensor poll, scheduler) runs as **CPU-pinned background processes** on the Grace ARM cores. The expensive agent / LLM / TTS work binds to the Blackwell GPU only when summoned by an event. The GPU does not run the LLM 24/7.

**Why.** Power, isolation, resilience. The LLM process restarting (model swap, OOM recovery, hot reload) must not deafen the home — pinning the always-on stack to its own CPU processes ensures it doesn't. Same principle as the edge/core split, just realised inside one machine with process isolation instead of two machines on a network.

### 3.2 Event-driven core

Every signal is an `Event` on a single bus. Wake-word triggers emit events. Audio classifier outputs emit events. Wearables emit events. The scheduler emits events. The patient saying "Guardian, I fell" emits events. The Orchestrator subscribes; sub-agents subscribe; the UI subscribes (via SSE). One mechanism ties everything together.

**Why.** Testability, audit, replay, decoupling.

### 3.3 Persistence-first

Every event is written to the append-only Event Log **before** processing. If anything crashes mid-incident, restart and replay. The Event Log is the system's source of truth — every projection (UI, weekly summary, clinical handoff) is a derived view of it.

**Why.** PHIPA audit, medical-legal weight, hot-restart capability.

### 3.4 Tiered model cascade

| Tier | Model | Use |
|---|---|---|
| **S** | Rules + regex, no LLM | Unambiguous signals (e.g., `audio_event=fall_sound` → Safety) |
| **A** | Phi-3.5-mini | Routing classification, Risk Classifier, severity scoring |
| **B** | Llama 3.1 8B | Conversational sub-agents (Safety, Companion, Reminder, Behavior dialog) |
| **C** | Meditron-7B | Clinical consults (differential diagnosis, drug interactions) |
| **D** | Llama 3.3 70B | Hard reasoning — weekly summaries, complex differentials, FHIR document drafting |

The Orchestrator picks the cheapest tier that can answer. Tier S handles a majority of routings. Tier D fires only for slow-time jobs.

**Why.** DGX VRAM is finite. Always paying Tier D prices is wrong. Always paying Tier B prices is also wrong.

### 3.5 Severity as the universal currency

Every event carries a CTAS-aligned severity:

- **Tier 1 — whisper:** soft TTS in-room, no other action.
- **Tier 2 — nudge:** TTS + UI toast + ambient light.
- **Tier 3 — alarm:** loud TTS + bright light + caregiver SMS.
- **Tier 4 — call:** 911 + family voice call + door unlock.

The Risk Classifier emits the severity; the Orchestrator maps severity to action via patient profile. **No scenario-specific severity logic exists.**

**Why.** Without this, every new scenario writes its own thresholds. With this, adding a scenario is mostly data.

### 3.6 Consent as a first-class type

Patient profile contains a `ConsentMatrix`:

- **Per-recipient:** family, family-doctor, specialist, counselor, probation officer, paramedic, court.
- **Per-data-category:** vitals, voice transcript, voice features only, mood, behavior, medication log, incident summary.
- **Per-mode:** always / on-incident / on-explicit-ask / never.

Every outbound tool reads the matrix before acting. Every outbound event is logged with the consent decision (allowed/blocked + reason). **No outbound action without an explicit consent path.**

**Why.** PHIPA. Also: behavioral scenarios (court-mandated, domestic violence, child welfare) live or die on this being clean.

### 3.7 Conversational floor lock

Only **one** sub-agent holds the TTS lock at a time. Others can run passive workflows but cannot speak. Handoff between sub-agents is explicit (`HandoffEvent` on the bus), with the new sub-agent acquiring the lock.

**Why.** A calm-keeping system that talks over itself is worse than one that says less.

### 3.8 Idempotent tools

Every outbound side-effect tool (911 dispatch, SMS, voice call, FHIR push, pharmacy refill) takes an idempotency key. Retries within the dedup window do not double-dial.

**Why.** Network flakes. Demo-day jitters. Defense against your own bugs.

### 3.9 One Pydantic for everything

Pydantic v2 models define every shape:

- DB rows (via SQLModel)
- API requests/responses (via FastAPI)
- Agent tool schemas (via LangGraph)
- Event payloads (the bus)
- MCP request/response

One type system, top to bottom. The same `IncidentSummary` model is what gets persisted, served to the UI, handed to the FHIR push tool, and shown to the agent.

**Why.** Every other source of truth becomes wrong at the worst possible time.

### 3.10 Two clocks

A **real-time loop** (Pipecat audio pipeline: edge VAD → STT → Orchestrator → Sub-Agent → TTS, sub-second budget) runs separately from a **slow-time loop** (Behavior Agent nightly job, weekly summaries, monthly trend pushes). They share the Event Log but not the Python execution context.

**Why.** Slow analytics must not block voice latency. Voice latency must not delay analytics.

---

## 4. The canonical architecture

```
╔════════════════════════════════════════════════════════════════════════╗
║                        DGX SPARK  (single device)                        ║
╠════════════════════════════════════════════════════════════════════════╣
│  ALWAYS-ON PROCESSES  (CPU-pinned to Grace cores)                        │
│                                                                          │
│   Audio  →  openWakeWord  →  Silero VAD  →  faster-whisper-int8  →  text │
│          ↓                                                                │
│          YAMNet  →  audio_event signals  (fall / cough / glass / silence) │
│                                                                          │
│   BLE wearable poller          Env. sensor poller (Matter / GPIO)        │
│        ↓                                ↓                                 │
│   Vitals stream                 Door / kettle / temp / motion             │
│                                                                          │
│   ALL → Candidate Events (typed Pydantic) → Event Bus                    │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│  ON-DEMAND PROCESSES  (Blackwell GPU + heavy CPU, summoned)              │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Event Bus  (NATS in prod, asyncio.Queue in hackathon)             │  │
│  │  ─ Every event written to append-only Event Log BEFORE routing    │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Orchestrator  (LangGraph supervisor)                              │  │
│  │  ─ Hybrid router (rules first → Phi-3.5-mini if ambiguous)         │  │
│  │  ─ Risk Classifier → Tier 1/2/3/4 severity                         │  │
│  │  ─ Conversation floor lock                                         │  │
│  │  ─ Cross-agent handoff protocol                                    │  │
│  │  ─ Logs every routing decision with a reason                       │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Sub-Agent Pool  (six LangGraph subgraphs sharing one LLM)         │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──┐│  │
│  │  │ Safety  │ │ Health  │ │Reminder │ │Companion │ │Behavior│ │CL││  │
│  │  └─────────┘ └─────────┘ └─────────┘ └──────────┘ └────────┘ └──┘│  │
│  │  Each: own prompt, own tool subset, own voice profile             │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Tool Bus  (Pydantic-typed Python functions)                       │  │
│  │  Sensing │ Memory & Reasoning │ Action │ Integrations              │  │
│  │  Decorators: @consent_check  @idempotent  @audit_log               │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                               ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Storage                                                           │  │
│  │  Patient profile + consent matrix (SQLite + SQLCipher)              │  │
│  │  Event Log  (append-only, content-hash chain — the source of truth) │  │
│  │  Vitals time-series (InfluxDB 3)                                    │  │
│  │  Conversation memory (in-process now, Qdrant nightly summaries)     │  │
│  │  Medical KB (Qdrant + NV-Embed-v2 / MedCPT)                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Real-time path:  Pipecat-driven, sub-second                             │
│  Slow-time path:  Arq workers — Behavior nightly, summaries, baselines   │
└────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    FastAPI HTTP + SSE
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
              UI            External         MCP servers
            (Next.js)    (Twilio, FHIR)   (Calendar, Spotify,
                                            Pharmacy, Toronto OD)
```

**Read it as:** edge feeds events → bus persists then routes → Orchestrator picks a Sub-Agent → Sub-Agent calls tools → tools dispatch side effects through gated decorators → storage holds the source of truth → UI and external systems see the result through the Backend's external API.

---

## 5. The five canonical flows

Every one of the 27 scenarios reduces to one (or a composition) of these five flows. The architecture handles each cleanly.

### Flow 1 — Active dialog (patient addresses Guardian)

```
Always-on:   wake-word + STT → text
Bus:         PatientUtteranceEvent persisted
Orch:        rules + Phi-3.5-mini → routes to Sub-Agent X
Sub:         Sub-Agent X uses Tier B LLM, calls tools
Bus:         tool intents persisted
Tools:       side effects dispatched (TTS, etc.)
SSE:         UI updated
```

Scenarios: 4, 5, 6, 8 (when Marcus speaks), 16, 23, 25, 27.

### Flow 2 — Passive trigger (no patient address)

```
Always-on:   audio_event / vitals_anomaly / env_signal → CandidateEvent
Bus:         persisted
Orch:        Risk Classifier → severity tier
Orch:        routes; for Tier 1-2 → soft check-in; for Tier 3-4 → immediate escalation
Multi:       for Tier 3-4, cross-agent fan-out (Safety primary + Companion parallel)
Tools:       side effects dispatched
```

Scenarios: 1, 2, 9 (when audio events fire), 11, 17, 20, 21, 22, 24, 26.

### Flow 3 — Scheduled (the clock fires)

```
APScheduler:  tick → ScheduledEvent
Bus:          persisted
Orch:         routes by event type — always Reminder Agent for med ticks
Reminder:     reads regimen + checks Conflict/Interaction → emits notification intent
Tools:        Notification Dispatcher fires (TTS + UI + smartwatch)
```

Scenarios: 3, the BP prompt in 4.

### Flow 4 — Slow-time (background worker)

```
Arq worker (nightly/weekly): pulls window from Event Log
Reasoning:                   Personal Baseline, Anomaly Detector, Pattern-Absence run
If output crosses threshold: emit synthetic AnalyticsEvent onto the bus
                             → handled as a normal event (Flow 2)
Else:                        update the baseline, exit
```

Scenarios: 7 (David's mood window), 18 (Frank's cognitive trend), 19 (Lisa's caregiver-burnout trajectory), 26 (Frank's sundowning pattern update).

### Flow 5 — Cross-agent handoff

```
Active sub-agent: emits HandoffEvent (target=Safety, severity=Tier 4, reason=...)
Orch:             releases floor lock from current sub-agent
Orch:             routes to target sub-agent with full context
Target:           acquires floor lock, continues from received state
```

Scenarios: 12 (Companion FAST → Safety dispatch), 13 (Tier 2 → Tier 3 fallback), 25 (Health differential → Reminder for clinic options), 9 (Behavior watch → Safety on glass-break).

---

## 6. Tension resolutions

Hard tradeoffs and the decisions taken.

### Hackathon stack vs. production stack

Every Phase 0–3 pick is a **strict subset** of the production stack — swappable behind a stable interface:

| Hackathon | Production | Interface that stays the same |
|---|---|---|
| vLLM | NIM + TensorRT-LLM | OpenAI-compatible HTTP |
| Kokoro TTS | NVIDIA Riva | Pipecat TTSService |
| Streamlit | Next.js + SSE | Backend REST + SSE |
| SQLite | SQLite + SQLCipher | Connection string |
| faster-whisper | Parakeet-TDT | Pipecat STTService |
| In-process asyncio.Queue | NATS | `event_bus.publish()` |

No hackathon code becomes technical debt.

### Six sub-agents vs. one big agent with role prompts

Six is right because:

- Each owns a distinct **escalation ceiling** (only Safety can call 911; Caregiver Liaison never calls 911 in-home).
- Each has a distinct **voice profile** (urgent / calm / gentle / firm / formal).
- Each has a distinct **tool subset** (Behavior Agent cannot directly call Twilio for the patient's family without going through Caregiver Liaison).
- Each has a distinct **time horizon** (Safety = seconds; Behavior = weeks).

But: all six **share the same backing LLM** (Llama 3.1 8B). They are not separate processes — they are LangGraph subgraphs with distinct system prompts, gated tool subsets, and isolated state. Adding a seventh is a config change.

### Privacy vs. functionality

Two consent gates on every outbound action:

1. **Per-recipient** (family, doctor, court, paramedic, …)
2. **Per-data-category** (vitals, voice transcript, voice-features-only, mood, behavior, …)

Default is "nothing leaves the device." Egress requires an explicit consented path. The consent matrix is auditable.

### Latency vs. capability

Three paths with three SLAs, all on the same DGX but in different process groups:

| Path | Budget | Lives in |
|---|---|---|
| Always-on detection | < 100ms | CPU-pinned background processes (Grace cores) |
| Real-time dialog (Pipecat loop) | < 1.5s total | GPU-bound LLM + TTS process (Blackwell) |
| Slow-time analytics | minutes-to-hours | Arq workers (CPU, batch GPU calls) |

No path is asked to do another's job. No path shares a Python process with another path.

### State complexity

The **Event Log is the system state**. Everything else is derived:

- UI = projection over Event Log
- Weekly summary = LLM compression of Event Log slice
- Personal Baseline = streaming stats over Event Log
- Conversation Memory = recent Event Log + nightly Qdrant summary
- Vitals view = time-series projection (also kept in InfluxDB for query speed)

Cold-restart needs only the Event Log + the consent matrix. Everything else rebuilds.

### Where Conversation Memory lives

In-process short-term (per-incident, low latency, lost on restart) + Qdrant long-term (nightly LLM-summarized episodes, durable, searchable). The Companion Agent reads both: short-term for "what did I just say to Eleanor," long-term for "what did we talk about last week."

### Where Personal Baseline lives

Two-tier: **streaming stats** (River, online) for per-event comparison, and **daily-aggregated baselines** (batch job into the Reasoning Modules' SQLite) for slow-changing patterns like Frank's sundowning window. Both are derived from the Event Log.

---

## 7. Component boundaries and contracts

| Layer | Owns | Must not touch |
|---|---|---|
| **Always-on processes** | Always-on detection, low-latency ingestion, vital/sensor polling | LLM inference, agent policy, outbound side effects |
| **Event Bus** | Persistence-before-routing, fan-out, replay | Application logic |
| **Orchestrator** | Routing, severity, floor lock, handoffs | Sub-agent internals, tool implementations, persistence |
| **Sub-Agents** | Policy, escalation ceiling, voice profile | Each other's internals, raw tool implementations, the bus |
| **Tool Bus** | Capability execution, consent check, idempotency, audit | Policy, routing, severity decisions |
| **Storage** | Persistence, encryption, audit chain | Application logic |
| **MCP servers** | External system protocols | Internal Guardian logic |
| **Backend (FastAPI)** | Process hosting, HTTP/SSE API, scheduling, side-effect dispatch | Sub-agent reasoning |

Anything that crosses a boundary does so as a **typed event or a typed tool call** — never an in-process method call.

---

## 8. What this architecture buys us

- **Hackathon-shippable.** Phases 0–3 from the dev plan use this same shape without rewrites.
- **27-scenario-coverable.** Every scenario maps to one of the five flows.
- **PHIPA-compliant by construction.** Consent + audit chain + encryption are foundational, not bolted on.
- **Hardware-appropriate.** DGX Spark does what it's good at (heavy LLM); always-on detection lives on cheap edge silicon.
- **Demo-defensible.** A judge can grasp the shape in 90 seconds: edge senses, bus persists, Orchestrator routes, six sub-agents specialize, four tool buckets, encrypted storage, consent gates everything outbound.
- **Extensible without rewrites.** A seventh sub-agent or a twentieth MCP integration is a config change, not an architectural one.

---

## 9. What this architecture costs us

Honest tradeoffs.

- **More moving parts than a single Python script.** True. But the multi-agent demand is real — scenarios 1, 9, 12, 14, 16 each genuinely require concurrent sub-agents.
- **Process partition discipline on a single machine.** True. The CPU-pinned always-on processes must not import the GPU LLM libraries (cuda, transformers) — that would pull the GPU into the always-on critical path. Enforced by separating the always-on package from the agent package and by CI tests that fail on cross-imports.
- **LangGraph learning curve.** True. But the manual alternative to a supervised multi-agent graph is worse than the framework — the routing logic and state checkpointing are not "easy" to roll yourself.
- **Strict Pydantic discipline.** True. Pays for itself the first time an FHIR push validates correctly without a single test having to be written.
- **Consent matrix overhead at onboarding.** True. But the demo of "watch me try to push X to recipient Y and watch it get blocked with a clear reason" is worth more than the friction.

---

## 10. Things I would change after the re-read

Honest second-pass notes — corrections to the prior docs that this architecture supersedes.

1. **Pipecat lives on the Edge, not in the Backend.** [`TECH_STACK.md`](TECH_STACK.md) §20 says Pipecat runs inside the Backend. Wrong. The audio pipeline's always-on stages (mic capture, wake word, VAD, STT) belong on the edge tier; only the LLM and TTS stages run on the DGX. The "Backend hosts Pipecat" picture conflates two SLAs.
2. **Conversation Memory is two stores, not one.** [`TECH_STACK.md`](TECH_STACK.md) §15 lumped conversation embeddings into Qdrant. Reality: in-process short-term + Qdrant long-term. Different access patterns; one store can't do both well.
3. **Personal Baseline is two layers, not one.** [`TECH_STACK.md`](TECH_STACK.md) §13 picked River for online stats. Real picture: River for streaming + a daily batch aggregation for slow-changing patterns (Frank's sundowning window in Scenario 26 needs the second).
4. **The Event Log is THE source of truth.** Across all four docs, the Event Log was treated as an audit trail. That undersells it. Every projection (UI, weekly summary, FHIR document, baseline) is a derived view of the Event Log — it *is* the application state. Treating it as audit-only invites duplicated state.
5. **Behavior Agent cannot call 911 directly.** [`TECH_STACK.md`](TECH_STACK.md) §11 listed Behavior's escalation ceiling as "counselor portal + probation officer." Should be more explicit: **911 is reachable only via a Safety Agent handoff.** This is a real policy choice for Scenarios 8, 9, 10 — Behavior's job is to recognize the moment, not to dial.
6. **The Risk Classifier runs *always*, not on demand.** [`TECH_STACK.md`](TECH_STACK.md) §13 implied the Risk Classifier is invoked by sub-agents. The architecture works better if the **Orchestrator** runs the Risk Classifier on every event *before* routing. Severity is a routing input, not a sub-agent's job.
7. **The 4-bucket Tool Bus is organizational, not enforced.** [`TECH_STACK.md`](TECH_STACK.md) §12 was already close on this. To be explicit: gating happens **per-agent** (Safety's allowed tools, Companion's allowed tools, …), not per-bucket. The buckets are how humans read the menu; they are not security boundaries.

These are not big rewrites — they are clarifications. The other documents are mostly right; this document is what they should converge to.

---

## 11. How the development plan maps onto this architecture

| Phase | What of this architecture is alive |
|---|---|
| **0** | Real-time path only, no Orchestrator, no Sub-Agents, no Event Log. The walking skeleton. |
| **1** | Backend + single agent (Orchestrator and Sub-Agent collapsed). Event Log emerges. Patient profile exists. |
| **2** | Three-tier split: Orchestrator + Safety + Companion. Tool Bus formalized. Conversational floor lock implemented. |
| **3** | Reminder Agent. Scheduled flow live. Vitals path. Notification dispatcher with severity tiers. UI on SSE. |
| **4** | Health Agent. Slow-time path (nightly Behavior-style jobs). Medical RAG. Anomaly Detector. Differential diagnosis becomes a Health Agent capability. |
| **5** | Behavior + Caregiver Liaison. **Consent matrix** lights up. Real Twilio + FHIR. Cross-agent handoff fully implemented. |
| **6** | Always-on processes formally separated from on-demand processes (CPU-pinned vs. GPU-bound). Pipecat split: edge stages (mic, VAD, STT) in always-on, LLM + TTS stages in on-demand. Audio event detection live. |
| **7** | PHIPA hardening across the board. SQLCipher, signed Event Log chain, hardware mic switch, Tailscale. |
| **8** | Specialized capabilities slot into the existing Tool Bus — no architectural change required (this is the test of a good architecture). |
| **9** | New sensing modalities (Wi-Fi CSI, environmental mesh) join the Sensing bucket of the Tool Bus. Same architecture. |

The development plan and this architecture converge cleanly. **Nothing in any phase requires rewriting an earlier phase.**

---

## 12. Open questions for the team

Things I'd want the team to decide explicitly before Phase 1 starts.

1. **CPU core partition.** How many Grace cores reserved for always-on vs. left for the LLM-supporting processes? Recommendation: pin 6 of 20 cores to the always-on package via `taskset` / cgroups; the rest are free for the LLM runtime, schedulers, and FastAPI.
2. **Wake-word vs. wake-word-free.** Recommendation: wake-word for v1 (cheaper, more reliable); evaluate wake-word-free for v2 once the rest is stable.
3. **MCP transport (stdio vs. HTTP).** Recommendation: stdio for local-only servers; HTTP only if an MCP server needs to live on the edge tier.
4. **Slow-time worker (Arq vs. a separate service).** Recommendation: Arq for now; revisit if slow-time jobs become heavy enough to want their own resource budget.
5. **Default consent posture at onboarding.** Recommendation: minimum-consent default (only emergency-services egress allowed); patient explicitly opts in to every other recipient.
6. **Cloned-voice consent.** Required from the *voice owner*, not the patient. Scenarios 17, 22, 26 all need someone other than the patient consenting to having their voice cloned. The onboarding flow must reflect this.

---

## TL;DR — the architecture in one paragraph

Guardian is **a six-sub-agent system on a four-bucket tool bus, all running on a single DGX Spark — with always-on detection isolated to CPU-pinned processes and heavy reasoning living on the Blackwell GPU — glued together by an event-bus-and-Event-Log spine, hosted in a FastAPI process, with consent and audit baked into every outbound tool call.** The Orchestrator routes; the Sub-Agents specialize; the Tool Bus executes; the Event Log remembers. Every scenario reduces to one of five canonical flows. Every privacy decision is a consent matrix lookup. Every hackathon pick is a strict subset of the production pick.
