# Guardian Demo — Toronto Open Data Reference (team-facing)

**What this file is.** A single index of the **relational** data (Toronto Open
Data) Guardian uses in the demo, with links, what each dataset gives us, and how
it's seeded. This is the *known-source* half of Guardian's data.

**What this file is NOT.** It is **not** part of any persona's vector record and
is **not** fed to the agent. The persona docs in `personas/<name>/` are pure
patient data — they deliberately contain **no dataset names, no tool names, and
no "use this data here" hints**. The mapping from a person's facts to a probable
dataset lives *here*, for us, so the agent is never rail-roaded down one path.
Matthew and Sarah are people; many situations could happen to either of them,
and the agent should reason over their facts and the live data — not a script.

All datasets below are **seeded locally** (downloaded snapshot committed to
`data/`, queried with the same local haversine/filter pattern as the existing
`data/cool_spaces.json` + `backend/tools/civic.py`). No live API calls in the demo.

---

## Two halves of Guardian's data

| Half | Source | Where it lives | How recalled |
|---|---|---|---|
| 🟦 **Relational** | Toronto Open Data (this file) | `data/*.json` (seeded snapshots) | tabular lookup / haversine / filter |
| 🟪 **Vector** | Onboarding extraction (interview + uploaded PDFs) | `personas/<name>/*.md` | semantic recall via `recall_history` |

---

## Scenario 1 — Matthew (emergency path)

| Dataset | Link | What it gives the demo | Seeding |
|---|---|---|---|
| **Ambulance Station Locations** | [open.toronto.ca/dataset/ambulance-station-locations](https://open.toronto.ca/dataset/ambulance-station-locations/) | Station coordinates → haversine to nearest station = the map anchor / best-case distance. | snapshot → `data/` |
| **Paramedic Services Incident Data** | [open.toronto.ca/dataset/paramedic-services-incident-data](https://open.toronto.ca/dataset/paramedic-services-incident-data/) | Incident type, priority, units, FSA → local **load context** by area. (No per-incident response time — so it cannot give a true live ETA.) | snapshot → `data/` |
| **Automated External Defibrillator (AED) Locations** | [open.toronto.ca/dataset/automated-external-defibrillator-aed-locations](https://open.toronto.ca/dataset/automated-external-defibrillator-aed-locations/) | Public AED coordinates + access notes → haversine to nearest AED for an on-site responder. | snapshot → `data/` |

**ETA is an honest aggregate, not a live number.** The quoted ETA combines:
(1) nearest-station distance, (2) area load context, and (3) a **published TPS
benchmark** (~8 min average / ~79% within the 8-min target, 2024 Auditor General).
The demo states plainly that this is an estimate, not a live dispatch time.

## Scenario 2 — Sarah (engagement path)

| Dataset | Link | What it gives the demo | Seeding |
|---|---|---|---|
| **Registered Programs and Drop-in Courses** | [open.toronto.ca/dataset/registered-programs-and-drop-in-courses-offering](https://open.toronto.ca/dataset/registered-programs-and-drop-in-courses-offering/) | The class catalogue (e.g. watercolour/art), with centre, time, location. | snapshot → `data/` |
| **Parks and Recreation Facilities** | [open.toronto.ca/dataset/parks-and-recreation-facilities](https://open.toronto.ca/dataset/parks-and-recreation-facilities/) | Facility **accessibility** attributes (step-free access, Wheel-Trans access) → filter to classes she can actually attend. | snapshot → `data/` |
| **TTC Wheel-Trans** | [open.toronto.ca/dataset/ttc-wheel-trans-origin-and-destination-survey-data](https://open.toronto.ca/dataset/ttc-wheel-trans-origin-and-destination-survey-data/) | Accessible door-to-door transit context → basis for the ride-booking beat. | snapshot → `data/` |
| **Washroom Facilities** (accessible parks/washrooms) | [open.toronto.ca/dataset/washroom-facilities](https://open.toronto.ca/dataset/washroom-facilities/) | Accessible outdoor-outing fallback (a park alternative to a class). | snapshot → `data/` |

---

## Interest → probable-dataset map (for us, not the agent)

A convenience for building/scripting the demo. The agent does **not** read this;
it reasons from each persona's facts at runtime.

| Persona fact (from their record) | Probable relational dataset |
|---|---|
| Cardiac history; high-acuity event | Ambulance Stations · Paramedic Incidents · AED Locations |
| Likes painting / classes; wheelchair user | Registered Programs · Parks & Rec Facilities (accessibility) |
| Needs accessible transport | TTC Wheel-Trans |
| Wants a low-effort outdoor outing | Parks · Accessible Washrooms |
| Heat/cold or "needs a cool place" | existing `data/cool_spaces.json` (`find_cool_space`) |

> **Note on freshness.** Slugs/links above are verified for Registered Programs,
> Parks & Rec Facilities, and AED Locations. Ambulance Stations, Paramedic
> Incident Data, Wheel-Trans, and Washrooms are referenced at the portal level —
> confirm the exact slug and last-updated date when you pull the snapshot.
