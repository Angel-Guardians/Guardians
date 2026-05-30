# Guardian — Components & Scenario Playbook

Companion document to `guardian_architecture.md`. This file describes each component in plain language and walks through eleven scenarios end-to-end, showing which sub-agents and tools are invoked and in what order.

---

## Part 1 — Component descriptions

### The orchestrator

**Guardian Orchestrator.** The single entry point and decision-maker. It holds the user profile (age, conditions, consent mode, emergency contacts) and the escalation policy. When any tool fires an event, it lands here first — the orchestrator decides which sub-agent owns the response, whether multiple sub-agents should run in parallel, and when to lift severity. Sub-agents never call each other directly; they recommend, the orchestrator dispatches.

### The six sub-agents

**Safety Agent.** Owns anything where the failure mode is physical harm in the next 60 seconds. Falls, panic phrases, breaking glass, the silent-morning case. It is the only sub-agent allowed to trigger 911 directly.

**Health Agent.** Owns vitals, anomalies, and chronic-condition signals. Heart rate deviations, blood pressure trends, glucose excursions, cycle-aware logic. Time horizon is minutes to days, not seconds.

**Reminder Agent.** Owns schedules and adherence. Medication, vitamins, appointments, refills. Handles state-dependent logic (workout day vs. rest day, cycle phase, fasting windows) and conflict checks between substances.

**Companion Agent.** Owns conversation, calming, and memory recall. Answers "did I take my medicine?", talks the user through a crisis, runs daily mood check-ins, retrieves past events from memory.

**Behavior Agent.** Owns long-horizon behavioral monitoring. Anger management, depression slide, addiction relapse cues, domestic-violence escalation patterns, child-welfare concerns. Time horizon is days to weeks.

**Caregiver Liaison.** The only sub-agent that talks to *other humans* — doctors, counselors, family, probation officers. Centralizes the consent model and produces the weekly clinical summary, counselor notes, and incident reports.

### The shared tools

**Sensing.**
- **Audio Listener** — ambient sound classification (thumps, raised voices, glass, crying, silence) plus wake-word and speech-to-text.
- **Vision / Motion Sensor** — camera or PIR; detects presence, posture, falls, and prolonged inactivity. On-device inference.
- **Wearable Vitals Stream** — continuous HR, HRV, SpO₂, sleep, steps from a watch.
- **BP Cuff / Glucose Meter** — discrete clinical readings at prompted times.
- **Environmental Sensors** — kettle, fridge door, light, room temperature, bed occupancy.
- **Manual Input** — tap-to-confirm, mood slider, pain level, "I took it" buttons.
- **Wake-Word + STT** — opens the spoken dialogue channel.
- **Geolocation** — coarse location for emergency dispatch and behavioral context.

**Memory & reasoning.**
- **Event Log** — append-only timestamped record of every observation and action.
- **Personal Baseline Model** — per-user rolling statistics for what is normal *for this person*.
- **Conversation Memory** — durable notes from spoken exchanges; supports recall queries.
- **Regimen / Schedule Store** — the user's medication, supplement, appointment, and routine plan with conflict rules.
- **Anomaly Detector** — compares live signals to the baseline; outputs a tiered deviation.
- **Pattern-Absence Detector** — detects missing expected events (no kettle, no morning movement).
- **Risk Classifier** — combines signals into a severity tier (1 whisper → 4 emergency).
- **Conflict / Interaction Checker** — substance and timing conflicts (iron vs. calcium, metformin needs food).
- **LLM Inference** — small/local for chat; larger/cloud for summaries and harder judgments.

**Action.**
- **Voice Output / TTS Dialog** — bidirectional speech, age-tuned and calm.
- **Notification Dispatcher** — phone push, smart-display banner, watch tap.
- **Ambient Lights / Chimes** — soft escalation before alarms.
- **Emergency Caller** — regulated 911 dial-out with synthesized situation summary.
- **Contact-Tree Messenger** — SMS, voice, or WhatsApp to family/caregiver/counselor.
- **UI / Dashboard Renderer** — the live page the user opens to see logs, trends, history.
- **Tap-to-Confirm Prompt** — the "I'm okay" signal whose *absence* is itself meaningful.

**Integrations.**
- **Apple Health / Fitbit / Google Health Connect** — wearable data ingest.
- **Dexcom / Omron BP** — direct medical device feeds.
- **Google / Apple Calendar** — appointments, refill timing.
- **Pharmacy / Refill API** — auto-refill triggering.
- **EHR / FHIR Share** — push summaries to clinicians.
- **Twilio Voice + SMS** — outbound telephony.
- **Counselor / Officer Portal** — the channel for counselor notes and court-mandated case reports.

---

## Part 2 — How to read the scenario flows

Each scenario is a numbered trace. Lines look like this:

> 4. **[Tool: Risk Classifier]** combines the signals → returns *Tier 4: medical emergency*
> 5. **Orchestrator** routes to **Safety Agent** (primary), spawns **Companion Agent** in parallel

Bracketed names in brackets are **tools** being called. Bolded names without brackets are **agents**. The number is the order in time. When two agents run in parallel, both are listed and their sub-steps interleave.

Every scenario ends with a "Components used" summary so you can scan which sub-agents and tools each flow touches.

---

## Part 3 — Eleven scenarios

### Scenario 1 — Midnight fall (Eleanor, 70, lives alone)

*Setting:* 2:14 AM. Eleanor gets up to use the bathroom, loses balance, fractures her hip on the bedroom floor. She is conscious but cannot stand.*

1. **[Audio Listener]** picks up a heavy thump followed by a short cry.
2. **[Vision / Motion Sensor]** confirms a body on the floor, no upright movement for 8 seconds.
3. **[Wearable Vitals Stream]** reports HR spiking from 62 → 138 with an irregular rhythm.
4. **Orchestrator** receives three correlated signals, calls **[Risk Classifier]** with all three plus **[Personal Baseline Model]** (her sleep HR normally sits at 58–66) → returns *Tier 4: medical emergency*.
5. **Orchestrator** routes to **Safety Agent** (primary) and spawns **Companion Agent** in parallel.
6. **Safety Agent** calls **[Emergency Caller]** → dials 911 with an auto-generated summary: address, age, cardiac history, observed fall, current vitals.
7. **Safety Agent** calls **[Contact-Tree Messenger]** → calls daughter Maria first, then neighbor Tom as backup.
8. **Companion Agent** calls **[Voice Output / TTS]** → *"Eleanor, I'm here. I've called 911 and Maria. Help is 7 minutes away. Try not to move. Can you tell me where it hurts most?"*
9. **Companion Agent** writes the full dialogue to **[Conversation Memory]** + **[Event Log]** as it happens.
10. **Companion Agent** issues periodic status: *"Paramedics are 3 minutes away."* … *"They're at your door now — I've unlocked it."*
11. After EMS arrives, **Caregiver Liaison** calls **[EHR / FHIR Share]** → pushes the full incident timeline and vitals to her cardiologist.

**Components used.** Sub-agents: Safety, Companion, Caregiver Liaison. Tools: Audio Listener, Vision/Motion, Wearable Vitals, Risk Classifier, Personal Baseline, Emergency Caller, Contact-Tree Messenger, Voice/TTS, Conversation Memory, Event Log, EHR/FHIR Share.

---

### Scenario 2 — Silent morning (Eleanor, the day after)

*Setting:* Eleanor is home from the hospital. Normally she's up by 7:00, kettle on by 7:10, radio on by 7:15. It's 8:40 and none of that has happened.*

1. **[Environmental Sensors]** report no kettle activation, no fridge open.
2. **[Vision / Motion Sensor]** reports no movement out of the bedroom.
3. **[Pattern-Absence Detector]** compares to **[Personal Baseline Model]** → her absence-of-routine probability has crossed the 95th percentile.
4. **Orchestrator** receives the absence signal. **[Risk Classifier]** returns *Tier 1: soft check-in* (not enough to call yet, but worth checking).
5. **Orchestrator** routes to **Safety Agent**.
6. **Safety Agent** starts the gentle-escalation ladder:
   - 8:40 — **[Ambient Lights / Chimes]** raises bedroom lights to 30% with a soft chime.
   - 8:43 — **[Voice Output / TTS]** *"Good morning Eleanor, just checking in. Tap your bracelet when you're up."*
   - 8:47 — Still no **[Tap-to-Confirm]**. Lights to 60%, chime louder.
   - 8:50 — Still no response. **[Risk Classifier]** re-evaluated with the missed taps → escalates to *Tier 2*.
7. **Safety Agent** calls **[Contact-Tree Messenger]** → texts Maria: *"Mom hasn't responded to a check-in for 10 minutes. I'm continuing to escalate."*
8. 8:54 — vitals stream shows Eleanor is breathing and moving slightly. Audio picks up *"I'm okay, just slept in."* **[Wake-Word + STT]** captures it. **Safety Agent** stands down to *Tier 0*.
9. **[Event Log]** records the full sequence so the pattern itself can be analyzed later (was she dehydrated? new sleep med?).

**Components used.** Sub-agents: Safety. Tools: Environmental Sensors, Vision/Motion, Pattern-Absence Detector, Personal Baseline, Risk Classifier, Ambient Lights/Chimes, Voice/TTS, Tap-to-Confirm, Contact-Tree Messenger, Wake-Word + STT, Event Log.

---

### Scenario 3 — Sarah's morning vitamin stack (Sarah, 30, healthy)

*Setting:* 7:30 AM. Sarah's regimen today includes iron (every-other-day), vitamin D, calcium, B12, omega-3. The conflict: iron and calcium compete for absorption and shouldn't be taken together.*

1. 7:30 — **Reminder Agent** wakes up on the scheduled tick.
2. **Reminder Agent** reads from **[Regimen / Schedule Store]** → today is an iron day, she also takes calcium daily, and yesterday's **[Event Log]** shows she worked out.
3. **Reminder Agent** calls **[Conflict / Interaction Checker]** with the planned items → returns *"Iron and calcium must be ≥2 hours apart. Iron with food, not with coffee."*
4. **Reminder Agent** generates a split schedule: iron + D + B12 at 7:30 with breakfast; calcium + omega-3 at 10:00; magnesium at 9:30 PM.
5. **Reminder Agent** calls **[Notification Dispatcher]** → phone + watch ping: *"Iron, vitamin D, B12 — take with breakfast. Coffee in 30+ minutes."*
6. Sarah taps **[Manual Input / "I took it"]**. The tap writes to **[Event Log]**.
7. **Reminder Agent** updates the live **[UI / Dashboard Renderer]** — Sarah's vitamin tracker now shows three green checks for the morning.
8. 10:00 — second notification fires for calcium + omega-3, same loop.

**Components used.** Sub-agents: Reminder. Tools: Regimen/Schedule Store, Event Log, Conflict/Interaction Checker, Notification Dispatcher, Manual Input, UI/Dashboard Renderer.

---

### Scenario 4 — Margaret's blood pressure trending high (Margaret, 64)

*Setting:* Margaret has been logging her BP every morning. Today's reading is 152/94, the third elevated reading in five days. Her target range is <135/85.*

1. 8:00 — **Reminder Agent** prompts: *"Time for your morning blood pressure reading."* via **[Notification Dispatcher]**.
2. Margaret takes her reading on the Omron cuff. **[BP Cuff / Glucose Meter]** + **[Dexcom / Omron BP integration]** stream the result into **[Event Log]**.
3. **Health Agent** runs the new reading through **[Anomaly Detector]** with **[Personal Baseline Model]**. Single reading: borderline. But it pulls the last 7 days from **[Event Log]** and sees a clear upward trend.
4. **[Risk Classifier]** returns *Tier 2: clinician-worthy, not emergency*.
5. **Orchestrator** routes to **Health Agent** (primary) and spawns **Caregiver Liaison** (follow-up).
6. **Health Agent** calls **[Voice Output / TTS]** → *"Margaret, your reading is 152/94. That's the third elevated one this week. I'd like to send a note to Dr. Patel. Is that okay?"*
7. Margaret says yes. **[Wake-Word + STT]** captures the consent.
8. **Caregiver Liaison** calls **[LLM Inference]** to draft a clinical summary: last 7 BP readings, current medications from **[Regimen / Schedule Store]**, recent sodium-flagged days, sleep quality.
9. **Caregiver Liaison** calls **[EHR / FHIR Share]** → pushes the note to Dr. Patel's inbox via MyChart.
10. **Reminder Agent** queues a follow-up: *"Reduce sodium today; remind to recheck BP this evening."*
11. **[UI / Dashboard Renderer]** updates Margaret's weekly view with the new flag.

**Components used.** Sub-agents: Health, Reminder, Caregiver Liaison. Tools: Notification Dispatcher, BP Cuff, Dexcom/Omron integration, Event Log, Anomaly Detector, Personal Baseline, Risk Classifier, Voice/TTS, Wake-Word + STT, LLM Inference, Regimen/Schedule Store, EHR/FHIR Share, UI/Dashboard Renderer.

---

### Scenario 5 — "Did I take my medicine?" (Margaret)

*Setting:* 11:00 AM. Margaret is fuzzy on whether she took her morning BP pill.*

1. Margaret: *"Guardian, did I take my blood pressure pill this morning?"*
2. **[Wake-Word + STT]** captures the question.
3. **Orchestrator** routes to **Companion Agent**.
4. **Companion Agent** queries **[Event Log]** for today's medication entries.
5. Found: *7:14 AM — BP pill, tap-confirmed.*
6. **Companion Agent** calls **[Voice Output / TTS]** → *"Yes — you took it at 7:14 this morning, right after breakfast."*
7. **[Conversation Memory]** logs the exchange so a future "did I ask about my pill today?" also works.

**Components used.** Sub-agents: Companion. Tools: Wake-Word + STT, Event Log, Voice/TTS, Conversation Memory.

---

### Scenario 6 — "What happened this week?" (Eleanor, post-hospital)

*Setting:* Sunday evening. Eleanor's daughter is coming over and Eleanor wants to recap her week.*

1. Eleanor: *"Guardian, can you tell me what happened this week?"*
2. **[Wake-Word + STT]** captures the query.
3. **Orchestrator** routes to **Companion Agent**.
4. **Companion Agent** pulls the last 7 days from **[Event Log]** and **[Conversation Memory]**.
5. **Companion Agent** calls **[LLM Inference]** (larger model) to compress the week into a gentle narrative — keeping clinical events but smoothing out the noise.
6. **Companion Agent** calls **[Voice Output / TTS]** → *"Tuesday you came home from the hospital. Maria visited Wednesday and Saturday. Your BP has been steady around 128 over 78. You missed one dose of your evening pill on Thursday — I reminded you and you took it twenty minutes later. You walked a little further each day. Tonight Maria is coming for dinner at 6."*
7. **[UI / Dashboard Renderer]** also surfaces a printable version Eleanor can show Maria.

**Components used.** Sub-agents: Companion. Tools: Wake-Word + STT, Event Log, Conversation Memory, LLM Inference, Voice/TTS, UI/Dashboard Renderer.

---

### Scenario 7 — Depressed young user, downward slide (David, 24)

*Setting:* David has been logging his mood daily for six weeks. The last 9 days have all been ≤3/10. Tonight he searches "is it worth it" in his journal and his voice during a Guardian check-in was flat and slow.*

1. Every morning **Companion Agent** runs the mood check-in via **[Voice/TTS]** + **[Manual Input]** mood slider. Results write to **[Event Log]**.
2. **Behavior Agent** runs nightly: pulls the 14-day mood window, voice prosody features, sleep/activity from **[Wearable Vitals Stream]**, compares to **[Personal Baseline Model]**.
3. Tonight: 9 consecutive low days + slowed speech + reduced movement + a concerning phrase typed in the journal. **Behavior Agent** calls **[Risk Classifier]** → returns *Tier 3: at-risk, not imminent*.
4. **Orchestrator** routes to **Behavior Agent** (primary), spawns **Companion Agent** (gentle outreach), puts **Safety Agent** on standby with a lowered escalation threshold for the night.
5. **Companion Agent** calls **[Voice/TTS]** → *"David, I've noticed the last week has been hard. I'm here. Would you like to talk for a few minutes, or just have me read something calming?"* Approach is gentle, not alarming.
6. The conversation is captured to **[Conversation Memory]** with elevated sensitivity flags.
7. **Behavior Agent** asks David's standing consent (set at onboarding) about looping in his therapist. If yes → **Caregiver Liaison** uses **[Counselor / Officer Portal]** to send a "trend alert" note — not the transcript, just the pattern.
8. If David refuses or doesn't respond, the threshold for any future Safety-tier event drops; a hotline contact is pre-loaded onto the home screen via **[UI / Dashboard Renderer]**.
9. **[Event Log]** records every step, including consent decisions, for any future clinical review.

**Components used.** Sub-agents: Behavior, Companion, Safety (standby), Caregiver Liaison. Tools: Voice/TTS, Manual Input, Event Log, Wearable Vitals, Personal Baseline, Risk Classifier, Conversation Memory, Counselor/Officer Portal, UI/Dashboard Renderer.

---

### Scenario 8 — Court-mandated anger management (Marcus, 38)

*Setting:* Marcus is on court-ordered behavioral monitoring after a domestic incident. He is at home, on a video call with his ex-partner, and the conversation is escalating.*

1. **[Audio Listener]** continuously runs voice-stress and volume analysis — court-mandated, with Marcus's signed consent on file.
2. Voice volume rises sharply, pitch becomes strained, pace accelerates. **[Audio Listener]** flags an excursion.
3. **Behavior Agent** compares to Marcus's **[Personal Baseline Model]** (his calm vs. stressed voice profile, learned over weeks).
4. **[Risk Classifier]** returns *Tier 2: early-warning, intervene now*.
5. **Orchestrator** routes to **Behavior Agent** (primary) and puts **Safety Agent** on a lowered threshold.
6. **Behavior Agent** invokes the pre-trained de-escalation routine from **[Regimen / Schedule Store]**: **[Ambient Lights]** dims and shifts to warm; **[Voice/TTS]** in a calm tone — *"Marcus, you've used the breathing technique before. Let's pause for thirty seconds. Breathe with me."*
7. **[Event Log]** records the excursion, the intervention, and Marcus's response — this log is part of his court record.
8. If voice levels keep climbing, **[Risk Classifier]** escalates to *Tier 3*. **Behavior Agent** stops attempting de-escalation and **Caregiver Liaison** uses **[Counselor / Officer Portal]** to alert his probation officer with the timestamped audio-feature trace (not raw audio).
9. If physical sounds (impact, breaking glass) occur, **Safety Agent** takes over and uses **[Emergency Caller]** directly.

**Components used.** Sub-agents: Behavior, Safety (standby/takeover), Caregiver Liaison. Tools: Audio Listener, Personal Baseline, Risk Classifier, Regimen/Schedule Store, Ambient Lights, Voice/TTS, Event Log, Counselor/Officer Portal, Emergency Caller.

---

### Scenario 9 — Domestic violence early signs (couple)

*Setting:* A couple has opted into shared monitoring as part of counseling. One evening, an argument escalates quickly — shouting, then a sound of something thrown.*

1. **[Audio Listener]** flags rapidly rising voices, both speakers showing stress markers — well above their joint **[Personal Baseline Model]**.
2. **Behavior Agent** opens an "escalation watch."
3. **[Audio Listener]** picks up an impact + glass.
4. **[Risk Classifier]** jumps to *Tier 4: immediate harm risk*.
5. **Orchestrator** routes to **Safety Agent** (primary), **Behavior Agent** (audit), **Caregiver Liaison** (follow-up).
6. **Safety Agent** calls **[Voice/TTS]** with a clear, calm intervention voice — *"This is Guardian. The situation has escalated. I will call for help in 20 seconds unless someone says 'we're okay.'"* (Pre-agreed wording, set up during counseling onboarding.)
7. No response, or a "yes call them" is heard. **Safety Agent** calls **[Emergency Caller]** with **[Geolocation]** + the audio-feature timeline as context.
8. **Caregiver Liaison** notifies the assigned counselor via **[Counselor / Officer Portal]**.
9. **[Event Log]** records the audio features (not raw audio), the wording exchanged, and the intervention sequence — tamper-evident copy retained for legal use.

**Components used.** Sub-agents: Behavior, Safety, Caregiver Liaison. Tools: Audio Listener, Personal Baseline, Risk Classifier, Voice/TTS, Emergency Caller, Geolocation, Counselor/Officer Portal, Event Log.

---

### Scenario 10 — Child with a careless caregiver (Theo, 14 months)

*Setting:* Theo's grandmother is the regular daytime caregiver. Her schedule (logged with consent) includes a feeding at 12:30. It's 1:45 and the regimen window has been missed, and Theo has been crying continuously for over 15 minutes.*

1. **[Pattern-Absence Detector]** flags the missed feeding window from **[Regimen / Schedule Store]**.
2. **[Audio Listener]** has been logging Theo's crying — duration is now in the high-distress band per **[Personal Baseline Model]**.
3. **[Environmental Sensors]** show the grandmother has been on the couch (no fridge or kitchen activity) for 45 minutes — possibly asleep.
4. **Behavior Agent** correlates the three signals → returns a *welfare concern* (not yet an emergency).
5. **Orchestrator** routes to **Behavior Agent** (primary) and stages **Caregiver Liaison** for next-step contact.
6. **Behavior Agent** calls **[Voice/TTS]** in the living room — *"Hi Grandma, just a check — Theo seems hungry. His next feeding was at 12:30."* (First, wake the caregiver gently.)
7. If she responds and acts: incident logged, no further action.
8. If no response in 3 minutes: **Caregiver Liaison** calls **[Contact-Tree Messenger]** → texts and then calls the parent: *"Theo's 12:30 feeding hasn't happened and he's been crying for 18 minutes. Grandma isn't responding to in-home prompts."*
9. Parent receives a live feed link via **[UI / Dashboard Renderer]** (consent-gated).
10. Only if no human responds and the distress signals continue does **Safety Agent** consider escalating to authorities. The bar is intentionally high — false reports do enormous harm.

**Components used.** Sub-agents: Behavior, Caregiver Liaison, Safety (last-resort). Tools: Pattern-Absence, Regimen/Schedule Store, Audio Listener, Personal Baseline, Environmental Sensors, Voice/TTS, Contact-Tree Messenger, UI/Dashboard Renderer, Event Log.

---

### Scenario 11 — Heart rate anomaly during sleep (Eleanor, post-recovery)

*Setting:* 3:20 AM. Eleanor is sleeping. Her wearable HR briefly drops to 38, then jumps to 124, then settles erratically.*

1. **[Wearable Vitals Stream]** sees the excursion.
2. **Health Agent** compares to **[Personal Baseline Model]** — Eleanor's resting nocturnal HR is 54–62. This is significantly outside. **[Anomaly Detector]** confirms a high-deviation event.
3. **[Risk Classifier]** returns *Tier 2: medical-significance, non-emergency* (no other distress signals: no fall, no calling out, vision shows her in bed).
4. **Orchestrator** routes to **Health Agent** (primary) and arms **Safety Agent** for the next 30 minutes with a lowered threshold.
5. **Health Agent** does *not* wake her abruptly. It uses **[Ambient Lights]** to glow softly at 5% and **[Voice/TTS]** in low volume — *"Eleanor, this is Guardian. Your heart rhythm looked unusual. Can you tap your bracelet so I know you're okay?"*
6. Eleanor stirs, taps **[Tap-to-Confirm]**. **Companion Agent** picks up: *"How are you feeling — any pain or shortness of breath?"* Eleanor says she's fine, just dreamt vividly.
7. **[Conversation Memory]** + **[Event Log]** capture the exchange and reading.
8. By morning, **Caregiver Liaison** calls **[EHR / FHIR Share]** → forwards the rhythm strip and her response to her cardiologist as an FYI, not an alarm.
9. **Health Agent** updates Eleanor's **[Personal Baseline Model]** with the new data point (and flags it for clinical review before letting it weight the baseline too heavily).

**Components used.** Sub-agents: Health, Companion, Safety (armed), Caregiver Liaison. Tools: Wearable Vitals, Personal Baseline, Anomaly Detector, Risk Classifier, Ambient Lights, Voice/TTS, Tap-to-Confirm, Conversation Memory, Event Log, EHR/FHIR Share.

---

## Cross-scenario observations

A few patterns are worth calling out because they justify the architecture:

**Tools are reused, sub-agents specialize.** Voice/TTS appears in 10 of 11 scenarios. Event Log appears in all 11. Personal Baseline appears in 9. Emergency Caller appears in 3 (and only in scenarios where Safety Agent is in charge). The tool layer earns its keep by being the common substrate; the sub-agents earn their keep by knowing *when* and *how* to use each tool for their domain.

**Severity is a tool output, not a hardcoded rule.** The Risk Classifier produces a tier, and the orchestrator decides what action level matches that tier. Every scenario above goes through this exact pattern — that's why the same fall sensor can trigger a soft check-in (Scenario 2) or a 911 call (Scenario 1) depending on context.

**Multiple sub-agents in parallel is the norm, not the exception.** A real fall isn't "Safety Agent does its thing." It's Safety calling 911, Companion talking to the user, and Caregiver Liaison preparing the clinical handoff — concurrent threads, coordinated by the orchestrator.

**Gentle escalation is a first-class behavior.** Five of the eleven scenarios (silent morning, BP trend, depressed user, anger management, sleep HR anomaly) start at a low tier and may never escalate. The system is designed so that not-an-emergency is its most common output, and that path is just as well-supported as the loud one.

**Audit logs are non-negotiable in any scenario with legal weight.** Scenarios 8, 9, and 10 all rely on the Event Log being tamper-evident — that single design choice is what makes Guardian usable in court-mandated, child-welfare, and domestic-violence contexts.
