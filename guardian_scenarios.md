# Guardian — Components & Scenario Playbook

Companion document to `guardian_architecture.md`. This file describes each component in plain language and walks through nineteen scenarios end-to-end, showing which sub-agents and tools are invoked and in what order.

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

## Part 3 — Nineteen scenarios

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

### Scenario 12 — Stroke FAST exam mid-conversation (Robert, 68)

*Setting:* 3:15 PM. Robert is on the phone with his daughter when his speech suddenly slurs and he can't find the word "newspaper." The call drops.*

1. **[Audio Listener]** picks up slurred articulation mid-sentence + a long silence.
2. **[Wearable Vitals Stream]** shows a small but real BP spike, HR climbing.
3. **Health Agent** runs the speech sample through a prosody-anomaly check against **[Personal Baseline Model]** — slurring is well outside Robert's normal articulation.
4. **[Risk Classifier]** returns *Tier 3: significant concern, possible TIA/stroke* — pre-emergency.
5. **Orchestrator** routes to **Safety Agent** (primary) and spawns **Companion Agent** for the verbal assessment.
6. **Companion Agent** initiates a verbal **FAST** exam through **[Voice/TTS]**:
   - *"Robert, this is Guardian. Can you smile for me — just say 'I'm smiling'?"* (Face)
   - *"Now lift both arms straight out in front of you."* — **[Vision / Motion Sensor]** watches for drift. (Arms)
   - *"Repeat after me: The sky is blue today."* — **[Audio Listener]** compares to baseline articulation. (Speech)
7. Two of three are abnormal: speech slurred, left arm drift visible.
8. **[Risk Classifier]** re-evaluates → *Tier 4: stroke in progress. Time is brain.*
9. **Safety Agent** calls **[Emergency Caller]** → 911 with: cardiac history, current vitals, **time of symptom onset = 3:15 PM** (logged by Audio Listener), FAST result.
10. **Safety Agent** calls **[Contact-Tree Messenger]** → daughter notified, brother dispatched to the house.
11. **Companion Agent** keeps Robert calm and prevents him from moving — *"Help is on the way in 6 minutes. Stay seated. Don't eat or drink anything. I'm here."*
12. **Caregiver Liaison** calls **[EHR / FHIR Share]** → pushes timeline + FAST result + vitals to the receiving stroke center *before* the ambulance arrives, shaving minutes off door-to-needle.

**Components used.** Sub-agents: Safety, Health, Companion, Caregiver Liaison. Tools: Audio Listener, Wearable Vitals, Personal Baseline, Risk Classifier, Vision/Motion, Voice/TTS, Emergency Caller, Contact-Tree Messenger, EHR/FHIR Share, Event Log.

---

### Scenario 13 — Hypoglycemia in a diabetic (James, 52, type 1)

*Setting:* 4:30 PM. James took insulin with lunch but skipped his usual mid-afternoon snack to push through a work deadline. His Dexcom hasn't issued an alarm yet, but his behavior is changing.*

1. **[Audio Listener]** notices James's tone has gone mildly slurred and unusually irritable on a call.
2. **[Wearable Vitals Stream]** shows HR climbing, fine tremor in motion data.
3. **[Dexcom / Omron BP integration]** streams live glucose: **62 mg/dL and falling**.
4. **Health Agent** correlates the three: low glucose + sympathetic activation + speech anomaly.
5. **[Risk Classifier]** returns *Tier 2: act now, not 911 yet*.
6. **Orchestrator** routes to **Health Agent** (primary) + **Companion Agent** (talk to him).
7. **Companion Agent** calls **[Voice/TTS]** in a direct, simple tone — *"James, your glucose is 62 and dropping. You need fast carbs right now. There's juice in the fridge."*
8. **[Environmental Sensors]** confirm the fridge opens within 90 seconds.
9. **Health Agent** monitors the CGM — glucose stabilizes at 78 within 12 minutes, then climbs to 95.
10. **Fallback path:** if James had not responded in 3 minutes, **[Risk Classifier]** would escalate to *Tier 3*. **Safety Agent** would take over: *"James — if you can hear me, tap your bracelet. If no tap in 60 seconds, I'm calling for help."*
11. **[Event Log]** captures the episode and response time. **Caregiver Liaison** includes it in the next monthly endocrinologist summary via **[EHR / FHIR Share]**.

**Components used.** Sub-agents: Health, Companion, Safety (standby), Caregiver Liaison. Tools: Audio Listener, Wearable Vitals, Dexcom/Omron, Risk Classifier, Voice/TTS, Environmental Sensors, Tap-to-Confirm, Event Log, EHR/FHIR Share.

---

### Scenario 14 — Anaphylactic reaction (Priya, 32, known peanut allergy)

*Setting:* 7:50 PM. Priya is eating takeout she ordered as "no nuts." Within five minutes she starts coughing repeatedly and her voice tightens.*

1. **[Audio Listener]** picks up repeated coughing → throat-clearing → audible wheeze.
2. **[Wearable Vitals Stream]** shows HR jumping 72 → 118, SpO₂ dropping 98% → 93%.
3. **Health Agent** cross-references the patient profile — *known peanut allergy, EpiPen prescribed, kept in kitchen drawer*.
4. **[Risk Classifier]** returns *Tier 4: anaphylaxis in progress*.
5. **Orchestrator** routes to **Safety Agent** (primary) and **Companion Agent** (direct first-aid coaching) — in parallel.
6. **Companion Agent** calls **[Voice/TTS]** with clear, urgent diction — *"Priya, this looks like an allergic reaction. Your EpiPen is in the kitchen drawer next to the sink. Inject it in your outer thigh, hold for 10 seconds. Do it now."*
7. **Safety Agent** calls **[Emergency Caller]** *in parallel* — does **not** wait to see if she can self-administer. The profile says EpiPens always require hospital follow-up.
8. **Safety Agent** uses **[Environmental Sensors / smart-home tool]** to unlock the front door for paramedics.
9. **Companion Agent** keeps her talking and lying flat — *"I called 911. They're 4 minutes away. Stay lying down, legs raised. Tell me how your breathing feels."*
10. **[Audio Listener]** monitors breath sounds — wheeze begins decreasing within 90 seconds of EpiPen use.
11. **Caregiver Liaison** calls **[EHR / FHIR Share]** → pushes allergen, EpiPen-administered timestamp, and current vitals trajectory to the receiving ER.

**Components used.** Sub-agents: Safety, Companion, Health, Caregiver Liaison. Tools: Audio Listener, Wearable Vitals, Risk Classifier, Voice/TTS, Emergency Caller, Environmental Sensors, EHR/FHIR Share, Event Log.

---

### Scenario 15 — Multilingual 911 handoff (Mr. Chen, 79, Mandarin-primary)

*Setting:* Continuation of an acute scenario. The ambulance has just arrived at Mr. Chen's home. He primarily speaks Mandarin. The paramedic at the door speaks English. Mr. Chen's daughter set up live-interpretation consent at onboarding.*

1. **[Audio Listener]** detects the paramedic's voice at the door + a new English voice asking questions.
2. **Caregiver Liaison** reads the consent flag: *"If paramedics arrive and patient's primary language ≠ first responder's language, act as live interpreter."*
3. **Caregiver Liaison** invokes the local **SeamlessM4T** speech-to-speech translation pipeline (via **[LLM Inference]** — speech model on DGX, no cloud).
4. **[Voice/TTS]** in the room operates bidirectionally now:
   - Paramedic: *"Sir, can you tell me where it hurts?"*
   - Guardian (Mandarin): 「先生，您能告訴我哪裡疼嗎？」
   - Mr. Chen (Mandarin): 「我的胸口，半個小時前開始的。」
   - Guardian (English): *"My chest — it started about half an hour ago."*
5. **Caregiver Liaison** simultaneously pushes the structured incident summary to the paramedic's tablet via **[Counselor / Officer Portal — paramedic variant]**: age, conditions (atrial fibrillation, hypertension), current medications, allergies, last vitals trend, plus the bilingual transcript of the last 5 minutes.
6. **[Event Log]** records every interpreted exchange. Mr. Chen's daughter, who set the consent, receives a copy.
7. Once the paramedic confirms communication is established, **Companion Agent** offers to continue translating into the ambulance via the daughter's phone.

**Components used.** Sub-agents: Caregiver Liaison, Companion. Tools: Audio Listener, LLM Inference (translation model), Voice/TTS, Counselor/Officer Portal, Event Log.

---

### Scenario 16 — Third-trimester preeclampsia warning (Aisha, 33, 31 weeks pregnant)

*Setting:* 6:00 AM. Aisha wakes with a severe headache and tells Guardian her vision is "spotty." Standard pregnancy aches, or something serious?*

1. Aisha: *"Guardian, I have this awful headache and I can't see right."*
2. **[Wake-Word + STT]** captures the report.
3. **Orchestrator** routes to **Health Agent** (primary). The pregnancy profile flag elevates default priority.
4. **Health Agent** runs a structured pregnancy-warning-signs interview through **Companion Agent** + **[Voice/TTS]**:
   - "When did the headache start?" — *"About an hour ago. It woke me up."*
   - "Where in your head?" — *"Front, throbbing."*
   - "Any swelling in your hands or face this morning?" — *"My rings won't fit."*
   - "Any pain in your upper belly?" — *"A little, on the right."*
5. **[Risk Classifier]** combines: severe headache + visual changes + facial swelling + RUQ pain → *Tier 4: probable preeclampsia/eclampsia*.
6. **Orchestrator** routes to **Safety Agent**.
7. **Reminder Agent** pulls Aisha's last BP reading from **[BP Cuff / Glucose Meter]** event log: **158/102 yesterday evening** — a reading she didn't flag.
8. **Safety Agent** calls **[Emergency Caller]** → 911 with: 33yo, 31 weeks pregnant, suspected preeclampsia, BP 158/102 from yesterday.
9. **Companion Agent** stays with Aisha — *"An ambulance is coming. Lie on your left side. Don't eat or drink anything. Your partner is being called now."*
10. **Caregiver Liaison** calls **[EHR / FHIR Share]** → pushes the symptom assessment and BP trend to her OB practice. They begin notifying the high-risk team at the receiving hospital before Aisha is loaded into the ambulance.

**Components used.** Sub-agents: Safety, Health, Companion, Reminder, Caregiver Liaison. Tools: Wake-Word + STT, Voice/TTS, Risk Classifier, Emergency Caller, BP Cuff, Event Log, EHR/FHIR Share.

---

### Scenario 17 — PTSD nightmare intervention (Daniel, 41, combat veteran)

*Setting:* 3:40 AM. Daniel is asleep but his breathing has become rapid and shallow; he begins vocalizing — short, panicked sounds. He opted into night monitoring after his VA counselor recommended it.*

1. **[Audio Listener]** classifies the vocalizations as distress-during-sleep, matching Daniel's stored pattern.
2. **[Wearable Vitals Stream]** shows HR jumping 58 → 112, HRV collapsing.
3. **Health Agent** confirms the deviation against **[Personal Baseline Model]**.
4. **[Risk Classifier]** returns *Tier 1: handle in-room, gently*.
5. **Orchestrator** routes to **Companion Agent**.
6. **Companion Agent** runs the pre-agreed grounding protocol stored in **[Regimen / Schedule Store]**:
   - **[Ambient Lights]** glow at 8% in a warm tone.
   - **[Voice/TTS]** in his wife's pre-cloned voice (consent given at onboarding) — *"Daniel, you're home. You're in bed. It's Tuesday. Three-forty AM. I'm here."* Specific, calm, oriented to time and place — the technique he uses in therapy.
7. Daniel stirs but does not fully wake. HR begins dropping.
8. If the protocol fails (HR keeps rising or he wakes panicking), **Companion Agent** escalates to a guided breathing exercise.
9. **[Conversation Memory]** + **[Event Log]** log the episode as features-only (Daniel's consent: no raw audio retained).
10. Monthly, **Caregiver Liaison** pushes aggregated trends to his VA counselor via **[Counselor / Officer Portal]** — frequency, time-of-night clustering, intervention success rate. No transcripts.

**Components used.** Sub-agents: Companion, Health, Caregiver Liaison. Tools: Audio Listener, Wearable Vitals, Personal Baseline, Risk Classifier, Regimen/Schedule Store, Ambient Lights, Voice/TTS, Conversation Memory, Event Log, Counselor/Officer Portal.

---

### Scenario 18 — Early cognitive decline (Frank, 72, lives with wife)

*Setting:* Frank uses Guardian for medication reminders and daily conversation. Over six months, subtle changes accumulate that no single conversation would catch.*

1. Every interaction with Frank writes to **[Event Log]** and **[Conversation Memory]**, with prosody features.
2. **Behavior Agent** runs a monthly longitudinal job: pulls 30 days of conversational data and computes features against **[Personal Baseline Model]** —
   - vocabulary diversity (type-token ratio)
   - average response latency
   - frequency of *"I don't remember"* / *"what was I saying"*
   - performance on the embedded micro-tests Companion Agent runs (a casual *"what did you have for breakfast?"* cross-checked against **[Environmental Sensors]** kitchen activity)
3. Months 1–4: stable. Month 5: response latency up 22%, vocabulary diversity down 8%. Month 6: same trend, plus 3 instances of repeating a story within 24 hours.
4. **[Anomaly Detector]** flags the trend as *significant longitudinal decline*.
5. **[Risk Classifier]** returns *Tier 1: clinician follow-up, not urgent*.
6. **Orchestrator** routes to **Caregiver Liaison** and checks Frank's standing consent for cognitive sharing.
7. Frank's consent (set at onboarding): *yes, share cognitive trends with my GP and my wife.*
8. **Caregiver Liaison** calls **[LLM Inference]** (larger model) to generate a structured cognitive summary: anonymized feature trends, consented illustrative examples, no raw transcripts.
9. **Caregiver Liaison** calls **[EHR / FHIR Share]** → routes the summary to Frank's GP.
10. **[UI / Dashboard Renderer]** surfaces a soft prompt for Frank: *"Your next checkup might be a good time to discuss memory. Want help preparing a few notes?"*
11. **Companion Agent** offers to help Frank journal what he himself has noticed — patient-led, not surveillance-feeling.

**Components used.** Sub-agents: Behavior, Companion, Caregiver Liaison. Tools: Event Log, Conversation Memory, Personal Baseline, Anomaly Detector, Risk Classifier, LLM Inference, EHR/FHIR Share, UI/Dashboard Renderer, Voice/TTS, Environmental Sensors.

---

### Scenario 19 — Caregiver burnout (Lisa, 51, primary caregiver for her mother)

*Setting:* Lisa lives with her 78-year-old mother who has Parkinson's. Lisa uses Guardian both to monitor her mother and (with her own consent) to monitor her own wellbeing — she set this up after a near-miss with a missed medication.*

1. **Behavior Agent** runs weekly on Lisa's data: daily mood logs (**[Manual Input / mood slider]**), voice features from her own interactions with Guardian (**[Audio Listener]** — features only), sleep from **[Wearable Vitals Stream]**, and her interaction patterns with the system (curt replies, ignored prompts).
2. Over four weeks: sleep degraded from 7.2h avg → 5.4h. Mood trending downward. Voice features showing flat affect. Manual-input completion rate falling — she's losing the energy to log.
3. **[Anomaly Detector]** + **[Personal Baseline Model]** flag the trajectory.
4. **[Risk Classifier]** returns *Tier 1: caregiver welfare concern* — Lisa is not in crisis, she is heading toward one.
5. **Orchestrator** routes to **Companion Agent**. The consent profile flags Lisa as the primary subject of this interaction, not background.
6. **Companion Agent** calls **[Voice/TTS]** in a private moment — *"Lisa, I've been keeping track of how you've been doing, not just your mom. The last few weeks look hard. Would you be open to hearing what I've noticed?"*
7. Lisa says yes. **Companion Agent** shares specifics: sleep, mood, the missed lunches.
8. **Companion Agent** offers concrete options stored in **[Regimen / Schedule Store]**: the local respite-care list Lisa pre-loaded, her own GP's number, the Parkinson's caregiver support group meeting tomorrow.
9. **Caregiver Liaison** (with consent) sends a gentle note to Lisa's sister via **[Contact-Tree Messenger]** — *"Lisa might appreciate some help this week. No emergency, just a heads-up."*
10. **[Event Log]** records the intervention. **Reminder Agent** queues a one-week follow-up check-in.

**Components used.** Sub-agents: Behavior, Companion, Caregiver Liaison, Reminder. Tools: Manual Input, Audio Listener, Wearable Vitals, Personal Baseline, Anomaly Detector, Risk Classifier, Voice/TTS, Regimen/Schedule Store, Contact-Tree Messenger, Event Log.

---

## Cross-scenario observations

A few patterns are worth calling out because they justify the architecture:

**Tools are reused, sub-agents specialize.** Voice/TTS appears in 18 of 19 scenarios. Event Log appears in all 19. Personal Baseline appears in 14. Emergency Caller appears in 6 (and only in scenarios where Safety Agent is in charge). The tool layer earns its keep by being the common substrate; the sub-agents earn their keep by knowing *when* and *how* to use each tool for their domain.

**Severity is a tool output, not a hardcoded rule.** The Risk Classifier produces a tier, and the orchestrator decides what action level matches that tier. Every scenario above goes through this exact pattern — that's why the same fall sensor can trigger a soft check-in (Scenario 2) or a 911 call (Scenario 1) depending on context, and the same speech-anomaly trigger can mean *low blood sugar — get juice* (Scenario 13) or *stroke — call 911* (Scenario 12) depending on the surrounding signals.

**Multiple sub-agents in parallel is the norm, not the exception.** A real fall isn't "Safety Agent does its thing." It's Safety calling 911, Companion talking to the user, and Caregiver Liaison preparing the clinical handoff — concurrent threads, coordinated by the orchestrator. The anaphylaxis scenario (14) calls 911 and coaches EpiPen use *simultaneously* — neither waits for the other.

**Gentle escalation is a first-class behavior.** Nine of the nineteen scenarios (silent morning, BP trend, depressed user, anger management, sleep HR anomaly, PTSD nightmare, cognitive decline, caregiver burnout, the no-911 branch of hypoglycemia) start at a low tier and may never escalate. The system is designed so that not-an-emergency is its most common output, and that path is just as well-supported as the loud one.

**Audit logs are non-negotiable in any scenario with legal weight.** Scenarios 8, 9, and 10 (court-mandated monitoring, domestic violence, child welfare) rely on the Event Log being tamper-evident — and scenarios 12, 14, and 16 lean on the same property for the clinical timeline (symptom-onset timestamp, EpiPen administration time, BP trend) that gets pushed to receiving hospitals via FHIR. That single design choice is what makes Guardian usable in both legally-charged and high-acuity clinical contexts.

**Time-of-onset matters as much as the event itself.** Scenarios 12 (stroke), 14 (anaphylaxis), and 16 (preeclampsia) all benefit from the Audio Listener / Wearable Stream having silently been recording *before* the event was recognized — so the symptom-onset timestamp handed to the receiving hospital is real, not estimated. Continuous on-device sensing is what makes that possible without privacy compromise.

**Caregiver Liaison plus EHR/FHIR Share is Guardian's secret weapon.** In 8 of the 19 scenarios (1, 4, 11, 12, 13, 14, 16, 18), a clinical summary lands in the right clinician's inbox without the patient having to remember anything, recount anything, or fill out a form. Half of clinical-care quality is getting the right context to the right human at the right time — Guardian automates the last mile of that.

**Translation as a peer integration, not a special case.** Scenario 15 reuses the same Voice/TTS + Caregiver Liaison + Event Log primitives as every other scenario; the only new thing is which model the LLM Inference tool wraps. That's the test of a good tool layer — a wildly different scenario should require no architectural change.
