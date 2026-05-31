# Guardian — Demo Scenario Walkthroughs (grounded in the repo)

Two scenarios, step by step. Every step names the **real** pieces from
`temp/Guardians`: the event type (`backend/events/types.py`), the severity tier
(`SeverityTier` in `backend/db/models.py`), the router rule
(`backend/orchestrator/router.py`), the sub-agent, and the exact tool
(`backend/tools/*`) with its inputs and outputs.

The architecture path is always the same (the event-driven design in
`backend/orchestrator/`):

```
watch / sensors → GuardianEvent on the bus
      → RiskClassifier.classify(event)  → sets event.severity (one tier)
      → Router.route(event)             → one sub-agent (never parallel)
      → sub-agent tool-calling loop      → a subset of the tool registry
      → tts reply + Event Log + Incident
```

> **Scope of this doc (decided 2026-05-31):** this is a spec for building the
> **demo + UI + video** for submission. **No code changes** — the team is
> building the real tools in parallel. Where a step needs something the code
> doesn't have yet, it's marked **`◇ NOT YET IN CODE`**: the demo *simulates*
> it truthfully now, and the team wires it later (the video can be re-cut then).
> A consolidated "not-yet-in-code" checklist for the team is at the bottom.
>
> **Demo personas (locked):** Scenario 1 = **Matthew** (replaces Eleanor in the
> seed); primary caregiver = **Sophie Tran, RN** (CPR/AED-trained, same building),
> daughter **Claire** (Ottawa) notified after. Scenario 2 = **Sarah Okafor**;
> primary support = her sister **Amara**.
>
> **911 in the demo:** the safety agent *conceptually* calls 911, but on camera
> we don't dial emergency services — we place the call to **a friend standing in
> for EMS**. The spoken line and UI still say "calling 911"; the actual dial
> target is a safe number.

---

## Scenario 1 — Matthew, 78, lives alone. Night fall → 911 + daughter.

**Persona:** **Matthew Brennan, 78**, lives alone at **200 Wellesley St E,
Toronto (M4X)** — a high-rise in St. James Town. Widower; daughter Claire is
in Ottawa (4.5h away). **Cardiac history: paroxysmal atrial fibrillation +
prior heart attack with stents + mild heart failure**, and he's **on a blood
thinner (apixaban)**. Wears the watch (GPS, HR, SpO₂, single-lead **ECG**,
accelerometer/fall-detection). **The watch is the only sensor — there is no
home microphone or fixed in-home sensor; everything is recorded and reported by
the watch.** Full profile lives in `demo/personas/matthew/` (the vector-store
source).

**Caregiver = Sophie Tran, RN** — a **Registered Nurse** who lives in the same
building, **trained in CPR + AED use**. She is the *primary* responder Guardian
calls (not the distant daughter), which is what makes the AED workflow real.

**Why the cardiac angle matters:** with AFib + prior MI, a nighttime fall isn't
just orthopedic — it can be **arrhythmic syncope** (a fast/irregular rhythm
making him faint), which carries a genuine **cardiac-arrest risk**. *That* is
why finding the nearest **public defibrillator (AED)** for the RN is meaningful;
without a cardiac risk, the AED beat would be pointless.

**Data legend (used in the "Data used" column):**
🟪 **VECTOR** = semantic recall over Matthew's profile docs (RAG via
`recall_history`). 🟦 **RELATIONAL** = Toronto Open Data tabular lookup
(haversine / filter). ⚪ **SENSOR** = live signals from the **watch — the only
sensor** (HR, SpO₂, single-lead ECG, accelerometer fall detection, GPS).

> **Where the two data halves come from (provenance).**
> 🟦 **RELATIONAL** data has a *known, public* source: Toronto Open Data
> (ambulance stations, paramedic incident data, AED locations), seeded locally —
> we can cite the exact dataset and download date.
> 🟪 **VECTOR** data has a *constructed-at-onboarding* source, which is why it
> feels less "official": each profile doc is the output of a one-time extraction
> step at installation — a guided voice **interview** (ASR → structured), scanned
> **document uploads** (med list, lab/ECG PDFs → OCR → normalize), and a
> **consent wizard**. Those docs are chunked, embedded, and recalled at runtime
> via `recall_history`. The full "how we got this data" layer lives in
> `personas/matthew/_manifest.md`, and every doc carries provenance frontmatter
> (`source_type` · `source_ref` · `captured_on` · `extraction_method` ·
> `confidence`). So when step 8 recalls Matthew's cardiac history, it is reading
> what the onboarding interview + uploaded 2021 discharge summary produced — not
> a live medical record.

**Tier path:** `tier_1_whisper` (idle) → `tier_4_call` (fall + abnormal rhythm).

| # | What happens | Sensors / Event | Data used | Classifier → Tier | Router → Agent | Tool calls (in order): input → output | What Guardian says | UI state |
|---|---|---|---|---|---|---|---|---|
| **1. Baseline** | 2:14am. Matthew asleep. Watch streams vitals; everything nominal, ECG in normal sinus rhythm. | `VitalSampleEvent(kind="hr", value=57)` streaming | ⚪ SENSOR | `tier_1_whisper` | (silent) | none | — (silent) | **Green.** "All quiet · HR 57 · sinus." |
| **2. Rhythm flares (the precursor)** | He wakes for the 2–3am bathroom trip. As he sits up, his watch ECG catches an **irregular, rapid rhythm** (AFib with rapid ventricular rate) — the near-faint precursor. | `VitalSampleEvent(kind="hr", value=142)`, ECG flag "irregularly irregular" | ⚪ SENSOR | `tier_2_nudge` (watching) | — | none | — | **Amber.** "Irregular rhythm detected." |
| **3. The fall** | Standing up, blood pressure drops on the arrhythmia → he nearly faints and falls. Accelerometer logs impact + orientation flip. | watch fall event (◇ note) | ⚪ SENSOR | — | — | none | — | Knob jumps. |
| **4. Corroboration** | Post-fall, all from the watch: motion goes flat (no recovery movement), HR still irregular ~135, SpO₂ dips. | `VitalSampleEvent(hr 135)`, `VitalSampleEvent(spo2 91)`, watch fall + no-motion flags | ⚪ SENSOR (watch only) | — | — | none | — | **Amber→Red.** "Possible fall — confirming." |
| **5. Risk classification** | Deterministic classifier: hard fall **+** non-response **+** abnormal rhythm → top tier, with a **cardiac flag**. | classifier reads events 2–4 | — | **`tier_4_call`** (cardiac) | — | none | — | Risk gauge maxes. |
| **6. Routing** | Fall event routes to safety. `RoutingDecisionEvent(routed_to="safety")`. | — | — | — | **safety** | none | — | Graph: Bus → Router → **Safety** lights. |
| **7. Safety speaks first (confirm window)** | Safety agent activates (`voice_profile="urgent"`). Holds the floor, gives Matthew ~8s to cancel a false alarm. | listens for reply | ⚪ SENSOR | — | safety | `tts_speak`: confirm prompt, then wait ~8s | "Matthew, I detected a fall and your heart rhythm looks off. Are you okay? Say *I'm okay* if you're fine." | **Red.** "Are you okay?" + 8s countdown. |
| **8. Recall who Matthew is** | No response. Before acting, the agent pulls his medical context so every downstream call is informed (anticoagulant flag, AFib, prior MI, RN Sophie, preferred hospital). | — | 🟪 **VECTOR** | — | safety | `recall_history(query="cardiac history, anticoagulation, emergency contacts", persona_id="matthew", k=4)` → `{notes:["AFib + prior MI + HFpEF","on apixaban (blood thinner)","caregiver Sophie Tran RN, AED-trained, same building","prefers St. Michael's Hospital"]}` | — (reasoning) | Side panel: "Profile recalled: cardiac, anticoagulated." |
| **9. Compute a real ETA** | The agent builds a defensible ETA from **two Toronto datasets + the published benchmark** (see ETA box below): nearest ambulance station gives the map anchor, the incident data gives local load, the benchmark gives the number. | — | 🟦 **RELATIONAL** (Ambulance Stations + Paramedic Incident Data) | — | safety | `estimate_ems_eta(lat=43.6672, lon=-79.3736, fsa="M4X")` → `{nearest_station_km:1.4, area_priority_load:"high", eta_minutes:8, basis:"TPS Code-4 benchmark"}` | — (reasoning) | Map pin + "Nearest station 1.4 km · ETA ~8 min". |
| **10. Call 911 (rich, vector-informed reason)** | Safety agent dials EMS. The `reason` string is built from the **vector recall** in step 8, so EMS hears the anticoagulation + cardiac flags. *(Demo: friend stands in for EMS; line/UI still say "911".)* | — | (uses 🟪 + 🟦 results) | — | safety | `call_911(reason="78yo male, witnessed fall + suspected arrhythmic syncope, AFib w/ rapid rate, prior MI, ON APIXABAN (anticoagulated), unresponsive ~10s", location="200 Wellesley St E, Apt 1407")` → `{service:"EMS", eta_minutes:8, status:"dispatched", call_id}` | "I'm calling 911 now — telling them you're on a blood thinner and your heart's in an abnormal rhythm." | "Calling 911…" → ✓ "EMS dispatched · ETA 8 min". |
| **11. Find nearest AED + send the RN** | Same activation, next tool. Because this is a possible cardiac arrest, the agent finds the **closest public defibrillator** and calls **Sophie (RN)**, telling her where to grab it — bridging the ~8-min gap. | — | 🟦 **RELATIONAL** (AED Locations, seeded) | — | safety | `find_nearest_aed(lat=43.6672, lon=-79.3736)` → `{name:"Wellesley Community Centre", address:"495 Sherbourne St", distance_m:420, access:"lobby"}` ; then `notify_caregiver(message="Matthew fell, suspected cardiac. Nearest AED: Wellesley CC lobby, 495 Sherbourne (~420m). EMS ETA 8 min.", contact="Sophie", phone="<book>")` → `{delivered:true, contact:"Sophie"}` | "Sophie, Matthew's had a possible cardiac fall. The nearest AED is in the Wellesley Centre lobby, 495 Sherbourne — please bring it. Paramedics are ~8 minutes out." | AED card + "Calling Sophie (RN)…" → ✓ "Sophie en route w/ AED". |
| **12. Reassure, notify daughter, monitor** | Agent closes with calm reassurance to Matthew, sends a status note to **Claire (daughter)**, opens an `Incident`, and keeps streaming vitals until EMS/ Sophie arrive, then de-escalates. | continued `VitalSampleEvent` stream on `incident_id`; emits `ToolInvocationEvent`×3 | 🟪 (contacts) | holds `tier_4_call` → steps down | safety | optional `notify_caregiver(contact="Claire", message="status update")`; repeat `tts_speak` | "Help is coming, Matthew — stay still. Sophie's almost there with a defibrillator and the ambulance is close. I've let Claire know." | **Red → Amber** on resolution. "Incident logged." |

> **ETA box — how the two emergency datasets combine (honest version).**
> A true per-patient ETA isn't public (dispatch depends on which unit is *free*,
> which is never open data). So `estimate_ems_eta` blends three real inputs:
> (1) 🟦 **Ambulance Station Locations** → haversine to nearest station = the
> map anchor / best-case distance; (2) 🟦 **Paramedic Incident Data** → filtered
> to Matthew's FSA (M4X) + high priority = local demand context (it has incident
> *type/priority/units/FSA* but **no per-call response time**); (3) the
> **published TPS benchmark** (~8 min average for top-acuity calls, met ~79% of
> the time per the 2024 Auditor General report) = the **number the agent
> quotes**. We say plainly that the quoted ETA is a published aggregate, not a
> live figure. Datasets are *seeded locally* (same pattern as `cool_spaces.json`).

> ◇ **NOT YET IN CODE — fall event entry.** The watch fall comes from the
> **accelerometer**, but `events/types.py` has no IMU fall event. Since the
> watch is the only sensor (no mic, so no `fall_sound` audio path), the team
> adds a small **`FallDetectedEvent`** + one router rule
> `("fall_detected","any","safety")`. Demo just shows it routing to safety.

> ◇ **NOT YET IN CODE — rhythm/ECG signal.** `VitalSampleEvent.kind` today is
> `hr|spo2|bp_*|glucose` — no rhythm/ECG classification. The "irregular rhythm"
> beat (step 2) needs an ECG/arrhythmia signal the team adds later. Demo
> simulates it. (The cardiac risk is real in Matthew's profile regardless.)

> ◇ **NOT YET IN CODE — safety tools + new AED/ETA tools.** Today
> `SafetyAgent.tool_names = ("call_person","find_cool_space")`. Team later binds
> `("call_911","notify_caregiver","call_person","find_nearest_aed","estimate_ems_eta")`.
> `call_911`/`notify_caregiver` already exist in `backend/tools/emergency.py`;
> `find_nearest_aed` + `estimate_ems_eta` are **new** (both follow the existing
> haversine pattern of `find_cool_space`). Demo simulates their I/O exactly.

> ◇ **NOT YET IN CODE — seeded datasets.** Three Toronto Open Data files are
> seeded locally for the demo: **AED Locations** (Paramedic Services, 2025),
> **Ambulance Station Locations**, **Paramedic Incident Data** (by FSA). Refresh
> cadence is labelled quarterly but the latest AED file is mid-2025, so in
> practice ~annual — fine, since we ship a seeded snapshot. Frame as *"seeded
> from Toronto's open datasets; production queries the live feed."*

---

## Scenario 2 — Sarah, 35, wheelchair user, isolated. Proactive engagement.

**Persona:** Sarah Okafor, 35, lives alone in a wheelchair-accessible apartment
(200 Sackville St, Regent Park · 43.6595, -79.3625 · FSA M5A). T10 paraplegia
(wheelchair user) + major depressive disorder (PHQ-9 = 14, moderate). Likes
watercolour painting and knitting. Primary support is her sister **Amara**.
Wears the watch (low activity, normal vitals) — **the only sensor.** Full
profile in `personas/sarah/` (same provenance-tagged extraction format as
Matthew; see `personas/sarah/_manifest.md`).

This is the **non-emergency** half of the story: Guardian as a companion that
*acts on her behalf*. One agent activation, a long sequence of tool calls.

**Data legend (same as Scenario 1):** 🟪 **VECTOR** = recall over Sarah's profile
docs via `recall_history`. 🟦 **RELATIONAL** = Toronto Open Data lookup. ⚪ **SENSOR**
= live watch signals (the only sensor: GPS, HR, SpO₂, accelerometer, tap).

**Toronto Open Data used (RELATIONAL, seeded locally):**
- 🟦 **Registered Programs and Drop-in Courses** — the painting/art class catalogue
  ([open.toronto.ca/dataset/registered-programs-and-drop-in-courses-offering](https://open.toronto.ca/dataset/registered-programs-and-drop-in-courses-offering/)).
- 🟦 **Parks and Recreation Facilities** — accessibility attributes (step-free access,
  Wheel-Trans access) to filter classes she can actually attend
  ([open.toronto.ca/dataset/parks-and-recreation-facilities](https://open.toronto.ca/dataset/parks-and-recreation-facilities/)).
- 🟦 **TTC Wheel-Trans** — accessible door-to-door transit, the basis for the ride booking.
- 🟦 **Parks & Washrooms (accessible)** — fallback for an outdoor-outing alternative.

> ◇ **NOT YET IN CODE — owner + four new tools (decided: companion owns it).**
> The booking flow needs four tools that don't exist yet. The **companion**
> agent owns the whole flow (one activation, sequential tool calls). For the
> real system the team adds and binds: `find_recreation_class`, `book_class`,
> `book_paratransit`, `update_calendar` (signatures at the bottom). The demo
> simulates each tool's input/output exactly as shown. No code change now.

> ◇ **NOT YET IN CODE — morning check-in trigger (decided: add the rule).**
> Today `scheduled_reminder → reminder` and `pattern_absence → safety`, so
> neither lands on the companion. For the real system the team adds a
> `scheduled_checkin → companion` routing rule, and the companion reads the
> 6-days-home `PatternAbsenceEvent` as context via `recall_history`. The demo
> shows the morning check-in landing on the companion. No code change now.

**Tier path:** all `tier_1_whisper` / `tier_2_nudge` — never an alarm.

| # | What happens | Sensors / Event | Data used | Classifier → Tier | Router → Agent | Tool calls (in order): input → output | What Guardian says | UI state |
|---|---|---|---|---|---|---|---|---|
| **1. Context builds (days before)** | Over ~6 days the watch's GPS shows Sarah hasn't left home; a background job logs it quietly. No interruption. | `PatternAbsenceEvent(expected="leaves_home", minutes_overdue=8640)` from watch GPS | ⚪ SENSOR | `tier_2_nudge` | (logged, not spoken) | none | — (silent) | Calm. A soft "isolation" flag stored. |
| **2. Morning check-in fires** | 8:00am. The daily check-in event hits the bus. | `ScheduledReminderEvent` / `scheduled_checkin` (◇ not-in-code rule) | — | `tier_1_whisper` | **companion** | none | — | **Warm/green.** "Good morning." |
| **3. Greeting + meds reminder** | Companion holds the floor gently and starts with her medication. | — | 🟪 VECTOR (meds doc) | — | companion | `get_schedule()` → `{due:[{med:"Sertraline 50mg", at:"08:00"}]}` ; `get_medications()` for detail (both resolve the default patient) | "Good morning, Sarah. It's time for your Sertraline — the 50 milligram one with breakfast." | Med card appears. |
| **4. She takes it / confirms** | Sarah taps the watch or says "done." | `TapConfirmedEvent(confirms="reminder:sertraline")` | ⚪ SENSOR | — | companion | `mark_med_taken(medication="Sertraline")` → `{logged:true, at:"08:02"}` | "Nice. That's logged." | Med card ✓. |
| **5. Notice the isolation** | Companion recalls recent context and sees the 6-day signal + her interests + last mood. Speaks with care, not alarm. | — | 🟪 VECTOR | — | companion | `recall_history(query="recent outings, mood, interests", persona_id="sarah", k=3)` → `{notes:["home 6 days", "enjoys watercolour & knitting", "PHQ-9 14 / low mood last screen"]}` | "I noticed you've been home about six days. That's a long stretch — how are you feeling?" | Gentle prompt; no red. |
| **6. Suggest something she likes** | Grounded in her own interests from `recall_history`, not generic. | 🟪 VECTOR | — | — | companion | (uses step-5 result) | "I remember you like painting. Want me to find a beginner-friendly class nearby — something accessible?" | Suggestion chip: "Find a painting class". |
| **7. Find an accessible class** | She agrees. Companion searches the **Registered Programs / Drop-in** catalogue, joined to **Parks & Rec Facilities** accessibility attributes, filtered for step-free access + proximity. **New tool.** | — | 🟦 RELATIONAL | — | companion | `find_recreation_class(interest="painting", lat=43.6595, lon=-79.3625, accessible=true)` → `{class_id:"WC-204", title:"Watercolour Basics", centre:"Wellesley Community Centre", address:"495 Sherbourne St", time:"Today 11:00", accessible:true, distance_km:1.3}` | "There's *Watercolour Basics* at Wellesley Community Centre at 11, fully accessible, about 1.3 km away. Want me to book it?" | Class card with details. |
| **8. Book the class** | Sarah says yes. Companion reserves a spot (registers with the centre). **New tool** (may call `call_person` under the hood). | — | — | — | companion | `book_class(class_id="WC-204", persona_id="sarah")` → `{confirmation_id:"CLS-7781", status:"booked", time:"11:00"}` | "Booked — you're in for 11 o'clock." | Class card → ✓ "Booked · 11:00". |
| **9. Book accessible transport** | Same activation, next tool. Books **Wheel-Trans** (accessible door-to-door) to arrive before class. **New tool.** | — | 🟦 RELATIONAL (Wheel-Trans) | — | companion | `book_paratransit(pickup="200 Sackville St", dropoff="495 Sherbourne St", arrive_by="11:00", persona_id="sarah", accessible=true)` → `{trip_id:"WT-3392", pickup_time:"10:30", status:"confirmed"}` | "I've booked Wheel-Trans to pick you up at 10:30 so you arrive in time." | Transport card → ✓ "Pickup 10:30". |
| **10. Update her calendar** | Companion writes both events to Sarah's calendar. **New tool.** | — | — | — | companion | `update_calendar(persona_id="sarah", events=[{title:"Wheel-Trans pickup", at:"10:30"}, {title:"Watercolour Basics @ Wellesley CC", at:"11:00"}])` → `{updated:true, count:2}` | "It's all on your calendar." | Calendar shows two new entries. |
| **11. Confirm the whole plan** | Companion reads the plan back in one warm summary. | emits `AgentReplyEvent`, `ToolInvocationEvent` ×4 | — | — | companion | (logging) | "All set, Sarah: Wheel-Trans at 10:30, Watercolour at 11 at Wellesley Centre. I think you'll like it. I'll check in after." | Plan summary card. |
| **12. Optional supporter loop + follow-up** | Low-key: optionally let her sister know she's going out (consent permitting), and schedule a gentle post-class check-in. | optional `notify_caregiver(...)`; schedules next check-in | 🟪 VECTOR (consent + contact) | `tier_1_whisper` | companion | optional `notify_caregiver(message="Sarah's heading to a class at 11 — good day", contact="Amara")` → `{delivered:true}` | "Have a great time. I'll ask how it went tonight." | "Follow-up scheduled." |

---

## Convergence with the codebase (verified against the repo, 2026-05-31)

The walkthrough is written to **sit on the implementation's convergence line** —
it uses the real tool, event, agent and router names wherever they already exist,
and flags only what is genuinely missing. Verified against
`/temp/Guardians/backend`.

### Already implemented — the demo uses these exact names

- **Tools** (in `backend/tools/`, advertised via `ToolSpec.name`):
  `call_911(reason, location)`, `notify_caregiver(message, contact="Sophie", phone)`,
  `call_person(...)`, `find_cool_space(lat, lon)`, `log_vital(metric, value, unit)`,
  `get_medications()`, `get_schedule()`, `mark_med_taken(medication)`,
  `recall_history(query, persona_id="eleanor", k=3)`. (Note: `get_schedule`,
  `get_medications`, `mark_med_taken` take **no** `persona_id` — they resolve the
  default patient from the DB.)
- **Agent tool bindings** — `SafetyAgent.tool_names` already includes
  `("call_911", "notify_caregiver", "call_person", "find_cool_space")`; companion =
  `("recall_history", "find_cool_space")`; health, reminder, caregiver, behavior as
  in `backend/agents/`.
- **`recall_history`** is built (keyword backend now, optional pgvector via
  `MEMORY_BACKEND`). It reads `data/personas/<persona_id>.md` — **one markdown
  file per persona** — and defaults to `eleanor`.
- **Events** — `VitalSampleEvent`, `AudioEventDetectedEvent`, `PatternAbsenceEvent`,
  `ScheduledReminderEvent`, `TapConfirmedEvent`, etc. all exist in
  `backend/events/types.py` with the fields the walkthrough uses.
- **Router rules** — the `RULES` table in `backend/orchestrator/router.py` already
  has `pattern_absence → safety`, `scheduled_reminder → reminder`,
  `audio_event_detected(fall_sound|glass_break) → safety`, etc.

### Not yet in code — the demo simulates these truthfully

1. **Seed personas** — `data/personas.json` + `data/personas/` only contain
   **eleanor**. Add **Matthew** and **Sarah** as `data/personas/matthew.md` /
   `data/personas/sarah.md` (the recall backend reads one `.md` per persona) — the
   content is the `demo/personas/<name>/` record concatenated (or chunked for
   pgvector). Add their contacts (**Sophie Tran RN** + **Claire**; **Amara**).
2. **Orchestrator logic** — `Router.route()` and `RiskClassifier.classify()` are
   still `NotImplementedError` stubs; the `RULES`/tier tables exist but aren't
   walked yet. Tier values shown in the tables are the intended outputs.
3. **Fall event** — there is no accelerometer fall event. Today fall = mic-based
   `AudioEventDetectedEvent(event_class="fall_sound")`. Since the **watch is the
   only sensor (no mic)**, add a `FallDetectedEvent` + rule
   `("fall_detected","any","safety")` sourced from the accelerometer.
4. **Rhythm/ECG signal** — `VitalSampleEvent.kind` has only
   `hr|spo2|bp_*|glucose`; add an arrhythmia/ECG value so the "irregular rhythm"
   precursor is real.
5. **New Scenario-1 tools** — `find_nearest_aed`, `estimate_ems_eta`; then add them
   to `SafetyAgent.tool_names` (the other four are already bound).
6. **Scenario-2 tools** — add and bind to the **companion** agent:
   `find_recreation_class`, `book_class`, `book_paratransit`, `update_calendar`.
7. **Check-in trigger** — add a `scheduled_checkin → companion` routing rule so the
   morning check-in lands on the companion (today `scheduled_reminder → reminder`
   and `pattern_absence → safety`).
8. **Seeded Toronto Open Data files** (snapshot locally, like `cool_spaces.json`):
   AED Locations, Ambulance Station Locations, Paramedic Incident Data (by FSA),
   plus Scenario-2's recreation/facilities data. See `DEMO_DATASETS.md`.

Proposed signatures for the new tools (for the team, not built now):

- `find_nearest_aed(lat: float, lon: float) -> dict` — haversine over seeded
  **AED Locations** (Toronto Paramedic Services); returns nearest defibrillator.
- `estimate_ems_eta(lat: float, lon: float, fsa: str) -> dict` — nearest
  ambulance station (haversine) + FSA incident-load context + published TPS
  Code-4 benchmark; returns an honest ETA window.
- `find_recreation_class(interest: str, lat: float, lon: float, accessible: bool = True) -> dict`
  — searches Toronto Parks & Rec / community-centre data (same haversine pattern as `find_cool_space`).
- `book_class(class_id: str, persona_id: str) -> dict` — reserves a spot (stub or `call_person` to the centre).
- `book_paratransit(pickup: str, dropoff: str, arrive_by: str, persona_id: str, accessible: bool = True) -> dict`
  — Wheel-Trans booking (stub).
- `update_calendar(persona_id: str, events: list[dict]) -> dict` — writes events (stub / local store).

**Toronto Open Data sources (for the team to seed from):**
AED Locations · Ambulance Station Locations · Paramedic Services Incident Data ·
Registered Programs & Drop-In Courses · Parks and Recreation Facilities — all
Open Government Licence – Toronto.

These steps and tool I/O are the source of truth for the scripted demo and the
UI states. The video can be re-cut once the team lands the real tools.
