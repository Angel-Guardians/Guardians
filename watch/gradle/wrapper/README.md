# Gradle wrapper

`gradle-wrapper.jar` is a binary and isn't checked in here. It is generated
automatically when you:

- **Open `watch/` in Android Studio** (recommended) — the IDE syncs Gradle and
  creates the jar for you, or
- run `gradle wrapper --gradle-version 8.7` from the `watch/` directory if you
  have a system Gradle installed.

After that, `./gradlew` (or `gradlew.bat` on Windows) works as usual.
