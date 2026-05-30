# Guardian Watch (Wear OS)

A standalone **Galaxy Watch / Wear OS** app that records the wearer's vitals on
the watch (working **offline**), then pushes them to the Guardian backend over
the **local network every minute**. It replaces the Polar-H10-over-BLE path from
the planning docs with a self-contained smartwatch that needs no phone in the
loop.

```
┌──────────────────────── Galaxy Watch ────────────────────────┐
│  Health Services API                                          │
│    • heart rate   (MeasureClient, live)                       │
│    • steps        (PassiveMonitoring, daily)                  │
│    • calories     (PassiveMonitoring, daily)                  │
│            │                                                  │
│            ▼                                                  │
│      Room database  ── offline-first buffer (sent flag) ──┐   │
│            │                                              │   │
│            ▼                                              │   │
│   MonitoringService (foreground)                          │   │
│     every 60s: POST unsent readings ──────────────────────┼─▶ │ Wi-Fi / LAN
│   SyncWorker (WorkManager, ~15m backstop) ────────────────┘   │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼
                 Guardian backend  (FastAPI, :8000)
                   POST /vitals/ingest   →  Vital table
                   GET  /vitals          ←  frontend Vitals page
```

## Why these choices

- **Direct HTTP over the LAN**, not a phone Data-Layer relay. A Wi-Fi Galaxy
  Watch reaches the backend itself, so no companion phone app is required. (If
  you ever need the phone-relay path, the watch readings are already in Room —
  swap the uploader for a `MessageClient`/`DataClient` sender.)
- **1-minute cadence lives in a foreground service.** Android's `WorkManager`
  has a **15-minute minimum** periodic interval, so the real per-minute loop
  runs in `MonitoringService`; `SyncWorker` is only a backstop that flushes a
  backlog if the service was killed.
- **Offline-first.** Every reading is written to Room with `sent = 0` and only
  marked `sent = 1` after the backend confirms receipt. Drop Wi-Fi, keep
  recording; readings upload on the next successful sync.

## Project layout

```
watch/
├── app/src/main/
│   ├── AndroidManifest.xml
│   ├── java/com/guardian/watch/
│   │   ├── GuardianWatchApp.kt          # Application + DI entry, enqueues backstop worker
│   │   ├── MainActivity.kt              # Compose UI host + runtime permissions
│   │   ├── di/GuardianGraph.kt          # tiny manual dependency graph (no Hilt)
│   │   ├── data/
│   │   │   ├── local/                   # Room entity, DAO, database
│   │   │   ├── remote/                  # Retrofit API, DTOs, ApiFactory
│   │   │   ├── repository/              # VitalsRepository (offline-first sync)
│   │   │   └── settings/                # DataStore (backend URL, patient id)
│   │   ├── health/
│   │   │   ├── HealthServicesManager.kt # HR (MeasureClient) + passive register
│   │   │   └── GuardianPassiveService.kt# steps/calories background delivery
│   │   ├── service/MonitoringService.kt # foreground: HR capture + 60s upload loop
│   │   ├── sync/SyncWorker.kt           # WorkManager backstop
│   │   └── ui/                          # Wear Compose screens + ViewModel
│   └── res/                             # icons (vector), strings, network config
├── build.gradle.kts, settings.gradle.kts, gradle/  # Kotlin-DSL + version catalog
└── README.md
```

## Prerequisites

- **Android Studio** (Ladybug or newer).
- A **Wear OS 3+ device or emulator** (Galaxy Watch 4/5/6/7, or a Wear OS
  emulator image). Heart rate works on real hardware; on the emulator use the
  **Extended controls → Virtual sensors / Health** panel to feed a synthetic HR.
- The **Guardian backend running** and reachable on your LAN (`make run` /
  `guardian-backend`; it already binds `0.0.0.0:8000`).

## Build & run

1. **Open the `watch/` folder** in Android Studio (open it as its own project,
   not the repo root). Let it sync — this also generates the Gradle wrapper jar
   (see `gradle/wrapper/README.md`).
2. Pick your watch device/emulator and **Run** the `app` configuration.
3. On first launch, grant the **Body sensors**, **Physical activity**, and
   **Notifications** permissions.
4. Open **Settings** on the watch and set the **Backend URL** to your dev
   machine, e.g. `http://192.168.1.50:8000`, and the **Patient ID** (default
   `1`, matching the frontend's `DEFAULT_PATIENT_ID`).
5. Toggle **Monitoring** on. Within a minute you'll see the unsent count drain
   and "Up to date · just now"; readings appear on the frontend **Vitals** page.

### Finding your backend's LAN IP

On the machine running the backend:

```powershell
ipconfig   # Windows — use the IPv4 address of your Wi-Fi adapter
```

The watch and that machine must be on the **same network**. Make sure the
backend port (`8000`) is allowed through the host firewall.

### Baking in a default URL (optional)

To avoid typing the URL on the watch, set it at build time in
`watch/gradle.properties` (or `local.properties`):

```properties
guardian.baseUrl=http://192.168.1.50:8000
```

It becomes `BuildConfig.GUARDIAN_DEFAULT_BASE_URL` and is used until overridden
in on-watch Settings.

## Backend API contract

This module ships with its receiving endpoint, added to the FastAPI backend:

**`POST /vitals/ingest`** — batch upload (what the watch calls each minute):

```json
{
  "patient_id": 1,
  "device": "galaxy_watch",
  "readings": [
    { "kind": "hr",       "value": 72.0, "ts": "2026-05-29T12:00:00Z" },
    { "kind": "steps",    "value": 1234, "ts": "2026-05-29T12:01:00Z" },
    { "kind": "calories", "value": 56.7, "ts": "2026-05-29T12:01:00Z" }
  ]
}
```

Response: `{ "accepted": 3 }`. Each reading becomes a row in the relational
`Vital(patient_id, ts, kind, value, source)` table, with `source = device`.

**`GET /vitals?kind=hr&since=24h&patient_id=1`** — read-back used by the
frontend Vitals page and for verification:

```json
{ "kind": "hr", "points": [ { "ts": "2026-05-29T12:00:00", "value": 72.0 } ] }
```

`since` accepts `30s`, `60m`, `24h`, `7d` (defaults to `24h`).

## What's captured

| Metric    | `kind`     | Source                                   |
|-----------|------------|------------------------------------------|
| Heart rate| `hr`       | `MeasureClient` (live, while monitoring) |
| Steps     | `steps`    | `PassiveMonitoring` `STEPS_DAILY`        |
| Calories  | `calories` | `PassiveMonitoring` `CALORIES_DAILY`     |

The `kind` strings line up with the backend's `Vital.kind` vocabulary, so HR
flows straight onto the existing Vitals chart. Steps/calories are stored and
queryable; extend the frontend if you want to chart them too.

## Permissions

| Permission                       | Why                                            |
|----------------------------------|------------------------------------------------|
| `BODY_SENSORS`                   | Heart rate                                     |
| `ACTIVITY_RECOGNITION`           | Steps / calories                               |
| `POST_NOTIFICATIONS` (API 33+)   | The ongoing foreground-service notification    |
| `FOREGROUND_SERVICE[_HEALTH]`    | Run the health monitoring service              |
| `INTERNET`, `ACCESS_NETWORK_STATE` | Upload to the backend                        |

## Notes & limitations

- **Cleartext HTTP.** The app permits plain `http://` to the LAN backend via
  `res/xml/network_security_config.xml`. For production, serve the backend over
  HTTPS and tighten that config.
- **Background heart rate.** HR is captured while the foreground service runs.
  For always-on passive HR in the background you'd add `BODY_SENSORS_BACKGROUND`
  (declared in the manifest) to the passive `setDataTypes` and request it
  separately — left out here to keep the permission flow simple.
- **Battery.** Continuous HR + a 60s network loop is intentionally aggressive
  for a monitoring use case. Loosen `SYNC_INTERVAL_MS` in `MonitoringService`
  if you want to trade latency for battery.
- **Dependency versions** are pinned in `gradle/libs.versions.toml`
  (`health-services-client` is `1.1.0-alpha05`); bump them there in one place.
```
