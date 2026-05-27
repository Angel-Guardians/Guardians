# Guardian: Home Emergency AI Companion

> An always-on, fully local AI agent that lives in your home, monitors for emergencies, keeps you calm, and dispatches help — without ever sending your personal health data to the cloud.

**Hackathon Track:** AI Agents & Automation
**Hardware:** NVIDIA DGX Spark (GB10 Grace Blackwell Superchip)
**Deployment:** In the patient's home
**Inference:** Fully local (no cloud API calls)
**Privacy:** On-device only, PHIPA-compliant design

---

## The Problem

Many medical emergencies at home go undetected for hours because no one is there to help. Toronto Paramedic Services responded to **350,000+ calls in 2024**, a large share from vulnerable people living alone. The gap between *something going wrong* and *help arriving* is where lives are lost.

Guardian closes that gap. It is the trusted presence in the room when no one else is.

---

## How Guardian Works

Guardian operates in two modes simultaneously.

### Passive Mode
Guardian listens to ambient audio in the home, detects distress signals (keywords, conversational patterns, prolonged silence, abnormal vitals), and proactively checks in. If the patient cannot respond or the situation is severe, Guardian informs an emergency contact or dispatches official medical services.

### Active Mode
The patient calls out to Guardian directly ("Hey Guardian, I'm scared", "Guardian, I fell"). Guardian asks structured triage questions, assesses urgency using the **Canadian Triage and Acuity Scale (CTAS)**, and takes graduated action — from a calming conversation, to notifying a family member, to dispatching an ambulance.

In **both** modes, Guardian generates a personalized incident report so first responders walk in already knowing the patient's history, medications, allergies, and what just happened.

---

## Three-Tier Agent Architecture

Guardian is not one monolithic agent — it's an **Orchestrator** routing to **six specialist sub-agents**, each owning a domain of care, all sharing a common toolbelt.

### Tier 1 — Orchestrator
The single point that hears every signal (voice, vitals, sensor reading, schedule tick, UI command) and decides *which sub-agent owns this*, in what mode, and at what severity. It enforces escalation policy across agents — e.g., a Health Agent vitals anomaly the patient can't explain triggers a Safety Agent escalation.

### Tier 2 — Specialist Sub-Agents

| Sub-Agent | Owns | Example scenarios |
|---|---|---|
| **Safety Agent** | Falls, panic, violence, immediate physical danger | The fall, silent-morning, "Guardian, I'm scared", domestic-violence early-warning |
| **Health Agent** | Vitals, anomalies, chronic-condition monitoring | Cardiac baseline deviation, Margaret's chronic panel, BP/glucose trends, slow-burn arm pain |
| **Reminder Agent** | Medications, vitamins, appointments, refill watch | Sarah's iron-vs-calcium timing, vitamin schedule UI, missed-med detection |
| **Companion Agent** | Conversation, recall, mood, calm-keeping | Memory recap ("what happened this week?"), mood check-ins, soothing during crisis |
| **Behavior Agent** | Anger, addiction, depression, court-mandated monitoring | Court-ordered anger monitoring, depressed-young-adult, addiction relapse signals |
| **Caregiver Liaison** | Reports, summaries, looping humans in | Weekly physician summary, counselor notes, probation-officer pings, family alerts |

### Tier 3 — Shared Tool Bus
Every sub-agent can call any tool. Tools are **stateless capabilities**, grouped into four buckets:

- **Sensing** — audio listener, wearable vitals stream, BP/glucose meters, vision/motion, geolocation, wake-word + STT, environmental sensors, manual input (tap, mood).
- **Memory & Reasoning** — event log (append-only), personal baseline model, conversation memory, regimen/schedule store, anomaly detector, pattern-absence detector, tiered risk classifier, drug-interaction check, LLM inference (small/large).
- **Action** — voice output / TTS dialog, notification dispatcher, ambient lights / chimes, emergency caller (911), contact-tree messenger, UI dashboard, tap-to-confirm prompts. Output is **tiered**: whisper → nudge → alarm → call.
- **Integrations** — Apple Health / Fitbit, Dexcom / Omron BP, Google / Apple Calendar, pharmacy / refill API, EHR / FHIR share, Twilio voice + SMS, counselor / probation-officer portals. Recipient routing varies per persona and consent mode.

> **Design principle:** Tools are stateless capabilities. Sub-agents own the policy. Orchestrator owns the user.

---

## Core Features

1. **Live conversation transcription & medical summary** — structured clinical notes and a paramedic handoff summary, generated automatically from the patient's own words.
2. **On-device personal medical database** — conditions, allergies, medications, baseline vitals, emergency contacts. No EHR integration, no cloud sync. Data never leaves the home.
3. **AI urgency triage & escalation** — smart escalation path (silent check-in → spoken check-in → family alert → 911), scored using the **CTAS** framework.
4. **Calm-keeping conversational support** — reassuring voice interaction with first-aid guidance while help is on the way. Guardian stays on the line.
5. **Location-aware ambulance dispatch** — nearest available unit assigned using Toronto Paramedic Services open data and ambulance station locations.
6. **Wearable vitals integration** — live heart rate, SpO₂, and pulse from Fitbit / Google Health feed into triage scoring and the paramedic handoff.

---

## System Triggers

Guardian decides when to engage based on a fusion of signals:

- **Voice** — direct address ("Hey Guardian…")
- **Conversation patterns** — distress phrases, confusion markers, sudden silence, slurred speech
- **Biometric sensors** — heart rate anomalies vs. personal baseline, SpO₂ drops, pulse irregularities
- **Activity rhythm** — deviation from the home's normal patterns of life (no kettle, no footsteps, no music past wake-up)

---

## Demo Scenarios

These are the scenarios we will demo at the hackathon. Each one exercises a different combination of Guardian's modes and features.

### 1. The Fall — Active Mode + Emergency Dispatch *(headline demo)*
**Persona:** 70-year-old woman, lives alone, known heart condition.
**Situation:** In the middle of the night she falls and breaks her hip. She cannot walk or reach a phone.
**Guardian response:**
- Detects the fall (audio cue + wearable accelerometer + her voice calling out).
- Dispatches 911 with her exact medical history, medications, and live vitals.
- Calls her emergency contact.
- Stays in conversation with her — calming her, taking notes, telling her how far away the ambulance is.

### 2. The Slow-Burn Symptom — Passive Continuity Across Days
**Persona:** 70-year-old man, no known conditions.
**Situation:** He mentions to Guardian that his left arm has been hurting for a few days. Guardian explains possible causes conversationally.
**Why this matters:** Days later, if he has a heart attack, Guardian *already knows* about the arm pain and shares that context with paramedics — turning a vague symptom into a critical clue.

### 3. The Confused Voice — Passive Distress Detection
**Persona:** Older adult with early cognitive decline.
**Trigger phrases:** "I don't remember," "I fell," "Who are you?", repeated confusion.
**Guardian response:** Soft check-in, light verbal assessment, escalation to caregiver or 911 if responses are off.

### 4. "Guardian, I'm Scared" — Active Reassurance
**Persona:** Anyone, any age.
**Situation:** Patient verbally reaches out — frightened, disoriented, or unsure what happened.
**Guardian response:** Asks simple grounding questions, validates feelings, monitors vitals during the conversation, escalates only if needed.

### 5. Memory Recap — Alzheimer's / Dementia Support
**Persona:** Patient with mild-to-moderate dementia.
**Asks:** "Did I take my medicine?" "What happened this week?" "Did my daughter call?"
**Guardian response:** Answers from local logs and generates a simple weekly summary in plain language.

### 6. Medication Reminder & Adherence
**Persona:** Any patient on a regular regimen.
**Guardian response:** Notices missed medication times or confusion about pills. Gently reminds the patient, confirms intake verbally, and logs adherence. Flags repeated misses to a caregiver.

### 7. Vitamin Schedule + UI — The Healthy User
**Persona:** Margaret-style or younger healthy adult who wants a smarter daily routine.
**Demo:** 40-year-old woman with no conditions sets up a vitamin schedule by voice. Guardian reminds her on schedule and surfaces intake history in a simple UI dashboard.

### 8. Margaret, 64 — Complex Daily Regimen
**Medical background:** Mild hypertension, osteoporosis risk, early Type 2 diabetes, mild arthritis, cholesterol monitoring.
**What Guardian does daily:**
- Times blood-pressure meds precisely (consistency is critical).
- Schedules Calcium + Vitamin D, B12, Omega-3, Magnesium, Iron, Metformin around meals.
- Prompts home BP and blood-glucose readings at consistent times, logs them, and flags trends outside her target range.
- Runs a gentle mood and short memory check-in.

### 9. Sarah, 30 — Active Lifestyle, Smart Timing
**Medical background:** Healthy, mild iron deficiency, active.
**What Guardian does:**
- Times iron every other day with food, **avoiding calcium-rich meals** (interaction-aware scheduling).
- Adjusts reminders for workout days vs. rest days (creatine + protein on training days, magnesium on rest days).
- Daily mood + energy log, flags multi-day low-mood patterns.
- Hydration nudges, especially on workout days.

### 10. The Silent Morning — Absence-of-Pattern Detection
**Situation:** A person living alone has a predictable morning rhythm — kettle, footsteps, music. One day the house is unusually silent past their normal wake-up window.
**Guardian response:** Does **not** scream emergency. Instead, gentle subtle escalation: soft voice check-in → lights in the room → louder prompts → caregiver alert → 911. Reacts to the *absence* of a life pattern, not a single signal.

### 11. Cardiac Baseline Deviation
**Trigger:** Wearable shows heart rate significantly above or below the patient's historical personal baseline.
**Guardian response:** Conversational check-in to rule out exertion / caffeine / anxiety, escalates if unexplained or paired with other symptoms.

---

## Additional Scenarios We Want to Cover

Beyond medical emergencies, Guardian extends to safeguard mental and social wellbeing.

### 12. Court-Ordered Behavioral Monitoring (Anger Management)
For individuals court-mandated to monitor anger or behavior. Guardian provides training cues and reinforcement, and calls emergency services at early signs of an outburst.

### 13. Young Adult with Depression
Daily check-ins, encouragement, addiction-relapse support, early-warning detection of suicidal ideation, connection to crisis resources.

### 14. Domestic Conflict / Broken Marriage
Discreet monitoring with consent, generates summary notes for couples counselors, escalates to emergency services at early signs of domestic violence.

### 15. Child with a Careless Caregiver
Monitors interactions, reminds the caregiver of necessary steps (feeding, medication, supervision), escalates to authorities on signs of misconduct.

---

## Suggested Scenarios (Recommended Additions)

These extend the same "local LLM helps life be easier, healthier, safer" premise and reuse the same hardware, audio, and wearable stack.

### Acute Detection
- **Stroke FAST exam.** When speech becomes slurred mid-conversation or the patient describes facial drooping, Guardian runs a verbal Face/Arms/Speech/Time check and dispatches immediately — every minute saved preserves brain tissue.
- **Anaphylaxis / severe allergic reaction.** Detects coughing fits, wheezing, throat-tightness language ("I can't breathe"), guides EpiPen use, calls 911 with the known allergy from the local profile.
- **Hypoglycemia in diabetics.** Listens for slurred speech, irritability, confusion — classic low-blood-sugar signs — and prompts a glucose check + fast carbs before the patient passes out.
- **Seizure detection & logging.** Audio vocalization patterns combined with wearable accelerometer data; logs duration and frequency for the neurologist.
- **Pediatric asthma attack.** Detects wheezing and short-breath language in children, coaches inhaler use, escalates if no improvement in minutes.
- **Choking detection.** Distinctive cough-then-silence acoustic pattern; Guardian gives Heimlich instructions to anyone else in the room, calls 911 if the patient cannot respond.

### Chronic & Preventive
- **Post-operative recovery coach.** After hospital discharge, Guardian guides daily wound checks, mobility milestones, watches conversational cues for fever or infection.
- **Cancer treatment side-effect monitor.** Tracks nausea, fatigue, appetite during chemo; flags neutropenic fevers and dehydration early.
- **Chronic pain journaling.** Voice-based daily pain diary (location, intensity, triggers), generates trend reports for clinic visits.
- **Sleep apnea & sleep quality.** Passive audio analysis of snoring and breathing gaps; correlates with next-morning mood/fatigue check-ins.
- **Cognitive decline early detection.** Longitudinal tracking of vocabulary diversity, response latency, and informal memory probes — surfaces early dementia signals to the PCP years before clinical diagnosis.
- **Fall-risk assessment.** Listens for unstable gait sounds (shuffling, stumbles), recommends PT or balance exercises *before* the first fall.
- **Hydration & heat-stroke prevention.** For the elderly during heat waves; monitors AC use, prompts water intake, escalates if confusion is detected.

### Specialized Personas
- **Pregnancy companion.** Week-by-week guidance, prenatal vitamin scheduling, vigilance for warning signs (severe headache, vision changes, decreased fetal movement language cues).
- **PTSD nightmare intervention.** Detects panic vocalizations during sleep, gentle wake-up, guided grounding exercises.
- **Eating disorder recovery.** Mealtime behavior patterns, body-image language tracking, supportive intervention.
- **Substance abuse relapse prevention.** Intoxication-pattern detection, isolation behavior cues, sponsor/hotline connection.
- **Palliative / end-of-life comfort.** Comfort conversation for hospice patients, pain monitoring, family-presence prompts, advance-directive awareness.
- **Caregiver burnout detection.** For family caregivers themselves — detects stress patterns in their voice and suggests respite resources.

### Daily Quality-of-Life
- **Telehealth visit prep & recap.** Organizes symptoms before a doctor's visit, then summarizes the doctor's advice in plain language afterward.
- **Vaccine & screening reminders.** Personalized health-maintenance schedule (flu shot, mammogram, colonoscopy) based on age and risk profile.
- **Smart-home safety integration.** Stove left on, fridge door open, faucet running too long → conversational check-in before automatic shutoff.
- **Bathroom-specific monitoring.** Most home falls happen in the bathroom; specialized acoustic profile for that room (water running too long, no movement, impact sounds).
- **Multilingual 911 interpretation.** When paramedics arrive, Guardian acts as a live interpreter for non-English speakers — leveraging Toronto's 911 language-interpretation dataset.
- **Hearing-impaired emergency alerts.** Visual / haptic alerts for deaf or hard-of-hearing users when smoke alarms, doorbells, or emergency sirens fire nearby.

---

## Stretch Goals

### Wi-Fi Pose Detection (Camera-free Movement Sensing)
Use changes in ambient Wi-Fi signal reflections to identify whether the patient is standing, sitting, lying down, walking normally, or falling — **without cameras and without sending video data anywhere**. Movement awareness with privacy preserved.

### Fitbit / Google Health Profile Updates
Continuously update the patient's local health profile with heart rate, SpO₂, sleep quality, activity level, and unusual vital trends. The longitudinal record sharpens triage accuracy, medication-reminder timing, daily check-ins, and the paramedic handoff report.

---

## Data Sources

**Toronto Open Data:**
- [Paramedic Services Incident Data](https://open.toronto.ca/dataset/paramedic-services-incident-data/)
- [Ambulance Station Locations](https://open.toronto.ca/dataset/ambulance-station-locations/)
- [Paramedic Services 911 Language Interpretation](https://open.toronto.ca/dataset/paramedic-services-911-language-interpretation/)
- [Specialized Patient Transports by Paramedics](https://open.toronto.ca/dataset/specialized-patient-transports-by-paramedics/)

**Synthetic patient data:** Generated to represent the scenarios above, so the system can be exercised end-to-end without exposing any real patient information.

---

## Privacy & Compliance

- **Fully local inference.** No cloud API calls. Conversations, medical records, and vitals never leave the device.
- **PHIPA-compliant design.** Built for Ontario's Personal Health Information Protection Act from day one.
- **No cameras required** in the default deployment. Audio + wearable + (optionally) Wi-Fi pose only.
- **User-owned data.** The patient can review, export, or delete their on-device record at any time.

---

## Hardware & Deployment Constraints

Guardian is designed for an in-home deployment, with these design limitations in mind:

- **Indoor deployment first.** Outdoor extensions face limits in weight, power, size, and privacy.
- **Always-on, low-latency local inference** on NVIDIA DGX Spark (GB10 Grace Blackwell Superchip).
- **Resilient to network outage** — emergency dispatch falls back to cellular if home internet is down.

---

## Knowledge Base Architecture

Guardian's local knowledge is layered:

- **Introductory interview** — onboarding session that builds the initial patient profile.
- **Patient database** — conditions, allergies, medications, baseline vitals.
- **Contact graph** — emergency contact, family members, family doctor, nearest emergency services.
- **General medical knowledge base** — first aid, triage protocols, drug interactions.
- **Specialized knowledge base** — patient-specific guidance for their conditions.
