# Guardian — Development Plan

A phased build plan from the simplest possible walking skeleton to a production-grade, multi-agent system. Each phase ships something **demoable on its own**; each subsequent phase strictly adds capability rather than rewriting the prior one.

The hackathon window is **Phases 0 → 3**. Everything from Phase 4 onward is post-hackathon roadmap.

---

## How to read this plan

Every phase has the same structure:

- **Goal** — the one sentence that defines "done."
- **Adds** — the concrete components introduced in this phase.
- **Demoable scenarios** — which entries from [guardian_scenarios.md](guardian_scenarios.md) work end-to-end after this phase.
- **Acceptance criteria** — the checklist that decides whether the phase is shippable.
- **Effort** — rough engineer-hours.
- **Risks & mitigations** — what could blow up, and the fallback.

Each phase **strictly extends** the prior one. No rewrites — code from Phase 1 still runs in Phase 8.

---

## Phase 0 — Walking Skeleton

**Goal.** Speak to a laptop. Hear it speak back. Prove the local audio + LLM + TTS loop works on the DGX Spark before any architecture exists.

### Adds

| Component | Pick | Why this one for Phase 0 |
|---|---|---|
| Audio in | `sounddevice` + push-to-talk hotkey | Skip wake word for now — keep it dead simple |
| STT | `faster-whisper` (small model) | Zero NVIDIA NeMo setup; works on any laptop while DGX environment matures |
| LLM | **Ollama + Llama 3.1 8B** | One-command install, no vLLM tuning yet |
| TTS | Kokoro-82M | Single Python package, runs on CPU if needed |
| App | Single Python script (`prototype.py`) | No FastAPI, no agents, no DB — just a `while True:` loop |

### Demoable scenarios

None from the playbook yet. The demo is: *press a key, say "What time is it?", hear it answered.*

### Acceptance criteria

- [ ] End-to-end round-trip latency under 4 seconds on the dev machine.
- [ ] Output audio is intelligible at normal volume.
- [ ] No cloud calls during the loop (verified by airplane mode).

### Effort

~4 hours.

### Risks & mitigations

- *Ollama doesn't run on the DGX Spark ARM image immediately.* → Fall back to a local laptop for Phase 0; the DGX gets first use in Phase 1.

---

## Phase 1 — MVP: The Fall Demo

**Goal.** The headline demo works: an elderly user says *"Hey Guardian, I fell"*, the system identifies the patient from a local profile, generates a personalized emergency summary, and "calls 911" (mocked to console + UI toast).

### Adds

| Component | Pick |
|---|---|
| **Backend skeleton** | FastAPI + Uvicorn + SQLModel + Alembic |
| **Patient profile DB** | SQLite — one table: `Patient` (name, age, conditions, meds, allergies, emergency contacts) |
| **Incident log** | SQLite — append-only `Incident` table (start time, transcript, actions taken) |
| **Wake word** | openWakeWord with a custom "Hey Guardian" model (or push-to-talk if training the wake word slips) |
| **Single agent** | One LangGraph graph (no Orchestrator + Sub-Agents split yet) |
| **Two tools** | `get_patient_profile()`, `call_911_mock(summary)` — the mock prints to console + writes to incident log |
| **System prompt** | Hard-coded "you are Guardian, a calm emergency assistant" |

### Demoable scenarios

- **Scenario 1 (Midnight Fall)** — simplified single-agent path. The system finds Eleanor's profile, generates a 911 summary, and "places the call" (mock).

### Acceptance criteria

- [ ] Saying "Hey Guardian, I fell" reliably triggers the wake word, transcribes correctly, and the agent calls the mock 911 tool with a summary that names the patient and her cardiac history.
- [ ] The same flow works from at least 6 feet from the mic.
- [ ] The `Incident` row is queryable from SQLite after the demo.
- [ ] The TTS response is reassuring in tone.

### Effort

~8 hours (Hackathon Day 1).

### Risks & mitigations

- *openWakeWord custom-model accuracy is bad with limited training data.* → Ship Phase 1 with push-to-talk; train the wake word in parallel and add when ready.
- *LangGraph's tool-calling loop misbehaves with Llama 3.1 8B.* → Constrain the agent to a Pydantic `EmergencyResponse` schema and forbid free-text replies during emergencies.

---

## Phase 2 — Three-Tier Architecture (Orchestrator + 2 Sub-Agents)

**Goal.** Introduce the real architecture so Phase 1's monolith becomes the **Safety Agent**, and a parallel **Companion Agent** keeps talking to the patient while Safety handles dispatch.

### Adds

| Component | Pick |
|---|---|
| **Orchestrator** | LangGraph `Supervisor` pattern, with a **hybrid router** — rules for unambiguous signals (e.g., `event.type == "fall"` → Safety), LLM for narrative cases |
| **Safety Agent** | LangGraph subgraph — owns 911 escalation, geolocation, contact-tree |
| **Companion Agent** | LangGraph subgraph — owns calm-keeping dialogue, status updates ("ambulance is 4 minutes away") |
| **Risk Classifier** | Rule-based v0 (no ML yet) — emits Tier 1–4 based on keywords + duration |
| **Event Log** | Append-only SQLite table — the spine of cross-agent state |
| **Conversation Memory** | In-process buffer per incident (durable in Phase 4) |
| **Tool bus skeleton** | `tools/` package with the four buckets; populated with `voice_tts`, `emergency_caller`, `contact_tree`, `get_patient_profile`, `event_log_write`, `risk_classifier` |
| **Per-agent voice profiles** | Two Kokoro voices: "urgent" (Safety) vs "calm" (Companion) |
| **Parallel sub-agents** | LangGraph `parallel` node — Safety + Companion run concurrently, both write to the same Event Log |

### Demoable scenarios

- **Scenario 1 (Midnight Fall)** — full multi-agent path now: Safety calls 911 while Companion speaks reassurance, both logging to the Event Log.
- **Scenario 4 (verbal "I'm scared" subset)** — Companion-only path with no escalation: simple Tier-1 reassurance flow.

### Acceptance criteria

- [ ] During the fall demo, you can hear two distinct voices in interleaved turns (urgent Safety status + calm Companion dialogue).
- [ ] The Event Log shows ordered entries from both sub-agents.
- [ ] Saying "Guardian, I'm scared but I'm fine" stays at Tier 1 (no 911 call).
- [ ] The Orchestrator's routing decision is logged with a reason ("matched rule: keyword='fell'").

### Effort

~6 hours (Hackathon Day 2 AM).

### Risks & mitigations

- *Two sub-agents talking over each other.* → Companion holds the TTS lock; Safety emits *intents* (not TTS calls) and Companion converts them to spoken status updates.
- *LangGraph parallel state merge conflicts.* → Single-writer-per-key state schema; document who writes what.

---

## Phase 3 — Vitals, Reminders, and a UI

**Goal.** Round out the hackathon demo with non-emergency scenarios and visible state. Add the **Reminder Agent** so daily-life value is obvious, the **vitals stream** so the Health story is visible, and a **UI** so judges can actually *see* the system thinking.

### Adds

| Component | Pick |
|---|---|
| **Reminder Agent** | LangGraph subgraph |
| **APScheduler** | In-process scheduler in the Backend — fires medication ticks |
| **Wearable integration** | Polar H10 chest strap → `bleak` (BLE) → InfluxDB time-series |
| **`bio_marker` tool** | Reads the latest InfluxDB sample on demand |
| **Personal Baseline (v0)** | Rolling mean / std-dev per vital per time-of-day, computed in NumPy nightly |
| **Notification dispatcher tool** | Severity-tiered: `whisper` (TTS only), `nudge` (TTS + UI toast), `alarm` (TTS + lights), `call` (Twilio) |
| **UI** | **Streamlit** for hackathon speed — three pages: Live, Vitals, History |
| **Mock Twilio** | Console output stand-in for SMS/voice |
| **Tap-to-confirm** | Streamlit button that emits a `confirmed` event to the event bus |

### Demoable scenarios

- **Scenario 1 (Midnight Fall)** — now with live vitals on the UI showing HR spiking.
- **Scenario 3 (Sarah's vitamins)** — Reminder Agent fires on schedule, dispatcher pushes a UI nudge, tap-to-confirm logs intake.
- **Scenario 5 ("Did I take my medicine?")** — Companion answers from the Event Log.
- **Scenario 11 (Sleep HR anomaly)** — simple version: Personal Baseline flags an HR excursion, Health stub routes through Companion for the gentle check-in.

### Acceptance criteria

- [ ] Wearable HR appears in the UI within 2 seconds of being read on the strap.
- [ ] A scheduled medication reminder fires at the configured time, displays on the UI, and a tap dismisses it.
- [ ] "Guardian, did I take my morning pill?" returns the right answer from the Event Log.
- [ ] Vitals chart in the UI updates live during the fall demo.

### Effort

~6 hours (Hackathon Day 2 PM).

### Risks & mitigations

- *Polar H10 BLE pairing flakes during the demo.* → Pre-pair and lock the device; have a simulated-vitals fallback toggle in the UI.
- *Streamlit struggles with real-time updates.* → Use `st.empty()` + a polling loop; if it fails, fall back to a static dashboard refreshed on F5.

---

> **End of hackathon scope.** Everything from Phase 4 onward is post-hackathon roadmap.

---

## Phase 4 — Health Agent + Medical Knowledge

**Goal.** Bring **clinical reasoning** online. The Health Agent now owns vitals and chronic monitoring; medical answers are grounded in real guidelines via RAG.

### Adds

| Component | Pick |
|---|---|
| **Health Agent** | LangGraph subgraph |
| **Anomaly Detector** | **PyOD** — IsolationForest + MAD per vital, plus a multivariate detector |
| **Pattern-Absence Detector** | Custom — rhythm fingerprint per day, flag deviations beyond N MAD from baseline |
| **Personal Baseline (v1)** | Online stats via **River** (proper streaming ML), per vital, per context |
| **Medical KB (RAG)** | Qdrant + NV-Embed-v2 + MedCPT dual-index, corpus: first-aid manuals + CTAS guidelines + RxNav |
| **`clinical_consult` tool** | Wraps Meditron-7B for clinical reasoning queries |
| **Drug-interaction check** | Local RxNav snapshot + deterministic rules engine |
| **Risk Classifier (v1)** | Replace the rule-based v0 with **Phi-3.5-mini** fine-tuned (or zero-shot constrained) on a curated set of tier-labeled events |
| **More tools** | `anomaly_check`, `baseline_compare`, `pattern_absence_check`, `interaction_check`, `clinical_consult` |

### Demoable scenarios

- **Scenario 4 (Margaret's BP trend)** — Health Agent detects the trend, Caregiver Liaison stub drafts a note.
- **Scenario 11 (Sleep HR anomaly)** — full version with Anomaly Detector + Personal Baseline.
- **Scenario 13 (Hypoglycemia)** — needs Dexcom integration too; can ship without it using mocked CGM data.
- **Scenario 2 (Silent morning)** — Pattern-Absence Detector handles the absence-of-routine logic.

### Acceptance criteria

- [ ] Margaret's 7-day BP trend correctly triggers a Tier-2 alert (and not a Tier-1 or Tier-3).
- [ ] The `clinical_consult` tool's answer cites specific guideline excerpts from the corpus.
- [ ] The drug-interaction tool flags iron + calcium taken within 2 hours.
- [ ] Pattern-Absence flags the "silent morning" within 10 minutes of the expected wake-up window.

### Effort

~3 days.

---

## Phase 5 — Behavior Agent + Caregiver Liaison + Real External Comms

**Goal.** Cover the long-horizon and inter-human scenarios — depression, anger, domestic violence, child welfare, caregiver burnout — and stop mocking the outbound channels.

### Adds

| Component | Pick |
|---|---|
| **Behavior Agent** | LangGraph subgraph |
| **Caregiver Liaison** | LangGraph subgraph — the only sub-agent that talks to other humans |
| **Real Twilio** | SMS + outbound voice (Programmable Messaging + Voice) |
| **Counselor / Officer Portal** | Build a simple HTTP-receiving stub (real partners come later) |
| **EHR / FHIR Share** | HAPI FHIR client — push structured summaries |
| **Consent model** | `consent` table in the patient DB with per-recipient, per-data-category flags |
| **Mood logging** | UI mood slider + voice mood check-in; writes to Event Log |
| **Voice-stress analysis** | OpenSMILE feature extraction; baseline per user |
| **More tools** | `send_sms`, `place_outbound_call`, `fhir_push_summary`, `counselor_alert`, `mood_log_write`, `voice_stress_features` |

### Demoable scenarios

- **Scenario 7 (Depressed user — David)** — full path: Behavior Agent's nightly job, Companion gentle outreach, optional therapist alert via Liaison.
- **Scenario 8 (Court-mandated anger — Marcus)** — voice-stress excursion, Behavior de-escalation, probation officer alert.
- **Scenario 9 (Domestic violence)** — pre-agreed wording, Safety + Behavior + Liaison coordinated.
- **Scenario 10 (Child welfare — Theo)** — pattern absence + crying duration + caregiver inactivity correlate.
- **Scenario 19 (Caregiver burnout — Lisa)** — Behavior Agent's weekly job on the caregiver themselves.

### Acceptance criteria

- [ ] A real SMS lands on a test phone with a real incident summary.
- [ ] An FHIR `Communication` resource is pushed to a HAPI test server and is queryable.
- [ ] The consent matrix correctly blocks an unauthorized recipient (auditable in the log).
- [ ] Voice-stress baseline reliably distinguishes the same user calm vs. agitated across 10 test recordings.

### Effort

~4–5 days.

---

## Phase 6 — Production-Grade Audio Pipeline

**Goal.** Replace the prototype audio loop with **Pipecat** (interruption-aware), upgrade STT to **Parakeet-TDT**, add **speaker recognition**, and add **acoustic event detection** so the Safety Agent doesn't need the patient to speak in order to act.

### Adds

| Component | Pick |
|---|---|
| **Pipecat** | Embed inside the Backend process as the audio pipeline (replaces ad-hoc loop) |
| **Silero VAD** | First-class voice activity detection |
| **NVIDIA Parakeet-TDT-1.1B** | Replace faster-whisper for STT |
| **pyannote.audio** | Speaker recognition — household member enrollment + diarization |
| **YAMNet + CLAP** | Audio event detection (falls, glass break, coughing, crying) |
| **Interruption handling** | Pipecat's built-in barge-in support — the patient can interrupt Companion mid-sentence |
| **More tools** | `speaker_identify`, `audio_event_classify` |

### Demoable scenarios

- **Scenario 1 (Midnight Fall)** — now triggered by **acoustic** detection (thump + cry), not just the patient saying "I fell."
- **Scenario 2 (Silent morning)** — fully acoustic absence detection (no kettle, no footsteps, no music).
- **Scenario 9 (Domestic violence)** — voice + glass-break detection working together.
- **Scenario 10 (Child welfare)** — crying duration + caregiver inactivity acoustically detected.

### Acceptance criteria

- [ ] A pre-recorded fall sound + a brief cry, played at normal volume in the room, triggers Safety Agent in under 5 seconds with no patient speech.
- [ ] The patient can interrupt Guardian mid-utterance and the system stops talking within 300ms.
- [ ] Speaker recognition correctly identifies the registered household member vs. a visitor in 9/10 cases.

### Effort

~4–5 days.

---

## Phase 7 — PHIPA Production Hardening

**Goal.** Make Guardian actually deployable in a real home with real PHI. **No new scenarios, no new agents** — just the security, privacy, and reliability work that turns a demo into a product.

### Adds

| Concern | Module |
|---|---|
| **Disk encryption** | LUKS (whole device) |
| **DB encryption** | SQLCipher (SQLite), `pgcrypto` (if migrated to Postgres) |
| **Audit log** | Append-only event log with content-hash chain for tamper evidence |
| **Hardware mic kill switch** | Physical switch on the ReSpeaker; status surfaced in UI |
| **Caregiver remote access** | Tailscale mesh — encrypted, ephemeral keys, no public exposure |
| **Auth** | Passkeys (WebAuthn) for household, Tailscale identity for caregivers |
| **Secrets** | `pass` + GPG (or Vault if multi-user) |
| **LLM runtime upgrade** | vLLM → **NVIDIA NIM + TensorRT-LLM** on Blackwell |
| **TTS upgrade** | Kokoro → **NVIDIA Riva** for sub-100ms first-byte latency |
| **UI upgrade** | Streamlit → **Next.js 15 + Recharts**, SSE for live updates, OpenAPI-generated client |
| **Observability** | Self-hosted **Langfuse** for agent tracing, Prometheus + Grafana for metrics |
| **Process management** | systemd units + `Podman` containers, watchdogs |
| **Backups** | Encrypted snapshots to a household NAS or local USB; never to cloud |

### Demoable scenarios

Same as Phase 6, but the system survives a power cycle, a network outage, and an attempted "give me Eleanor's records" social-engineering attempt.

### Acceptance criteria

- [ ] All PHI at rest is encrypted; rebooting without the passphrase blocks access.
- [ ] The audit log can detect a single-row tamper (hash chain breaks).
- [ ] Toggling the mic kill switch shows immediately in the UI and silences the audio pipeline.
- [ ] A network-outage test: the device continues to function for 1 hour with no internet, including 911 dispatch (cellular fallback) and all on-device inference.
- [ ] Langfuse shows a complete trace for a full incident, including every tool call and reasoning step.

### Effort

~2 weeks.

---

## Phase 8 — Specialized Capabilities

**Goal.** Add the high-value but specialized features that distinguish Guardian in particular markets and personas.

### Adds (each independently shippable)

| Capability | Module | Unlocks scenarios |
|---|---|---|
| **Multilingual live interpretation** | Meta SeamlessM4T v2 (speech ↔ speech) | Scenario 15 (Mr. Chen 911 handoff) |
| **Voice cloning** | XTTS-v2 — cloned trusted-family voice for crisis comfort | Scenario 17 (PTSD nightmare with spouse's voice) |
| **Stroke FAST protocol** | Custom verbal-exam routine + speech-anomaly thresholds | Scenario 12 |
| **Pregnancy companion** | Trimester-aware regimen + warning-sign interview templates | Scenario 16 |
| **Cognitive decline tracker** | Longitudinal vocabulary diversity + response latency + micro-tests | Scenario 18 |
| **Smart home actuators** | Hue / Matter via `python-matter-server` for ambient lights, smart locks | All "Ambient Lights" steps; Scenario 14 door unlock |
| **Vision / motion sensor** | On-device camera with privacy-preserving pose inference | Reinforces Scenarios 1, 2, 10, 11 |
| **Hypoglycemia early detection** | Dexcom Share / Follow API integration | Scenario 13 |
| **Anaphylaxis protocol** | EpiPen-aware emergency script + door-unlock side effect | Scenario 14 |

### Demoable scenarios

All 19 scenarios from the playbook are now live.

### Acceptance criteria

Per-capability — each module ships with its own scenario script that demonstrates the new capability without regressing prior phases.

### Effort

~1 week per capability, parallelizable across the team.

---

## Phase 9 — Stretch: Camera-Free Sensing

**Goal.** Eliminate the camera entirely without losing pose / fall awareness.

### Adds

| Component | Pick |
|---|---|
| **Wi-Fi CSI extraction** | ESP32-CSI-Tool ($5 hardware) or Nexmon CSI on a Broadcom-equipped router |
| **CSI activity classifier** | Custom model trained on labeled CSI traces (Wi-Pose / Person-in-WiFi-style architecture) |
| **Environmental sensor mesh** | Matter devices (kettle plug, fridge door sensor, bed occupancy mat) |

### Demoable scenarios

- **Scenario 1 (Fall)** — fall detected via CSI signature change, no camera, no audio.
- **Scenario 2 (Silent morning)** — bed-occupancy + Wi-Fi pose confirms absence of expected movement.

### Acceptance criteria

- [ ] A scripted "person falling" in the CSI test rig is correctly classified in 8/10 trials.
- [ ] The system runs with the camera physically covered and still passes all fall-detection scenarios.

### Effort

Open-ended research effort; not on the critical path.

---

## Dependency Graph (Phase Ordering Constraints)

```
Phase 0 ──▶ Phase 1 ──▶ Phase 2 ──▶ Phase 3 ───┐
                                               │
                                               ▼
                                            Phase 4 ──▶ Phase 5
                                                          │
                                                          ▼
                                                       Phase 6 ──▶ Phase 7 ──▶ Phase 8
                                                                                  │
                                                                                  ▼
                                                                                Phase 9
```

- **Phase 4 (Health Agent) and Phase 5 (Behavior + Liaison) can run in parallel** if you have ≥2 engineers — they touch different sub-agents and don't share modules beyond the shared tool bus.
- **Phase 7 (Hardening) can start in parallel with Phase 6 (Pipecat)** — the hardening work is mostly orthogonal to the audio pipeline.
- **Phase 8 (Specialized) is fully parallelizable** — each capability is its own track.

---

## Feature Matrix Across Phases

| Feature | P0 | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 |
|---|---|---|---|---|---|---|---|---|---|
| Voice loop (STT → LLM → TTS) | x | x | x | x | x | x | x | x | x |
| Patient profile DB |  | x | x | x | x | x | x | x | x |
| Single agent + tools |  | x | (refactored) | | | | | | |
| Orchestrator + Safety/Companion |  |  | x | x | x | x | x | x | x |
| Wake word ("Hey Guardian") |  | x | x | x | x | x | x | x | x |
| Wearable vitals |  |  |  | x | x | x | x | x | x |
| Reminder Agent + scheduler |  |  |  | x | x | x | x | x | x |
| Streamlit UI |  |  |  | x | x | x | (→ Next.js) | | |
| Next.js UI |  |  |  |  |  |  |  | x | x |
| Health Agent + medical RAG |  |  |  |  | x | x | x | x | x |
| Anomaly + pattern-absence detectors |  |  |  |  | x | x | x | x | x |
| Behavior + Caregiver Liaison agents |  |  |  |  |  | x | x | x | x |
| Real Twilio + FHIR |  |  |  |  |  | x | x | x | x |
| Consent model |  |  |  |  |  | x | x | x | x |
| Pipecat + Parakeet + speaker ID |  |  |  |  |  |  | x | x | x |
| Audio event detection |  |  |  |  |  |  | x | x | x |
| SQLCipher + LUKS + audit chain |  |  |  |  |  |  |  | x | x |
| NIM/TensorRT + Riva |  |  |  |  |  |  |  | x | x |
| Translation (SeamlessM4T) |  |  |  |  |  |  |  |  | x |
| Voice cloning (XTTS) |  |  |  |  |  |  |  |  | x |
| Wi-Fi CSI sensing |  |  |  |  |  |  |  |  | (P9) |

---

## Scenario Coverage by Phase

A scenario is "covered" when its full happy path runs end-to-end on the demo machine.

| Scenario | First covered in |
|---|---|
| 1. Midnight fall (Eleanor) | Phase 1 (single-agent), Phase 2 (multi-agent), Phase 6 (acoustic trigger) |
| 2. Silent morning | Phase 4 (Pattern-Absence), Phase 6 (acoustic), Phase 9 (CSI) |
| 3. Sarah's vitamin stack | Phase 3 |
| 4. Margaret's BP trend | Phase 4 |
| 5. "Did I take my medicine?" | Phase 3 |
| 6. "What happened this week?" | Phase 4 (needs durable Conversation Memory) |
| 7. Depressed user (David) | Phase 5 |
| 8. Court-mandated anger (Marcus) | Phase 5 |
| 9. Domestic violence | Phase 5 (+ Phase 6 for glass-break detection) |
| 10. Child welfare (Theo) | Phase 5 (+ Phase 6 for crying detection) |
| 11. Sleep HR anomaly (Eleanor) | Phase 3 (basic), Phase 4 (proper) |
| 12. Stroke FAST exam | Phase 8 |
| 13. Hypoglycemia | Phase 8 (Dexcom) |
| 14. Anaphylaxis | Phase 8 (door unlock) |
| 15. Multilingual 911 handoff | Phase 8 (SeamlessM4T) |
| 16. Preeclampsia warning | Phase 8 (pregnancy module) |
| 17. PTSD nightmare | Phase 8 (voice cloning) |
| 18. Cognitive decline | Phase 8 (longitudinal tracker) |
| 19. Caregiver burnout | Phase 5 |

---

## Phase Exit Checklists (TL;DR per phase)

| Phase | "Done when…" |
|---|---|
| **0** | The laptop talks back to you locally, no cloud. |
| **1** | "Hey Guardian, I fell" → mocked 911 call with Eleanor's history. |
| **2** | Same fall demo, but Safety and Companion run in parallel, both logged. |
| **3** | A judge can see live vitals, schedule a reminder, and tap-confirm. |
| **4** | Margaret's BP trend triggers a graceful clinician note. |
| **5** | A real SMS lands on a real phone; an FHIR resource lands in a real (test) server. |
| **6** | A pre-recorded fall sound (no voice) triggers Safety Agent. |
| **7** | Reboot without the passphrase = no PHI access; mic kill switch works. |
| **8** | All 19 scenarios run end-to-end on the demo machine. |
| **9** | A camera-covered demo passes the fall scenario via Wi-Fi CSI. |
