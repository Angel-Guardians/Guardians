# Guardian — Flutter app

A calm, friendly mobile/desktop client for the Guardian elder-care backend.
It mirrors the Next.js web frontend (`../frontend`) but is designed mobile‑first:
big touch targets, clear status colours, and a simple bottom‑nav layout.

> The phone screens an aging‑in‑place caregiver actually wants: at‑a‑glance
> vitals, one‑tap medication confirmation, a chat line to the Guardian agent,
> location, and lab‑report uploads.

## What's inside

| Tab / screen | What it does |
|---|---|
| **Home** | Greeting, fall alert banner, and summary cards (profile, vitals, meds, location, medical history). Pull to refresh. |
| **Vitals** | 24‑hour line charts for heart rate, SpO₂, blood pressure (systolic/diastolic), steps and calories. |
| **Talk** | Chat with the Guardian agent (`POST /turn/`). Shows the reply, which specialist routed it, and the tools it used. |
| **Care** | Today's medication schedule with one‑tap confirmation and a progress bar. |
| **Profile** | Full editor: basic info, conditions/allergies (chips), emergency contacts, medications, plus an emergency‑summary preview. Sticky save bar. |
| **Location** (from Home) | Latest GPS position, accuracy, "open in Google Maps", and 24 h history. |
| **Medical history** (from Home) | Pick & upload a lab‑results PDF, see the auto‑extracted values and profile updates, browse/delete past records. |

Extras in the header: backend **online/offline dot**, **patient switcher**
(when the backend has more than one patient), **light/dark/system theme**
toggle, and a **settings** dialog to change the backend URL.

## Prerequisites

- [Flutter SDK](https://docs.flutter.dev/get-started/install) 3.3 or newer
  (`flutter doctor` should be green for at least one target).
- The Guardian backend running and reachable (`../backend`, default port 8000).

## First‑time setup

This repo ships the Dart source (`lib/`), `pubspec.yaml` and config only — not
the generated native folders (`android/`, `ios/`, `web/`, …). Generate them
once. The snippet below backs up `lib/` + `pubspec.yaml` so `flutter create`
can't clobber them:

### Windows (PowerShell)

```powershell
cd D:\Projects\Guardians\flutter_frontend
Move-Item lib lib_bak; Move-Item pubspec.yaml pubspec_bak.yaml
flutter create . --project-name guardian_app --org com.guardians
Remove-Item lib -Recurse -Force
Move-Item lib_bak lib
Move-Item pubspec_bak.yaml pubspec.yaml -Force
flutter pub get
```

### macOS / Linux (bash)

```bash
cd flutter_frontend
mv lib lib_bak && mv pubspec.yaml pubspec_bak.yaml
flutter create . --project-name guardian_app --org com.guardians
rm -rf lib && mv lib_bak lib && mv pubspec_bak.yaml pubspec.yaml
flutter pub get
```

> If you prefer, you can instead run `flutter create` in an empty folder and
> copy this `lib/` + `pubspec.yaml` over the result.

## ⚠️ Two things that trip everyone up

### 1. The backend URL depends on where the app runs

A phone/emulator cannot see your computer's `localhost`. Default is the Android
emulator address; change it from the **gear icon → Backend connection** in the
app, or edit `lib/config.dart`:

| Target | Base URL |
|---|---|
| Android emulator | `http://10.0.2.2:8000` (default) |
| iOS simulator | `http://localhost:8000` |
| Real device (Wi‑Fi) | `http://<your-computer-LAN-IP>:8000` |
| Windows/macOS/Linux desktop | `http://localhost:8000` |
| Web (`flutter run -d chrome`) | `http://localhost:8000` (see CORS note) |

### 2. Android blocks plain HTTP by default

The backend is served over `http://` (not `https://`). Android 9+ blocks
cleartext traffic, so add this to the generated
`android/app/src/main/AndroidManifest.xml` on the `<application>` tag:

```xml
<application
    android:label="guardian_app"
    android:usesCleartextTraffic="true"
    ... >
```

(For production you'd use HTTPS or a scoped network‑security config instead.)

> **Web target:** the browser enforces CORS. If you run `-d chrome`, enable CORS
> on the FastAPI backend (`CORSMiddleware`) for the dev origin.

## Run

```bash
flutter run                 # pick a device when prompted
flutter run -d chrome       # web
flutter run -d windows      # desktop
```

## Project structure

```
lib/
  main.dart                 App shell + bottom navigation
  config.dart               Default backend URL & pref keys
  theme.dart                Material 3 theme (calm medical blue, light/dark)
  models/models.dart        JSON models mirroring the FastAPI backend
  services/api_client.dart  Typed HTTP client (mirrors frontend/src/lib/api.ts)
  state/app_state.dart      Provider ChangeNotifier: URL, patient, profile
  widgets/
    app_header.dart         Top bar: patient switcher, theme, settings
    common.dart             Cards, pills, avatars, metric tiles, empty states
    tag_input.dart          Chip editor for conditions/allergies
  screens/
    dashboard_screen.dart
    vitals_screen.dart
    chat_screen.dart
    reminders_screen.dart
    profile_screen.dart
    location_screen.dart
    medical_history_screen.dart
```

## Building the Android APK on this machine (important)

The debug APK builds successfully → `build/app/outputs/flutter-apk/app-debug.apk`.
Getting there required working around this machine's broken JVM networking (the
Gradle/Google/Maven CDNs are only reachable over the proxy-aware Windows stack;
the JVM's own DNS/IPv6 path fails with `UnknownHostException` / `Network is
unreachable`). All fixes are committed in the project:

| File | Workaround |
|------|-----------|
| `android/gradle/wrapper/gradle-wrapper.properties` | Points at a **local** `file:///C:/Android/gradle-9.1.0-all.zip` (the wrapper can't download from `services.gradle.org`). |
| `android/gradle.properties` | `org.gradle.jvmargs` adds `-Djdk.net.hosts.file=C:/Android/gradle-hosts.txt` (feeds the JVM working **IPv4** addresses) and `-Djava.net.preferIPv4Stack=true`. Also `kotlin.incremental=false` (incremental `.tab` caches get locked/corrupted here). |
| `android/build.gradle.kts` | Forces every plugin module to `compileSdk 36` (some plugins default to 34, which fails the AAR-metadata check). |
| `C:\Android\gradle-hosts.txt` | Static IPv4 host map, generated by `tools/refresh-gradle-hosts.ps1`. |

### Build / rebuild

```powershell
flutter build apk --debug      # or: flutter run  (device picked)
```

If a build fails with `UnknownHostException` or `Network is unreachable`, the CDN
IPs have drifted — regenerate the host map and rebuild:

```powershell
powershell -ExecutionPolicy Bypass -File tools\refresh-gradle-hosts.ps1
flutter build apk --debug
```

> These workarounds are specific to this dev machine's network. On a normal
> network none of them are needed — you could delete the `gradle-hosts.txt` /
> IPv4 JVM args and use the stock `services.gradle.org` wrapper URL.

### Install the APK

```powershell
flutter install                # to the connected device
# or copy build/app/outputs/flutter-apk/app-debug.apk to the phone and tap it
```

## Emergency calling (place a real call + speak the alert)

The app can dial a phone number over the device SIM and speak a received
message aloud:

- **Where the number comes from:** when a turn's reply includes a calling tool
  (`call_911`, `call_person`, `alert_emergency_contacts`, `notify_caregiver`),
  the app extracts the number and pops a **Call now** sheet on the Talk screen.
  You can also tap the green **call** icon next to any emergency contact in the
  Profile screen.
- **What it checks first:** `CallService.status()` verifies it's running on a
  phone (`Platform.isAndroid/iOS`), that telephony hardware exists, and that a
  **SIM is ready** (Android `TelephonyManager.simState`, read via a small
  `MethodChannel` in `MainActivity.kt`). If not, the **Call now** button is
  disabled and the reason is shown.
- **The call + voice:** with `CALL_PHONE` granted it dials directly via the SIM
  (otherwise it opens the dialer pre-filled). After a short connect delay it
  enables the speakerphone and speaks the message with `flutter_tts`.

> **Platform limitation (important):** Android/iOS do **not** let a third-party
> app inject audio into a live cellular voice stream. So the "voice" is played
> through the **loudspeaker**, not mixed into the call line. It works as a spoken
> alert when the phone is near the listener / on speaker. True in-call audio
> would require a telephony/VoIP backend (e.g. the backend's Twilio path).

Permissions added to `AndroidManifest.xml`: `CALL_PHONE`, `MODIFY_AUDIO_SETTINGS`
(and `INTERNET` + cleartext HTTP). This feature is Android-first; on iOS/web/desktop
it falls back to opening the dialer.

## Backend endpoints used

`GET /ping` · `GET /health` · `GET /patient/` · `GET|PUT /patient/{id}/profile` ·
`POST /turn/` · `GET /vitals?kind=&since=` · `GET /vitals/falls` ·
`GET /location` · `GET /medications` · `POST /events` (confirm intake) ·
`POST /lab-records/upload` · `GET /lab-records` · `GET|DELETE /lab-records/{id}`

Some endpoints (e.g. `/medications`) may still be TODO on the backend — the app
degrades gracefully and shows a friendly empty state rather than crashing.

## State & persistence

- **provider** for app state; **shared_preferences** persists the active
  patient, backend URL and theme.
- No login — single-caregiver demo app, patient chosen via the header switcher.
